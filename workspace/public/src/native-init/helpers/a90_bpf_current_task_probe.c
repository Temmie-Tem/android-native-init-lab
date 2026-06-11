/*
 * a90_bpf_current_task_probe — V2194 current_task read-chain probe.
 *
 * Purpose:
 *   - combine V2192 probe_read with V2193 bpf_get_current_task;
 *   - discover task_struct offsets live by comparing task memory against BPF
 *     helpers for current pid/tgid/uid/comm;
 *   - keep the run bounded and read-only.
 *
 * Safety:
 *   - no attach unless --allow-attach is supplied;
 *   - only sched:sched_switch tracepoint is used;
 *   - no kernel writes, no probe_write_user, no cgroup attach, no Wi-Fi action;
 *   - all kernel memory access is bpf_probe_read only.
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

#define A90_VERSION "a90_bpf_current_task_probe v2194"
#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"
#define MAX_INSNS 256
#define LOG_BUF_SIZE 32768

#define A90_FN_map_lookup_elem 1
#define A90_FN_probe_read 4
#define A90_FN_get_current_pid_tgid 14
#define A90_FN_get_current_uid_gid 15
#define A90_FN_get_current_comm 16
#define A90_FN_get_current_task 35

struct emitter {
    struct bpf_insn insn[MAX_INSNS];
    int n;
};

struct stats {
    uint64_t total;
    uint64_t hits;
    uint64_t last0;
    uint64_t last1;
};

enum probe_kind {
    PROBE_COMM,
    PROBE_PID,
    PROBE_TGID,
    PROBE_CRED,
};

struct candidate_result {
    int off;
    struct stats stats;
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

static void emit_ld_map_fd(struct emitter *e, uint8_t dst, int map_fd) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, BPF_PSEUDO_MAP_FD, 0, map_fd);
    emit(e, 0, 0, 0, 0, 0);
}

static void emit_zero_stack(struct emitter *e, int16_t off, int size) {
    if (size >= 8) {
        emit(e, BPF_ST | BPF_MEM | BPF_DW, BPF_REG_10, 0, off, 0);
        if (size >= 16) {
            emit(e, BPF_ST | BPF_MEM | BPF_DW, BPF_REG_10, 0, (int16_t)(off + 8), 0);
        }
    } else {
        emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, off, 0);
    }
}

static int emit_probe_read_stack(struct emitter *e, int16_t stack_off, int size, uint8_t base_reg, int candidate_off, int check_ret) {
    emit_zero_stack(e, stack_off, size);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, stack_off);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, size);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_3, base_reg, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_3, 0, 0, candidate_off);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_probe_read);
    if (check_ret) {
        return emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    }
    return -1;
}

static void emit_u32_low(struct emitter *e, uint8_t reg) {
    emit(e, BPF_ALU64 | BPF_LSH | BPF_K, reg, 0, 0, 32);
    emit(e, BPF_ALU64 | BPF_RSH | BPF_K, reg, 0, 0, 32);
}

static void emit_stats_lookup(struct emitter *e, int map_fd) {
    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -80, 0);
    emit_ld_map_fd(e, BPF_REG_1, map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -80);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
}

static void emit_xadd_one(struct emitter *e, int value_off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_0, BPF_REG_1, (int16_t)value_off, 0);
}

static void emit_update_total(struct emitter *e, int map_fd) {
    emit_stats_lookup(e, map_fd);
    int jnull = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_0, 0, 0, 0);
    emit_xadd_one(e, 0);
    patch_jump(e, jnull);
}

static void emit_update_hit(struct emitter *e, int map_fd, uint8_t last0_reg, uint8_t last1_reg) {
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, last0_reg, -96, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, last1_reg, -88, 0);
    emit_stats_lookup(e, map_fd);
    int jnull = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_0, 0, 0, 0);
    emit_xadd_one(e, 8);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_10, -96, 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_2, BPF_REG_10, -88, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_0, last0_reg, 16, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_0, last1_reg, 24, 0);
    patch_jump(e, jnull);
}

static int build_candidate_prog(struct emitter *e, int map_fd, enum probe_kind kind, int off, int cred_uid_off, int cred_euid_off) {
    e->n = 0;

    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_task);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_0, 0, 0); /* task */
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_pid_tgid);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_7, BPF_REG_0, 0, 0); /* pid_tgid */
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_uid_gid);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_8, BPF_REG_0, 0, 0); /* uid_gid */

    emit_update_total(e, map_fd);

    if (kind == PROBE_COMM) {
        emit_zero_stack(e, -16, 16);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, -16);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, 16);
        emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_comm);
        int jerr = emit_probe_read_stack(e, -32, 16, BPF_REG_6, off, 1);
        emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_10, -16, 0);
        emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_2, BPF_REG_10, -32, 0);
        int jne0 = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_1, BPF_REG_2, 0, 0);
        emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_10, -8, 0);
        emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_2, BPF_REG_10, -24, 0);
        int jne1 = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_1, BPF_REG_2, 0, 0);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_7, 0, 0);
        emit_u32_low(e, BPF_REG_1);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_7, 0, 0);
        emit(e, BPF_ALU64 | BPF_RSH | BPF_K, BPF_REG_2, 0, 0, 32);
        emit_update_hit(e, map_fd, BPF_REG_1, BPF_REG_2);
        patch_jump(e, jerr);
        patch_jump(e, jne0);
        patch_jump(e, jne1);
    } else if (kind == PROBE_PID || kind == PROBE_TGID) {
        int jerr = emit_probe_read_stack(e, -16, 4, BPF_REG_6, off, 1);
        emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_1, BPF_REG_10, -16, 0);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_4, BPF_REG_7, 0, 0);
        emit_u32_low(e, BPF_REG_4);
        int jzero = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_4, 0, 0, 0);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_7, 0, 0);
        if (kind == PROBE_PID) {
            emit_u32_low(e, BPF_REG_2);
        } else {
            emit(e, BPF_ALU64 | BPF_RSH | BPF_K, BPF_REG_2, 0, 0, 32);
        }
        int jne = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_1, BPF_REG_2, 0, 0);
        emit_update_hit(e, map_fd, BPF_REG_1, BPF_REG_2);
        patch_jump(e, jerr);
        patch_jump(e, jzero);
        patch_jump(e, jne);
    } else if (kind == PROBE_CRED) {
        int jerr0 = emit_probe_read_stack(e, -16, 8, BPF_REG_6, off, 1);
        emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_10, -16, 0); /* cred ptr */
        int jnull = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_9, 0, 0, 0);
        int jerr1 = emit_probe_read_stack(e, -40, 8, BPF_REG_6, off - 8, 1);
        emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_4, BPF_REG_10, -40, 0); /* real_cred ptr */
        int jne_ptr = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_9, BPF_REG_4, 0, 0);
        int jerr2 = emit_probe_read_stack(e, -24, 4, BPF_REG_9, cred_uid_off, 1);
        int jerr3 = emit_probe_read_stack(e, -32, 4, BPF_REG_9, cred_euid_off, 1);
        emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_1, BPF_REG_10, -24, 0); /* uid */
        emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_2, BPF_REG_10, -32, 0); /* euid */
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_3, BPF_REG_8, 0, 0);
        emit_u32_low(e, BPF_REG_3);
        int jne0 = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_1, BPF_REG_3, 0, 0);
        int jne1 = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_2, BPF_REG_3, 0, 0);
        emit_update_hit(e, map_fd, BPF_REG_1, BPF_REG_2);
        patch_jump(e, jerr0);
        patch_jump(e, jnull);
        patch_jump(e, jerr1);
        patch_jump(e, jne_ptr);
        patch_jump(e, jerr2);
        patch_jump(e, jerr3);
        patch_jump(e, jne0);
        patch_jump(e, jne1);
    }

    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static int create_stats_map(void) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_type = BPF_MAP_TYPE_ARRAY;
    attr.key_size = 4;
    attr.value_size = sizeof(struct stats);
    attr.max_entries = 1;
    return (int)sys_bpf(BPF_MAP_CREATE, &attr, sizeof(attr));
}

static int map_lookup_stats(int map_fd, struct stats *out) {
    uint32_t key = 0;
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_fd = (uint32_t)map_fd;
    attr.key = u64ptr(&key);
    attr.value = u64ptr(out);
    return (int)sys_bpf(BPF_MAP_LOOKUP_ELEM, &attr, sizeof(attr));
}

static int load_prog(const struct emitter *e, int verbose) {
    char license[] = "GPL";
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    memset(log_buf, 0, sizeof(log_buf));
    attr.prog_type = BPF_PROG_TYPE_TRACEPOINT;
    attr.insn_cnt = (uint32_t)e->n;
    attr.insns = u64ptr(e->insn);
    attr.license = u64ptr(license);
    if (verbose) {
        attr.log_buf = u64ptr(log_buf);
        attr.log_size = sizeof(log_buf);
        attr.log_level = 1;
    }
    int fd = (int)sys_bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
    if (fd < 0 && verbose && log_buf[0]) {
        printf("verifier_log_begin\n%s\nverifier_log_end\n", log_buf);
    }
    return fd;
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

static int run_candidate(enum probe_kind kind, int off, int dwell_ms, int allow_attach, int verbose,
                         int cred_uid_off, int cred_euid_off, struct stats *out) {
    memset(out, 0, sizeof(*out));
    int map_fd = create_stats_map();
    if (map_fd < 0) {
        return -1;
    }
    struct emitter e;
    build_candidate_prog(&e, map_fd, kind, off, cred_uid_off, cred_euid_off);
    int prog_fd = load_prog(&e, verbose);
    if (prog_fd < 0) {
        int saved = errno;
        close(map_fd);
        errno = saved;
        return -1;
    }
    if (!allow_attach) {
        close(prog_fd);
        close(map_fd);
        return 0;
    }
    int tp_id = -1;
    if (tracepoint_id("sched", "sched_switch", &tp_id) != 0) {
        int saved = errno;
        close(prog_fd);
        close(map_fd);
        errno = saved;
        return -1;
    }
    int tp_fd = attach_tracepoint(prog_fd, tp_id);
    if (tp_fd < 0) {
        int saved = errno;
        close(prog_fd);
        close(map_fd);
        errno = saved;
        return -1;
    }
    usleep((useconds_t)dwell_ms * 1000U);
    map_lookup_stats(map_fd, out);
    ioctl(tp_fd, PERF_EVENT_IOC_DISABLE, 0);
    close(tp_fd);
    close(prog_fd);
    close(map_fd);
    return 0;
}

static void maybe_record_top(struct candidate_result *top, int top_n, int off, const struct stats *stats) {
    if (stats->hits == 0) {
        return;
    }
    for (int i = 0; i < top_n; i++) {
        if (stats->hits > top[i].stats.hits) {
            for (int j = top_n - 1; j > i; j--) {
                top[j] = top[j - 1];
            }
            top[i].off = off;
            top[i].stats = *stats;
            return;
        }
    }
}

static const char *kind_name(enum probe_kind kind) {
    switch (kind) {
        case PROBE_COMM: return "comm";
        case PROBE_PID: return "pid";
        case PROBE_TGID: return "tgid";
        case PROBE_CRED: return "cred";
        default: return "unknown";
    }
}

static int scan_kind(enum probe_kind kind, int start, int end, int step, int dwell_ms, int allow_attach,
                     int verbose, int cred_uid_off, int cred_euid_off, struct candidate_result *best) {
    struct candidate_result top[5];
    memset(top, 0, sizeof(top));
    best->off = -1;
    memset(&best->stats, 0, sizeof(best->stats));

    for (int off = start; off <= end; off += step) {
        struct stats stats;
        if (run_candidate(kind, off, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &stats) != 0) {
            printf("probe kind=%s off=%d error_errno=%d\n", kind_name(kind), off, errno);
            return -1;
        }
        maybe_record_top(top, 5, off, &stats);
    }

    printf("scan kind=%s start=%d end=%d step=%d dwell_ms=%d\n", kind_name(kind), start, end, step, dwell_ms);
    for (int i = 0; i < 5; i++) {
        if (top[i].stats.hits == 0) {
            continue;
        }
        printf("candidate rank=%d kind=%s off=%d total=%llu hits=%llu last0=%llu last1=%llu\n",
               i + 1, kind_name(kind), top[i].off,
               (unsigned long long)top[i].stats.total,
               (unsigned long long)top[i].stats.hits,
               (unsigned long long)top[i].stats.last0,
               (unsigned long long)top[i].stats.last1);
    }
    *best = top[0];
    return 0;
}

static void usage(const char *argv0) {
    fprintf(stderr,
        "%s\n"
        "usage: %s [--allow-attach] [--start N] [--end N] [--dwell-ms N] [--verbose]\n"
        "       %s --allow-attach --comm-off N --pid-off N --tgid-off N --cred-off N\n"
        "default scans task_struct comm/pid/tgid/cred offsets via sched:sched_switch.\n",
        A90_VERSION, argv0, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int verbose = 0;
    int start = 0;
    int end = 4096;
    int dwell_ms = 10;
    int cred_uid_off = 4;
    int cred_euid_off = 20;
    int fixed_comm_off = -1;
    int fixed_pid_off = -1;
    int fixed_tgid_off = -1;
    int fixed_cred_off = -1;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--start") && i + 1 < argc) {
            start = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--end") && i + 1 < argc) {
            end = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--dwell-ms") && i + 1 < argc) {
            dwell_ms = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--cred-uid-off") && i + 1 < argc) {
            cred_uid_off = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--cred-euid-off") && i + 1 < argc) {
            cred_euid_off = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--comm-off") && i + 1 < argc) {
            fixed_comm_off = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--pid-off") && i + 1 < argc) {
            fixed_pid_off = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--tgid-off") && i + 1 < argc) {
            fixed_tgid_off = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--cred-off") && i + 1 < argc) {
            fixed_cred_off = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--help")) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    if (start < 0) start = 0;
    if (end < start) end = start;
    if (end > 8192) end = 8192;
    if (dwell_ms < 1) dwell_ms = 1;
    if (dwell_ms > 100) dwell_ms = 100;

    struct rlimit rl;
    rl.rlim_cur = RLIM_INFINITY;
    rl.rlim_max = RLIM_INFINITY;
    setrlimit(RLIMIT_MEMLOCK, &rl);

    printf("%s\n", A90_VERSION);
    printf("allow_attach=%d start=%d end=%d dwell_ms=%d cred_uid_off=%d cred_euid_off=%d\n",
           allow_attach, start, end, dwell_ms, cred_uid_off, cred_euid_off);

    if (fixed_comm_off >= 0 || fixed_pid_off >= 0 || fixed_tgid_off >= 0 || fixed_cred_off >= 0) {
        if (fixed_comm_off < 0 || fixed_pid_off < 0 || fixed_tgid_off < 0 || fixed_cred_off < 0) {
            fprintf(stderr, "fixed mode requires --comm-off/--pid-off/--tgid-off/--cred-off\n");
            return 2;
        }
        struct stats comm_stats, pid_stats, tgid_stats, cred_stats;
        int rc = 0;
        if (run_candidate(PROBE_COMM, fixed_comm_off, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &comm_stats) != 0) rc = 1;
        if (run_candidate(PROBE_PID, fixed_pid_off, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &pid_stats) != 0) rc = 1;
        if (run_candidate(PROBE_TGID, fixed_tgid_off, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &tgid_stats) != 0) rc = 1;
        if (run_candidate(PROBE_CRED, fixed_cred_off, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &cred_stats) != 0) rc = 1;
        printf("fixed kind=comm off=%d total=%llu hits=%llu last0=%llu last1=%llu\n",
               fixed_comm_off, (unsigned long long)comm_stats.total, (unsigned long long)comm_stats.hits,
               (unsigned long long)comm_stats.last0, (unsigned long long)comm_stats.last1);
        printf("fixed kind=pid off=%d total=%llu hits=%llu last0=%llu last1=%llu\n",
               fixed_pid_off, (unsigned long long)pid_stats.total, (unsigned long long)pid_stats.hits,
               (unsigned long long)pid_stats.last0, (unsigned long long)pid_stats.last1);
        printf("fixed kind=tgid off=%d total=%llu hits=%llu last0=%llu last1=%llu\n",
               fixed_tgid_off, (unsigned long long)tgid_stats.total, (unsigned long long)tgid_stats.hits,
               (unsigned long long)tgid_stats.last0, (unsigned long long)tgid_stats.last1);
        printf("fixed kind=cred off=%d total=%llu hits=%llu last0=%llu last1=%llu\n",
               fixed_cred_off, (unsigned long long)cred_stats.total, (unsigned long long)cred_stats.hits,
               (unsigned long long)cred_stats.last0, (unsigned long long)cred_stats.last1);
        if (!allow_attach) {
            printf("decision=v2194-current-task-readchain-fixed-check-only\n");
        } else if (!rc && comm_stats.hits && pid_stats.hits && tgid_stats.hits && cred_stats.hits) {
            printf("decision=v2194-current-task-readchain-pass\n");
        } else {
            printf("decision=v2194-current-task-readchain-incomplete\n");
        }
        return rc;
    }

    struct candidate_result best_comm, best_pid, best_tgid, best_cred;
    int rc = 0;
    if (scan_kind(PROBE_COMM, start, end, 8, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &best_comm) != 0) rc = 1;
    if (scan_kind(PROBE_PID, start, end, 4, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &best_pid) != 0) rc = 1;
    if (scan_kind(PROBE_TGID, start, end, 4, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &best_tgid) != 0) rc = 1;
    if (scan_kind(PROBE_CRED, start, end, 8, dwell_ms, allow_attach, verbose, cred_uid_off, cred_euid_off, &best_cred) != 0) rc = 1;

    printf("summary comm_off=%d comm_hits=%llu pid_off=%d pid_hits=%llu tgid_off=%d tgid_hits=%llu cred_off=%d cred_hits=%llu\n",
           best_comm.off, (unsigned long long)best_comm.stats.hits,
           best_pid.off, (unsigned long long)best_pid.stats.hits,
           best_tgid.off, (unsigned long long)best_tgid.stats.hits,
           best_cred.off, (unsigned long long)best_cred.stats.hits);

    if (!allow_attach) {
        printf("decision=v2194-current-task-readchain-check-only\n");
    } else if (!rc && best_comm.stats.hits && best_pid.stats.hits && best_tgid.stats.hits && best_cred.stats.hits) {
        printf("decision=v2194-current-task-readchain-pass\n");
    } else {
        printf("decision=v2194-current-task-readchain-incomplete\n");
    }
    return rc;
}
