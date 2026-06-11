/*
 * a90_bpf_raw_frame_sample_ring — V2213 bounded-large raw frame sampler.
 *
 * Scope:
 *   - attaches read-only BPF to sched:sched_switch;
 *   - supports helper-pid filtering or all-task sampling;
 *   - stores raw saved-context/frame-slot samples in a bounded BPF array ring;
 *   - reads current->thread.cpu_context.{fp,sp,pc};
 *   - reads raw memory at fp+0/fp+8, parent fp+0/fp+8, and sp+0/sp+8.
 *
 * Safety:
 *   - default is check-only/load-only;
 *   - attach requires --allow-attach;
 *   - no tracefs writes, no cgroup attach, no probe_write_user, no kernel write.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
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

#define A90_VERSION "a90_bpf_raw_frame_sample_ring v2213"
#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"
#define MAX_INSNS 512
#define LOG_BUF_SIZE 65536
#define MAX_CPUS 32
#define SAMPLE_CAPACITY 1024
#define SAMPLE_MASK (SAMPLE_CAPACITY - 1)

#define A90_FN_map_lookup_elem 1
#define A90_FN_probe_read 4
#define A90_FN_get_current_pid_tgid 14
#define A90_FN_get_current_comm 16
#define A90_FN_get_current_task 35

#define THREAD_CPU_CONTEXT_OFF 2944
#define CPUCTX_FP_OFF 80
#define CPUCTX_SP_OFF 88
#define CPUCTX_PC_OFF 96

struct stats_value {
    uint64_t count;
    uint64_t read_errors;
    uint64_t last_pid_tgid;
};

struct sample_value {
    uint64_t seq;
    uint64_t pid_tgid;
    uint64_t task_ptr;
    uint64_t thread_fp;
    uint64_t thread_sp;
    uint64_t thread_pc;
    uint64_t fp_slot_next;
    uint64_t fp_slot_raw_lr;
    uint64_t fp2_slot_next;
    uint64_t fp2_slot_raw_lr;
    uint64_t sp_slot0;
    uint64_t sp_slot8;
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

static void emit_u32_low(struct emitter *e, uint8_t reg) {
    emit(e, BPF_ALU64 | BPF_LSH | BPF_K, reg, 0, 0, 32);
    emit(e, BPF_ALU64 | BPF_RSH | BPF_K, reg, 0, 0, 32);
}

static void emit_inc_stats_u64(struct emitter *e, int value_off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_1, (int16_t)value_off, 0);
}

static void emit_zero_sample_u64(struct emitter *e, int value_off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_1, (int16_t)value_off, 0);
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

static int emit_read_u64_to_sample(struct emitter *e, int value_off, uint8_t base_reg, int candidate_off) {
    int jerr = emit_probe_read_stack(e, -24, 8, base_reg, candidate_off);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_10, -24, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_1, (int16_t)value_off, 0);
    int jdone = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, jerr);
    emit_inc_stats_u64(e, (int)offsetof(struct stats_value, read_errors));
    patch_jump(e, jdone);
    return value_off;
}

static void emit_clear_sample(struct emitter *e) {
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, task_ptr));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, thread_fp));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, thread_sp));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, thread_pc));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, fp_slot_next));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, fp_slot_raw_lr));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, fp2_slot_next));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, fp2_slot_raw_lr));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, sp_slot0));
    emit_zero_sample_u64(e, (int)offsetof(struct sample_value, sp_slot8));
}

static void emit_store_comm(struct emitter *e) {
    emit(e, BPF_ST | BPF_MEM | BPF_DW, BPF_REG_10, 0, -40, 0);
    emit(e, BPF_ST | BPF_MEM | BPF_DW, BPF_REG_10, 0, -32, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, -40);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, 16);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_comm);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_10, -40, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_1,
         (int16_t)offsetof(struct sample_value, comm), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_1, BPF_REG_10, -32, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_1,
         (int16_t)(offsetof(struct sample_value, comm) + 8), 0);
}

static int build_prog(struct emitter *e, int stats_map_fd, int sample_map_fd, int target_pid, int all_tasks) {
    e->n = 0;

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

    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_pid_tgid);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_7, BPF_REG_0, 0, 0);
    if (!all_tasks) {
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_7, 0, 0);
        emit_u32_low(e, BPF_REG_6);
        int low_match = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, target_pid);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_7, 0, 0);
        emit(e, BPF_ALU64 | BPF_RSH | BPF_K, BPF_REG_6, 0, 0, 32);
        int high_match = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, target_pid);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
        emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
        patch_jump(e, low_match);
        patch_jump(e, high_match);
    }

    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7,
         (int16_t)offsetof(struct stats_value, last_pid_tgid), 0);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8,
         (int16_t)offsetof(struct stats_value, count), 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, BPF_REG_6, -48, 0);
    emit_inc_stats_u64(e, (int)offsetof(struct stats_value, count));

    emit(e, BPF_ALU64 | BPF_AND | BPF_K, BPF_REG_6, 0, 0, SAMPLE_MASK);
    emit(e, BPF_STX | BPF_MEM | BPF_W, BPF_REG_10, BPF_REG_6, -4, 0);
    emit_ld_map_fd(e, BPF_REG_1, sample_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -4);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int sample_ok = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, sample_ok);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_9, BPF_REG_0, 0, 0);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_10, -48, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_6,
         (int16_t)offsetof(struct sample_value, seq), 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_7,
         (int16_t)offsetof(struct sample_value, pid_tgid), 0);
    emit_clear_sample(e);
    emit_store_comm(e);

    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_task);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_9, BPF_REG_0,
         (int16_t)offsetof(struct sample_value, task_ptr), 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_0, 0, 0);

    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, thread_fp),
                            BPF_REG_6, THREAD_CPU_CONTEXT_OFF + CPUCTX_FP_OFF);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, thread_sp),
                            BPF_REG_6, THREAD_CPU_CONTEXT_OFF + CPUCTX_SP_OFF);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, thread_pc),
                            BPF_REG_6, THREAD_CPU_CONTEXT_OFF + CPUCTX_PC_OFF);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9,
         (int16_t)offsetof(struct sample_value, thread_fp), 0);
    int fp_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, fp_slot_next), BPF_REG_6, 0);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, fp_slot_raw_lr), BPF_REG_6, 8);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9,
         (int16_t)offsetof(struct sample_value, fp_slot_next), 0);
    int fp2_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, fp2_slot_next), BPF_REG_6, 0);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, fp2_slot_raw_lr), BPF_REG_6, 8);
    patch_jump(e, fp2_null);
    patch_jump(e, fp_null);

    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9,
         (int16_t)offsetof(struct sample_value, thread_sp), 0);
    int sp_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, sp_slot0), BPF_REG_6, 0);
    emit_read_u64_to_sample(e, (int)offsetof(struct sample_value, sp_slot8), BPF_REG_6, 8);
    patch_jump(e, sp_null);

    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return e->n;
}

static void sleep_trigger_ms(int duration_ms) {
    struct timespec req;
    req.tv_sec = 0;
    req.tv_nsec = 1000000L;
    for (int elapsed = 0; elapsed < duration_ms; elapsed++) {
        nanosleep(&req, NULL);
    }
}

static void print_sample(unsigned int idx, const struct sample_value *value) {
    char comm[17];
    memcpy(comm, value->comm, 16);
    comm[16] = '\0';
    printf("sample idx=%u seq=%llu tgid=%u pid=%u task=0x%016llx thread_fp=0x%016llx thread_sp=0x%016llx thread_pc=0x%016llx fp_slot_next=0x%016llx fp_slot_raw_lr=0x%016llx fp2_slot_next=0x%016llx fp2_slot_raw_lr=0x%016llx sp_slot0=0x%016llx sp_slot8=0x%016llx comm=%s\n",
           idx,
           (unsigned long long)value->seq,
           (unsigned int)(value->pid_tgid >> 32),
           (unsigned int)(value->pid_tgid & 0xffffffffULL),
           (unsigned long long)value->task_ptr,
           (unsigned long long)value->thread_fp,
           (unsigned long long)value->thread_sp,
           (unsigned long long)value->thread_pc,
           (unsigned long long)value->fp_slot_next,
           (unsigned long long)value->fp_slot_raw_lr,
           (unsigned long long)value->fp2_slot_next,
           (unsigned long long)value->fp2_slot_raw_lr,
           (unsigned long long)value->sp_slot0,
           (unsigned long long)value->sp_slot8,
           comm);
}

static void usage(const char *argv0) {
    fprintf(stderr,
        "%s\n"
        "usage: %s [--duration-ms N] [--print-limit N] [--all-tasks] [--allow-attach] [--verbose]\n"
        "default: check-only/load-only, helper-pid filter, no attach\n",
        A90_VERSION, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int verbose = 0;
    int all_tasks = 0;
    int duration_ms = 1000;
    int print_limit = 256;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--all-tasks")) {
            all_tasks = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--duration-ms") && i + 1 < argc) {
            duration_ms = atoi(argv[++i]);
            if (duration_ms < 10 || duration_ms > 120000) {
                fprintf(stderr, "duration-ms must be 10..120000\n");
                return 2;
            }
        } else if (!strcmp(argv[i], "--print-limit") && i + 1 < argc) {
            print_limit = atoi(argv[++i]);
            if (print_limit < 0 || print_limit > SAMPLE_CAPACITY) {
                fprintf(stderr, "print-limit must be 0..%d\n", SAMPLE_CAPACITY);
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

    int target_pid = (int)getpid();

    printf("%s\n", A90_VERSION);
    printf("allow_attach=%d duration_ms=%d target_pid=%d all_tasks=%d print_limit=%d verbose=%d\n",
           allow_attach, duration_ms, target_pid, all_tasks, print_limit, verbose);
    printf("offsets thread_cpu_context=%d cpu_context_fp=%d cpu_context_sp=%d cpu_context_pc=%d sample_capacity=%d\n",
           THREAD_CPU_CONTEXT_OFF, CPUCTX_FP_OFF, CPUCTX_SP_OFF, CPUCTX_PC_OFF, SAMPLE_CAPACITY);

    struct rlimit rl = { RLIM_INFINITY, RLIM_INFINITY };
    if (setrlimit(RLIMIT_MEMLOCK, &rl) != 0 && verbose) {
        fprintf(stderr, "setrlimit(MEMLOCK) failed: %s\n", strerror(errno));
    }

    int stats_map = create_map(BPF_MAP_TYPE_ARRAY, 4, sizeof(struct stats_value), 1);
    int sample_map = create_map(BPF_MAP_TYPE_ARRAY, 4, sizeof(struct sample_value), SAMPLE_CAPACITY);
    if (stats_map < 0 || sample_map < 0) {
        printf("result=map-create-failed stats_fd=%d sample_fd=%d errno=%d\n", stats_map, sample_map, errno);
        perror("map-create");
        return 1;
    }

    struct emitter e;
    int insns = build_prog(&e, stats_map, sample_map, target_pid, all_tasks);
    printf("insn_cnt=%d stats_value_size=%zu sample_value_size=%zu\n",
           insns, sizeof(struct stats_value), sizeof(struct sample_value));
    int prog_fd = load_prog(e.insn, insns, verbose);
    if (prog_fd < 0) {
        int saved = errno;
        printf("result=bpf-load-failed errno=%d log_available=%d\n", saved, log_buf[0] ? 1 : 0);
        if (verbose && log_buf[0]) {
            printf("verifier_log_begin\n%s\nverifier_log_end\n", log_buf);
        }
        close(stats_map);
        close(sample_map);
        return 1;
    }
    printf("bpf_prog_fd=%d\n", prog_fd);

    if (!allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        close(prog_fd);
        close(stats_map);
        close(sample_map);
        return 0;
    }

    int tp_id = -1;
    if (tracepoint_id("sched", "sched_switch", &tp_id) != 0) {
        printf("result=tracepoint-id-failed errno=%d\n", errno);
        close(prog_fd);
        close(stats_map);
        close(sample_map);
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
        close(stats_map);
        close(sample_map);
        return 1;
    }

    printf("observe_begin=1\n");
    fflush(stdout);
    sleep_trigger_ms(duration_ms);
    printf("observe_end=1\n");

    for (int i = 0; i < attach_ok; i++) {
        ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
        close(fds[i]);
    }

    uint32_t key = 0;
    struct stats_value stats;
    memset(&stats, 0, sizeof(stats));
    if (map_lookup(stats_map, &key, &stats) != 0) {
        printf("result=stats-read-failed errno=%d\n", errno);
        close(prog_fd);
        close(stats_map);
        close(sample_map);
        return 1;
    }
    printf("stats count=%llu read_errors=%llu last_tgid=%u last_pid=%u sample_capacity=%d all_tasks=%d print_limit=%d\n",
           (unsigned long long)stats.count,
           (unsigned long long)stats.read_errors,
           (unsigned int)(stats.last_pid_tgid >> 32),
           (unsigned int)(stats.last_pid_tgid & 0xffffffffULL),
           SAMPLE_CAPACITY,
           all_tasks,
           print_limit);

    int printed = 0;
    int occupied = 0;
    for (uint32_t i = 0; i < SAMPLE_CAPACITY; i++) {
        struct sample_value sample;
        memset(&sample, 0, sizeof(sample));
        if (map_lookup(sample_map, &i, &sample) != 0) {
            continue;
        }
        if (sample.task_ptr == 0 && sample.pid_tgid == 0 && sample.seq == 0) {
            continue;
        }
        occupied++;
        if (printed < print_limit) {
            print_sample(i, &sample);
            printed++;
        }
    }
    printf("samples occupied=%d printed=%d capacity=%d\n", occupied, printed, SAMPLE_CAPACITY);
    printf("result=v2213-raw-frame-sample-ring-complete\n");

    close(prog_fd);
    close(stats_map);
    close(sample_map);
    return 0;
}
