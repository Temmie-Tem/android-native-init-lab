// V2449/V2460 Android-side msm_audio_cal diagnostic thread-set clone-following ioctl observer.
// Measurement-only helper: attaches all existing TIDs in an Android audio
// process, follows new threads with PTRACE_O_TRACECLONE, records diagnostic syscall/ioctl/fd telemetry, and
// copies request buffers only for fd-matched private offline decoding. It does not open
// /dev/msm_audio_cal itself and does not issue any audio ioctl.

#define _GNU_SOURCE
#include <asm/ptrace.h>
#include <asm/unistd.h>
#include <elf.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef __NR_ioctl
#define __NR_ioctl 29
#endif

#define A90_COMPAT_ARM_NR_IOCTL 54UL
#define A90_COMPAT_ARM_GPR_COUNT 18U
#define A90_COMPAT_ARM_GPR_BYTES (A90_COMPAT_ARM_GPR_COUNT * sizeof(uint32_t))

#ifndef __WALL
#define __WALL 0x40000000
#endif

#define DEFAULT_MAX_BYTES 512U
#define DEFAULT_DURATION_SEC 8
#define DEFAULT_MAX_EVENTS 128
#define DEFAULT_MAX_UNMATCHED_SAMPLES 32
#define DEFAULT_MAX_DMABUF_BYTES 65536U
#define MAX_TRACED_TASKS 256
#define WAIT_POLL_USEC 10000
#define A90_CAL_CMD_SET_COMPAT 0xc00461cbUL
#define A90_CAL_CMD_SET_NATIVE 0xc00861cbUL
#define A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE 39U

struct options {
    pid_t pid;
    pid_t tgid;
    pid_t fd_pid;
    const char *out_path;
    const char *device_substr;
    size_t max_bytes;
    int duration_sec;
    int max_events;
    int max_unmatched_samples;
    const char *dmabuf_out_dir;
    size_t max_dmabuf_bytes;
};

struct pending_ioctl {
    int active;
    int seq;
    const char *abi;
    unsigned long syscall_nr;
    size_t regset_len;
    long fd;
    unsigned long request;
    unsigned long argp;
};

struct syscall_frame {
    const char *abi;
    unsigned long syscall_nr;
    size_t regset_len;
    long fd;
    unsigned long request;
    unsigned long argp;
    long ret;
};

struct traced_task {
    pid_t tid;
    int alive;
    int entering_syscall;
    int options_set;
    struct pending_ioctl pending;
};

struct decoded_cal_header {
    int valid;
    uint32_t data_size;
    uint32_t version;
    uint32_t cal_type;
    uint32_t cal_type_size;
    uint32_t type_version;
    uint32_t buffer_number;
    uint32_t cal_size;
    uint32_t mem_handle;
};

struct capture_stats {
    int syscall_stop_count;
    int syscall_entry_count;
    int ioctl_any_entry_count;
    int ioctl_fd_match_count;
    int ioctl_fd_miss_count;
    int fd_readlink_error_count;
    int unmatched_samples;
};

static void usage(const char *argv0) {
    fprintf(stderr,
            "usage: %s --tgid TGID --out PATH [--pid PID] [--fd-pid TGID] [--device-substr /dev/msm_audio_cal] "
            "[--max-bytes 512] [--duration-sec 8] [--max-events 128] [--max-unmatched-samples 32] "
            "[--dmabuf-out-dir PATH] [--max-dmabuf-bytes 65536]\n",
            argv0);
}

static int parse_int_arg(const char *text, long min_value, long max_value, long *out) {
    char *end = NULL;
    errno = 0;
    long value = strtol(text, &end, 0);
    if (errno || end == text || *end != '\0' || value < min_value || value > max_value) {
        return -1;
    }
    *out = value;
    return 0;
}

static int parse_options(int argc, char **argv, struct options *opts) {
    opts->pid = -1;
    opts->tgid = -1;
    opts->fd_pid = -1;
    opts->out_path = NULL;
    opts->device_substr = "/dev/msm_audio_cal";
    opts->max_bytes = DEFAULT_MAX_BYTES;
    opts->duration_sec = DEFAULT_DURATION_SEC;
    opts->max_events = DEFAULT_MAX_EVENTS;
    opts->max_unmatched_samples = DEFAULT_MAX_UNMATCHED_SAMPLES;
    opts->dmabuf_out_dir = NULL;
    opts->max_dmabuf_bytes = DEFAULT_MAX_DMABUF_BYTES;

    for (int arg_index = 1; arg_index < argc; arg_index++) {
        if (!strcmp(argv[arg_index], "--pid") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 4194304, &value)) return -1;
            opts->pid = (pid_t)value;
        } else if (!strcmp(argv[arg_index], "--tgid") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 4194304, &value)) return -1;
            opts->tgid = (pid_t)value;
        } else if (!strcmp(argv[arg_index], "--fd-pid") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 4194304, &value)) return -1;
            opts->fd_pid = (pid_t)value;
        } else if (!strcmp(argv[arg_index], "--out") && arg_index + 1 < argc) {
            opts->out_path = argv[++arg_index];
        } else if (!strcmp(argv[arg_index], "--device-substr") && arg_index + 1 < argc) {
            opts->device_substr = argv[++arg_index];
        } else if (!strcmp(argv[arg_index], "--max-bytes") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 4096, &value)) return -1;
            opts->max_bytes = (size_t)value;
        } else if (!strcmp(argv[arg_index], "--duration-sec") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 120, &value)) return -1;
            opts->duration_sec = (int)value;
        } else if (!strcmp(argv[arg_index], "--max-events") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 4096, &value)) return -1;
            opts->max_events = (int)value;
        } else if (!strcmp(argv[arg_index], "--max-unmatched-samples") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 0, 1024, &value)) return -1;
            opts->max_unmatched_samples = (int)value;
        } else if (!strcmp(argv[arg_index], "--dmabuf-out-dir") && arg_index + 1 < argc) {
            opts->dmabuf_out_dir = argv[++arg_index];
        } else if (!strcmp(argv[arg_index], "--max-dmabuf-bytes") && arg_index + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++arg_index], 1, 1048576, &value)) return -1;
            opts->max_dmabuf_bytes = (size_t)value;
        } else {
            return -1;
        }
    }
    if (opts->tgid <= 0 && opts->pid > 0) opts->tgid = opts->pid;
    if (opts->pid <= 0 && opts->tgid > 0) opts->pid = opts->tgid;
    if (opts->fd_pid <= 0) opts->fd_pid = opts->tgid;
    return (opts->tgid > 0 && opts->pid > 0 && opts->out_path != NULL) ? 0 : -1;
}

static long long now_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        struct timeval tv;
        gettimeofday(&tv, NULL);
        return (long long)tv.tv_sec * 1000LL + (long long)tv.tv_usec / 1000LL;
    }
    return (long long)ts.tv_sec * 1000LL + (long long)ts.tv_nsec / 1000000LL;
}

static long long wall_ms(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)tv.tv_sec * 1000LL + (long long)tv.tv_usec / 1000LL;
}

static int get_syscall_frame(pid_t tid, struct syscall_frame *frame) {
    union {
        struct user_pt_regs native;
        uint32_t compat[A90_COMPAT_ARM_GPR_COUNT];
    } regs;
    struct iovec iov;
    memset(&regs, 0, sizeof(regs));
    memset(frame, 0, sizeof(*frame));
    iov.iov_base = &regs;
    iov.iov_len = sizeof(regs);
    if (ptrace(PTRACE_GETREGSET, tid, (void *)(uintptr_t)NT_PRSTATUS, &iov) != 0) {
        return -1;
    }

    frame->regset_len = iov.iov_len;
    if (iov.iov_len == A90_COMPAT_ARM_GPR_BYTES) {
        frame->abi = "aarch32";
        frame->syscall_nr = regs.compat[7];
        frame->fd = (int32_t)regs.compat[0];
        frame->request = regs.compat[1];
        frame->argp = regs.compat[2];
        frame->ret = (int32_t)regs.compat[0];
        return 0;
    }

    if (iov.iov_len == sizeof(struct user_pt_regs)) {
        frame->abi = "aarch64";
        frame->syscall_nr = regs.native.regs[8];
        frame->fd = (long)regs.native.regs[0];
        frame->request = regs.native.regs[1];
        frame->argp = regs.native.regs[2];
        frame->ret = (long)regs.native.regs[0];
        return 0;
    }

    errno = EINVAL;
    return -1;
}

static int fd_resolve_target(pid_t pid, long fd, char *target, size_t target_size) {
    char path[128];
    snprintf(path, sizeof(path), "/proc/%ld/fd/%ld", (long)pid, fd);
    ssize_t bytes = readlink(path, target, target_size - 1);
    if (bytes < 0) {
        snprintf(target, target_size, "readlink-error:%s", strerror(errno));
        return -1;
    }
    target[bytes] = '\0';
    return 0;
}

static int fd_matches_device(pid_t pid, long fd, const char *needle, char *target, size_t target_size, int *readlink_errno) {
    errno = 0;
    if (fd_resolve_target(pid, fd, target, target_size) != 0) {
        if (readlink_errno) *readlink_errno = errno;
        return 0;
    }
    if (readlink_errno) *readlink_errno = 0;
    return strstr(target, needle) != NULL;
}

static ssize_t read_remote_process_vm(pid_t tid, unsigned long remote, unsigned char *buf, size_t len) {
    struct iovec local_iov = {.iov_base = buf, .iov_len = len};
    struct iovec remote_iov = {.iov_base = (void *)(uintptr_t)remote, .iov_len = len};
    return process_vm_readv(tid, &local_iov, 1, &remote_iov, 1, 0);
}

static ssize_t read_remote_ptrace(pid_t tid, unsigned long remote, unsigned char *buf, size_t len) {
    size_t copied = 0;
    while (copied < len) {
        errno = 0;
        long word = ptrace(PTRACE_PEEKDATA, tid, (void *)(uintptr_t)(remote + copied), NULL);
        if (errno != 0) {
            break;
        }
        size_t chunk = sizeof(word);
        if (chunk > len - copied) chunk = len - copied;
        memcpy(buf + copied, &word, chunk);
        copied += chunk;
    }
    return copied > 0 ? (ssize_t)copied : -1;
}

static ssize_t read_remote(pid_t tid, unsigned long remote, unsigned char *buf, size_t len) {
    if (remote == 0 || len == 0) return 0;
    ssize_t bytes = read_remote_process_vm(tid, remote, buf, len);
    if (bytes >= 0) return bytes;
    return read_remote_ptrace(tid, remote, buf, len);
}

static void json_escape(FILE *fp, const char *text) {
    for (const unsigned char *cursor = (const unsigned char *)text; *cursor; cursor++) {
        if (*cursor == '"' || *cursor == '\\') {
            fputc('\\', fp);
            fputc(*cursor, fp);
        } else if (*cursor >= 0x20 && *cursor <= 0x7e) {
            fputc(*cursor, fp);
        } else {
            fprintf(fp, "\\u%04x", *cursor);
        }
    }
}

static void write_hex(FILE *fp, const unsigned char *buf, ssize_t len) {
    static const char hexdigits[] = "0123456789abcdef";
    for (ssize_t byte_index = 0; byte_index < len; byte_index++) {
        fputc(hexdigits[(buf[byte_index] >> 4) & 0xf], fp);
        fputc(hexdigits[buf[byte_index] & 0xf], fp);
    }
}

static uint32_t read_le32(const unsigned char *buf) {
    return ((uint32_t)buf[0]) |
           ((uint32_t)buf[1] << 8) |
           ((uint32_t)buf[2] << 16) |
           ((uint32_t)buf[3] << 24);
}

static struct decoded_cal_header decode_cal_header(const unsigned char *buf, ssize_t len) {
    struct decoded_cal_header header;
    memset(&header, 0, sizeof(header));
    if (len < 32) return header;
    header.data_size = read_le32(buf + 0);
    header.version = read_le32(buf + 4);
    header.cal_type = read_le32(buf + 8);
    header.cal_type_size = read_le32(buf + 12);
    header.type_version = read_le32(buf + 16);
    header.buffer_number = read_le32(buf + 20);
    header.cal_size = read_le32(buf + 24);
    header.mem_handle = read_le32(buf + 28);
    header.valid = header.data_size >= 32 && header.data_size <= DEFAULT_MAX_BYTES;
    return header;
}

static int is_dmabuf_capture_target(unsigned long request, const struct decoded_cal_header *header) {
    if (!header || !header->valid) return 0;
    if (request != A90_CAL_CMD_SET_COMPAT && request != A90_CAL_CMD_SET_NATIVE) return 0;
    return header->cal_type == A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE &&
           header->cal_size > 0 &&
           header->mem_handle > 0;
}

static void write_header(FILE *fp, const struct options *opts) {
    fprintf(fp,
            "{\"event\":\"start\",\"ts_ms\":%lld,\"wall_ms\":%lld,"
            "\"pid\":%ld,\"tgid\":%ld,\"fd_pid\":%ld,\"duration_sec\":%d,"
            "\"max_bytes\":%zu,\"max_unmatched_samples\":%d,"
            "\"dmabuf_capture_enabled\":%s,\"max_dmabuf_bytes\":%zu,"
            "\"trace_mode\":\"threadset-clone-following-diagnostic\",\"device_substr\":\"",
            now_ms(), wall_ms(),
            (long)opts->pid, (long)opts->tgid, (long)opts->fd_pid, opts->duration_sec,
            opts->max_bytes, opts->max_unmatched_samples,
            opts->dmabuf_out_dir ? "true" : "false", opts->max_dmabuf_bytes);
    json_escape(fp, opts->device_substr);
    fprintf(fp, "\",\"note\":\"private raw hex only for fd-matched payloads; unmatched samples are metadata-only\"}\n");
    fflush(fp);
}

static void write_error(FILE *fp, const char *where, pid_t tid, int errnum) {
    fprintf(fp, "{\"event\":\"error\",\"ts_ms\":%lld,\"wall_ms\":%lld,\"where\":\"", now_ms(), wall_ms());
    json_escape(fp, where);
    fprintf(fp, "\",\"tid\":%ld,\"errno\":%d,\"strerror\":\"", (long)tid, errnum);
    json_escape(fp, strerror(errnum));
    fprintf(fp, "\"}\n");
    fflush(fp);
}

static void write_trace_event(FILE *fp, const char *event, pid_t tid, pid_t child_tid) {
    fprintf(fp, "{\"event\":\"");
    json_escape(fp, event);
    fprintf(fp, "\",\"ts_ms\":%lld,\"wall_ms\":%lld,\"tid\":%ld", now_ms(), wall_ms(), (long)tid);
    if (child_tid > 0) fprintf(fp, ",\"child_tid\":%ld", (long)child_tid);
    fprintf(fp, "}\n");
    fflush(fp);
}

static void write_entry(FILE *fp, int seq, pid_t tid, pid_t fd_pid, const char *abi,
                        unsigned long syscall_nr, size_t regset_len, const char *fd_target,
                        unsigned long request, unsigned long argp,
                        const unsigned char *buf, ssize_t read_len, int read_errno) {
    fprintf(fp,
            "{\"event\":\"ioctl_entry\",\"ts_ms\":%lld,\"wall_ms\":%lld,"
            "\"seq\":%d,\"tid\":%ld,\"fd_pid\":%ld,\"abi\":\"",
            now_ms(), wall_ms(), seq, (long)tid, (long)fd_pid);
    json_escape(fp, abi);
    fprintf(fp,
            "\",\"syscall_nr\":%lu,\"regset_len\":%zu,"
            "\"request\":\"0x%lx\",\"argp\":\"0x%lx\",\"fd_target\":\"",
            syscall_nr, regset_len, request, argp);
    json_escape(fp, fd_target);
    fprintf(fp, "\",\"read_len\":%zd,\"read_errno\":%d,\"bytes_hex\":\"",
            read_len > 0 ? read_len : 0, read_errno);
    if (read_len > 0) write_hex(fp, buf, read_len);
    fprintf(fp, "\"}\n");
    fflush(fp);
}

static void write_dmabuf_capture_event(FILE *fp, int seq, pid_t tid, pid_t fd_pid,
                                       const struct decoded_cal_header *header,
                                       const char *status, const char *path,
                                       size_t capture_len, ssize_t written_len,
                                       int open_errno, int mmap_errno, int write_errno) {
    fprintf(fp,
            "{\"event\":\"dmabuf_capture\",\"ts_ms\":%lld,\"wall_ms\":%lld,"
            "\"seq\":%d,\"tid\":%ld,\"fd_pid\":%ld,"
            "\"data_size\":%u,\"cal_type\":%u,\"buffer_number\":%u,"
            "\"cal_size\":%u,\"mem_handle\":%u,\"capture_len\":%zu,"
            "\"written_len\":%zd,\"open_errno\":%d,\"mmap_errno\":%d,\"write_errno\":%d,"
            "\"status\":\"",
            now_ms(), wall_ms(), seq, (long)tid, (long)fd_pid,
            header ? header->data_size : 0, header ? header->cal_type : 0,
            header ? header->buffer_number : 0, header ? header->cal_size : 0,
            header ? header->mem_handle : 0, capture_len, written_len,
            open_errno, mmap_errno, write_errno);
    json_escape(fp, status);
    fprintf(fp, "\",\"path\":\"");
    if (path) json_escape(fp, path);
    fprintf(fp, "\"}\n");
    fflush(fp);
}

static ssize_t write_all(int fd, const unsigned char *buf, size_t len) {
    size_t total = 0;
    while (total < len) {
        ssize_t rc = write(fd, buf + total, len - total);
        if (rc < 0) {
            if (errno == EINTR) continue;
            return total > 0 ? (ssize_t)total : -1;
        }
        if (rc == 0) break;
        total += (size_t)rc;
    }
    return (ssize_t)total;
}

static void capture_dmabuf_payload(FILE *fp, const struct options *opts, int seq, pid_t tid,
                                   const struct decoded_cal_header *header) {
    if (!opts->dmabuf_out_dir || !header) return;
    if (mkdir(opts->dmabuf_out_dir, 0700) != 0 && errno != EEXIST) {
        write_dmabuf_capture_event(fp, seq, tid, opts->fd_pid, header, "mkdir-failed", "",
                                   0, -1, 0, 0, errno);
        return;
    }

    size_t capture_len = header->cal_size;
    if (capture_len > opts->max_dmabuf_bytes) capture_len = opts->max_dmabuf_bytes;
    if (capture_len == 0) return;

    char proc_fd_path[128];
    snprintf(proc_fd_path, sizeof(proc_fd_path), "/proc/%ld/fd/%u", (long)opts->fd_pid, header->mem_handle);
    int source_fd = open(proc_fd_path, O_RDONLY | O_CLOEXEC);
    if (source_fd < 0) {
        write_dmabuf_capture_event(fp, seq, tid, opts->fd_pid, header, "open-proc-fd-failed", "",
                                   capture_len, -1, errno, 0, 0);
        return;
    }

    void *mapped = mmap(NULL, capture_len, PROT_READ, MAP_SHARED, source_fd, 0);
    if (mapped == MAP_FAILED) {
        int mmap_errno = errno;
        close(source_fd);
        write_dmabuf_capture_event(fp, seq, tid, opts->fd_pid, header, "mmap-failed", "",
                                   capture_len, -1, 0, mmap_errno, 0);
        return;
    }

    char out_path[512];
    snprintf(out_path, sizeof(out_path), "%s/dmabuf-seq%04d-cal%u-fd%u.bin",
             opts->dmabuf_out_dir, seq, header->cal_type, header->mem_handle);
    int out_fd = open(out_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (out_fd < 0) {
        int write_errno = errno;
        munmap(mapped, capture_len);
        close(source_fd);
        write_dmabuf_capture_event(fp, seq, tid, opts->fd_pid, header, "open-output-failed", out_path,
                                   capture_len, -1, 0, 0, write_errno);
        return;
    }

    ssize_t written = write_all(out_fd, (const unsigned char *)mapped, capture_len);
    int write_errno = written == (ssize_t)capture_len ? 0 : errno;
    close(out_fd);
    munmap(mapped, capture_len);
    close(source_fd);
    write_dmabuf_capture_event(fp, seq, tid, opts->fd_pid, header,
                               written == (ssize_t)capture_len ? "ok" : "write-short",
                               out_path, capture_len, written, 0, 0, write_errno);
}

static void write_exit(FILE *fp, pid_t tid, const struct pending_ioctl *pending, long ret) {
    fprintf(fp,
            "{\"event\":\"ioctl_exit\",\"ts_ms\":%lld,\"wall_ms\":%lld,"
            "\"seq\":%d,\"tid\":%ld,\"abi\":\"",
            now_ms(), wall_ms(), pending->seq, (long)tid);
    json_escape(fp, pending->abi);
    fprintf(fp,
            "\",\"syscall_nr\":%lu,\"regset_len\":%zu,\"request\":\"0x%lx\","
            "\"argp\":\"0x%lx\",\"ret\":%ld}\n",
            pending->syscall_nr, pending->regset_len, pending->request, pending->argp, ret);
    fflush(fp);
}

static void write_unmatched_ioctl(FILE *fp, const struct options *opts, pid_t tid, long fd,
                                  const char *abi, unsigned long syscall_nr, size_t regset_len,
                                  unsigned long request, unsigned long argp,
                                  const char *fd_target, int readlink_errno,
                                  struct capture_stats *stats) {
    if (stats->unmatched_samples >= opts->max_unmatched_samples) return;
    stats->unmatched_samples++;
    fprintf(fp,
            "{\"event\":\"ioctl_unmatched\",\"ts_ms\":%lld,\"wall_ms\":%lld,"
            "\"sample\":%d,\"tid\":%ld,\"fd_pid\":%ld,\"fd\":%ld,"
            "\"abi\":\"",
            now_ms(), wall_ms(), stats->unmatched_samples, (long)tid, (long)opts->fd_pid,
            fd);
    json_escape(fp, abi);
    fprintf(fp,
            "\",\"syscall_nr\":%lu,\"regset_len\":%zu,"
            "\"request\":\"0x%lx\",\"argp\":\"0x%lx\",\"readlink_errno\":%d,"
            "\"fd_target\":\"",
            syscall_nr, regset_len, request, argp, readlink_errno);
    json_escape(fp, fd_target);
    fprintf(fp, "\"}\n");
    fflush(fp);
}

static struct traced_task *find_task(struct traced_task *tasks, int task_count, pid_t tid) {
    for (int index = 0; index < task_count; index++) {
        if (tasks[index].alive && tasks[index].tid == tid) return &tasks[index];
    }
    return NULL;
}

static struct traced_task *add_task(struct traced_task *tasks, int *task_count, pid_t tid, FILE *out) {
    struct traced_task *existing = find_task(tasks, *task_count, tid);
    if (existing) return existing;
    if (*task_count >= MAX_TRACED_TASKS) {
        write_error(out, "add-task-capacity", tid, ENOSPC);
        return NULL;
    }
    struct traced_task *task = &tasks[*task_count];
    memset(task, 0, sizeof(*task));
    task->tid = tid;
    task->alive = 1;
    task->entering_syscall = 1;
    (*task_count)++;
    write_trace_event(out, "tracee-add", tid, 0);
    return task;
}

static int set_trace_options(struct traced_task *task, FILE *out) {
    if (!task || task->options_set) return 0;
    long options = PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACECLONE;
    if (ptrace(PTRACE_SETOPTIONS, task->tid, NULL, (void *)(uintptr_t)options) != 0) {
        write_error(out, "PTRACE_SETOPTIONS", task->tid, errno);
        return -1;
    }
    task->options_set = 1;
    return 0;
}

static int resume_syscall(struct traced_task *task, int signal_to_deliver, FILE *out) {
    if (!task || !task->alive) return 0;
    if (ptrace(PTRACE_SYSCALL, task->tid, NULL, (void *)(uintptr_t)signal_to_deliver) != 0) {
        write_error(out, "PTRACE_SYSCALL", task->tid, errno);
        task->alive = 0;
        return -1;
    }
    return 0;
}

static int wait_for_specific_stop(pid_t tid, int *status, long long deadline, FILE *out, const char *where) {
    for (;;) {
        pid_t wait_result = waitpid(tid, status, __WALL | WNOHANG);
        if (wait_result == tid) return 0;
        if (wait_result < 0) {
            if (errno == EINTR) continue;
            if (errno == ECHILD || errno == ESRCH) return -1;
            write_error(out, where, tid, errno);
            return -1;
        }
        if (now_ms() >= deadline) {
            fprintf(out, "{\"event\":\"timeout\",\"where\":\"");
            json_escape(out, where);
            fprintf(out, "\",\"tid\":%ld}\n", (long)tid);
            fflush(out);
            return 1;
        }
        usleep(WAIT_POLL_USEC);
    }
}

static int wait_for_any_stop(int *status, long long deadline, FILE *out) {
    for (;;) {
        pid_t wait_result = waitpid(-1, status, __WALL | WNOHANG);
        if (wait_result > 0) return wait_result;
        if (wait_result < 0) {
            if (errno == EINTR) continue;
            if (errno == ECHILD) return 0;
            write_error(out, "waitpid-any", 0, errno);
            return -1;
        }
        if (now_ms() >= deadline) return 0;
        usleep(WAIT_POLL_USEC);
    }
}

static void stop_and_detach_all(struct traced_task *tasks, int task_count, FILE *out) {
    for (int index = 0; index < task_count; index++) {
        if (!tasks[index].alive) continue;
        if (kill(tasks[index].tid, SIGSTOP) != 0 && errno != ESRCH) {
            write_error(out, "kill-sigstop-for-detach", tasks[index].tid, errno);
        }
    }
    long long deadline = now_ms() + 1000LL;
    int status = 0;
    while (now_ms() < deadline) {
        int any_alive = 0;
        for (int index = 0; index < task_count; index++) {
            if (tasks[index].alive) any_alive = 1;
        }
        if (!any_alive) break;
        pid_t stopped_tid = waitpid(-1, &status, __WALL | WNOHANG);
        if (stopped_tid > 0) {
            struct traced_task *task = find_task(tasks, task_count, stopped_tid);
            if (task) {
                ptrace(PTRACE_DETACH, stopped_tid, NULL, NULL);
                task->alive = 0;
                write_trace_event(out, "detached", stopped_tid, 0);
            }
            continue;
        }
        if (stopped_tid < 0 && errno != EINTR && errno != ECHILD) {
            write_error(out, "waitpid-detach-any", 0, errno);
            break;
        }
        usleep(WAIT_POLL_USEC);
    }
    for (int index = 0; index < task_count; index++) {
        if (tasks[index].alive) {
            ptrace(PTRACE_DETACH, tasks[index].tid, NULL, NULL);
            tasks[index].alive = 0;
            write_trace_event(out, "detached-late", tasks[index].tid, 0);
        }
    }
}

static void handle_syscall_stop(FILE *out, const struct options *opts, struct traced_task *task,
                                int *sequence, int *events, struct capture_stats *stats) {
    struct syscall_frame frame;
    stats->syscall_stop_count++;
    if (get_syscall_frame(task->tid, &frame) != 0) {
        write_error(out, "PTRACE_GETREGSET", task->tid, errno);
        return;
    }

    if (task->entering_syscall) {
        stats->syscall_entry_count++;
        if ((frame.abi && !strcmp(frame.abi, "aarch64") && frame.syscall_nr == __NR_ioctl) ||
            (frame.abi && !strcmp(frame.abi, "aarch32") && frame.syscall_nr == A90_COMPAT_ARM_NR_IOCTL)) {
            stats->ioctl_any_entry_count++;
            long fd = frame.fd;
            unsigned long request = frame.request;
            unsigned long argp = frame.argp;
            char target[512];
            target[0] = '\0';
            int readlink_errno = 0;
            if (fd_matches_device(opts->fd_pid, fd, opts->device_substr, target, sizeof(target), &readlink_errno)) {
                stats->ioctl_fd_match_count++;
                unsigned char *buf = calloc(1, opts->max_bytes);
                if (!buf) {
                    write_error(out, "calloc", task->tid, errno);
                } else {
                    errno = 0;
                    ssize_t bytes = read_remote(task->tid, argp, buf, opts->max_bytes);
                    int read_errno = (bytes < 0) ? errno : 0;
                    (*sequence)++;
                    task->pending.active = 1;
                    task->pending.seq = *sequence;
                    task->pending.abi = frame.abi;
                    task->pending.syscall_nr = frame.syscall_nr;
                    task->pending.regset_len = frame.regset_len;
                    task->pending.fd = fd;
                    task->pending.request = request;
                    task->pending.argp = argp;
                    write_entry(out, *sequence, task->tid, opts->fd_pid, frame.abi,
                                frame.syscall_nr, frame.regset_len, target, request, argp, buf, bytes, read_errno);
                    struct decoded_cal_header cal_header = decode_cal_header(buf, bytes);
                    if (is_dmabuf_capture_target(request, &cal_header)) {
                        capture_dmabuf_payload(out, opts, *sequence, task->tid, &cal_header);
                    }
                    free(buf);
                    (*events)++;
                }
            } else {
                stats->ioctl_fd_miss_count++;
                if (readlink_errno) stats->fd_readlink_error_count++;
                write_unmatched_ioctl(out, opts, task->tid, fd, frame.abi, frame.syscall_nr,
                                      frame.regset_len, request, argp, target, readlink_errno, stats);
            }
        }
    } else if (task->pending.active) {
        write_exit(out, task->tid, &task->pending, frame.ret);
        memset(&task->pending, 0, sizeof(task->pending));
    }
    task->entering_syscall = !task->entering_syscall;
}

static int parse_tid_name(const char *name, pid_t *out) {
    char *end = NULL;
    errno = 0;
    long value = strtol(name, &end, 10);
    if (errno || end == name || *end != '\0' || value <= 0 || value > 4194304) return -1;
    *out = (pid_t)value;
    return 0;
}

static int enumerate_task_tids(pid_t tgid, pid_t *tids, int max_tids, FILE *out) {
    char path[128];
    snprintf(path, sizeof(path), "/proc/%ld/task", (long)tgid);
    DIR *dir = opendir(path);
    if (!dir) {
        write_error(out, "opendir-task", tgid, errno);
        return -1;
    }
    int count = 0;
    struct dirent *entry = NULL;
    while ((entry = readdir(dir)) != NULL) {
        pid_t tid = 0;
        if (parse_tid_name(entry->d_name, &tid) != 0) continue;
        if (count < max_tids) {
            tids[count++] = tid;
        }
    }
    closedir(dir);
    fprintf(out, "{\"event\":\"task-scan\",\"tgid\":%ld,\"count\":%d}\n", (long)tgid, count);
    fflush(out);
    return count;
}

static int attach_one_tid(pid_t tid, struct traced_task *tasks, int *task_count, long long deadline, FILE *out) {
    if (find_task(tasks, *task_count, tid)) return 0;
    if (ptrace(PTRACE_ATTACH, tid, NULL, NULL) != 0) {
        if (errno == ESRCH) return 0;
        write_error(out, "PTRACE_ATTACH", tid, errno);
        return -1;
    }
    int status = 0;
    int wait_rc = wait_for_specific_stop(tid, &status, deadline, out, "waitpid-attach-threadset");
    if (wait_rc != 0) {
        ptrace(PTRACE_DETACH, tid, NULL, NULL);
        return -1;
    }
    struct traced_task *task = add_task(tasks, task_count, tid, out);
    if (!task) {
        ptrace(PTRACE_DETACH, tid, NULL, NULL);
        return -1;
    }
    return 0;
}

static int attach_existing_threadset(const struct options *opts, struct traced_task *tasks, int *task_count, long long deadline, FILE *out) {
    pid_t tids[MAX_TRACED_TASKS];
    int total_attached = 0;
    for (int pass = 0; pass < 3; pass++) {
        if (now_ms() >= deadline) break;
        int count = enumerate_task_tids(opts->tgid, tids, MAX_TRACED_TASKS, out);
        if (count < 0) return -1;
        int attached_this_pass = 0;
        for (int index = 0; index < count; index++) {
            if (find_task(tasks, *task_count, tids[index])) continue;
            if (attach_one_tid(tids[index], tasks, task_count, deadline, out) == 0) {
                if (find_task(tasks, *task_count, tids[index])) {
                    attached_this_pass++;
                    total_attached++;
                }
            }
        }
        fprintf(out, "{\"event\":\"threadset-pass\",\"tgid\":%ld,\"pass\":%d,\"attached_this_pass\":%d,\"total_tracees\":%d}\n",
                (long)opts->tgid, pass + 1, attached_this_pass, *task_count);
        fflush(out);
        if (attached_this_pass == 0) break;
    }
    return total_attached > 0 ? 0 : -1;
}

static int set_options_and_resume_all(struct traced_task *tasks, int task_count, FILE *out) {
    int ok = 0;
    for (int index = 0; index < task_count; index++) {
        if (!tasks[index].alive) continue;
        if (set_trace_options(&tasks[index], out) != 0) continue;
        if (resume_syscall(&tasks[index], 0, out) != 0) continue;
        ok++;
    }
    return ok > 0 ? 0 : -1;
}

static void initialize_cloned_child(pid_t child_tid, struct traced_task *tasks, int *task_count,
                                    long long deadline, FILE *out) {
    struct traced_task *child = add_task(tasks, task_count, child_tid, out);
    if (!child) return;

    int child_status = 0;
    long long child_deadline = now_ms() + 250LL;
    if (child_deadline > deadline) child_deadline = deadline;
    int wait_rc = wait_for_specific_stop(child_tid, &child_status, child_deadline, out, "waitpid-clone-child");
    if (wait_rc != 0) return;

    if (WIFEXITED(child_status) || WIFSIGNALED(child_status)) {
        fprintf(out, "{\"event\":\"target-exit\",\"tid\":%ld,\"status\":%d}\n", (long)child_tid, child_status);
        fflush(out);
        child->alive = 0;
        return;
    }
    if (!WIFSTOPPED(child_status)) return;

    if (set_trace_options(child, out) == 0 && resume_syscall(child, 0, out) == 0) {
        write_trace_event(out, "clone-child-resumed", child_tid, 0);
    }
}

int main(int argc, char **argv) {
    struct options opts;
    if (parse_options(argc, argv, &opts)) {
        usage(argv[0]);
        return 2;
    }

    FILE *out = fopen(opts.out_path, "a");
    if (!out) {
        fprintf(stderr, "open output failed: %s\n", strerror(errno));
        return 2;
    }
    chmod(opts.out_path, 0600);
    write_header(out, &opts);

    long long deadline = now_ms() + (long long)opts.duration_sec * 1000LL;
    int status = 0;
    struct traced_task tasks[MAX_TRACED_TASKS];
    memset(tasks, 0, sizeof(tasks));
    int task_count = 0;

    if (attach_existing_threadset(&opts, tasks, &task_count, deadline, out) != 0 ||
        set_options_and_resume_all(tasks, task_count, out) != 0) {
        stop_and_detach_all(tasks, task_count, out);
        fclose(out);
        return 3;
    }

    int sequence = 0;
    int events = 0;
    int timed_out = 0;
    struct capture_stats stats;
    memset(&stats, 0, sizeof(stats));

    while (now_ms() < deadline && events < opts.max_events) {
        pid_t stopped_tid = wait_for_any_stop(&status, deadline, out);
        if (stopped_tid == 0) {
            timed_out = now_ms() >= deadline;
            if (timed_out) break;
            continue;
        }
        if (stopped_tid < 0) break;

        struct traced_task *task = find_task(tasks, task_count, stopped_tid);
        if (!task) {
            task = add_task(tasks, &task_count, stopped_tid, out);
            if (!task) continue;
        }

        if (WIFEXITED(status) || WIFSIGNALED(status)) {
            fprintf(out, "{\"event\":\"target-exit\",\"tid\":%ld,\"status\":%d}\n", (long)stopped_tid, status);
            fflush(out);
            task->alive = 0;
            continue;
        }
        if (!WIFSTOPPED(status)) {
            resume_syscall(task, 0, out);
            continue;
        }

        int stop_signal = WSTOPSIG(status);
        unsigned int ptrace_event = (unsigned int)status >> 16;
        if (stop_signal == SIGTRAP && ptrace_event == PTRACE_EVENT_CLONE) {
            unsigned long event_msg = 0;
            if (ptrace(PTRACE_GETEVENTMSG, stopped_tid, NULL, &event_msg) == 0) {
                pid_t child_tid = (pid_t)event_msg;
                write_trace_event(out, "clone", stopped_tid, child_tid);
                initialize_cloned_child(child_tid, tasks, &task_count, deadline, out);
            } else {
                write_error(out, "PTRACE_GETEVENTMSG", stopped_tid, errno);
            }
            set_trace_options(task, out);
            resume_syscall(task, 0, out);
            continue;
        }

        if (stop_signal == (SIGTRAP | 0x80)) {
            handle_syscall_stop(out, &opts, task, &sequence, &events, &stats);
            resume_syscall(task, 0, out);
            continue;
        }

        if (stop_signal == SIGSTOP || stop_signal == SIGTRAP) {
            set_trace_options(task, out);
            resume_syscall(task, 0, out);
            continue;
        }

        set_trace_options(task, out);
        resume_syscall(task, stop_signal, out);
    }

    fprintf(out,
            "{\"event\":\"stop\",\"ts_ms\":%lld,\"wall_ms\":%lld,"
            "\"captured_entries\":%d,\"tracees\":%d,\"timed_out\":%s,"
            "\"syscall_stop_count\":%d,\"syscall_entry_count\":%d,"
            "\"ioctl_any_entry_count\":%d,\"ioctl_fd_match_count\":%d,"
            "\"ioctl_fd_miss_count\":%d,\"fd_readlink_error_count\":%d,"
            "\"unmatched_samples\":%d}\n",
            now_ms(), wall_ms(), events, task_count, timed_out ? "true" : "false",
            stats.syscall_stop_count, stats.syscall_entry_count, stats.ioctl_any_entry_count,
            stats.ioctl_fd_match_count, stats.ioctl_fd_miss_count,
            stats.fd_readlink_error_count, stats.unmatched_samples);
    fflush(out);
    stop_and_detach_all(tasks, task_count, out);
    fclose(out);
    return 0;
}
