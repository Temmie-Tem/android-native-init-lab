/*
 * a90_bpf_helper_probe — bounded BPF helper capability probe.
 *
 * Scope:
 *   - load/attach tiny tracepoint programs for get_current_task/get_stackid;
 *   - load-only probe_write_user program behind a zero-valued map gate;
 *   - optionally attach a pass-through CGROUP_SKB program to a temporary cgroup;
 *   - optionally dump stackmap values after a get_stackid runtime hit.
 *
 * Safety:
 *   - default is check-only, no attach;
 *   - tracepoint attach requires --allow-attach and is duration-bound;
 *   - cgroup attach requires --allow-cgroup-attach and uses a temporary empty
 *     cgroup;
 *   - probe_write_user is never intentionally executed.
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
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
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

#ifndef BPF_FUNC_get_stackid
#define BPF_FUNC_get_stackid 27
#endif

#ifndef BPF_FUNC_get_current_task
#define BPF_FUNC_get_current_task 35
#endif

#ifndef BPF_FUNC_probe_write_user
#define BPF_FUNC_probe_write_user 36
#endif

#ifndef BPF_MAP_TYPE_STACK_TRACE
#define BPF_MAP_TYPE_STACK_TRACE 7
#endif

#ifndef BPF_PROG_TYPE_CGROUP_SKB
#define BPF_PROG_TYPE_CGROUP_SKB 8
#endif

#ifndef BPF_CGROUP_INET_INGRESS
#define BPF_CGROUP_INET_INGRESS 0
#endif

#ifndef BPF_PROG_ATTACH
#define BPF_PROG_ATTACH 8
#endif

#ifndef BPF_PROG_DETACH
#define BPF_PROG_DETACH 9
#endif

#define A90_VERSION "a90_bpf_helper_probe v2195"
#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"
#define MAX_INSNS 128
#define LOG_BUF_SIZE 65536
#define STACK_DEPTH 127
#define STACK_MAX_ENTRIES 128

#define A90_FN_map_lookup_elem 1
#define A90_FN_map_update_elem 2
#define A90_FN_get_stackid BPF_FUNC_get_stackid
#define A90_FN_get_current_task BPF_FUNC_get_current_task
#define A90_FN_probe_write_user BPF_FUNC_probe_write_user

struct emitter {
    struct bpf_insn insn[MAX_INSNS];
    int n;
};

struct probe_result {
    const char *name;
    int load_ok;
    int attach_ok;
    int runtime_ok;
    int load_errno;
    int attach_errno;
    unsigned long long count;
    unsigned long long last;
    char detail[256];
};

struct stack_dump_result {
    int requested;
    int lookup_ok;
    int lookup_errno;
    uint32_t stackid;
    int depth;
    int nonzero;
    int kernelish;
    uint64_t ips[STACK_DEPTH];
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

static int load_prog(enum bpf_prog_type type,
                     const struct bpf_insn *insns,
                     int insn_count,
                     const char *license,
                     int verbose) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    memset(log_buf, 0, sizeof(log_buf));
    attr.prog_type = type;
    attr.insns = u64ptr(insns);
    attr.insn_cnt = (uint32_t)insn_count;
    attr.license = u64ptr(license);
    if (verbose) {
        attr.log_buf = u64ptr(log_buf);
        attr.log_size = sizeof(log_buf);
        attr.log_level = 1;
    }
    return (int)sys_bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
}

static void print_verifier_log(const char *name, int verbose) {
    if (!verbose || !log_buf[0]) {
        return;
    }
    printf("verifier_log_begin name=%s\n", name);
    fputs(log_buf, stdout);
    if (log_buf[strlen(log_buf) - 1] != '\n') {
        putchar('\n');
    }
    printf("verifier_log_end name=%s\n", name);
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

static int attach_tracepoint(int prog_fd, int tp_id) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.type = PERF_TYPE_TRACEPOINT;
    attr.size = sizeof(attr);
    attr.config = (uint64_t)tp_id;
    attr.sample_period = 1;
    attr.wakeup_events = 1;
    int fd = (int)sys_perf(&attr, -1, 0, -1, PERF_FLAG_FD_CLOEXEC);
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

static void emit_stats_update(struct emitter *e, int stats_map_fd, int last_reg) {
    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -4, 0);
    emit_ld_map_fd(e, BPF_REG_1, stats_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -4);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int null_jump = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_0, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, 1);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_0, BPF_REG_1, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_0, (uint8_t)last_reg, 8, 0);
    patch_jump(e, null_jump);
}

static int build_get_current_task_prog(struct emitter *e, int stats_map_fd) {
    e->n = 0;
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_task);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_7, 0, 0, 1);
    emit_stats_update(e, stats_map_fd, BPF_REG_7);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static int build_get_stackid_prog(struct emitter *e, int stats_map_fd, int stack_map_fd) {
    e->n = 0;
    emit_ld_map_fd(e, BPF_REG_2, stack_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_3, 0, 0, BPF_F_REUSE_STACKID);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_stackid);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_7, BPF_REG_0, 0, 0);
    emit_stats_update(e, stats_map_fd, BPF_REG_7);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static int build_probe_write_user_loadonly_prog(struct emitter *e, int gate_map_fd) {
    e->n = 0;
    /*
     * Gate probe_write_user behind an ARRAY map value. The verifier must
     * validate the helper path because the map value is runtime data, while
     * the default zero value means the helper is never executed.
     */
    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -4, 0);
    emit_ld_map_fd(e, BPF_REG_1, gate_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -4);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int skip_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_0, 0, 0);
    int skip_zero = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_7, 0, 0, 0);
    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -8, 0);
    emit_ld_imm64(e, BPF_REG_1, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -8);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_3, 0, 0, 1);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_probe_write_user);
    patch_jump(e, skip_null);
    patch_jump(e, skip_zero);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static int build_cgroup_pass_prog(struct emitter *e) {
    e->n = 0;
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 1);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static void print_result(const struct probe_result *r) {
    printf("probe name=%s load_ok=%d attach_ok=%d runtime_ok=%d load_errno=%d attach_errno=%d count=%llu last=%llu detail=%s\n",
           r->name, r->load_ok, r->attach_ok, r->runtime_ok, r->load_errno,
           r->attach_errno, r->count, r->last, r->detail[0] ? r->detail : "-");
}

static int looks_kernel_address(uint64_t value) {
    return value >= 0xffffff0000000000ULL;
}

static void dump_stackmap_value(int stack_map_fd, uint64_t stackid_value) {
    struct stack_dump_result d;
    memset(&d, 0, sizeof(d));
    d.requested = 1;
    d.depth = STACK_DEPTH;

    int64_t signed_stackid = (int64_t)stackid_value;
    if (signed_stackid < 0 || signed_stackid >= STACK_MAX_ENTRIES) {
        d.lookup_errno = EINVAL;
        printf("stackmap_dump requested=%d lookup_ok=%d stackid=%lld depth=%d nonzero=%d kernelish=%d errno=%d detail=stackid_out_of_range\n",
               d.requested, d.lookup_ok, (long long)signed_stackid, d.depth,
               d.nonzero, d.kernelish, d.lookup_errno);
        return;
    }

    d.stackid = (uint32_t)signed_stackid;
    if (map_lookup(stack_map_fd, &d.stackid, d.ips) != 0) {
        d.lookup_errno = errno;
        printf("stackmap_dump requested=%d lookup_ok=%d stackid=%u depth=%d nonzero=%d kernelish=%d errno=%d detail=map_lookup_failed\n",
               d.requested, d.lookup_ok, d.stackid, d.depth, d.nonzero,
               d.kernelish, d.lookup_errno);
        return;
    }

    d.lookup_ok = 1;
    for (int i = 0; i < STACK_DEPTH; i++) {
        if (d.ips[i] != 0) {
            d.nonzero++;
        }
        if (looks_kernel_address(d.ips[i])) {
            d.kernelish++;
        }
    }
    printf("stackmap_dump requested=%d lookup_ok=%d stackid=%u depth=%d nonzero=%d kernelish=%d errno=%d detail=ok\n",
           d.requested, d.lookup_ok, d.stackid, d.depth, d.nonzero,
           d.kernelish, d.lookup_errno);
    for (int i = 0; i < STACK_DEPTH; i++) {
        if (d.ips[i] == 0) {
            continue;
        }
        printf("stack_ip index=%d value=0x%016llx kernelish=%d\n",
               i, (unsigned long long)d.ips[i], looks_kernel_address(d.ips[i]));
    }
}

static void run_trace_probe(const char *name,
                            int mode,
                            int allow_attach,
                            int duration_sec,
                            int verbose,
                            int dump_stackmap) {
    struct probe_result r;
    memset(&r, 0, sizeof(r));
    r.name = name;
    int stats_map = create_map(BPF_MAP_TYPE_ARRAY, 4, 16, 1);
    int stack_map = -1;
    if (stats_map < 0) {
        r.load_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "stats_map_create_failed");
        print_result(&r);
        return;
    }
    if (mode == 2) {
        stack_map = create_map((enum bpf_map_type)BPF_MAP_TYPE_STACK_TRACE,
                               4, STACK_DEPTH * 8, STACK_MAX_ENTRIES);
        if (stack_map < 0) {
            r.load_errno = errno;
            snprintf(r.detail, sizeof(r.detail), "stack_map_create_failed");
            close(stats_map);
            print_result(&r);
            return;
        }
    }

    struct emitter e;
    int insns = (mode == 1)
        ? build_get_current_task_prog(&e, stats_map)
        : build_get_stackid_prog(&e, stats_map, stack_map);
    int prog_fd = load_prog(BPF_PROG_TYPE_TRACEPOINT, e.insn, insns, "GPL", verbose);
    if (prog_fd < 0) {
        r.load_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "prog_load_failed:%s", log_buf[0] ? "verifier_log_available" : "no_log");
        print_verifier_log(name, verbose);
        close(stats_map);
        if (stack_map >= 0) {
            close(stack_map);
        }
        print_result(&r);
        return;
    }
    r.load_ok = 1;
    if (!allow_attach) {
        snprintf(r.detail, sizeof(r.detail), "load_only");
        close(prog_fd);
        close(stats_map);
        if (stack_map >= 0) {
            close(stack_map);
        }
        print_result(&r);
        return;
    }

    int tp_id = -1;
    if (tracepoint_id("sched", "sched_switch", &tp_id) != 0) {
        r.attach_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "sched_switch_id_failed");
        close(prog_fd);
        close(stats_map);
        if (stack_map >= 0) {
            close(stack_map);
        }
        print_result(&r);
        return;
    }
    int tp_fd = attach_tracepoint(prog_fd, tp_id);
    if (tp_fd < 0) {
        r.attach_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "attach_failed");
        close(prog_fd);
        close(stats_map);
        if (stack_map >= 0) {
            close(stack_map);
        }
        print_result(&r);
        return;
    }
    r.attach_ok = 1;
    sleep((unsigned int)duration_sec);
    uint32_t key = 0;
    uint64_t value[2] = {0, 0};
    if (map_lookup(stats_map, &key, value) == 0) {
        r.count = (unsigned long long)value[0];
        r.last = (unsigned long long)value[1];
        r.runtime_ok = value[0] > 0;
        snprintf(r.detail, sizeof(r.detail), "tp_id=%d", tp_id);
    } else {
        snprintf(r.detail, sizeof(r.detail), "stats_lookup_failed_errno_%d", errno);
    }
    ioctl(tp_fd, PERF_EVENT_IOC_DISABLE, 0);
    close(tp_fd);
    print_result(&r);
    if (mode == 2 && dump_stackmap) {
        if (r.runtime_ok) {
            dump_stackmap_value(stack_map, value[1]);
        } else {
            printf("stackmap_dump requested=1 lookup_ok=0 stackid=-1 depth=%d nonzero=0 kernelish=0 errno=%d detail=no_runtime_stackid\n",
                   STACK_DEPTH, ENOENT);
        }
    }
    close(prog_fd);
    close(stats_map);
    if (stack_map >= 0) {
        close(stack_map);
    }
}

static void run_probe_write_user_loadonly(int verbose) {
    struct probe_result r;
    memset(&r, 0, sizeof(r));
    r.name = "probe_write_user_loadonly";
    int gate_map = create_map(BPF_MAP_TYPE_ARRAY, 4, 8, 1);
    if (gate_map < 0) {
        r.load_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "gate_map_create_failed");
        print_result(&r);
        return;
    }
    struct emitter e;
    int insns = build_probe_write_user_loadonly_prog(&e, gate_map);
    int prog_fd = load_prog(BPF_PROG_TYPE_TRACEPOINT, e.insn, insns, "GPL", verbose);
    if (prog_fd < 0) {
        r.load_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "prog_load_failed:%s", log_buf[0] ? "verifier_log_available" : "no_log");
        print_verifier_log(r.name, verbose);
    } else {
        r.load_ok = 1;
        snprintf(r.detail, sizeof(r.detail), "load_only_not_attached_not_executed");
        close(prog_fd);
    }
    close(gate_map);
    print_result(&r);
}

static int bpf_prog_attach(int prog_fd, int target_fd, enum bpf_attach_type attach_type) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.target_fd = (uint32_t)target_fd;
    attr.attach_bpf_fd = (uint32_t)prog_fd;
    attr.attach_type = attach_type;
    return (int)sys_bpf((enum bpf_cmd)BPF_PROG_ATTACH, &attr, sizeof(attr));
}

static int bpf_prog_detach(int target_fd, enum bpf_attach_type attach_type) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.target_fd = (uint32_t)target_fd;
    attr.attach_type = attach_type;
    return (int)sys_bpf((enum bpf_cmd)BPF_PROG_DETACH, &attr, sizeof(attr));
}

static void run_cgroup_probe(int allow_attach, int verbose) {
    struct probe_result r;
    memset(&r, 0, sizeof(r));
    r.name = "cgroup_skb_pass";
    struct emitter e;
    int insns = build_cgroup_pass_prog(&e);
    int prog_fd = load_prog((enum bpf_prog_type)BPF_PROG_TYPE_CGROUP_SKB, e.insn, insns, "GPL", verbose);
    if (prog_fd < 0) {
        r.load_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "prog_load_failed:%s", log_buf[0] ? "verifier_log_available" : "no_log");
        print_verifier_log(r.name, verbose);
        print_result(&r);
        return;
    }
    r.load_ok = 1;
    if (!allow_attach) {
        snprintf(r.detail, sizeof(r.detail), "load_only");
        close(prog_fd);
        print_result(&r);
        return;
    }

    char path[128];
    snprintf(path, sizeof(path), "/sys/fs/cgroup/a90-bpf-v2193-%ld", (long)getpid());
    if (mkdir(path, 0700) != 0) {
        r.attach_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "mkdir_temp_cgroup_failed");
        close(prog_fd);
        print_result(&r);
        return;
    }
    int cgfd = open(path, O_DIRECTORY | O_RDONLY | O_CLOEXEC);
    if (cgfd < 0) {
        r.attach_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "open_temp_cgroup_failed");
        rmdir(path);
        close(prog_fd);
        print_result(&r);
        return;
    }
    if (bpf_prog_attach(prog_fd, cgfd, (enum bpf_attach_type)BPF_CGROUP_INET_INGRESS) == 0) {
        r.attach_ok = 1;
        r.runtime_ok = 1;
        snprintf(r.detail, sizeof(r.detail), "temp_cgroup_attach_detach");
        bpf_prog_detach(cgfd, (enum bpf_attach_type)BPF_CGROUP_INET_INGRESS);
    } else {
        r.attach_errno = errno;
        snprintf(r.detail, sizeof(r.detail), "attach_failed_temp_cgroup");
    }
    close(cgfd);
    rmdir(path);
    close(prog_fd);
    print_result(&r);
}

static void usage(const char *argv0) {
    fprintf(stderr,
        "%s\n"
        "usage: %s [--allow-attach] [--allow-cgroup-attach] [--duration SEC] [--dump-stackmap] [--verbose]\n",
        A90_VERSION, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int allow_cgroup_attach = 0;
    int verbose = 0;
    int dump_stackmap = 0;
    int duration_sec = 1;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--allow-cgroup-attach")) {
            allow_cgroup_attach = 1;
        } else if (!strcmp(argv[i], "--dump-stackmap")) {
            dump_stackmap = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--duration") && i + 1 < argc) {
            duration_sec = atoi(argv[++i]);
            if (duration_sec < 1) {
                duration_sec = 1;
            }
            if (duration_sec > 5) {
                duration_sec = 5;
            }
        } else if (!strcmp(argv[i], "--help")) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    struct rlimit rl;
    rl.rlim_cur = RLIM_INFINITY;
    rl.rlim_max = RLIM_INFINITY;
    setrlimit(RLIMIT_MEMLOCK, &rl);

    printf("%s\n", A90_VERSION);
    printf("allow_attach=%d allow_cgroup_attach=%d duration_sec=%d dump_stackmap=%d verbose=%d\n",
           allow_attach, allow_cgroup_attach, duration_sec, dump_stackmap, verbose);
    run_trace_probe("get_current_task", 1, allow_attach, duration_sec, verbose, 0);
    run_trace_probe("get_stackid", 2, allow_attach, duration_sec, verbose, dump_stackmap);
    run_probe_write_user_loadonly(verbose);
    run_cgroup_probe(allow_cgroup_attach, verbose);
    printf("result=v2195-helper-capability-probe-complete\n");
    return 0;
}
