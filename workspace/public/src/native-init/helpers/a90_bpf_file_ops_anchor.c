/*
 * a90_bpf_file_ops_anchor — V2204 clean file_operations slide anchor probe.
 *
 * Scope:
 *   - opens known files in this helper process;
 *   - attaches read-only BPF to sched:sched_switch;
 *   - filters current task to this helper pid/tgid;
 *   - reads current->files->fdt->fd[fd]->f_op with bpf_probe_read;
 *   - reports runtime f_op pointers for known static fops symbols.
 *
 * Safety:
 *   - default is check-only/load-only;
 *   - attach requires --allow-attach;
 *   - opens files read-only only;
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

#define A90_VERSION "a90_bpf_file_ops_anchor v2206"
#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"
#define MAX_INSNS 512
#define LOG_BUF_SIZE 65536
#define MAX_CPUS 32

#define A90_FN_map_lookup_elem 1
#define A90_FN_probe_read 4
#define A90_FN_get_current_pid_tgid 14
#define A90_FN_get_current_task 35

#define TASK_FILES_OFF 2176
#define FILES_FDT_OFF 32
#define FDTABLE_FD_OFF 8
#define FILE_F_OP_OFF 40
#define FILE_PRIVATE_DATA_OFF 208
#define FOPS_LLSEEK_OFF 8
#define FOPS_READ_OFF 16
#define FOPS_WRITE_OFF 24
#define FOPS_READ_ITER_OFF 32
#define FOPS_WRITE_ITER_OFF 40
#define FOPS_MMAP_OFF 88
#define FOPS_GET_UNMAPPED_AREA_OFF 152
#define FOPS_SPLICE_WRITE_OFF 176

struct summary_value {
    uint64_t count;
    uint64_t read_errors;
    uint64_t last_pid_tgid;
    uint64_t task_ptr;
    uint64_t files_ptr;
    uint64_t fdt_ptr;
    uint64_t fd_array_ptr;
    uint64_t fd0_file;
    uint64_t fd0_fop;
    uint64_t fd1_file;
    uint64_t fd1_fop;
    uint64_t fd2_file;
    uint64_t fd2_fop;
    uint64_t fd0_private;
    uint64_t fd1_private;
    uint64_t fd2_private;
    uint64_t fd0_llseek;
    uint64_t fd0_read;
    uint64_t fd0_write;
    uint64_t fd0_read_iter;
    uint64_t fd0_write_iter;
    uint64_t fd0_mmap;
    uint64_t fd0_get_unmapped_area;
    uint64_t fd0_splice_write;
    uint64_t fd1_llseek;
    uint64_t fd1_read;
    uint64_t fd1_write;
    uint64_t fd1_read_iter;
    uint64_t fd1_write_iter;
    uint64_t fd1_mmap;
    uint64_t fd1_get_unmapped_area;
    uint64_t fd1_splice_write;
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

static void emit_inc_u64(struct emitter *e, int value_off) {
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_7, 0, 0, 1);
    emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_8, BPF_REG_7, value_off, 0);
}

static int emit_read_u64_to_value(struct emitter *e, int value_off, uint8_t base_reg, int candidate_off) {
    int jerr = emit_probe_read_stack(e, -16, 8, base_reg, candidate_off);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_7, BPF_REG_10, -16, 0);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_7, value_off, 0);
    int jdone = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
    patch_jump(e, jerr);
    emit_inc_u64(e, (int)offsetof(struct summary_value, read_errors));
    patch_jump(e, jdone);
    return value_off;
}

static void emit_read_fd_file_and_fop(struct emitter *e, int fd, int file_off, int fop_off, int private_off) {
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8,
         (int16_t)offsetof(struct summary_value, fd_array_ptr), 0);
    emit_read_u64_to_value(e, file_off, BPF_REG_6, fd * 8);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8, (int16_t)file_off, 0);
    int jnull = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_value(e, fop_off, BPF_REG_6, FILE_F_OP_OFF);
    emit_read_u64_to_value(e, private_off, BPF_REG_6, FILE_PRIVATE_DATA_OFF);
    patch_jump(e, jnull);
}

static void emit_read_fop_members(struct emitter *e,
                                  int fop_value_off,
                                  int llseek_off,
                                  int read_off,
                                  int write_off,
                                  int read_iter_off,
                                  int write_iter_off,
                                  int mmap_off,
                                  int get_unmapped_area_off,
                                  int splice_write_off) {
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8, (int16_t)fop_value_off, 0);
    int fop_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_value(e, llseek_off, BPF_REG_6, FOPS_LLSEEK_OFF);
    emit_read_u64_to_value(e, read_off, BPF_REG_6, FOPS_READ_OFF);
    emit_read_u64_to_value(e, write_off, BPF_REG_6, FOPS_WRITE_OFF);
    emit_read_u64_to_value(e, read_iter_off, BPF_REG_6, FOPS_READ_ITER_OFF);
    emit_read_u64_to_value(e, write_iter_off, BPF_REG_6, FOPS_WRITE_ITER_OFF);
    emit_read_u64_to_value(e, mmap_off, BPF_REG_6, FOPS_MMAP_OFF);
    emit_read_u64_to_value(e, get_unmapped_area_off, BPF_REG_6, FOPS_GET_UNMAPPED_AREA_OFF);
    emit_read_u64_to_value(e, splice_write_off, BPF_REG_6, FOPS_SPLICE_WRITE_OFF);
    patch_jump(e, fop_null);
}

static int build_prog(struct emitter *e, int summary_map_fd, int target_pid, int fd0, int fd1, int fd2) {
    e->n = 0;

    emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -4, 0);
    emit_ld_map_fd(e, BPF_REG_1, summary_map_fd);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -4);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
    int summary_ok = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, summary_ok);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_8, BPF_REG_0, 0, 0);

    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_pid_tgid);

    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_0, 0, 0);
    emit_u32_low(e, BPF_REG_6);
    int low_match = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, target_pid);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_0, 0, 0);
    emit(e, BPF_ALU64 | BPF_RSH | BPF_K, BPF_REG_6, 0, 0, 32);
    int high_match = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, target_pid);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    patch_jump(e, low_match);
    patch_jump(e, high_match);

    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_0,
         (int16_t)offsetof(struct summary_value, last_pid_tgid), 0);
    emit_inc_u64(e, (int)offsetof(struct summary_value, count));

    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_get_current_task);
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_8, BPF_REG_0,
         (int16_t)offsetof(struct summary_value, task_ptr), 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_6, BPF_REG_0, 0, 0);
    emit_read_u64_to_value(e, (int)offsetof(struct summary_value, files_ptr), BPF_REG_6, TASK_FILES_OFF);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8,
         (int16_t)offsetof(struct summary_value, files_ptr), 0);
    int files_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_value(e, (int)offsetof(struct summary_value, fdt_ptr), BPF_REG_6, FILES_FDT_OFF);
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_8,
         (int16_t)offsetof(struct summary_value, fdt_ptr), 0);
    int fdt_null = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_6, 0, 0, 0);
    emit_read_u64_to_value(e, (int)offsetof(struct summary_value, fd_array_ptr), BPF_REG_6, FDTABLE_FD_OFF);

    emit_read_fd_file_and_fop(e, fd0, (int)offsetof(struct summary_value, fd0_file),
                              (int)offsetof(struct summary_value, fd0_fop),
                              (int)offsetof(struct summary_value, fd0_private));
    emit_read_fd_file_and_fop(e, fd1, (int)offsetof(struct summary_value, fd1_file),
                              (int)offsetof(struct summary_value, fd1_fop),
                              (int)offsetof(struct summary_value, fd1_private));
    emit_read_fd_file_and_fop(e, fd2, (int)offsetof(struct summary_value, fd2_file),
                              (int)offsetof(struct summary_value, fd2_fop),
                              (int)offsetof(struct summary_value, fd2_private));

    emit_read_fop_members(e,
                          (int)offsetof(struct summary_value, fd0_fop),
                          (int)offsetof(struct summary_value, fd0_llseek),
                          (int)offsetof(struct summary_value, fd0_read),
                          (int)offsetof(struct summary_value, fd0_write),
                          (int)offsetof(struct summary_value, fd0_read_iter),
                          (int)offsetof(struct summary_value, fd0_write_iter),
                          (int)offsetof(struct summary_value, fd0_mmap),
                          (int)offsetof(struct summary_value, fd0_get_unmapped_area),
                          (int)offsetof(struct summary_value, fd0_splice_write));
    emit_read_fop_members(e,
                          (int)offsetof(struct summary_value, fd1_fop),
                          (int)offsetof(struct summary_value, fd1_llseek),
                          (int)offsetof(struct summary_value, fd1_read),
                          (int)offsetof(struct summary_value, fd1_write),
                          (int)offsetof(struct summary_value, fd1_read_iter),
                          (int)offsetof(struct summary_value, fd1_write_iter),
                          (int)offsetof(struct summary_value, fd1_mmap),
                          (int)offsetof(struct summary_value, fd1_get_unmapped_area),
                          (int)offsetof(struct summary_value, fd1_splice_write));

    patch_jump(e, files_null);
    patch_jump(e, fdt_null);
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

static void print_summary(const struct summary_value *value) {
    printf("summary count=%llu read_errors=%llu last_tgid=%u last_pid=%u task=0x%016llx files=0x%016llx fdt=0x%016llx fd_array=0x%016llx fd0_file=0x%016llx fd0_fop=0x%016llx fd0_private=0x%016llx fd1_file=0x%016llx fd1_fop=0x%016llx fd1_private=0x%016llx fd2_file=0x%016llx fd2_fop=0x%016llx fd2_private=0x%016llx fd0_llseek=0x%016llx fd0_read=0x%016llx fd0_write=0x%016llx fd0_read_iter=0x%016llx fd0_write_iter=0x%016llx fd0_mmap=0x%016llx fd0_get_unmapped_area=0x%016llx fd0_splice_write=0x%016llx fd1_llseek=0x%016llx fd1_read=0x%016llx fd1_write=0x%016llx fd1_read_iter=0x%016llx fd1_write_iter=0x%016llx fd1_mmap=0x%016llx fd1_get_unmapped_area=0x%016llx fd1_splice_write=0x%016llx\n",
           (unsigned long long)value->count,
           (unsigned long long)value->read_errors,
           (unsigned int)(value->last_pid_tgid >> 32),
           (unsigned int)(value->last_pid_tgid & 0xffffffffULL),
           (unsigned long long)value->task_ptr,
           (unsigned long long)value->files_ptr,
           (unsigned long long)value->fdt_ptr,
           (unsigned long long)value->fd_array_ptr,
           (unsigned long long)value->fd0_file,
           (unsigned long long)value->fd0_fop,
           (unsigned long long)value->fd0_private,
           (unsigned long long)value->fd1_file,
           (unsigned long long)value->fd1_fop,
           (unsigned long long)value->fd1_private,
           (unsigned long long)value->fd2_file,
           (unsigned long long)value->fd2_fop,
           (unsigned long long)value->fd2_private,
           (unsigned long long)value->fd0_llseek,
           (unsigned long long)value->fd0_read,
           (unsigned long long)value->fd0_write,
           (unsigned long long)value->fd0_read_iter,
           (unsigned long long)value->fd0_write_iter,
           (unsigned long long)value->fd0_mmap,
           (unsigned long long)value->fd0_get_unmapped_area,
           (unsigned long long)value->fd0_splice_write,
           (unsigned long long)value->fd1_llseek,
           (unsigned long long)value->fd1_read,
           (unsigned long long)value->fd1_write,
           (unsigned long long)value->fd1_read_iter,
           (unsigned long long)value->fd1_write_iter,
           (unsigned long long)value->fd1_mmap,
           (unsigned long long)value->fd1_get_unmapped_area,
           (unsigned long long)value->fd1_splice_write);
}

static void usage(const char *argv0) {
    fprintf(stderr,
        "%s\n"
        "usage: %s [--duration-ms N] [--allow-attach] [--verbose]\n"
        "default: check-only/load-only, no attach\n",
        A90_VERSION, argv0);
}

int main(int argc, char **argv) {
    int allow_attach = 0;
    int verbose = 0;
    int duration_ms = 80;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--duration-ms") && i + 1 < argc) {
            duration_ms = atoi(argv[++i]);
            if (duration_ms < 10 || duration_ms > 2000) {
                fprintf(stderr, "duration-ms must be 10..2000\n");
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

    int fd_null = open("/dev/null", O_RDONLY | O_CLOEXEC);
    int fd_zero = open("/dev/zero", O_RDONLY | O_CLOEXEC);
    int fd_version = open("/proc/version", O_RDONLY | O_CLOEXEC);
    if (fd_null < 0 || fd_zero < 0 || fd_version < 0) {
        perror("open anchor files");
        return 1;
    }
    int target_pid = (int)getpid();

    printf("%s\n", A90_VERSION);
    printf("allow_attach=%d duration_ms=%d target_pid=%d verbose=%d\n",
           allow_attach, duration_ms, target_pid, verbose);
    printf("offsets task_files=%d files_fdt=%d fdtable_fd=%d file_f_op=%d file_private_data=%d fops_llseek=%d fops_read=%d fops_write=%d fops_read_iter=%d fops_write_iter=%d fops_mmap=%d fops_get_unmapped_area=%d fops_splice_write=%d\n",
           TASK_FILES_OFF, FILES_FDT_OFF, FDTABLE_FD_OFF, FILE_F_OP_OFF, FILE_PRIVATE_DATA_OFF,
           FOPS_LLSEEK_OFF, FOPS_READ_OFF, FOPS_WRITE_OFF, FOPS_READ_ITER_OFF, FOPS_WRITE_ITER_OFF,
           FOPS_MMAP_OFF, FOPS_GET_UNMAPPED_AREA_OFF, FOPS_SPLICE_WRITE_OFF);
    printf("anchor fd0=%d path=/dev/null expected=null_fops fd1=%d path=/dev/zero expected=zero_fops fd2=%d path=/proc/version expected=version_proc_fops\n",
           fd_null, fd_zero, fd_version);

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

    struct emitter e;
    int insns = build_prog(&e, summary_map, target_pid, fd_null, fd_zero, fd_version);
    printf("insn_cnt=%d value_size=%zu\n", insns, sizeof(struct summary_value));
    int prog_fd = load_prog(e.insn, insns, verbose);
    if (prog_fd < 0) {
        int saved = errno;
        printf("result=bpf-load-failed errno=%d log_available=%d\n", saved, log_buf[0] ? 1 : 0);
        if (verbose && log_buf[0]) {
            printf("verifier_log_begin\n%s\nverifier_log_end\n", log_buf);
        }
        close(summary_map);
        return 1;
    }
    printf("bpf_prog_fd=%d\n", prog_fd);

    if (!allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        close(prog_fd);
        close(summary_map);
        return 0;
    }

    int tp_id = -1;
    if (tracepoint_id("sched", "sched_switch", &tp_id) != 0) {
        printf("result=tracepoint-id-failed errno=%d\n", errno);
        close(prog_fd);
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
        close(summary_map);
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
    struct summary_value value;
    memset(&value, 0, sizeof(value));
    if (map_lookup(summary_map, &key, &value) != 0) {
        printf("result=summary-read-failed errno=%d\n", errno);
        close(prog_fd);
        close(summary_map);
        return 1;
    }
    print_summary(&value);
    printf("result=v2204-file-ops-anchor-complete\n");

    close(prog_fd);
    close(summary_map);
    close(fd_null);
    close(fd_zero);
    close(fd_version);
    return 0;
}
