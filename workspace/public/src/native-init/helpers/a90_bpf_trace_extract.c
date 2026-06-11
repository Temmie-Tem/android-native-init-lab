/*
 * a90_bpf_trace_extract — parametric eBPF tracepoint field extractor.
 *
 * One binary, fully data-driven (no recompile to retarget):
 *   - target tracepoint by name (--event group:event); /id and /format are
 *     resolved from tracefs at runtime.
 *   - Tier-1 read: a scalar field straight out of the tracepoint record
 *     (--field NAME, offset/size taken from the kernel's own format file, or
 *     --field-raw OFF:SIZE). The record layout IS the BPF prog ctx layout for
 *     BPF_PROG_TYPE_TRACEPOINT, so no struct offsets are needed.
 *   - Tier-2 read: follow a pointer carried in the record into kernel memory
 *     (--deref CTXOFF:o1,o2,...:SIZE) via bpf_probe_read (RKP-safe in-kernel
 *     read). Offsets come from kernel source + config, validated on device.
 *   - output modes (--mode):
 *       sample : array map [count,last,sum]   -> last value + count + avg
 *       freq   : hash  map value->count       -> value distribution over window
 *       stream : perf_event_array + per-cpu mmap -> raw value time series
 *
 * The BPF program is assembled instruction-by-instruction at runtime from the
 * parsed parameters; there is no libbpf or LLVM dependency.
 *
 * Safety: read-only. No tracefs control writes, no Wi-Fi trigger, no network
 * action. Attach requires explicit --allow-attach; default is --check-only.
 */

#define _GNU_SOURCE

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
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

/* helper ids (stable kernel ABI) */
#define A90_FN_map_lookup_elem 1
#define A90_FN_map_update_elem 2
#define A90_FN_probe_read 4
#define A90_FN_perf_event_output 25

#ifndef BPF_F_CURRENT_CPU
#define BPF_F_CURRENT_CPU 0xffffffffULL
#endif

#define A90_VERSION "a90_bpf_trace_extract v2192"

#define TRACEFS_A "/sys/kernel/tracing/events"
#define TRACEFS_B "/sys/kernel/debug/tracing/events"

#define MAX_INSNS 512
#define MAX_DEREF 8

enum out_mode { MODE_SAMPLE, MODE_FREQ, MODE_STREAM };

struct read_spec {
    int is_deref;          /* 0 = Tier-1 ctx scalar, 1 = Tier-2 pointer chase */
    int ctx_off;           /* ctx offset of the scalar (Tier-1) or pointer (Tier-2) */
    int size;              /* final read size in bytes: 1,2,4,8 */
    int chain[MAX_DEREF];  /* Tier-2 intermediate/final offsets */
    int chain_len;
};

/* ---- syscall thunks ---- */
static uint64_t u64ptr(const void *p) { return (uint64_t)(uintptr_t)p; }

static long sys_bpf(enum bpf_cmd cmd, union bpf_attr *attr, unsigned int size) {
    return syscall(__NR_bpf, cmd, attr, size);
}
static long sys_perf(struct perf_event_attr *attr, pid_t pid, int cpu, int group, unsigned long flags) {
    return syscall(__NR_perf_event_open, attr, pid, cpu, group, flags);
}

/* ---- instruction emitter ---- */
struct emitter {
    struct bpf_insn insn[MAX_INSNS];
    int n;
};

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

/* 64-bit immediate / map fd load occupies two insn slots */
static void emit_ld_imm64(struct emitter *e, uint8_t dst, uint8_t src, int64_t imm) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, src, 0, (int32_t)(imm & 0xffffffff));
    emit(e, 0, 0, 0, 0, (int32_t)((uint64_t)imm >> 32));
}
static void emit_ld_map_fd(struct emitter *e, uint8_t dst, int map_fd) {
    emit(e, BPF_LD | BPF_DW | BPF_IMM, dst, BPF_PSEUDO_MAP_FD, 0, map_fd);
    emit(e, 0, 0, 0, 0, 0);
}

static uint8_t ldx_size(int size) {
    switch (size) {
        case 1: return BPF_B;
        case 2: return BPF_H;
        case 4: return BPF_W;
        default: return BPF_DW;
    }
}

/* ---- emit the value-read prologue: leaves the read value in R7 ---- */
/* R9 holds ctx (saved at entry, used by stream output). R6 scratch pointer. */
static void emit_read(struct emitter *e, const struct read_spec *rs) {
    if (!rs->is_deref) {
        /* R7 = *(size)(ctx + off) */
        emit(e, BPF_LDX | BPF_MEM | ldx_size(rs->size), BPF_REG_7, BPF_REG_9, (int16_t)rs->ctx_off, 0);
        return;
    }
    /* Tier-2: R6 = *(u64)(ctx + ctx_off) */
    emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_9, (int16_t)rs->ctx_off, 0);
    for (int i = 0; i < rs->chain_len; i++) {
        int last = (i == rs->chain_len - 1);
        int sz = last ? rs->size : 8;
        /* bpf_probe_read(dst=R10-16, size=sz, src=R6 + chain[i]) */
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_10, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_1, 0, 0, -16);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_2, 0, 0, sz);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_3, BPF_REG_6, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_3, 0, 0, rs->chain[i]);
        emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_probe_read);
        if (!last) {
            /* R6 = *(u64)(R10-16) */
            emit(e, BPF_LDX | BPF_MEM | BPF_DW, BPF_REG_6, BPF_REG_10, -16, 0);
        } else {
            /* R7 = *(size)(R10-16) */
            emit(e, BPF_LDX | BPF_MEM | ldx_size(rs->size), BPF_REG_7, BPF_REG_10, -16, 0);
        }
    }
}

/* ---- assemble the full program for a given mode ---- */
static int build_prog(struct emitter *e, const struct read_spec *rs, enum out_mode mode, int map_fd) {
    e->n = 0;
    /* R9 = ctx */
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_9, BPF_REG_1, 0, 0);

    emit_read(e, rs); /* -> R7 = value */

    if (mode == MODE_SAMPLE) {
        /* key = 0 at R10-8 */
        emit(e, BPF_ST | BPF_MEM | BPF_W, BPF_REG_10, 0, -8, 0);
        emit_ld_map_fd(e, BPF_REG_1, map_fd);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -8);
        emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
        /* if R0 == 0 goto exit */
        int jnull = emit(e, BPF_JMP | BPF_JEQ | BPF_K, BPF_REG_0, 0, 0, 0);
        /* count += 1  (val[0]) */
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 1);
        emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_0, BPF_REG_1, 0, 0);
        /* last = R7 (val[1] @ +8) */
        emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_0, BPF_REG_7, 8, 0);
        /* sum += R7 (val[2] @ +16) */
        emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_0, BPF_REG_7, 16, 0);
        e->insn[jnull].off = (int16_t)(e->n - jnull - 1);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
        emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
        return 0;
    }

    if (mode == MODE_FREQ) {
        /* key = value at R10-8 */
        emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, BPF_REG_7, -8, 0);
        emit_ld_map_fd(e, BPF_REG_1, map_fd);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -8);
        emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_lookup_elem);
        /* if R0 != 0 goto do_xadd */
        int jfound = emit(e, BPF_JMP | BPF_JNE | BPF_K, BPF_REG_0, 0, 0, 0);
        /* not found: init count=1 at R10-16, map_update_elem(map, key=R10-8, val=R10-16, ANY) */
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 1);
        emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, BPF_REG_1, -16, 0);
        emit_ld_map_fd(e, BPF_REG_1, map_fd);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_2, BPF_REG_10, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_2, 0, 0, -8);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_3, BPF_REG_10, 0, 0);
        emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_3, 0, 0, -16);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_4, 0, 0, BPF_ANY);
        emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_map_update_elem);
        int jdone = emit(e, BPF_JMP | BPF_JA, 0, 0, 0, 0);
        /* do_xadd: *(u64)R0 += 1 */
        e->insn[jfound].off = (int16_t)(e->n - jfound - 1);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_1, 0, 0, 1);
        emit(e, BPF_STX | BPF_XADD | BPF_DW, BPF_REG_0, BPF_REG_1, 0, 0);
        e->insn[jdone].off = (int16_t)(e->n - jdone - 1);
        emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
        emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
        return 0;
    }

    /* MODE_STREAM: bpf_perf_event_output(ctx, map, BPF_F_CURRENT_CPU, &val, 8) */
    emit(e, BPF_STX | BPF_MEM | BPF_DW, BPF_REG_10, BPF_REG_7, -8, 0);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_1, BPF_REG_9, 0, 0); /* ctx */
    emit_ld_map_fd(e, BPF_REG_2, map_fd);
    emit_ld_imm64(e, BPF_REG_3, 0, (int64_t)BPF_F_CURRENT_CPU);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_X, BPF_REG_4, BPF_REG_10, 0, 0);
    emit(e, BPF_ALU64 | BPF_ADD | BPF_K, BPF_REG_4, 0, 0, -8);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_5, 0, 0, 8);
    emit(e, BPF_JMP | BPF_CALL, 0, 0, 0, A90_FN_perf_event_output);
    emit(e, BPF_ALU64 | BPF_MOV | BPF_K, BPF_REG_0, 0, 0, 0);
    emit(e, BPF_JMP | BPF_EXIT, 0, 0, 0, 0);
    return 0;
}

/* ---- map / prog / attach ---- */
static int create_map(enum out_mode mode, int ncpu) {
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    switch (mode) {
        case MODE_SAMPLE:
            attr.map_type = BPF_MAP_TYPE_ARRAY;
            attr.key_size = sizeof(uint32_t);
            attr.value_size = sizeof(uint64_t) * 3; /* count,last,sum */
            attr.max_entries = 1;
            break;
        case MODE_FREQ:
            attr.map_type = BPF_MAP_TYPE_HASH;
            attr.key_size = sizeof(uint64_t);
            attr.value_size = sizeof(uint64_t);
            attr.max_entries = 2048;
            break;
        case MODE_STREAM:
            attr.map_type = BPF_MAP_TYPE_PERF_EVENT_ARRAY;
            attr.key_size = sizeof(uint32_t);
            attr.value_size = sizeof(uint32_t);
            attr.max_entries = (uint32_t)ncpu;
            break;
    }
    return (int)sys_bpf(BPF_MAP_CREATE, &attr, sizeof(attr));
}

static int load_prog(const struct emitter *e, int verbose) {
    char license[] = "GPL";
    static char log_buf[16384];
    log_buf[0] = '\0';
    union bpf_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.prog_type = BPF_PROG_TYPE_TRACEPOINT;
    attr.insn_cnt = (uint32_t)e->n;
    attr.insns = u64ptr(e->insn);
    attr.license = u64ptr(license);
    /* This 4.14 kernel rejects BPF_PROG_LOAD with EINVAL when a log buffer is
     * supplied at log_level=0; only attach the buffer when actually logging. */
    if (verbose) {
        attr.log_buf = u64ptr(log_buf);
        attr.log_size = sizeof(log_buf);
        attr.log_level = 1;
    }
    int fd = (int)sys_bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
    if (fd < 0 && verbose && log_buf[0])
        fprintf(stderr, "bpf_log=%s\n", log_buf);
    return fd;
}

static int attach_tp(int prog_fd, long long tp_id) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.type = PERF_TYPE_TRACEPOINT;
    attr.size = sizeof(attr);
    attr.config = (uint64_t)tp_id;
    attr.sample_period = 1;
    attr.wakeup_events = 1;
    int fd = (int)sys_perf(&attr, -1, 0, -1, PERF_FLAG_FD_CLOEXEC);
    if (fd < 0) return -1;
    if (ioctl(fd, PERF_EVENT_IOC_SET_BPF, prog_fd) != 0) { int s = errno; close(fd); errno = s; return -1; }
    if (ioctl(fd, PERF_EVENT_IOC_ENABLE, 0) != 0) { int s = errno; close(fd); errno = s; return -1; }
    return fd;
}

/* ---- tracefs helpers ---- */
static const char *tracefs_base(void) {
    if (access(TRACEFS_A, R_OK) == 0) return TRACEFS_A;
    return TRACEFS_B;
}

static int read_id(const char *group, const char *event, long long *out) {
    char path[512];
    snprintf(path, sizeof(path), "%s/%s/%s/id", tracefs_base(), group, event);
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    long long v = -1;
    int ok = (fscanf(f, "%lld", &v) == 1 && v > 0);
    fclose(f);
    if (!ok) { errno = EINVAL; return -1; }
    *out = v;
    return 0;
}

/* resolve a named field's offset/size from the format file */
static int resolve_field(const char *group, const char *event, const char *name,
                         int *out_off, int *out_size) {
    char path[512];
    snprintf(path, sizeof(path), "%s/%s/%s/format", tracefs_base(), group, event);
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char line[1024];
    int found = 0;
    while (fgets(line, sizeof(line), f)) {
        char *p = strstr(line, "field:");
        if (!p) continue;
        char *semi = strchr(p, ';');
        char *offp = strstr(line, "offset:");
        char *szp = strstr(line, "size:");
        if (!semi || !offp || !szp) continue;
        /* identifier = last token before ';', strip trailing [..] */
        *semi = '\0';
        char *id_end = semi;
        char *id = id_end;
        while (id > p && *(id - 1) != ' ' && *(id - 1) != '*') id--;
        char ident[128];
        size_t len = (size_t)(id_end - id);
        if (len >= sizeof(ident)) len = sizeof(ident) - 1;
        memcpy(ident, id, len);
        ident[len] = '\0';
        char *br = strchr(ident, '[');
        if (br) *br = '\0';
        if (strcmp(ident, name) == 0) {
            *out_off = atoi(offp + 7);
            *out_size = atoi(szp + 5);
            found = 1;
            break;
        }
    }
    fclose(f);
    if (!found) { errno = ENOENT; return -1; }
    return 0;
}

/* ---- output readers ---- */
static int read_sample(int map_fd) {
    uint32_t key = 0;
    uint64_t val[3] = {0, 0, 0};
    union bpf_attr a;
    memset(&a, 0, sizeof(a));
    a.map_fd = (uint32_t)map_fd;
    a.key = u64ptr(&key);
    a.value = u64ptr(val);
    if (sys_bpf(BPF_MAP_LOOKUP_ELEM, &a, sizeof(a)) != 0) return -1;
    printf("count=%llu\n", (unsigned long long)val[0]);
    printf("last=%llu\n", (unsigned long long)val[1]);
    if (val[0])
        printf("avg=%llu\n", (unsigned long long)(val[2] / val[0]));
    printf("sum=%llu\n", (unsigned long long)val[2]);
    return 0;
}

static int dump_freq(int map_fd, int top) {
    uint64_t key = 0, next = 0, cnt = 0;
    union bpf_attr a;
    int printed = 0;
    int have_key = 0;
    while (printed < top) {
        memset(&a, 0, sizeof(a));
        a.map_fd = (uint32_t)map_fd;
        a.key = have_key ? u64ptr(&key) : 0;
        a.next_key = u64ptr(&next);
        if (sys_bpf(BPF_MAP_GET_NEXT_KEY, &a, sizeof(a)) != 0) break;
        memset(&a, 0, sizeof(a));
        a.map_fd = (uint32_t)map_fd;
        a.key = u64ptr(&next);
        a.value = u64ptr(&cnt);
        if (sys_bpf(BPF_MAP_LOOKUP_ELEM, &a, sizeof(a)) == 0)
            printf("value=%llu count=%llu\n", (unsigned long long)next, (unsigned long long)cnt);
        key = next;
        have_key = 1;
        printed++;
    }
    printf("distinct_printed=%d\n", printed);
    return 0;
}

/* ---- stream: per-cpu perf buffer ---- */
struct perf_ring {
    void *base;
    struct perf_event_mmap_page *meta;
    int fd;
    size_t data_size;
    size_t page;
};

static int open_perf_output(int cpu) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.type = PERF_TYPE_SOFTWARE;
    attr.config = PERF_COUNT_SW_BPF_OUTPUT;
    attr.size = sizeof(attr);
    attr.sample_type = PERF_SAMPLE_RAW;
    attr.sample_period = 1;
    attr.wakeup_events = 1;
    return (int)sys_perf(&attr, -1, cpu, -1, PERF_FLAG_FD_CLOEXEC);
}

static int stream_loop(int map_fd, int ncpu, int duration_sec) {
    long page = sysconf(_SC_PAGESIZE);
    size_t pages = 8; /* data pages (power of 2) */
    size_t map_len = (size_t)page * (1 + pages);
    struct perf_ring *rings = calloc((size_t)ncpu, sizeof(*rings));
    struct pollfd *pfds = calloc((size_t)ncpu, sizeof(*pfds));
    int active = 0;
    for (int cpu = 0; cpu < ncpu; cpu++) {
        int fd = open_perf_output(cpu);
        if (fd < 0) { rings[cpu].fd = -1; continue; }
        void *base = mmap(NULL, map_len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (base == MAP_FAILED) { close(fd); rings[cpu].fd = -1; continue; }
        ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
        rings[cpu].base = base;
        rings[cpu].meta = (struct perf_event_mmap_page *)base;
        rings[cpu].fd = fd;
        rings[cpu].page = (size_t)page;
        rings[cpu].data_size = (size_t)page * pages;
        /* register fd in perf_event_array map[cpu] */
        uint32_t k = (uint32_t)cpu;
        union bpf_attr a;
        memset(&a, 0, sizeof(a));
        a.map_fd = (uint32_t)map_fd;
        a.key = u64ptr(&k);
        a.value = u64ptr(&fd);
        a.flags = BPF_ANY;
        sys_bpf(BPF_MAP_UPDATE_ELEM, &a, sizeof(a));
        pfds[active].fd = fd;
        pfds[active].events = POLLIN;
        active++;
    }
    if (active == 0) {
        fprintf(stderr, "stream: no per-cpu perf buffer opened\n");
        free(rings); free(pfds);
        return -1;
    }
    printf("stream_cpus=%d\n", active);
    fflush(stdout);

    time_t end = time(NULL) + duration_sec;
    uint64_t emitted = 0;
    while (time(NULL) < end) {
        int pr = poll(pfds, (nfds_t)active, 200);
        if (pr <= 0) continue;
        for (int cpu = 0; cpu < ncpu; cpu++) {
            struct perf_ring *r = &rings[cpu];
            if (r->fd < 0) continue;
            struct perf_event_mmap_page *meta = r->meta;
            uint64_t head = meta->data_head;
            __sync_synchronize();
            uint64_t tail = meta->data_tail;
            uint8_t *data = (uint8_t *)r->base + r->page;
            while (tail < head) {
                struct perf_event_header *hdr =
                    (struct perf_event_header *)(data + (tail % r->data_size));
                if (hdr->type == PERF_RECORD_SAMPLE) {
                    /* layout: u32 size; then raw bytes (our 8-byte value) */
                    uint8_t *p = (uint8_t *)(hdr + 1);
                    uint32_t rawsz;
                    memcpy(&rawsz, p, 4);
                    if (rawsz >= 8) {
                        uint64_t v;
                        memcpy(&v, p + 4, 8);
                        printf("value=%llu\n", (unsigned long long)v);
                        emitted++;
                    }
                }
                tail += hdr->size;
            }
            __sync_synchronize();
            meta->data_tail = head;
        }
    }
    for (int cpu = 0; cpu < ncpu; cpu++) {
        if (rings[cpu].fd < 0) continue;
        ioctl(rings[cpu].fd, PERF_EVENT_IOC_DISABLE, 0);
        munmap(rings[cpu].base, map_len);
        close(rings[cpu].fd);
    }
    printf("stream_emitted=%llu\n", (unsigned long long)emitted);
    free(rings); free(pfds);
    return 0;
}

/* ---- arg parsing ---- */
static int parse_event(const char *s, char *group, size_t gl, char *event, size_t el) {
    const char *colon = strchr(s, ':');
    if (!colon) return -1;
    size_t n = (size_t)(colon - s);
    if (n == 0 || n >= gl) return -1;
    memcpy(group, s, n);
    group[n] = '\0';
    if (strlen(colon + 1) == 0 || strlen(colon + 1) >= el) return -1;
    strcpy(event, colon + 1);
    return 0;
}

/* --deref CTXOFF:o1,o2,...:SIZE */
static int parse_deref(const char *s, struct read_spec *rs) {
    char buf[256];
    if (strlen(s) >= sizeof(buf)) return -1;
    strcpy(buf, s);
    char *c1 = strchr(buf, ':');
    if (!c1) return -1;
    *c1 = '\0';
    char *chain = c1 + 1;
    char *c2 = strrchr(chain, ':');
    if (!c2) return -1;
    *c2 = '\0';
    char *szs = c2 + 1;
    rs->is_deref = 1;
    rs->ctx_off = atoi(buf);
    rs->size = atoi(szs);
    rs->chain_len = 0;
    char *tok = strtok(chain, ",");
    while (tok) {
        if (rs->chain_len >= MAX_DEREF) return -1;
        rs->chain[rs->chain_len++] = atoi(tok);
        tok = strtok(NULL, ",");
    }
    return rs->chain_len > 0 ? 0 : -1;
}

static void usage(FILE *o) {
    fprintf(o,
        "%s\n"
        "usage:\n"
        "  a90_bpf_trace_extract --event GROUP:EVENT [read] [--mode M] [opts]\n"
        "read (choose one):\n"
        "  --field NAME            scalar field, offset/size from format file\n"
        "  --field-raw OFF:SIZE    scalar field, explicit ctx offset/size\n"
        "  --deref CTXOFF:o1,..:SZ pointer chase via bpf_probe_read\n"
        "modes: --mode sample|freq|stream     (default sample)\n"
        "opts:  --duration-sec N (0..120)  --top N (freq)  --allow-attach  --verbose  --check-only\n"
        "safety: read-only; no tracefs writes, no Wi-Fi/network action; attach gated by --allow-attach\n",
        A90_VERSION);
}

int main(int argc, char **argv) {
    char group[128] = "", event[128] = "";
    struct read_spec rs;
    memset(&rs, 0, sizeof(rs));
    rs.size = 8;
    int have_read = 0;
    char field_name[128] = "";
    enum out_mode mode = MODE_SAMPLE;
    int duration_sec = 2;
    int top = 32;
    int allow_attach = 0, check_only = 0, verbose = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--event") && i + 1 < argc) {
            if (parse_event(argv[++i], group, sizeof(group), event, sizeof(event))) {
                fprintf(stderr, "bad --event (want GROUP:EVENT)\n"); return 2;
            }
        } else if (!strcmp(argv[i], "--field") && i + 1 < argc) {
            strncpy(field_name, argv[++i], sizeof(field_name) - 1);
            have_read = 1;
        } else if (!strcmp(argv[i], "--field-raw") && i + 1 < argc) {
            char *spec = argv[++i]; char *c = strchr(spec, ':');
            if (!c) { fprintf(stderr, "bad --field-raw\n"); return 2; }
            rs.is_deref = 0; rs.ctx_off = atoi(spec); rs.size = atoi(c + 1); have_read = 1;
        } else if (!strcmp(argv[i], "--deref") && i + 1 < argc) {
            if (parse_deref(argv[++i], &rs)) { fprintf(stderr, "bad --deref\n"); return 2; }
            have_read = 1;
        } else if (!strcmp(argv[i], "--mode") && i + 1 < argc) {
            const char *m = argv[++i];
            if (!strcmp(m, "sample")) mode = MODE_SAMPLE;
            else if (!strcmp(m, "freq")) mode = MODE_FREQ;
            else if (!strcmp(m, "stream")) mode = MODE_STREAM;
            else { fprintf(stderr, "bad --mode\n"); return 2; }
        } else if (!strcmp(argv[i], "--duration-sec") && i + 1 < argc) {
            duration_sec = atoi(argv[++i]);
            if (duration_sec < 0 || duration_sec > 120) { fprintf(stderr, "duration 0..120\n"); return 2; }
        } else if (!strcmp(argv[i], "--top") && i + 1 < argc) {
            top = atoi(argv[++i]);
            if (top < 1 || top > 4096) top = 32;
        } else if (!strcmp(argv[i], "--allow-attach")) {
            allow_attach = 1;
        } else if (!strcmp(argv[i], "--check-only")) {
            check_only = 1;
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
            usage(stdout); return 0;
        } else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            usage(stderr); return 2;
        }
    }

    printf("%s\n", A90_VERSION);
    if (!group[0] || !event[0]) { fprintf(stderr, "missing --event\n"); return 2; }
    if (!have_read) { fprintf(stderr, "missing read spec (--field/--field-raw/--deref)\n"); return 2; }

    /* resolve named field offset/size from the kernel's own format file */
    if (field_name[0]) {
        if (resolve_field(group, event, field_name, &rs.ctx_off, &rs.size) != 0) {
            printf("result=field-resolve-failed\n");
            perror("resolve-field"); return 1;
        }
        rs.is_deref = 0;
    }
    if (rs.size != 1 && rs.size != 2 && rs.size != 4 && rs.size != 8) {
        fprintf(stderr, "read size must be 1/2/4/8 (got %d)\n", rs.size); return 2;
    }

    printf("event=%s:%s\n", group, event);
    printf("tracefs=%s\n", tracefs_base());
    if (rs.is_deref) {
        printf("read=deref ctx_off=%d size=%d chain_len=%d\n", rs.ctx_off, rs.size, rs.chain_len);
    } else {
        printf("read=scalar off=%d size=%d%s%s\n", rs.ctx_off, rs.size,
               field_name[0] ? " field=" : "", field_name);
    }
    printf("mode=%s duration_sec=%d\n",
           mode == MODE_SAMPLE ? "sample" : mode == MODE_FREQ ? "freq" : "stream", duration_sec);

    if (check_only || !allow_attach) {
        printf("result=check-only\n");
        printf("attach_attempted=0\n");
        return 0;
    }

    /* BPF map/prog memory is charged against RLIMIT_MEMLOCK on this kernel;
     * raise it (root) so HASH/PERF maps are not rejected with EPERM. */
    struct rlimit rl = { RLIM_INFINITY, RLIM_INFINITY };
    if (setrlimit(RLIMIT_MEMLOCK, &rl) != 0 && verbose)
        fprintf(stderr, "setrlimit(MEMLOCK) failed: %s\n", strerror(errno));

    long long tp_id = -1;
    if (read_id(group, event, &tp_id) != 0) {
        printf("result=tracepoint-id-failed\n"); perror("tp-id"); return 1;
    }
    printf("tracepoint_id=%lld\n", tp_id);

    int ncpu = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpu < 1) ncpu = 1;

    int map_fd = create_map(mode, ncpu);
    if (map_fd < 0) { printf("result=map-create-failed\n"); printf("errno=%d\n", errno); perror("map"); return 1; }

    struct emitter e;
    build_prog(&e, &rs, mode, map_fd);
    printf("insn_cnt=%d\n", e.n);

    int prog_fd = load_prog(&e, verbose);
    if (prog_fd < 0) { int s = errno; close(map_fd); printf("result=bpf-load-failed\n"); printf("errno=%d\n", s); errno = s; perror("bpf-load"); return 1; }
    printf("bpf_prog_fd=%d\n", prog_fd);

    int tp_fd = attach_tp(prog_fd, tp_id);
    if (tp_fd < 0) { int s = errno; close(prog_fd); close(map_fd); printf("result=attach-failed\n"); printf("errno=%d\n", s); errno = s; perror("attach"); return 1; }
    printf("attach_attempted=1\n");
    printf("observe_begin=1\n");
    fflush(stdout);

    int rc = 0;
    if (mode == MODE_STREAM) {
        rc = stream_loop(map_fd, ncpu, duration_sec);
    } else {
        sleep((unsigned int)duration_sec);
    }

    ioctl(tp_fd, PERF_EVENT_IOC_DISABLE, 0);
    close(tp_fd);
    close(prog_fd);
    printf("observe_end=1\n");

    if (mode == MODE_SAMPLE) {
        if (read_sample(map_fd) != 0) { close(map_fd); printf("result=sample-read-failed\n"); return 1; }
    } else if (mode == MODE_FREQ) {
        dump_freq(map_fd, top);
    }
    close(map_fd);
    printf("result=%s\n", rc == 0 ? "extract-pass" : "extract-partial");
    return rc == 0 ? 0 : 1;
}
