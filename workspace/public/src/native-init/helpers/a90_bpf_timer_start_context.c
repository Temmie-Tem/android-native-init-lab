/*
 * a90_bpf_timer_start_context — bounded timer_start context probe.
 *
 * Scope:
 *   - tracepoint: timer:timer_start only;
 *   - read tracepoint ctx fields: timer, function, expires, now, flags;
 *   - optionally filter one runtime function pointer;
 *   - capture current pid/tgid, comm, and stackid for matching events;
 *   - dump one ARRAY summary and one STACK_TRACE map value from userspace.
 *
 * Safety:
 *   - default is check-only/load-only;
 *   - attach requires --allow-attach;
 *   - duration bounded to 1..30 seconds;
 *   - no tracefs writes, no cgroup attach, no probe_write_user, no kernel write.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
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

#ifndef BPF_F_REUSE_STACKID
#define BPF_F_REUSE_STACKID (1ULL << 10)
#endif

#ifndef BPF_FUNC_get_current_pid_tgid
#define BPF_FUNC_get_current_pid_tgid 14
#endif

#ifndef BPF_FUNC_get_current_comm
#define BPF_FUNC_get_current_comm 16
#endif

#ifndef BPF_FUNC_get_stackid
#define BPF_FUNC_get_stackid 27
#endif

#ifndef BPF_MAP_TYPE_STACK_TRACE
#define BPF_MAP_TYPE_STACK_TRACE 7
#endif

#define A90_VERSION "a90_bpf_timer_start_context v2200"
#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"
#define MAX_INSNS 256
#define LOG_BUF_SIZE 65536
#define STACK_DEPTH 127
#define STACK_MAX_ENTRIES 256
#define MAX_CPUS 32

#define A90_FN_map_lookup_elem 1
#define A90_FN_get_current_pid_tgid BPF_FUNC_get_current_pid_tgid
#define A90_FN_get_current_comm BPF_FUNC_get_current_comm
#define A90_FN_get_stackid BPF_FUNC_get_stackid

/* timer:timer_start tracepoint ctx offsets on this 4.14 kernel. */
#define CTX_TIMER 8
#define CTX_FUNCTION 16
#define CTX_EXPIRES 24
#define CTX_NOW 32
#define CTX_FLAGS 40

struct summary_value {
    uint64_t count;
    uint64_t last_function;
    uint64_t last_timer;
    uint64_t last_expires;
    uint64_t last_now;
    int64_t last_timeout;
    uint64_t last_pid_tgid;
    int64_t last_stackid;
    uint64_t last_flags;
    uint64_t timeout_min;
    uint64_t timeout_max;
    uint64_t timeout_sum;
    uint64_t timeout_eq1_count;
    uint64_t timeout_le4_count;
    uint64_t timeout_eq18000_count;
    uint64_t timeout_ge1000_count;
    uint64_t timeout_zero_count;
    char comm[16];
};

struct emitter {
    struct bpf_insn insn[MAX_INSNS];
    int n;
};

static char log_buf[LOG_BUF_SIZE];

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
        fprintf(stderr, "emit_overflow=1\n");
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

static void patch_jump(struct emitter *e, int idx) {
    e->insn[idx].off = (int16_t)(e->n - idx - 1);
}

static void emit_ld_imm64(struct emitter *e, uint8_t dst, uint8_t src, int64_t imm) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, src, 0, (int32_t)(imm & 0xffffffff));
    emit(e, 0, 0, 0, 0, (int32_t)((uint64_t)imm >> 32));
}

static void emit_ld_map_fd(struct emitter *e, uint8_t dst, int map_fd) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, BPF_PSEUDO_MAP_FD, 0, map_fd);
    emit(e, 0, 0, 0, 0, 0);
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
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    memset(log_buf, 0, sizeof(log_buf));
    attr.prog_type = BPF_PROG_TYPE_TRACEPOINT;
    attr.insns = u64ptr(insns);
    attr.insn_cnt = (uint32_t)insn_count;
    attr.license = u64ptr("GPL");
    if (verbose) {
        attr.log_buf = u64ptr(log_buf);
        attr.log_size = sizeof(log_buf);
        attr.log_level = 1;
    }
    return (int)sys_bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
}

static int read_int_file(const char *path, int *out) {
    char buf[64];
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (n <= 0) {
        return -1;
    }
    buf[n] = '\0';
    *out = atoi(buf);
    return 0;
}

static int tracepoint_id(const char *group, const char *event, int *out) {
    char path[256];
    snprintf(path, sizeof(path), "%s/%s/%s/id", TRACEFS_A, group, event);
    if (read_int_file(path, out) == 0) {
        return 0;
    }
    snprintf(path, sizeof(path), "%s/%s/%s/id", TRACEFS_B, group, event);
    return read_int_file(path, out);
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

static int looks_kernel_address(uint64_t value) {
    return value >= 0xffffff0000000000ULL;
}

static void emit_store_ctx_u64(struct emitter *e, int value_off, int ctx_off) {
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, ctx_off, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6, value_off, 0);
}

static void emit_inc_u64(struct emitter *e, int value_off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_7, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_7, value_off, 0);
}

static int build_timer_start_prog(struct emitter *e,
                                  int summary_map_fd,
                                  int stack_map_fd,
                                  uint64_t filter_function) {
    e->n = 0;
    /* R9 = ctx */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_9, BPF_REG_1, 0, 0);

    /* R7 = ctx->function */
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_9, CTX_FUNCTION, 0);
    if (filter_function) {
        emit_ld_imm64(e, BPF_REG_6, 0, (int64_t)filter_function);
        int keep = emit(e, BPF_JMP | BPF_JEQ | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
        emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
        patch_jump(e, keep);
    }

    /* summary = map_lookup(summary_map, &key0) */
    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -4, 0);
    emit_ld_map_fd(e, BPF_REG_1, summary_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -4);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int summary_ok = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, summary_ok);

    /* R8 = summary value pointer */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_8, BPF_REG_0, 0, 0);

    /* count += 1 */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_6, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, count), 0);

    /* Last scalar fields. */
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7,
         (int16_t)offsetof(struct summary_value, last_function), 0);
    emit_store_ctx_u64(e, (int)offsetof(struct summary_value, last_timer), CTX_TIMER);
    emit_store_ctx_u64(e, (int)offsetof(struct summary_value, last_expires), CTX_EXPIRES);
    emit_store_ctx_u64(e, (int)offsetof(struct summary_value, last_now), CTX_NOW);

    /* timeout = expires - now */
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, CTX_EXPIRES, 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_9, CTX_NOW, 0);
    emit(e, BPF_ALU64 | BPF_SUB | BPF_X, BPF_REG_6, BPF_REG_7, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, last_timeout), 0);

    /* Timeout distribution. Keep before helper calls so R8 remains map-value PTR. */
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, timeout_sum), 0);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct summary_value, timeout_min), 0);
    int min_zero = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_7, 0, 0, 0);
    int min_gt = emit(e, BPF_JMP | BPF_JGT | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    int min_skip = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, min_zero);
    patch_jump(e, min_gt);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, timeout_min), 0);
    patch_jump(e, min_skip);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct summary_value, timeout_max), 0);
    int max_skip = emit(e, BPF_JMP | BPF_JGT | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, timeout_max), 0);
    patch_jump(e, max_skip);

    int zero_skip = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_inc_u64(e, (int)offsetof(struct summary_value, timeout_zero_count));
    patch_jump(e, zero_skip);

    int eq1_skip = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_6, 0, 0, 1);
    emit_inc_u64(e, (int)offsetof(struct summary_value, timeout_eq1_count));
    patch_jump(e, eq1_skip);

    int le4_skip = emit(e, BPF_JMP | BPF_JGT | BPF_K, BPF_REG_6, 0, 0, 4);
    emit_inc_u64(e, (int)offsetof(struct summary_value, timeout_le4_count));
    patch_jump(e, le4_skip);

    int eq18000_skip = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_6, 0, 0, 18000);
    emit_inc_u64(e, (int)offsetof(struct summary_value, timeout_eq18000_count));
    patch_jump(e, eq18000_skip);

    int ge1000_update = emit(e, BPF_JMP | BPF_JGT | BPF_K, BPF_REG_6, 0, 0, 999);
    int ge1000_skip = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, ge1000_update);
    emit_inc_u64(e, (int)offsetof(struct summary_value, timeout_ge1000_count));
    patch_jump(e, ge1000_skip);

    emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_6, BPF_REG_9, CTX_FLAGS, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, last_flags), 0);

    /* current pid/tgid */
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_pid_tgid);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_0,
         (int16_t)offsetof(struct summary_value, last_pid_tgid), 0);

    /* stackid */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_9, 0, 0);
    emit_ld_map_fd(e, BPF_REG_2, stack_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_3, 0, 0, BPF_F_REUSE_STACKID);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_stackid);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_0,
         (int16_t)offsetof(struct summary_value, last_stackid), 0);

    /* current comm into stack, then copy two u64 chunks into map value. */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, -32);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, 16);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_comm);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_10, -32, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct summary_value, comm), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_10, -24, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)(offsetof(struct summary_value, comm) + 8), 0);

    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static void print_stackmap_value(int stack_map_fd, int64_t stackid) {
    uint64_t ips[STACK_DEPTH];
    memset(ips, 0, sizeof(ips));
    if (stackid < 0 || stackid >= STACK_MAX_ENTRIES) {
        printf("stackmap_dump requested=1 lookup_ok=0 stackid=%lld depth=%d nonzero=0 kernelish=0 errno=%d detail=stackid_out_of_range\n",
               (long long)stackid, STACK_DEPTH, EINVAL);
        return;
    }
    uint32_t key = (uint32_t)stackid;
    if (map_lookup(stack_map_fd, &key, ips) != 0) {
        printf("stackmap_dump requested=1 lookup_ok=0 stackid=%u depth=%d nonzero=0 kernelish=0 errno=%d detail=map_lookup_failed\n",
               key, STACK_DEPTH, errno);
        return;
    }
    int nonzero = 0;
    int kernelish = 0;
    for (int i = 0; i < STACK_DEPTH; i++) {
        if (ips[i]) {
            nonzero++;
        }
        if (looks_kernel_address(ips[i])) {
            kernelish++;
        }
    }
    printf("stackmap_dump requested=1 lookup_ok=1 stackid=%u depth=%d nonzero=%d kernelish=%d errno=0 detail=ok\n",
           key, STACK_DEPTH, nonzero, kernelish);
    for (int i = 0; i < STACK_DEPTH; i++) {
        if (!ips[i]) {
            continue;
        }
        printf("stack_ip index=%d value=0x%016llx kernelish=%d\n",
               i, (unsigned long long)ips[i], looks_kernel_address(ips[i]));
    }
}

static void print_summary(const struct summary_value *value) {
    uint32_t pid = (uint32_t)(value->last_pid_tgid & 0xffffffffULL);
    uint32_t tgid = (uint32_t)(value->last_pid_tgid >> 32);
    char comm[17];
    memset(comm, 0, sizeof(comm));
    memcpy(comm, value->comm, sizeof(value->comm));
    printf("summary count=%llu last_function=0x%016llx last_timer=0x%016llx last_expires=%llu last_now=%llu last_timeout=%lld last_flags=0x%llx last_pid=%u last_tgid=%u last_stackid=%lld comm=%s timeout_min=%llu timeout_max=%llu timeout_sum=%llu timeout_eq1=%llu timeout_le4=%llu timeout_eq18000=%llu timeout_ge1000=%llu timeout_zero=%llu\n",
           (unsigned long long)value->count,
           (unsigned long long)value->last_function,
           (unsigned long long)value->last_timer,
           (unsigned long long)value->last_expires,
           (unsigned long long)value->last_now,
           (long long)value->last_timeout,
           (unsigned long long)value->last_flags,
           pid,
           tgid,
           (long long)value->last_stackid,
           comm[0] ? comm : "-",
           (unsigned long long)value->timeout_min,
           (unsigned long long)value->timeout_max,
           (unsigned long long)value->timeout_sum,
           (unsigned long long)value->timeout_eq1_count,
           (unsigned long long)value->timeout_le4_count,
           (unsigned long long)value->timeout_eq18000_count,
           (unsigned long long)value->timeout_ge1000_count,
           (unsigned long long)value->timeout_zero_count);
}

static uint64_t parse_u64(const char *s) {
    return strtoull(s, NULL, 0);
}

static void usage(const char *argv0) {
    fprintf(stderr,
        "%s\n"
        "usage: %s [--filter-function HEX] [--duration SEC] [--allow-attach] [--verbose]\n"
        "default: check-only/load-only, no attach\n",
        A90_VERSION, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int verbose = 0;
    int duration_sec = 2;
    uint64_t filter_function = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--duration") && i + 1 < argc) {
            duration_sec = atoi(argv[++i]);
            if (duration_sec < 1 || duration_sec > 30) {
                fprintf(stderr, "duration must be 1..30\n");
                return 2;
            }
        } else if (!strcmp(argv[i], "--filter-function") && i + 1 < argc) {
            filter_function = parse_u64(argv[++i]);
        } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    printf("%s\n", A90_VERSION);
    printf("allow_attach=%d duration_sec=%d filter_function=0x%016llx verbose=%d\n",
           allow_attach, duration_sec, (unsigned long long)filter_function, verbose);

    struct rlimit rl = { RLIM_INFINITY, RLIM_INFINITY };
    if (setrlimit(RLIMIT_MEMLOCK, &rl) != 0 && verbose) {
        fprintf(stderr, "setrlimit(MEMLOCK) failed: %s\n", strerror(errno));
    }

    int summary_map = create_map(BPF_MAP_TYPE_ARRAY, 4, sizeof(struct summary_value), 1);
    if (summary_map < 0) {
        printf("result=map-create-failed map=summary errno=%d\n", errno);
        perror("summary-map");
        return 1;
    }
    int stack_map = create_map((enum bpf_map_type)BPF_MAP_TYPE_STACK_TRACE,
                               4, STACK_DEPTH * 8, STACK_MAX_ENTRIES);
    if (stack_map < 0) {
        printf("result=map-create-failed map=stack errno=%d\n", errno);
        perror("stack-map");
        close(summary_map);
        return 1;
    }

    struct emitter e;
    int insns = build_timer_start_prog(&e, summary_map, stack_map, filter_function);
    printf("insn_cnt=%d\n", insns);
    int prog_fd = load_prog(e.insn, insns, verbose);
    if (prog_fd < 0) {
        int saved = errno;
        printf("result=bpf-load-failed errno=%d log_available=%d\n", saved, log_buf[0] ? 1 : 0);
        if (verbose && log_buf[0]) {
            printf("verifier_log_begin\n%s\nverifier_log_end\n", log_buf);
        }
        close(stack_map);
        close(summary_map);
        return 1;
    }
    printf("bpf_prog_fd=%d\n", prog_fd);

    if (!allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        close(prog_fd);
        close(stack_map);
        close(summary_map);
        return 0;
    }

    int tp_id = -1;
    if (tracepoint_id("timer", "timer_start", &tp_id) != 0) {
        printf("result=tracepoint-id-failed errno=%d\n", errno);
        close(prog_fd);
        close(stack_map);
        close(summary_map);
        return 1;
    }
    printf("tracepoint_id=%d\n", tp_id);

    int ncpu = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpu < 1) {
        ncpu = 1;
    }
    if (ncpu > MAX_CPUS) {
        ncpu = MAX_CPUS;
    }
    int fds[MAX_CPUS];
    int attach_ok = 0;
    memset(fds, -1, sizeof(fds));
    for (int cpu = 0; cpu < ncpu; cpu++) {
        int fd = attach_tracepoint_cpu(prog_fd, tp_id, cpu);
        if (fd >= 0) {
            fds[attach_ok++] = fd;
        } else if (verbose) {
            fprintf(stderr, "attach cpu=%d failed errno=%d\n", cpu, errno);
        }
    }
    printf("attach_attempted=1 attach_ok=%d ncpu=%d\n", attach_ok, ncpu);
    if (attach_ok == 0) {
        printf("result=attach-failed errno=%d\n", errno);
        close(prog_fd);
        close(stack_map);
        close(summary_map);
        return 1;
    }

    printf("observe_begin=1\n");
    fflush(stdout);
    sleep((unsigned int)duration_sec);
    printf("observe_end=1\n");

    for (int i = 0; i < attach_ok; i++) {
        ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
        close(fds[i]);
    }

    uint32_t key = 0;
    struct summary_value value;
    memset(&value, 0, sizeof(value));
    if (map_lookup(summary_map, &key, &value) != 0) {
        printf("result=summary-read-failed errno=%d\n", errno);
        close(prog_fd);
        close(stack_map);
        close(summary_map);
        return 1;
    }
    print_summary(&value);
    print_stackmap_value(stack_map, value.last_stackid);
    printf("result=v2200-timer-start-context-complete\n");

    close(prog_fd);
    close(stack_map);
    close(summary_map);
    return 0;
}
