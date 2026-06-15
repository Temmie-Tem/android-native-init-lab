// V2415 Android-side msm_audio_cal ioctl observer.
// Measurement-only helper: attaches to an Android audio process, records ioctl
// metadata and copies the user request buffer before the kernel sees it.  It
// does not open /dev/msm_audio_cal itself and does not issue any audio ioctl.

#define _GNU_SOURCE
#include <asm/unistd.h>
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <asm/ptrace.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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

#define DEFAULT_MAX_BYTES 512U
#define DEFAULT_DURATION_SEC 8
#define DEFAULT_MAX_EVENTS 64

struct options {
    pid_t pid;
    const char *out_path;
    const char *device_substr;
    size_t max_bytes;
    int duration_sec;
    int max_events;
};

struct pending_ioctl {
    int active;
    int seq;
    long fd;
    unsigned long request;
    unsigned long argp;
};

static void usage(const char *argv0) {
    fprintf(stderr,
            "usage: %s --pid PID --out PATH [--device-substr /dev/msm_audio_cal] "
            "[--max-bytes 512] [--duration-sec 8] [--max-events 64]\n",
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
    opts->out_path = NULL;
    opts->device_substr = "/dev/msm_audio_cal";
    opts->max_bytes = DEFAULT_MAX_BYTES;
    opts->duration_sec = DEFAULT_DURATION_SEC;
    opts->max_events = DEFAULT_MAX_EVENTS;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--pid") && i + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++i], 1, 4194304, &value)) return -1;
            opts->pid = (pid_t)value;
        } else if (!strcmp(argv[i], "--out") && i + 1 < argc) {
            opts->out_path = argv[++i];
        } else if (!strcmp(argv[i], "--device-substr") && i + 1 < argc) {
            opts->device_substr = argv[++i];
        } else if (!strcmp(argv[i], "--max-bytes") && i + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++i], 1, 4096, &value)) return -1;
            opts->max_bytes = (size_t)value;
        } else if (!strcmp(argv[i], "--duration-sec") && i + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++i], 1, 120, &value)) return -1;
            opts->duration_sec = (int)value;
        } else if (!strcmp(argv[i], "--max-events") && i + 1 < argc) {
            long value = 0;
            if (parse_int_arg(argv[++i], 1, 4096, &value)) return -1;
            opts->max_events = (int)value;
        } else {
            return -1;
        }
    }
    return (opts->pid > 0 && opts->out_path != NULL) ? 0 : -1;
}

static long long now_ms(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)tv.tv_sec * 1000LL + (long long)tv.tv_usec / 1000LL;
}

static int get_regs(pid_t pid, struct user_pt_regs *regs) {
    struct iovec iov;
    memset(regs, 0, sizeof(*regs));
    iov.iov_base = regs;
    iov.iov_len = sizeof(*regs);
    return ptrace(PTRACE_GETREGSET, pid, (void *)(uintptr_t)NT_PRSTATUS, &iov);
}

static int fd_matches_device(pid_t pid, long fd, const char *needle, char *target, size_t target_size) {
    char path[128];
    snprintf(path, sizeof(path), "/proc/%ld/fd/%ld", (long)pid, fd);
    ssize_t n = readlink(path, target, target_size - 1);
    if (n < 0) {
        snprintf(target, target_size, "readlink-error:%s", strerror(errno));
        return 0;
    }
    target[n] = '\0';
    return strstr(target, needle) != NULL;
}

static ssize_t read_remote_process_vm(pid_t pid, unsigned long remote, unsigned char *buf, size_t len) {
    struct iovec local_iov = {.iov_base = buf, .iov_len = len};
    struct iovec remote_iov = {.iov_base = (void *)(uintptr_t)remote, .iov_len = len};
    return process_vm_readv(pid, &local_iov, 1, &remote_iov, 1, 0);
}

static ssize_t read_remote_ptrace(pid_t pid, unsigned long remote, unsigned char *buf, size_t len) {
    size_t copied = 0;
    while (copied < len) {
        errno = 0;
        long word = ptrace(PTRACE_PEEKDATA, pid, (void *)(uintptr_t)(remote + copied), NULL);
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

static ssize_t read_remote(pid_t pid, unsigned long remote, unsigned char *buf, size_t len) {
    if (remote == 0 || len == 0) return 0;
    ssize_t n = read_remote_process_vm(pid, remote, buf, len);
    if (n >= 0) return n;
    return read_remote_ptrace(pid, remote, buf, len);
}

static void json_escape(FILE *fp, const char *text) {
    for (const unsigned char *p = (const unsigned char *)text; *p; p++) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', fp);
            fputc(*p, fp);
        } else if (*p >= 0x20 && *p <= 0x7e) {
            fputc(*p, fp);
        } else {
            fprintf(fp, "\\u%04x", *p);
        }
    }
}

static void write_hex(FILE *fp, const unsigned char *buf, ssize_t len) {
    static const char hexdigits[] = "0123456789abcdef";
    for (ssize_t i = 0; i < len; i++) {
        fputc(hexdigits[(buf[i] >> 4) & 0xf], fp);
        fputc(hexdigits[buf[i] & 0xf], fp);
    }
}

static void write_header(FILE *fp, const struct options *opts) {
    fprintf(fp,
            "{\"event\":\"start\",\"pid\":%ld,\"duration_sec\":%d,"
            "\"max_bytes\":%zu,\"device_substr\":\"",
            (long)opts->pid, opts->duration_sec, opts->max_bytes);
    json_escape(fp, opts->device_substr);
    fprintf(fp, "\",\"note\":\"private raw hex; do not commit\"}\n");
    fflush(fp);
}

static void write_error(FILE *fp, const char *where, int errnum) {
    fprintf(fp, "{\"event\":\"error\",\"where\":\"");
    json_escape(fp, where);
    fprintf(fp, "\",\"errno\":%d,\"strerror\":\"", errnum);
    json_escape(fp, strerror(errnum));
    fprintf(fp, "\"}\n");
    fflush(fp);
}

static void write_entry(FILE *fp, int seq, pid_t pid, const char *fd_target,
                        unsigned long request, unsigned long argp,
                        const unsigned char *buf, ssize_t read_len, int read_errno) {
    fprintf(fp,
            "{\"event\":\"ioctl_entry\",\"seq\":%d,\"pid\":%ld,"
            "\"request\":\"0x%lx\",\"argp\":\"0x%lx\",\"fd_target\":\"",
            seq, (long)pid, request, argp);
    json_escape(fp, fd_target);
    fprintf(fp, "\",\"read_len\":%zd,\"read_errno\":%d,\"bytes_hex\":\"",
            read_len > 0 ? read_len : 0, read_errno);
    if (read_len > 0) write_hex(fp, buf, read_len);
    fprintf(fp, "\"}\n");
    fflush(fp);
}

static void write_exit(FILE *fp, const struct pending_ioctl *pending, long ret) {
    fprintf(fp,
            "{\"event\":\"ioctl_exit\",\"seq\":%d,\"request\":\"0x%lx\","
            "\"argp\":\"0x%lx\",\"ret\":%ld}\n",
            pending->seq, pending->request, pending->argp, ret);
    fflush(fp);
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

    if (ptrace(PTRACE_ATTACH, opts.pid, NULL, NULL) != 0) {
        write_error(out, "PTRACE_ATTACH", errno);
        fclose(out);
        return 3;
    }

    int status = 0;
    if (waitpid(opts.pid, &status, 0) < 0) {
        write_error(out, "waitpid-attach", errno);
        ptrace(PTRACE_DETACH, opts.pid, NULL, NULL);
        fclose(out);
        return 3;
    }
    if (ptrace(PTRACE_SETOPTIONS, opts.pid, NULL, (void *)(uintptr_t)PTRACE_O_TRACESYSGOOD) != 0) {
        write_error(out, "PTRACE_SETOPTIONS", errno);
    }

    long long deadline = now_ms() + (long long)opts.duration_sec * 1000LL;
    int entering = 1;
    int seq = 0;
    int events = 0;
    int signal_to_deliver = 0;
    struct pending_ioctl pending;
    memset(&pending, 0, sizeof(pending));

    while (now_ms() < deadline && events < opts.max_events) {
        if (ptrace(PTRACE_SYSCALL, opts.pid, NULL, (void *)(uintptr_t)signal_to_deliver) != 0) {
            write_error(out, "PTRACE_SYSCALL", errno);
            break;
        }
        signal_to_deliver = 0;
        if (waitpid(opts.pid, &status, 0) < 0) {
            write_error(out, "waitpid-loop", errno);
            break;
        }
        if (WIFEXITED(status) || WIFSIGNALED(status)) {
            fprintf(out, "{\"event\":\"target-exit\",\"status\":%d}\n", status);
            break;
        }
        if (!WIFSTOPPED(status)) continue;
        int sig = WSTOPSIG(status);
        if (sig != (SIGTRAP | 0x80)) {
            signal_to_deliver = sig;
            continue;
        }

        struct user_pt_regs regs;
        if (get_regs(opts.pid, &regs) != 0) {
            write_error(out, "PTRACE_GETREGSET", errno);
            break;
        }

        if (entering) {
            unsigned long syscall_nr = regs.regs[8];
            if (syscall_nr == __NR_ioctl) {
                long fd = (long)regs.regs[0];
                unsigned long request = regs.regs[1];
                unsigned long argp = regs.regs[2];
                char target[512];
                target[0] = '\0';
                if (fd_matches_device(opts.pid, fd, opts.device_substr, target, sizeof(target))) {
                    unsigned char *buf = calloc(1, opts.max_bytes);
                    if (!buf) {
                        write_error(out, "calloc", errno);
                    } else {
                        errno = 0;
                        ssize_t n = read_remote(opts.pid, argp, buf, opts.max_bytes);
                        int read_errno = (n < 0) ? errno : 0;
                        seq++;
                        pending.active = 1;
                        pending.seq = seq;
                        pending.fd = fd;
                        pending.request = request;
                        pending.argp = argp;
                        write_entry(out, seq, opts.pid, target, request, argp, buf, n, read_errno);
                        free(buf);
                        events++;
                    }
                }
            }
        } else {
            if (pending.active) {
                long ret = (long)regs.regs[0];
                write_exit(out, &pending, ret);
                memset(&pending, 0, sizeof(pending));
            }
        }
        entering = !entering;
    }

    fprintf(out, "{\"event\":\"stop\",\"captured_entries\":%d}\n", events);
    fflush(out);
    ptrace(PTRACE_DETACH, opts.pid, NULL, NULL);
    fclose(out);
    return 0;
}
