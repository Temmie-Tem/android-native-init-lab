#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef __NR_bpf
#define __NR_bpf 280
#endif

#ifndef BPF_PSEUDO_MAP_FD
#define BPF_PSEUDO_MAP_FD 1
#endif

#define A90_BPF_TRACE_COUNTER_VERSION "a90_bpf_trace_counter v782"
#define DEFAULT_TRACEPOINT_ID_PATH "/sys/kernel/tracing/events/msm_pil_event/pil_notif/id"

static uint64_t ptr_to_u64(const void *ptr) {
    return (uint64_t)(uintptr_t)ptr;
}

static long sys_bpf(enum bpf_cmd cmd, union bpf_attr *attr, unsigned int size) {
    return syscall(__NR_bpf, cmd, attr, size);
}

static long sys_perf_event_open(struct perf_event_attr *attr, pid_t pid, int cpu, int group_fd, unsigned long flags) {
    return syscall(__NR_perf_event_open, attr, pid, cpu, group_fd, flags);
}

static int read_tracepoint_id(const char *path, long long *out_id) {
    char buffer[64];
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    ssize_t got = read(fd, buffer, sizeof(buffer) - 1);
    int saved = errno;
    close(fd);
    if (got <= 0) {
        errno = saved;
        return -1;
    }
    buffer[got] = '\0';
    char *end = NULL;
    errno = 0;
    long long value = strtoll(buffer, &end, 10);
    if (errno != 0 || end == buffer || value <= 0) {
        errno = EINVAL;
        return -1;
    }
    *out_id = value;
    return 0;
}

static int create_counter_map(void) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_type = BPF_MAP_TYPE_ARRAY;
    attr.key_size = sizeof(uint32_t);
    attr.value_size = sizeof(uint64_t);
    attr.max_entries = 1;
    return (int)sys_bpf(BPF_MAP_CREATE, &attr, sizeof(attr));
}

static int lookup_counter(int map_fd, uint64_t *value_out) {
    uint32_t key = 0;
    uint64_t value = 0;
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_fd = (uint32_t)map_fd;
    attr.key = ptr_to_u64(&key);
    attr.value = ptr_to_u64(&value);
    if (sys_bpf(BPF_MAP_LOOKUP_ELEM, &attr, sizeof(attr)) != 0) {
        return -1;
    }
    *value_out = value;
    return 0;
}

static int load_counter_tracepoint_prog(int map_fd, int verbose) {
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
            .imm = 0,
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
        fprintf(stderr, "bpf_log=%s\n", log_buffer);
    }
    return fd;
}

static int attach_perf_event(int prog_fd, long long tracepoint_id) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.type = PERF_TYPE_TRACEPOINT;
    attr.size = sizeof(attr);
    attr.config = (uint64_t)tracepoint_id;
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
            "  a90_bpf_trace_counter --check-only\n"
            "  a90_bpf_trace_counter --allow-attach [--duration-sec SEC] [--tracepoint-id-path PATH] [--verbose]\n"
            "\n"
            "default target: msm_pil_event:pil_notif\n"
            "safety: no Wi-Fi trigger, no network action, no tracefs writes\n",
            A90_BPF_TRACE_COUNTER_VERSION);
}

int main(int argc, char **argv) {
    const char *id_path = DEFAULT_TRACEPOINT_ID_PATH;
    int allow_attach = 0;
    int check_only = 0;
    int verbose = 0;
    int duration_sec = 1;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--check-only") == 0) {
            check_only = 1;
        } else if (strcmp(argv[i], "--allow-attach") == 0) {
            allow_attach = 1;
        } else if (strcmp(argv[i], "--verbose") == 0) {
            verbose = 1;
        } else if (strcmp(argv[i], "--duration-sec") == 0 && i + 1 < argc) {
            if (parse_duration(argv[++i], &duration_sec) != 0) {
                perror("duration-sec");
                return 2;
            }
        } else if (strcmp(argv[i], "--tracepoint-id-path") == 0 && i + 1 < argc) {
            id_path = argv[++i];
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            usage(stdout);
            return 0;
        } else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            usage(stderr);
            return 2;
        }
    }

    printf("%s\n", A90_BPF_TRACE_COUNTER_VERSION);
    printf("target=msm_pil_event:pil_notif\n");
    printf("tracepoint_id_path=%s\n", id_path);
    printf("duration_sec=%d\n", duration_sec);
    if (check_only || !allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        return 0;
    }

    long long tracepoint_id = -1;
    if (read_tracepoint_id(id_path, &tracepoint_id) != 0) {
        printf("result=tracepoint-id-failed\n");
        printf("errno=%d\n", errno);
        perror("tracepoint-id");
        return 1;
    }
    printf("tracepoint_id=%lld\n", tracepoint_id);

    int map_fd = create_counter_map();
    if (map_fd < 0) {
        printf("result=map-create-failed\n");
        printf("errno=%d\n", errno);
        perror("map-create");
        return 1;
    }

    int prog_fd = load_counter_tracepoint_prog(map_fd, verbose);
    if (prog_fd < 0) {
        int saved = errno;
        close(map_fd);
        printf("result=bpf-load-failed\n");
        printf("errno=%d\n", saved);
        errno = saved;
        perror("bpf-load");
        return 1;
    }
    printf("bpf_prog_fd=%d\n", prog_fd);

    int perf_fd = attach_perf_event(prog_fd, tracepoint_id);
    if (perf_fd < 0) {
        int saved = errno;
        close(prog_fd);
        close(map_fd);
        printf("result=attach-failed\n");
        printf("errno=%d\n", saved);
        errno = saved;
        perror("attach");
        return 1;
    }
    printf("perf_fd=%d\n", perf_fd);
    printf("attach_attempted=1\n");
    printf("observe_begin=1\n");
    fflush(stdout);
    sleep((unsigned int)duration_sec);
    ioctl(perf_fd, PERF_EVENT_IOC_DISABLE, 0);
    close(perf_fd);
    close(prog_fd);

    uint64_t count = 0;
    if (lookup_counter(map_fd, &count) != 0) {
        int saved = errno;
        close(map_fd);
        printf("result=count-lookup-failed\n");
        printf("errno=%d\n", saved);
        errno = saved;
        perror("count-lookup");
        return 1;
    }
    close(map_fd);
    printf("observe_end=1\n");
    printf("event_count=%llu\n", (unsigned long long)count);
    printf("result=attach-count-pass\n");
    return 0;
}
