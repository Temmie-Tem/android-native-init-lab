/*
 * a90_bpf_workqueue_func_sample_ring — bounded workqueue function sampler.
 *
 * Captures workqueue:workqueue_queue_work and workqueue:workqueue_execute_start
 * tracepoints into a small BPF array map.  The only kernel reads are scalar
 * tracepoint-record fields already copied by the kernel tracepoint itself.
 *
 * Safety: read-only BPF tracepoint attach.  No tracefs control writes, no
 * network action, no probe_write_user, no kernel or partition writes.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef __NR_bpf
#define __NR_bpf 280
#endif

#ifndef BPF_PSEUDO_MAP_FD
#define BPF_PSEUDO_MAP_FD 1
#endif

#define A90_VERSION "a90_bpf_workqueue_func_sample_ring v2273"

#define A90_FN_map_lookup_elem 1
#define A90_FN_ktime_get_ns 5
#define A90_FN_get_current_pid_tgid 14

#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"

#define MAX_INSNS 512
#define MAX_CPUS 16
#define MAX_SAMPLES 2048

#define KIND_QUEUE_WORK 1
#define KIND_EXECUTE_START 2

/* Static tracepoint record offsets for Samsung 4.14 workqueue events. */
#define QUEUE_CTX_WORK 8
#define QUEUE_CTX_FUNCTION 16
#define QUEUE_CTX_WORKQUEUE 24
#define QUEUE_CTX_REQ_CPU 32
#define QUEUE_CTX_CPU 36
#define EXEC_CTX_WORK 8
#define EXEC_CTX_FUNCTION 16

struct sample_value {
    uint64_t kind;
    uint64_t seq;
    uint64_t ts_ns;
    uint64_t pid_tgid;
    uint64_t work;
    uint64_t function;
    uint64_t workqueue;
    uint64_t req_cpu;
    uint64_t cpu;
};

struct stats_value {
    uint64_t total;
    uint64_t stored;
    uint64_t queue_work;
    uint64_t execute_start;
    uint64_t overflow;
};

struct emitter {
    struct bpf_insn insn[MAX_INSNS];
    int n;
};

static uint64_t u64ptr(const void *p) {
    return (uint64_t)(uintptr_t)p;
}

static long sys_bpf(enum bpf_cmd cmd, union bpf_attr *attr, unsigned int size) {
    return syscall(__NR_bpf, cmd, attr, size);
}

static long sys_perf(struct perf_event_attr *attr, pid_t pid, int cpu, int group, unsigned long flags) {
    return syscall(__NR_perf_event_open, attr, pid, cpu, group, flags);
}

static int emit(struct emitter *e, uint8_t code, uint8_t dst, uint8_t src, int16_t off, int32_t imm) {
    if (e->n >= MAX_INSNS) {
        fprintf(stderr, "emit overflow\n");
        exit(3);
    }
    struct bpf_insn in;
    memset(&in, 0, sizeof(in));
    in.code = code;
    in.dst_reg = dst;
    in.src_reg = src;
    in.off = off;
    in.imm = imm;
    e->insn[e->n++] = in;
    return e->n - 1;
}

static void patch_jump(struct emitter *e, int at) {
    e->insn[at].off = (int16_t)(e->n - at - 1);
}

static void emit_ld_imm64(struct emitter *e, uint8_t dst, uint8_t src, int64_t imm) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, src, 0, (int32_t)(imm & 0xffffffff));
    emit(e, 0, 0, 0, 0, (int32_t)((uint64_t)imm >> 32));
}

static void emit_ld_map_fd(struct emitter *e, uint8_t dst, int map_fd) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, BPF_PSEUDO_MAP_FD, 0, map_fd);
    emit(e, 0, 0, 0, 0, 0);
}

static void emit_inc_u64(struct emitter *e, int off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_1, (int16_t)off, 0);
}

static void emit_store_imm64(struct emitter *e, int off, uint64_t value) {
    emit_ld_imm64(e, BPF_REG_1, 0, (int64_t)value);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_1, (int16_t)off, 0);
}

static void emit_store_ctx_u64(struct emitter *e, int sample_off, int ctx_off) {
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_9, (int16_t)ctx_off, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_1, (int16_t)sample_off, 0);
}

static void emit_store_ctx_u32_as_u64(struct emitter *e, int sample_off, int ctx_off) {
    emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_1, BPF_REG_9, (int16_t)ctx_off, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_1, (int16_t)sample_off, 0);
}

static int create_map(enum bpf_map_type type, uint32_t key_size, uint32_t value_size, uint32_t max_entries) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_type = type;
    attr.key_size = key_size;
    attr.value_size = value_size;
    attr.max_entries = max_entries;
    return (int)sys_bpf(BPF_MAP_CREATE, &attr, sizeof(attr));
}

static int map_lookup(int map_fd, const void *key, void *value) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_fd = (uint32_t)map_fd;
    attr.key = u64ptr(key);
    attr.value = u64ptr(value);
    return (int)sys_bpf(BPF_MAP_LOOKUP_ELEM, &attr, sizeof(attr));
}

static int load_prog(const struct bpf_insn *insns, int insn_count, int verbose) {
    char license[] = "GPL";
    static char log_buf[32768];
    log_buf[0] = '\0';
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.prog_type = BPF_PROG_TYPE_TRACEPOINT;
    attr.insn_cnt = (uint32_t)insn_count;
    attr.insns = u64ptr(insns);
    attr.license = u64ptr(license);
    if (verbose) {
        attr.log_buf = u64ptr(log_buf);
        attr.log_size = sizeof(log_buf);
        attr.log_level = 1;
    }
    int fd = (int)sys_bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
    if (fd < 0 && verbose && log_buf[0]) {
        fprintf(stderr, "bpf_log=%s\n", log_buf);
    }
    return fd;
}

static const char *tracefs_base(void) {
    if (access(TRACEFS_A, R_OK) == 0) {
        return TRACEFS_A;
    }
    return TRACEFS_B;
}

static int tracepoint_id(const char *group, const char *event, int *out) {
    char path[512];
    FILE *file;
    int value;
    snprintf(path, sizeof(path), "%s/%s/%s/id", tracefs_base(), group, event);
    file = fopen(path, "r");
    if (!file) {
        return -1;
    }
    if (fscanf(file, "%d", &value) != 1 || value <= 0) {
        fclose(file);
        errno = EINVAL;
        return -1;
    }
    fclose(file);
    *out = value;
    return 0;
}

static int attach_tracepoint_cpu(int prog_fd, int tp_id, int cpu) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.type = PERF_TYPE_TRACEPOINT;
    attr.size = sizeof(attr);
    attr.config = (uint64_t)tp_id;
    attr.sample_period = 1;
    attr.wakeup_events = 1;
    int fd = (int)sys_perf(&attr, -1, cpu, -1, PERF_FLAG_FD_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    if (ioctl(fd, PERF_EVENT_IOC_SET_BPF, prog_fd) != 0) {
        int saved = errno;
        close(fd);
        errno = saved;
        return -1;
    }
    if (ioctl(fd, PERF_EVENT_IOC_ENABLE, 0) != 0) {
        int saved = errno;
        close(fd);
        errno = saved;
        return -1;
    }
    return fd;
}

static int build_workqueue_prog(struct emitter *e,
                                int stats_map_fd,
                                int samples_map_fd,
                                int kind) {
    const bool is_queue = kind == KIND_QUEUE_WORK;
    e->n = 0;

    /* R9 = tracepoint ctx. */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_9, BPF_REG_1, 0, 0);

    /* stats = map_lookup(stats_map, &key0) -> R8. */
    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -4, 0);
    emit_ld_map_fd(e, BPF_REG_1, stats_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -4);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int stats_ok = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, stats_ok);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_8, BPF_REG_0, 0, 0);

    /* R6 = seq before increment. */
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8,
         (int16_t)offsetof(struct stats_value, total), 0);
    emit_inc_u64(e, (int)offsetof(struct stats_value, total));
    emit_inc_u64(e, is_queue ? (int)offsetof(struct stats_value, queue_work)
                              : (int)offsetof(struct stats_value, execute_start));

    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, MAX_SAMPLES);
    int below_limit = emit(e, BPF_JMP | BPF_JGT | BPF_X, BPF_REG_1, BPF_REG_6, 0, 0);
    emit_inc_u64(e, (int)offsetof(struct stats_value, overflow));
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, below_limit);

    /* sample = map_lookup(samples_map, &seq). */
    emit(e, BPF_STX | BPF_MEM | BPF_W, BPF_REG_10, BPF_REG_6, -8, 0);
    emit_ld_map_fd(e, BPF_REG_1, samples_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -8);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int sample_ok = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, sample_ok);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_7, BPF_REG_0, 0, 0);

    emit_inc_u64(e, (int)offsetof(struct stats_value, stored));

    emit_store_imm64(e, (int)offsetof(struct sample_value, kind), (uint64_t)kind);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_6,
         (int16_t)offsetof(struct sample_value, seq), 0);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_ktime_get_ns);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_0,
         (int16_t)offsetof(struct sample_value, ts_ns), 0);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_pid_tgid);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_0,
         (int16_t)offsetof(struct sample_value, pid_tgid), 0);

    emit_store_ctx_u64(e, (int)offsetof(struct sample_value, work),
                       is_queue ? QUEUE_CTX_WORK : EXEC_CTX_WORK);
    emit_store_ctx_u64(e, (int)offsetof(struct sample_value, function),
                       is_queue ? QUEUE_CTX_FUNCTION : EXEC_CTX_FUNCTION);
    if (is_queue) {
        emit_store_ctx_u64(e, (int)offsetof(struct sample_value, workqueue), QUEUE_CTX_WORKQUEUE);
        emit_store_ctx_u32_as_u64(e, (int)offsetof(struct sample_value, req_cpu), QUEUE_CTX_REQ_CPU);
        emit_store_ctx_u32_as_u64(e, (int)offsetof(struct sample_value, cpu), QUEUE_CTX_CPU);
    } else {
        emit_store_imm64(e, (int)offsetof(struct sample_value, workqueue), 0);
        emit_store_imm64(e, (int)offsetof(struct sample_value, req_cpu), 0);
        emit_store_imm64(e, (int)offsetof(struct sample_value, cpu), 0);
    }

    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static void sleep_ms(int duration_ms) {
    struct timespec ts;
    ts.tv_sec = duration_ms / 1000;
    ts.tv_nsec = (long)(duration_ms % 1000) * 1000000L;
    while (nanosleep(&ts, &ts) != 0 && errno == EINTR) {
    }
}

static uint64_t parse_u64(const char *text) {
    return strtoull(text, NULL, 0);
}

static const char *kind_name(uint64_t kind) {
    if (kind == KIND_QUEUE_WORK) {
        return "queue_work";
    }
    if (kind == KIND_EXECUTE_START) {
        return "execute_start";
    }
    return "unknown";
}

static void usage(const char *argv0) {
    fprintf(stderr,
            "%s\n"
            "usage: %s [--duration-ms N] [--print-limit N] [--allow-attach] [--verbose]\n"
            "default is check-only/load-only; attach requires --allow-attach\n",
            A90_VERSION, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int verbose = 0;
    int duration_ms = 45000;
    int print_limit = MAX_SAMPLES;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--duration-ms") && i + 1 < argc) {
            duration_ms = (int)parse_u64(argv[++i]);
            if (duration_ms < 1 || duration_ms > 120000) {
                fprintf(stderr, "duration-ms must be 1..120000\n");
                return 2;
            }
        } else if (!strcmp(argv[i], "--print-limit") && i + 1 < argc) {
            print_limit = (int)parse_u64(argv[++i]);
            if (print_limit < 1 || print_limit > MAX_SAMPLES) {
                fprintf(stderr, "print-limit must be 1..%d\n", MAX_SAMPLES);
                return 2;
            }
        } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    printf("%s\n", A90_VERSION);
    printf("allow_attach=%d duration_ms=%d print_limit=%d verbose=%d max_samples=%d\n",
           allow_attach, duration_ms, print_limit, verbose, MAX_SAMPLES);
    printf("offsets queue_work.work=%d queue_work.function=%d queue_work.workqueue=%d queue_work.req_cpu=%d queue_work.cpu=%d execute_start.work=%d execute_start.function=%d\n",
           QUEUE_CTX_WORK, QUEUE_CTX_FUNCTION, QUEUE_CTX_WORKQUEUE,
           QUEUE_CTX_REQ_CPU, QUEUE_CTX_CPU, EXEC_CTX_WORK, EXEC_CTX_FUNCTION);

    struct rlimit rl = { RLIM_INFINITY, RLIM_INFINITY };
    if (setrlimit(RLIMIT_MEMLOCK, &rl) != 0 && verbose) {
        fprintf(stderr, "setrlimit(MEMLOCK) failed: %s\n", strerror(errno));
    }

    int stats_map = create_map(BPF_MAP_TYPE_ARRAY, 4, sizeof(struct stats_value), 1);
    if (stats_map < 0) {
        printf("result=map-create-failed map=stats errno=%d\n", errno);
        perror("stats-map");
        return 1;
    }
    int samples_map = create_map(BPF_MAP_TYPE_ARRAY, 4, sizeof(struct sample_value), MAX_SAMPLES);
    if (samples_map < 0) {
        printf("result=map-create-failed map=samples errno=%d\n", errno);
        perror("samples-map");
        close(stats_map);
        return 1;
    }

    struct emitter queue_emitter;
    struct emitter execute_emitter;
    int queue_insns = build_workqueue_prog(&queue_emitter, stats_map, samples_map, KIND_QUEUE_WORK);
    int execute_insns = build_workqueue_prog(&execute_emitter, stats_map, samples_map, KIND_EXECUTE_START);
    printf("insn_cnt queue_work=%d execute_start=%d\n", queue_insns, execute_insns);

    int queue_prog = load_prog(queue_emitter.insn, queue_insns, verbose);
    if (queue_prog < 0) {
        int saved = errno;
        printf("result=bpf-load-failed event=queue_work errno=%d\n", saved);
        perror("bpf-load-queue");
        close(samples_map);
        close(stats_map);
        return 1;
    }
    int execute_prog = load_prog(execute_emitter.insn, execute_insns, verbose);
    if (execute_prog < 0) {
        int saved = errno;
        printf("result=bpf-load-failed event=execute_start errno=%d\n", saved);
        perror("bpf-load-execute");
        close(queue_prog);
        close(samples_map);
        close(stats_map);
        return 1;
    }
    printf("bpf_prog_fd queue_work=%d execute_start=%d\n", queue_prog, execute_prog);

    if (!allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        close(execute_prog);
        close(queue_prog);
        close(samples_map);
        close(stats_map);
        return 0;
    }

    int queue_tp = -1;
    int execute_tp = -1;
    if (tracepoint_id("workqueue", "workqueue_queue_work", &queue_tp) != 0) {
        printf("result=tracepoint-id-failed event=queue_work errno=%d\n", errno);
        close(execute_prog);
        close(queue_prog);
        close(samples_map);
        close(stats_map);
        return 1;
    }
    if (tracepoint_id("workqueue", "workqueue_execute_start", &execute_tp) != 0) {
        printf("result=tracepoint-id-failed event=execute_start errno=%d\n", errno);
        close(execute_prog);
        close(queue_prog);
        close(samples_map);
        close(stats_map);
        return 1;
    }
    printf("tracepoint_id queue_work=%d execute_start=%d\n", queue_tp, execute_tp);

    int ncpu = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpu < 1) {
        ncpu = 1;
    }
    if (ncpu > MAX_CPUS) {
        ncpu = MAX_CPUS;
    }
    int fds[MAX_CPUS * 2];
    int fd_count = 0;
    int queue_attach_ok = 0;
    int execute_attach_ok = 0;
    for (int cpu = 0; cpu < ncpu; cpu++) {
        int fd = attach_tracepoint_cpu(queue_prog, queue_tp, cpu);
        if (fd >= 0) {
            fds[fd_count++] = fd;
            queue_attach_ok++;
        } else if (verbose) {
            fprintf(stderr, "attach queue cpu=%d failed errno=%d\n", cpu, errno);
        }
        fd = attach_tracepoint_cpu(execute_prog, execute_tp, cpu);
        if (fd >= 0) {
            fds[fd_count++] = fd;
            execute_attach_ok++;
        } else if (verbose) {
            fprintf(stderr, "attach execute cpu=%d failed errno=%d\n", cpu, errno);
        }
    }
    printf("attach_attempted=1 ncpu=%d queue_attach_ok=%d execute_attach_ok=%d\n",
           ncpu, queue_attach_ok, execute_attach_ok);
    if (queue_attach_ok == 0 && execute_attach_ok == 0) {
        printf("result=attach-failed errno=%d\n", errno);
        close(execute_prog);
        close(queue_prog);
        close(samples_map);
        close(stats_map);
        return 1;
    }

    printf("observe_begin=1\n");
    fflush(stdout);
    sleep_ms(duration_ms);
    printf("observe_end=1\n");

    for (int i = 0; i < fd_count; i++) {
        ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
        close(fds[i]);
    }

    uint32_t key = 0;
    struct stats_value stats;
    memset(&stats, 0, sizeof(stats));
    if (map_lookup(stats_map, &key, &stats) != 0) {
        printf("result=stats-read-failed errno=%d\n", errno);
        close(execute_prog);
        close(queue_prog);
        close(samples_map);
        close(stats_map);
        return 1;
    }
    printf("stats total=%" PRIu64 " stored=%" PRIu64 " queue_work=%" PRIu64 " execute_start=%" PRIu64 " overflow=%" PRIu64 "\n",
           stats.total, stats.stored, stats.queue_work, stats.execute_start, stats.overflow);

    uint64_t to_print = stats.stored;
    if (to_print > (uint64_t)print_limit) {
        to_print = (uint64_t)print_limit;
    }
    printf("samples printed=%" PRIu64 " print_limit=%d\n", to_print, print_limit);
    for (uint32_t i = 0; i < (uint32_t)to_print; i++) {
        struct sample_value sample;
        memset(&sample, 0, sizeof(sample));
        if (map_lookup(samples_map, &i, &sample) != 0) {
            printf("sample index=%u lookup=0 errno=%d\n", i, errno);
            continue;
        }
        uint32_t pid = (uint32_t)(sample.pid_tgid & 0xffffffffULL);
        uint32_t tgid = (uint32_t)(sample.pid_tgid >> 32);
        printf("sample index=%u kind=%s kind_id=%" PRIu64 " seq=%" PRIu64 " ts_ns=%" PRIu64 " pid=%u tgid=%u work=0x%016" PRIx64 " function=0x%016" PRIx64 " workqueue=0x%016" PRIx64 " req_cpu=%" PRIu64 " cpu=%" PRIu64 "\n",
               i, kind_name(sample.kind), sample.kind, sample.seq, sample.ts_ns,
               pid, tgid, sample.work, sample.function, sample.workqueue,
               sample.req_cpu, sample.cpu);
    }

    printf("result=v2273-workqueue-func-sample-ring-complete\n");
    close(execute_prog);
    close(queue_prog);
    close(samples_map);
    close(stats_map);
    return 0;
}
