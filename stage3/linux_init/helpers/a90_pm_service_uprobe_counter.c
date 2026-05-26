#define _GNU_SOURCE

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef __NR_bpf
#define __NR_bpf 280
#endif

#ifndef BPF_PSEUDO_MAP_FD
#define BPF_PSEUDO_MAP_FD 1
#endif

#ifndef PERF_FLAG_FD_CLOEXEC
#define PERF_FLAG_FD_CLOEXEC (1UL << 3)
#endif

#define A90_PM_UPROBE_COUNTER_VERSION "a90_pm_service_uprobe_counter v1076"
#define DEFAULT_TRACEFS_ROOT "/sys/kernel/tracing"
#define FALLBACK_TRACEFS_ROOT "/sys/kernel/debug/tracing"
#define DEFAULT_BINARY "/vendor/bin/pm-service"
#define DEFAULT_GROUP "a90pm1076"
#define MAX_EVENTS 16
#define MAX_LABEL_LEN 48
#define MAX_PATH_LEN 4096
#define MAX_LINE_LEN 8192

enum run_result {
    RUN_CHECK_ONLY = 0,
    RUN_PASS = 1,
    RUN_FAILED = 2,
};

struct event_spec {
    char label[MAX_LABEL_LEN];
    unsigned long long offset;
    long long id;
    int prog_fd;
    int perf_fd;
    uint64_t count;
    int registered;
    int attached;
};

static volatile sig_atomic_t stop_requested;
static pid_t child_pid = -1;

static uint64_t ptr_to_u64(const void *ptr) {
    return (uint64_t)(uintptr_t)ptr;
}

static long sys_bpf(enum bpf_cmd cmd, union bpf_attr *attr, unsigned int size) {
    return syscall(__NR_bpf, cmd, attr, size);
}

static long sys_perf_event_open(struct perf_event_attr *attr, pid_t pid, int cpu, int group_fd, unsigned long flags) {
    return syscall(__NR_perf_event_open, attr, pid, cpu, group_fd, flags);
}

static long long monotonic_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }
    return (long long)ts.tv_sec * 1000LL + (long long)(ts.tv_nsec / 1000000L);
}

static void on_signal(int signo) {
    (void)signo;
    stop_requested = 1;
}

static int file_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0;
}

static int write_text_file(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    size_t len = strlen(text);
    ssize_t written = write(fd, text, len);
    int saved = errno;
    close(fd);
    if (written < 0 || (size_t)written != len) {
        errno = written < 0 ? saved : EIO;
        return -1;
    }
    return 0;
}

static int read_int64_file(const char *path, long long *out_value) {
    char buf[64];
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    ssize_t got = read(fd, buf, sizeof(buf) - 1);
    int saved = errno;
    close(fd);
    if (got <= 0) {
        errno = got < 0 ? saved : EIO;
        return -1;
    }
    buf[got] = '\0';
    char *end = NULL;
    errno = 0;
    long long value = strtoll(buf, &end, 10);
    if (errno != 0 || end == buf || value <= 0) {
        errno = EINVAL;
        return -1;
    }
    *out_value = value;
    return 0;
}

static int create_counter_map(unsigned int event_count) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_type = BPF_MAP_TYPE_ARRAY;
    attr.key_size = sizeof(uint32_t);
    attr.value_size = sizeof(uint64_t);
    attr.max_entries = event_count;
    return (int)sys_bpf(BPF_MAP_CREATE, &attr, sizeof(attr));
}

static int lookup_counter(int map_fd, uint32_t index, uint64_t *value_out) {
    uint64_t value = 0;
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_fd = (uint32_t)map_fd;
    attr.key = ptr_to_u64(&index);
    attr.value = ptr_to_u64(&value);
    if (sys_bpf(BPF_MAP_LOOKUP_ELEM, &attr, sizeof(attr)) != 0) {
        return -1;
    }
    *value_out = value;
    return 0;
}

static int load_counter_prog(int map_fd, uint32_t index, int verbose) {
    struct bpf_insn program[] = {
        {
            .code = BPF_LD | BPF_DW | BPF_IMM,
            .dst_reg = BPF_REG_1,
            .src_reg = BPF_PSEUDO_MAP_FD,
            .off = 0,
            .imm = map_fd,
        },
        {
            .code = 0,
            .dst_reg = 0,
            .src_reg = 0,
            .off = 0,
            .imm = 0,
        },
        {
            .code = BPF_ALU64 | BPF_MOV | BPF_X,
            .dst_reg = BPF_REG_2,
            .src_reg = BPF_REG_10,
            .off = 0,
            .imm = 0,
        },
        {
            .code = BPF_ALU64 | BPF_ADD | BPF_K,
            .dst_reg = BPF_REG_2,
            .src_reg = 0,
            .off = 0,
            .imm = -4,
        },
        {
            .code = BPF_ST | BPF_MEM | BPF_W,
            .dst_reg = BPF_REG_10,
            .src_reg = 0,
            .off = -4,
            .imm = (int32_t)index,
        },
        {
            .code = BPF_JMP | BPF_CALL,
            .dst_reg = 0,
            .src_reg = 0,
            .off = 0,
            .imm = BPF_FUNC_map_lookup_elem,
        },
        {
            .code = BPF_JMP | BPF_JEQ | BPF_K,
            .dst_reg = BPF_REG_0,
            .src_reg = 0,
            .off = 2,
            .imm = 0,
        },
        {
            .code = BPF_ALU64 | BPF_MOV | BPF_K,
            .dst_reg = BPF_REG_1,
            .src_reg = 0,
            .off = 0,
            .imm = 1,
        },
        {
            .code = BPF_STX | BPF_XADD | BPF_DW,
            .dst_reg = BPF_REG_0,
            .src_reg = BPF_REG_1,
            .off = 0,
            .imm = 0,
        },
        {
            .code = BPF_ALU64 | BPF_MOV | BPF_K,
            .dst_reg = BPF_REG_0,
            .src_reg = 0,
            .off = 0,
            .imm = 0,
        },
        {
            .code = BPF_JMP | BPF_EXIT,
            .dst_reg = 0,
            .src_reg = 0,
            .off = 0,
            .imm = 0,
        },
    };
    char license[] = "GPL";
    char log_buffer[8192];
    memset(log_buffer, 0, sizeof(log_buffer));

    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.prog_type = BPF_PROG_TYPE_TRACEPOINT;
    attr.insn_cnt = (uint32_t)(sizeof(program) / sizeof(program[0]));
    attr.insns = ptr_to_u64(program);
    attr.license = ptr_to_u64(license);
    attr.log_buf = ptr_to_u64(log_buffer);
    attr.log_size = sizeof(log_buffer);
    attr.log_level = verbose ? 1 : 0;

    int fd = (int)sys_bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
    if (fd < 0 && verbose && log_buffer[0] != '\0') {
        fprintf(stderr, "bpf_log[%u]=%s\n", index, log_buffer);
    }
    return fd;
}

static int attach_tracepoint_prog(int prog_fd, long long event_id) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.type = PERF_TYPE_TRACEPOINT;
    attr.size = sizeof(attr);
    attr.config = (uint64_t)event_id;
    attr.sample_period = 1;
    attr.wakeup_events = 1;

    int perf_fd = (int)sys_perf_event_open(&attr, -1, 0, -1, PERF_FLAG_FD_CLOEXEC);
    if (perf_fd < 0) {
        return -1;
    }
    if (ioctl(perf_fd, PERF_EVENT_IOC_SET_BPF, prog_fd) != 0) {
        int saved = errno;
        close(perf_fd);
        errno = saved;
        return -1;
    }
    if (ioctl(perf_fd, PERF_EVENT_IOC_ENABLE, 0) != 0) {
        int saved = errno;
        close(perf_fd);
        errno = saved;
        return -1;
    }
    return perf_fd;
}

static int safe_label(const char *label) {
    size_t len = strlen(label);
    if (len == 0 || len >= MAX_LABEL_LEN) {
        return 0;
    }
    for (size_t i = 0; i < len; i++) {
        unsigned char ch = (unsigned char)label[i];
        if (!(isalnum(ch) || ch == '_')) {
            return 0;
        }
    }
    return 1;
}

static int parse_event_spec(const char *text, struct event_spec *spec) {
    const char *colon = strchr(text, ':');
    if (colon == NULL || colon == text || colon[1] == '\0') {
        errno = EINVAL;
        return -1;
    }
    size_t label_len = (size_t)(colon - text);
    if (label_len >= sizeof(spec->label)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memset(spec, 0, sizeof(*spec));
    memcpy(spec->label, text, label_len);
    spec->label[label_len] = '\0';
    if (!safe_label(spec->label)) {
        errno = EINVAL;
        return -1;
    }
    char *end = NULL;
    errno = 0;
    unsigned long long offset = strtoull(colon + 1, &end, 0);
    if (errno != 0 || end == colon + 1 || *end != '\0' || offset == 0 || (offset % 4ULL) != 0ULL) {
        errno = EINVAL;
        return -1;
    }
    spec->offset = offset;
    spec->id = -1;
    spec->prog_fd = -1;
    spec->perf_fd = -1;
    return 0;
}

static const char *pick_tracefs_root(const char *requested) {
    char path[MAX_PATH_LEN];
    if (requested != NULL && requested[0] != '\0') {
        return requested;
    }
    snprintf(path, sizeof(path), "%s/uprobe_events", DEFAULT_TRACEFS_ROOT);
    if (file_exists(path)) {
        return DEFAULT_TRACEFS_ROOT;
    }
    snprintf(path, sizeof(path), "%s/uprobe_events", FALLBACK_TRACEFS_ROOT);
    if (file_exists(path)) {
        return FALLBACK_TRACEFS_ROOT;
    }
    return DEFAULT_TRACEFS_ROOT;
}

static int remove_uprobe_event(const char *tracefs_root, const char *group, const char *label) {
    char path[MAX_PATH_LEN];
    char line[MAX_LINE_LEN];
    snprintf(path, sizeof(path), "%s/uprobe_events", tracefs_root);
    snprintf(line, sizeof(line), "-:%s/%s\n", group, label);
    return write_text_file(path, line);
}

static int register_uprobe_event(const char *tracefs_root,
                                 const char *group,
                                 const char *binary,
                                 struct event_spec *spec) {
    char path[MAX_PATH_LEN];
    char line[MAX_LINE_LEN];
    snprintf(path, sizeof(path), "%s/uprobe_events", tracefs_root);
    remove_uprobe_event(tracefs_root, group, spec->label);
    if (snprintf(line,
                 sizeof(line),
                 "p:%s/%s %s:0x%llx\n",
                 group,
                 spec->label,
                 binary,
                 spec->offset) >= (int)sizeof(line)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (write_text_file(path, line) != 0) {
        return -1;
    }
    spec->registered = 1;
    return 0;
}

static int read_uprobe_event_id(const char *tracefs_root, const char *group, struct event_spec *spec) {
    char path[MAX_PATH_LEN];
    snprintf(path, sizeof(path), "%s/events/%s/%s/id", tracefs_root, group, spec->label);
    return read_int64_file(path, &spec->id);
}

static int parse_duration(const char *text, int *out_duration_sec) {
    char *end = NULL;
    errno = 0;
    long value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 0 || value > 120) {
        errno = EINVAL;
        return -1;
    }
    *out_duration_sec = (int)value;
    return 0;
}

static void usage(FILE *out) {
    fprintf(out,
            "%s\n"
            "usage:\n"
            "  a90_pm_service_uprobe_counter --check-only\n"
            "  a90_pm_service_uprobe_counter --allow-tracefs-write --allow-attach --event LABEL:OFFSET [options]\n"
            "  a90_pm_service_uprobe_counter --allow-tracefs-write --allow-attach --allow-child-command --event LABEL:OFFSET -- COMMAND...\n"
            "\n"
            "options:\n"
            "  --binary PATH              default: /vendor/bin/pm-service\n"
            "  --tracefs-root PATH        default: auto /sys/kernel/tracing then /sys/kernel/debug/tracing\n"
            "  --group NAME               default: a90pm1076\n"
            "  --duration-sec SEC         0..120, default 8\n"
            "  --stop-on-child-exit       stop observation once child exits\n"
            "  --verbose                  print verifier logs on BPF load failure\n"
            "\n"
            "safety: default is check-only; no tracefs write, attach, child command, Wi-Fi action, or network action without explicit flags\n",
            A90_PM_UPROBE_COUNTER_VERSION);
}

static void close_events(struct event_spec *events, unsigned int count) {
    for (unsigned int i = 0; i < count; i++) {
        if (events[i].perf_fd >= 0) {
            ioctl(events[i].perf_fd, PERF_EVENT_IOC_DISABLE, 0);
            close(events[i].perf_fd);
            events[i].perf_fd = -1;
        }
        if (events[i].prog_fd >= 0) {
            close(events[i].prog_fd);
            events[i].prog_fd = -1;
        }
    }
}

static void cleanup_events(const char *tracefs_root, const char *group, struct event_spec *events, unsigned int count) {
    for (unsigned int i = 0; i < count; i++) {
        if (events[i].registered) {
            if (remove_uprobe_event(tracefs_root, group, events[i].label) == 0) {
                printf("event.%s.cleanup=removed\n", events[i].label);
            } else {
                printf("event.%s.cleanup=remove-failed\n", events[i].label);
                printf("event.%s.cleanup_errno=%d\n", events[i].label, errno);
            }
            events[i].registered = 0;
        }
    }
}

static int spawn_child(char **child_argv) {
    pid_t pid = fork();
    if (pid < 0) {
        return -1;
    }
    if (pid == 0) {
        execvp(child_argv[0], child_argv);
        perror("child-exec");
        _exit(127);
    }
    child_pid = pid;
    return 0;
}

static int wait_child_nonblock(int *exit_code, int *signal_no, int *done) {
    int status = 0;
    pid_t got;
    *done = 0;
    if (child_pid <= 0) {
        return 0;
    }
    got = waitpid(child_pid, &status, WNOHANG);
    if (got < 0) {
        if (errno == ECHILD) {
            *done = 1;
            child_pid = -1;
            return 0;
        }
        return -1;
    }
    if (got == 0) {
        return 0;
    }
    *done = 1;
    if (WIFEXITED(status)) {
        *exit_code = WEXITSTATUS(status);
    } else if (WIFSIGNALED(status)) {
        *signal_no = WTERMSIG(status);
    }
    child_pid = -1;
    return 0;
}

static void terminate_child_if_needed(int *term_sent, int *kill_sent) {
    if (child_pid <= 0) {
        return;
    }
    if (kill(child_pid, SIGTERM) == 0) {
        *term_sent = 1;
    }
    long long deadline = monotonic_ms() + 1000LL;
    while (monotonic_ms() < deadline) {
        int exit_code = -1;
        int signal_no = 0;
        int done = 0;
        if (wait_child_nonblock(&exit_code, &signal_no, &done) == 0 && done) {
            return;
        }
        usleep(50000);
    }
    if (child_pid > 0 && kill(child_pid, SIGKILL) == 0) {
        *kill_sent = 1;
    }
    waitpid(child_pid, NULL, 0);
    child_pid = -1;
}

int main(int argc, char **argv) {
    const char *binary = DEFAULT_BINARY;
    const char *tracefs_arg = NULL;
    const char *group = DEFAULT_GROUP;
    struct event_spec events[MAX_EVENTS];
    unsigned int event_count = 0;
    int allow_tracefs_write = 0;
    int allow_attach = 0;
    int allow_child_command = 0;
    int check_only = 0;
    int verbose = 0;
    int stop_on_child_exit = 0;
    int duration_sec = 8;
    int child_argc_start = -1;

    memset(events, 0, sizeof(events));
    for (unsigned int i = 0; i < MAX_EVENTS; i++) {
        events[i].id = -1;
        events[i].prog_fd = -1;
        events[i].perf_fd = -1;
    }

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--") == 0) {
            child_argc_start = i + 1;
            break;
        } else if (strcmp(argv[i], "--check-only") == 0) {
            check_only = 1;
        } else if (strcmp(argv[i], "--allow-tracefs-write") == 0) {
            allow_tracefs_write = 1;
        } else if (strcmp(argv[i], "--allow-attach") == 0) {
            allow_attach = 1;
        } else if (strcmp(argv[i], "--allow-child-command") == 0) {
            allow_child_command = 1;
        } else if (strcmp(argv[i], "--verbose") == 0) {
            verbose = 1;
        } else if (strcmp(argv[i], "--stop-on-child-exit") == 0) {
            stop_on_child_exit = 1;
        } else if (strcmp(argv[i], "--binary") == 0 && i + 1 < argc) {
            binary = argv[++i];
        } else if (strcmp(argv[i], "--tracefs-root") == 0 && i + 1 < argc) {
            tracefs_arg = argv[++i];
        } else if (strcmp(argv[i], "--group") == 0 && i + 1 < argc) {
            group = argv[++i];
        } else if (strcmp(argv[i], "--duration-sec") == 0 && i + 1 < argc) {
            if (parse_duration(argv[++i], &duration_sec) != 0) {
                perror("duration-sec");
                return 2;
            }
        } else if (strcmp(argv[i], "--event") == 0 && i + 1 < argc) {
            if (event_count >= MAX_EVENTS) {
                fprintf(stderr, "too many events\n");
                return 2;
            }
            if (parse_event_spec(argv[++i], &events[event_count]) != 0) {
                perror("event");
                return 2;
            }
            event_count++;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            usage(stdout);
            return 0;
        } else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            usage(stderr);
            return 2;
        }
    }

    const char *tracefs_root = pick_tracefs_root(tracefs_arg);
    printf("%s\n", A90_PM_UPROBE_COUNTER_VERSION);
    printf("binary=%s\n", binary);
    printf("tracefs_root=%s\n", tracefs_root);
    printf("group=%s\n", group);
    printf("duration_sec=%d\n", duration_sec);
    printf("event_count=%u\n", event_count);
    printf("allow_tracefs_write=%d\n", allow_tracefs_write);
    printf("allow_attach=%d\n", allow_attach);
    printf("allow_child_command=%d\n", allow_child_command);

    if (!safe_label(group)) {
        printf("result=invalid-group\n");
        return 2;
    }
    if (check_only || !allow_tracefs_write || !allow_attach) {
        printf("result=check-only\n");
        printf("tracefs_write_attempted=0\n");
        printf("attach_attempted=0\n");
        printf("child_command_attempted=0\n");
        return 0;
    }
    if (event_count == 0) {
        printf("result=no-events\n");
        return 2;
    }
    if (child_argc_start >= 0 && child_argc_start < argc && !allow_child_command) {
        printf("result=child-command-blocked\n");
        return 2;
    }

    char uprobe_events_path[MAX_PATH_LEN];
    snprintf(uprobe_events_path, sizeof(uprobe_events_path), "%s/uprobe_events", tracefs_root);
    if (!file_exists(uprobe_events_path)) {
        printf("result=tracefs-uprobe-events-missing\n");
        printf("uprobe_events=%s\n", uprobe_events_path);
        return 1;
    }

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    int map_fd = create_counter_map(event_count);
    if (map_fd < 0) {
        printf("result=map-create-failed\n");
        printf("errno=%d\n", errno);
        perror("map-create");
        return 1;
    }
    printf("map_fd=%d\n", map_fd);

    enum run_result result = RUN_FAILED;
    int child_exit_code = -1;
    int child_signal = 0;
    int child_done = 0;
    int child_started = 0;
    int child_term_sent = 0;
    int child_kill_sent = 0;

    for (unsigned int i = 0; i < event_count; i++) {
        if (register_uprobe_event(tracefs_root, group, binary, &events[i]) != 0) {
            printf("event.%s.register=failed\n", events[i].label);
            printf("event.%s.errno=%d\n", events[i].label, errno);
            perror("register-uprobe");
            goto cleanup;
        }
        printf("event.%s.register=ok\n", events[i].label);
        if (read_uprobe_event_id(tracefs_root, group, &events[i]) != 0) {
            printf("event.%s.id_read=failed\n", events[i].label);
            printf("event.%s.errno=%d\n", events[i].label, errno);
            perror("read-uprobe-id");
            goto cleanup;
        }
        printf("event.%s.id=%lld\n", events[i].label, events[i].id);
        events[i].prog_fd = load_counter_prog(map_fd, i, verbose);
        if (events[i].prog_fd < 0) {
            printf("event.%s.bpf_load=failed\n", events[i].label);
            printf("event.%s.errno=%d\n", events[i].label, errno);
            perror("bpf-load");
            goto cleanup;
        }
        events[i].perf_fd = attach_tracepoint_prog(events[i].prog_fd, events[i].id);
        if (events[i].perf_fd < 0) {
            printf("event.%s.attach=failed\n", events[i].label);
            printf("event.%s.errno=%d\n", events[i].label, errno);
            perror("attach");
            goto cleanup;
        }
        events[i].attached = 1;
        printf("event.%s.attach=ok\n", events[i].label);
    }

    if (child_argc_start >= 0 && child_argc_start < argc) {
        printf("child.command=%s\n", argv[child_argc_start]);
        if (spawn_child(&argv[child_argc_start]) != 0) {
            printf("child.start=failed\n");
            printf("child.errno=%d\n", errno);
            perror("child-start");
            goto cleanup;
        }
        child_started = 1;
        printf("child.pid=%d\n", child_pid);
    }

    printf("observe_begin=1\n");
    fflush(stdout);
    long long deadline = monotonic_ms() + (long long)duration_sec * 1000LL;
    while (!stop_requested && monotonic_ms() < deadline) {
        if (child_started && !child_done) {
            if (wait_child_nonblock(&child_exit_code, &child_signal, &child_done) != 0) {
                printf("child.wait=failed\n");
                printf("child.errno=%d\n", errno);
                perror("child-wait");
                goto cleanup;
            }
            if (child_done && stop_on_child_exit) {
                break;
            }
        }
        usleep(100000);
    }
    if (child_started && !child_done) {
        if (wait_child_nonblock(&child_exit_code, &child_signal, &child_done) != 0) {
            printf("child.wait=failed\n");
            printf("child.errno=%d\n", errno);
            perror("child-wait");
            goto cleanup;
        }
    }
    if (child_started && !child_done) {
        terminate_child_if_needed(&child_term_sent, &child_kill_sent);
        child_done = 1;
    }

    close_events(events, event_count);
    for (unsigned int i = 0; i < event_count; i++) {
        if (lookup_counter(map_fd, i, &events[i].count) != 0) {
            printf("event.%s.count=lookup-failed\n", events[i].label);
            printf("event.%s.errno=%d\n", events[i].label, errno);
            perror("count-lookup");
            goto cleanup;
        }
        printf("event.%s.count=%llu\n", events[i].label, (unsigned long long)events[i].count);
    }
    printf("observe_end=1\n");
    printf("child.started=%d\n", child_started);
    printf("child.done=%d\n", child_done);
    printf("child.exit_code=%d\n", child_exit_code);
    printf("child.signal=%d\n", child_signal);
    printf("child.term_sent=%d\n", child_term_sent);
    printf("child.kill_sent=%d\n", child_kill_sent);
    result = RUN_PASS;

cleanup:
    close_events(events, event_count);
    cleanup_events(tracefs_root, group, events, event_count);
    if (map_fd >= 0) {
        close(map_fd);
    }
    if (result == RUN_PASS) {
        printf("result=uprobe-count-pass\n");
        return 0;
    }
    printf("result=uprobe-count-failed\n");
    return 1;
}
