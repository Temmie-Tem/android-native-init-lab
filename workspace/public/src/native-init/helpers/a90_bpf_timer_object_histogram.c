/*
 * a90_bpf_timer_object_histogram — bounded timer_start object histogram.
 *
 * Scope:
 *   - tracepoint: timer:timer_start only;
 *   - key rows by timer_start.function;
 *   - read tracepoint ctx fields and struct timer_list fields;
 *   - capture current pid/tgid, comm, and stackid per row;
 *   - dump sorted userspace rows for object-discriminator analysis.
 *
 * Safety:
 *   - default is check-only/load-only;
 *   - attach requires --allow-attach;
 *   - duration bounded to 1..30 seconds;
 *   - --busy-observe avoids self-generating schedule_timeout sleeps;
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

#ifndef BPF_ANY
#define BPF_ANY 0
#endif

#define A90_VERSION "a90_bpf_timer_object_histogram v2202"
#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"
#define MAX_INSNS 768
#define LOG_BUF_SIZE 65536
#define STACK_DEPTH 127
#define STACK_MAX_ENTRIES 512
#define MAX_CPUS 32
#define DEFAULT_MAX_ROWS 4096

#define A90_FN_map_lookup_elem 1
#define A90_FN_map_update_elem 2
#define A90_FN_probe_read 4
#define A90_FN_get_current_pid_tgid BPF_FUNC_get_current_pid_tgid
#define A90_FN_get_current_comm BPF_FUNC_get_current_comm
#define A90_FN_get_stackid BPF_FUNC_get_stackid

#define CTX_TIMER 8
#define CTX_FUNCTION 16
#define CTX_EXPIRES 24
#define CTX_NOW 32
#define CTX_FLAGS 40

#define TIMER_ENTRY_NEXT 0
#define TIMER_ENTRY_PPREV 8
#define TIMER_EXPIRES 16
#define TIMER_FUNCTION 24
#define TIMER_DATA 32
#define TIMER_FLAGS 40

#define KEY_OFF (-8)
#define SCRATCH_OFF (-16)
#define COMM_OFF (-40)
#define INIT_VALUE_OFF (-224)

struct row_value {
    uint64_t count;
    uint64_t last_timer;
    uint64_t last_expires;
    uint64_t last_now;
    int64_t last_timeout;
    uint64_t last_flags;
    uint64_t obj_entry_next;
    uint64_t obj_entry_pprev;
    uint64_t obj_expires;
    uint64_t obj_function;
    uint64_t obj_data;
    int64_t obj_data_delta;
    uint64_t obj_flags;
    uint64_t timeout_min;
    uint64_t timeout_max;
    uint64_t timeout_sum;
    uint64_t obj_read_errors;
    uint64_t obj_function_match;
    uint64_t obj_expires_match;
    uint64_t last_pid_tgid;
    int64_t last_stackid;
    char comm[16];
};

struct dumped_row {
    uint64_t function;
    struct row_value value;
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

static int map_get_next_key(int map_fd, const void *key, void *next_key) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.map_fd = (uint32_t)map_fd;
    attr.key = key ? u64ptr(key) : 0;
    attr.next_key = u64ptr(next_key);
    return (int)sys_bpf(BPF_MAP_GET_NEXT_KEY, &attr, sizeof(attr));
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

static void emit_inc_u64(struct emitter *e, int value_off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_7, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_7, value_off, 0);
}

static int emit_probe_read_stack(struct emitter *e, int16_t stack_off, int size, uint8_t base_reg, int candidate_off) {
    if (size == 8) {
        emit(e, BPF_ST | BPF_MEM | BPF_DW, BPF_REG_10, 0, stack_off, 0);
    } else {
        emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, stack_off, 0);
    }
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, stack_off);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, size);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_3, base_reg, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_3, 0, 0, candidate_off);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_probe_read);
    return emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
}

static void emit_read_timer_u64(struct emitter *e, int value_off, int timer_off) {
    int jerr = emit_probe_read_stack(e, SCRATCH_OFF, 8, BPF_REG_6, timer_off);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_10, SCRATCH_OFF, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7, value_off, 0);
    int jdone = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, jerr);
    emit_inc_u64(e, (int)offsetof(struct row_value, obj_read_errors));
    patch_jump(e, jdone);
}

static void emit_read_timer_u32_as_u64(struct emitter *e, int value_off, int timer_off) {
    int jerr = emit_probe_read_stack(e, SCRATCH_OFF, 4, BPF_REG_6, timer_off);
    emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_7, BPF_REG_10, SCRATCH_OFF, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7, value_off, 0);
    int jdone = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, jerr);
    emit_inc_u64(e, (int)offsetof(struct row_value, obj_read_errors));
    patch_jump(e, jdone);
}

static void emit_zero_init_value(struct emitter *e) {
    for (int off = 0; off < (int)sizeof(struct row_value); off += 8) {
        emit(e, BPF_ST | BPF_MEM | BPF_DW, BPF_REG_10, 0, INIT_VALUE_OFF + off, 0);
    }
}

static void emit_map_lookup_by_key(struct emitter *e, int row_map_fd) {
    emit_ld_map_fd(e, BPF_REG_1, row_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, KEY_OFF);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
}

static int build_timer_histogram_prog(struct emitter *e, int row_map_fd, int stack_map_fd) {
    e->n = 0;
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_9, BPF_REG_1, 0, 0);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_9, CTX_FUNCTION, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, BPF_REG_7, KEY_OFF, 0);

    emit_map_lookup_by_key(e, row_map_fd);
    int found = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit_zero_init_value(e);
    emit_ld_map_fd(e, BPF_REG_1, row_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, KEY_OFF);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_3, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_3, 0, 0, INIT_VALUE_OFF);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_4, 0, 0, BPF_ANY);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_update_elem);
    emit_map_lookup_by_key(e, row_map_fd);
    patch_jump(e, found);
    int row_ok = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, row_ok);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_8, BPF_REG_0, 0, 0);

    emit_inc_u64(e, (int)offsetof(struct row_value, count));

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, CTX_TIMER, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, last_timer), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, CTX_EXPIRES, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, last_expires), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_9, CTX_NOW, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7,
         (int16_t)offsetof(struct row_value, last_now), 0);
    emit(e, BPF_ALU64 | BPF_SUB | BPF_X, BPF_REG_6, BPF_REG_7, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, last_timeout), 0);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, timeout_sum), 0);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct row_value, timeout_min), 0);
    int min_zero = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_7, 0, 0, 0);
    int min_gt = emit(e, BPF_JMP | BPF_JGT | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    int min_skip = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, min_zero);
    patch_jump(e, min_gt);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, timeout_min), 0);
    patch_jump(e, min_skip);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct row_value, timeout_max), 0);
    int max_skip = emit(e, BPF_JMP | BPF_JGT | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, timeout_max), 0);
    patch_jump(e, max_skip);

    emit(e, BPF_LDX | BPF_MEM | BPF_W, BPF_REG_6, BPF_REG_9, CTX_FLAGS, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, last_flags), 0);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, CTX_TIMER, 0);
    emit_read_timer_u64(e, (int)offsetof(struct row_value, obj_entry_next), TIMER_ENTRY_NEXT);
    emit_read_timer_u64(e, (int)offsetof(struct row_value, obj_entry_pprev), TIMER_ENTRY_PPREV);
    emit_read_timer_u64(e, (int)offsetof(struct row_value, obj_expires), TIMER_EXPIRES);
    emit_read_timer_u64(e, (int)offsetof(struct row_value, obj_function), TIMER_FUNCTION);
    emit_read_timer_u64(e, (int)offsetof(struct row_value, obj_data), TIMER_DATA);
    emit_read_timer_u32_as_u64(e, (int)offsetof(struct row_value, obj_flags), TIMER_FLAGS);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct row_value, obj_data), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8,
         (int16_t)offsetof(struct row_value, last_timer), 0);
    emit(e, BPF_ALU64 | BPF_SUB | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7,
         (int16_t)offsetof(struct row_value, obj_data_delta), 0);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct row_value, obj_function), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, CTX_FUNCTION, 0);
    int fn_mismatch = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    emit_inc_u64(e, (int)offsetof(struct row_value, obj_function_match));
    patch_jump(e, fn_mismatch);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_8,
         (int16_t)offsetof(struct row_value, obj_expires), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, CTX_EXPIRES, 0);
    int expires_mismatch = emit(e, BPF_JMP | BPF_JNE | BPF_X, BPF_REG_7, BPF_REG_6, 0, 0);
    emit_inc_u64(e, (int)offsetof(struct row_value, obj_expires_match));
    patch_jump(e, expires_mismatch);

    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_pid_tgid);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_0,
         (int16_t)offsetof(struct row_value, last_pid_tgid), 0);

    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_9, 0, 0);
    emit_ld_map_fd(e, BPF_REG_2, stack_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_3, 0, 0, BPF_F_REUSE_STACKID);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_stackid);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_0,
         (int16_t)offsetof(struct row_value, last_stackid), 0);

    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, COMM_OFF);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, 16);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_comm);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_10, COMM_OFF, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)offsetof(struct row_value, comm), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_10, COMM_OFF + 8, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_6,
         (int16_t)(offsetof(struct row_value, comm) + 8), 0);

    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static void busy_observe_seconds(int duration_sec) {
    struct timespec start;
    struct timespec now;
    volatile unsigned long spin = 0;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (;;) {
        spin++;
        clock_gettime(CLOCK_MONOTONIC, &now);
        time_t sec = now.tv_sec - start.tv_sec;
        long nsec = now.tv_nsec - start.tv_nsec;
        if (nsec < 0) {
            sec--;
            nsec += 1000000000L;
        }
        if (sec > duration_sec || (sec == duration_sec && nsec >= 0)) {
            break;
        }
    }
    (void)spin;
}

static int compare_rows(const void *a, const void *b) {
    const struct dumped_row *ra = a;
    const struct dumped_row *rb = b;
    if (ra->value.count < rb->value.count) {
        return 1;
    }
    if (ra->value.count > rb->value.count) {
        return -1;
    }
    if (ra->function < rb->function) {
        return -1;
    }
    if (ra->function > rb->function) {
        return 1;
    }
    return 0;
}

static void print_stackmap_value(int stack_map_fd, int rank, uint64_t function, int64_t stackid) {
    uint64_t ips[STACK_DEPTH];
    memset(ips, 0, sizeof(ips));
    if (stackid < 0 || stackid >= STACK_MAX_ENTRIES) {
        printf("stackmap rank=%d function=0x%016llx lookup_ok=0 stackid=%lld errno=%d detail=stackid_out_of_range\n",
               rank, (unsigned long long)function, (long long)stackid, EINVAL);
        return;
    }
    uint32_t key = (uint32_t)stackid;
    if (map_lookup(stack_map_fd, &key, ips) != 0) {
        printf("stackmap rank=%d function=0x%016llx lookup_ok=0 stackid=%lld errno=%d detail=map_lookup_failed\n",
               rank, (unsigned long long)function, (long long)stackid, errno);
        return;
    }
    int nonzero = 0;
    int kernelish = 0;
    for (int i = 0; i < STACK_DEPTH; i++) {
        if (!ips[i]) {
            break;
        }
        nonzero++;
        if (looks_kernel_address(ips[i])) {
            kernelish++;
        }
    }
    printf("stackmap rank=%d function=0x%016llx lookup_ok=1 stackid=%lld nonzero=%d kernelish=%d\n",
           rank, (unsigned long long)function, (long long)stackid, nonzero, kernelish);
    for (int i = 0; i < nonzero; i++) {
        printf("stack_ip rank=%d index=%d value=0x%016llx kernelish=%d\n",
               rank, i, (unsigned long long)ips[i], looks_kernel_address(ips[i]) ? 1 : 0);
    }
}

static int dump_rows(int row_map_fd, int stack_map_fd, int top, int dump_stacks) {
    struct dumped_row *rows = calloc((size_t)DEFAULT_MAX_ROWS, sizeof(*rows));
    if (!rows) {
        return -1;
    }
    uint64_t key = 0;
    uint64_t next = 0;
    int have_key = 0;
    int total = 0;
    while (total < DEFAULT_MAX_ROWS) {
        if (map_get_next_key(row_map_fd, have_key ? &key : NULL, &next) != 0) {
            break;
        }
        rows[total].function = next;
        if (map_lookup(row_map_fd, &next, &rows[total].value) == 0) {
            total++;
        }
        key = next;
        have_key = 1;
    }
    qsort(rows, (size_t)total, sizeof(rows[0]), compare_rows);
    int printed = total < top ? total : top;
    printf("rows_total=%d rows_printed=%d\n", total, printed);
    for (int i = 0; i < printed; i++) {
        const struct row_value *v = &rows[i].value;
        uint32_t pid = (uint32_t)(v->last_pid_tgid >> 32);
        uint32_t tgid = (uint32_t)(v->last_pid_tgid & 0xffffffffULL);
        long long avg_timeout = v->count ? (long long)((int64_t)v->timeout_sum / (int64_t)v->count) : 0LL;
        printf("row rank=%d function=0x%016llx count=%llu last_timer=0x%016llx "
               "last_timeout=%lld timeout_min=%lld timeout_max=%lld timeout_avg=%lld "
               "last_flags=0x%llx obj_entry_next=0x%016llx obj_entry_pprev=0x%016llx "
               "obj_expires=%llu obj_function=0x%016llx obj_data=0x%016llx "
               "obj_data_delta=%lld obj_flags=0x%llx obj_read_errors=%llu "
               "obj_function_match=%llu obj_expires_match=%llu pid=%u tgid=%u "
               "stackid=%lld comm=%s\n",
               i,
               (unsigned long long)rows[i].function,
               (unsigned long long)v->count,
               (unsigned long long)v->last_timer,
               (long long)v->last_timeout,
               (long long)(int64_t)v->timeout_min,
               (long long)(int64_t)v->timeout_max,
               avg_timeout,
               (unsigned long long)v->last_flags,
               (unsigned long long)v->obj_entry_next,
               (unsigned long long)v->obj_entry_pprev,
               (unsigned long long)v->obj_expires,
               (unsigned long long)v->obj_function,
               (unsigned long long)v->obj_data,
               (long long)v->obj_data_delta,
               (unsigned long long)v->obj_flags,
               (unsigned long long)v->obj_read_errors,
               (unsigned long long)v->obj_function_match,
               (unsigned long long)v->obj_expires_match,
               pid,
               tgid,
               (long long)v->last_stackid,
               v->comm);
        if (dump_stacks) {
            print_stackmap_value(stack_map_fd, i, rows[i].function, v->last_stackid);
        }
    }
    free(rows);
    return 0;
}

static void usage(const char *argv0) {
    fprintf(stderr,
        "%s\n"
        "usage: %s [--duration SEC] [--top N] [--max-rows N] [--allow-attach] [--busy-observe] [--dump-stacks] [--verbose]\n"
        "default: check-only/load-only, no attach\n",
        A90_VERSION, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int busy_observe = 0;
    int dump_stacks = 0;
    int verbose = 0;
    int duration_sec = 2;
    int top = 16;
    int max_rows = DEFAULT_MAX_ROWS;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--busy-observe")) {
            busy_observe = 1;
        } else if (!strcmp(argv[i], "--dump-stacks")) {
            dump_stacks = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--duration") && i + 1 < argc) {
            duration_sec = atoi(argv[++i]);
            if (duration_sec < 1 || duration_sec > 30) {
                fprintf(stderr, "duration must be 1..30\n");
                return 2;
            }
        } else if (!strcmp(argv[i], "--top") && i + 1 < argc) {
            top = atoi(argv[++i]);
            if (top < 1 || top > 128) {
                fprintf(stderr, "top must be 1..128\n");
                return 2;
            }
        } else if (!strcmp(argv[i], "--max-rows") && i + 1 < argc) {
            max_rows = atoi(argv[++i]);
            if (max_rows < 16 || max_rows > DEFAULT_MAX_ROWS) {
                fprintf(stderr, "max-rows must be 16..4096\n");
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
    printf("allow_attach=%d duration_sec=%d top=%d max_rows=%d busy_observe=%d dump_stacks=%d verbose=%d\n",
           allow_attach, duration_sec, top, max_rows, busy_observe, dump_stacks, verbose);

    struct rlimit rl = { RLIM_INFINITY, RLIM_INFINITY };
    if (setrlimit(RLIMIT_MEMLOCK, &rl) != 0 && verbose) {
        fprintf(stderr, "setrlimit(MEMLOCK) failed: %s\n", strerror(errno));
    }

    int row_map = create_map(BPF_MAP_TYPE_HASH, 8, sizeof(struct row_value), (uint32_t)max_rows);
    if (row_map < 0) {
        printf("result=map-create-failed map=row errno=%d\n", errno);
        perror("row-map");
        return 1;
    }
    int stack_map = create_map((enum bpf_map_type)BPF_MAP_TYPE_STACK_TRACE,
                               4, STACK_DEPTH * 8, STACK_MAX_ENTRIES);
    if (stack_map < 0) {
        printf("result=map-create-failed map=stack errno=%d\n", errno);
        perror("stack-map");
        close(row_map);
        return 1;
    }

    struct emitter e;
    int insns = build_timer_histogram_prog(&e, row_map, stack_map);
    printf("insn_cnt=%d value_size=%zu\n", insns, sizeof(struct row_value));
    int prog_fd = load_prog(e.insn, insns, verbose);
    if (prog_fd < 0) {
        int saved = errno;
        printf("result=bpf-load-failed errno=%d log_available=%d\n", saved, log_buf[0] ? 1 : 0);
        if (verbose && log_buf[0]) {
            printf("verifier_log_begin\n%s\nverifier_log_end\n", log_buf);
        }
        close(stack_map);
        close(row_map);
        return 1;
    }
    printf("bpf_prog_fd=%d\n", prog_fd);

    if (!allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        close(prog_fd);
        close(stack_map);
        close(row_map);
        return 0;
    }

    int tp_id = -1;
    if (tracepoint_id("timer", "timer_start", &tp_id) != 0) {
        printf("result=tracepoint-id-failed errno=%d\n", errno);
        close(prog_fd);
        close(stack_map);
        close(row_map);
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
        close(row_map);
        return 1;
    }

    printf("observe_begin=1\n");
    fflush(stdout);
    if (busy_observe) {
        busy_observe_seconds(duration_sec);
    } else {
        sleep((unsigned int)duration_sec);
    }
    printf("observe_end=1\n");

    for (int i = 0; i < attach_ok; i++) {
        ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
        close(fds[i]);
    }

    if (dump_rows(row_map, stack_map, top, dump_stacks) != 0) {
        printf("result=row-dump-failed errno=%d\n", errno);
        close(prog_fd);
        close(stack_map);
        close(row_map);
        return 1;
    }
    printf("result=v2202-timer-object-histogram-complete\n");

    close(prog_fd);
    close(stack_map);
    close(row_map);
    return 0;
}
