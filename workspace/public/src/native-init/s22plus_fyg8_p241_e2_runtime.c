// SPDX-License-Identifier: MIT
/* P2.41 E2 exact-module and read-only bind/UDC runtime. */

#ifndef S22PLUS_FYG8_P233_PROFILE
#error "S22PLUS_FYG8_P233_PROFILE=3 is required"
#endif

#if S22PLUS_FYG8_P233_PROFILE != 3
#error "P2.41 E2 runtime requires checkpoint profile 3"
#endif

#ifndef S22PLUS_FYG8_P233_RUN_ID_BYTES
#error "S22PLUS_FYG8_P233_RUN_ID_BYTES must be supplied by the host build"
#endif

#define S22_R4W1E_E1_RUN_ID_BYTES S22PLUS_FYG8_P233_RUN_ID_BYTES
#define e1_run s22_p241_included_e1b_run
#define _start s22_p241_included_start
#include "s22plus_r4w1e_e1_runtime.c"
#undef _start
#undef e1_run

#include "s22plus_fyg8_p241_e2_plan.h"
#include "s22plus_o2_loader_core.h"

#define NR_GETDENTS64 61
#define NR_READLINKAT 78
#define NR_NEWFSTATAT 79
#define NR_CLOCK_GETTIME 113

#define AT_SYMLINK_NOFOLLOW 0x100
#define S_IFMT 0170000U
#define S_IFLNK 0120000U
#define CLOCK_MONOTONIC 1

#define ENOENT 2

#define S22_P241_MODULE_STAGE_BASE 0x40U
#define S22_P241_GATE_STAGE_BASE 0x7bU
#define S22_P241_SUCCESS_STAGE 0x8fU
#define S22_P241_GATE_TIMEOUT_SEC 20LL
#define S22_P241_GATE_POLL_NS 100000000LL
#define S22_P241_SYMLINK_TARGET_MAX 512U
#define S22_P241_DIRENT_BUFFER_SIZE 4096U

_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 59U, "E2 module count");
_Static_assert(S22PLUS_O2_BIND_GATE_COUNT == 8U, "E2 gate count");
_Static_assert(
    S22_P241_MODULE_STAGE_BASE + S22PLUS_O2_MODULE_PLAN_COUNT - 1U == 0x7aU,
    "E2 module stage range");
_Static_assert(
    S22_P241_GATE_STAGE_BASE + S22PLUS_O2_BIND_GATE_COUNT - 1U == 0x82U,
    "E2 gate stage range");

struct s22_p241_kernel_stat {
    uint64_t st_dev;
    uint64_t st_ino;
    uint32_t st_mode;
    uint32_t st_nlink;
    uint32_t st_uid;
    uint32_t st_gid;
    uint64_t st_rdev;
    uint64_t pad1;
    int64_t st_size;
    int32_t st_blksize;
    int32_t pad2;
    int64_t st_blocks;
    int64_t st_atime;
    uint64_t st_atime_nsec;
    int64_t st_mtime;
    uint64_t st_mtime_nsec;
    int64_t st_ctime;
    uint64_t st_ctime_nsec;
    uint32_t unused4;
    uint32_t unused5;
};

struct s22_p241_linux_dirent64 {
    uint64_t d_ino;
    int64_t d_off;
    uint16_t d_reclen;
    uint8_t d_type;
    char d_name[];
};

_Static_assert(sizeof(struct s22_p241_kernel_stat) == 128U, "arm64 stat size");
_Static_assert(
    offsetof(struct s22_p241_linux_dirent64, d_name) == 19U,
    "arm64 getdents64 name offset");

static const char *const k_e2_gate_basenames[] = {
    "soc:hwlock",
    "soc:qcom,smem",
    "80860000.aop_cmd_db_region",
    "af20000.rsc",
    "100000.clock-controller",
    "a600000.ssusb",
    "a600000.dwc3",
};

static long p241_finit_module(int fd, const char *params) {
    return syscall6(
        NR_FINIT_MODULE, fd, (long)(uintptr_t)params, 0, 0, 0, 0);
}

static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *stat_buffer, int flags) {
    return syscall6(
        NR_NEWFSTATAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        (long)(uintptr_t)stat_buffer,
        flags,
        0,
        0);
}

static long p241_readlinkat(const char *path, char *buffer, size_t size) {
    return syscall6(
        NR_READLINKAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        (long)(uintptr_t)buffer,
        (long)size,
        0,
        0);
}

static long p241_getdents64(int fd, void *buffer, size_t size) {
    return syscall6(
        NR_GETDENTS64, fd, (long)(uintptr_t)buffer, (long)size, 0, 0, 0);
}

static long p241_clock_gettime(struct timespec64 *time_value) {
    return syscall6(
        NR_CLOCK_GETTIME,
        CLOCK_MONOTONIC,
        (long)(uintptr_t)time_value,
        0,
        0,
        0,
        0);
}

static int p241_timespec_before(
    const struct timespec64 *left, const struct timespec64 *right) {
    return left->tv_sec < right->tv_sec ||
        (left->tv_sec == right->tv_sec && left->tv_nsec < right->tv_nsec);
}

static int p241_build_module_path(
    char *output, size_t capacity, const char *filename) {
    static const char prefix[] = "/lib/modules/";
    size_t prefix_size = sizeof(prefix) - 1U;
    size_t filename_size = cstr_len(filename);
    if (prefix_size + filename_size + 1U > capacity) {
        return -EINVAL;
    }
    for (size_t index = 0; index < prefix_size; ++index) {
        output[index] = prefix[index];
    }
    for (size_t index = 0; index < filename_size; ++index) {
        output[prefix_size + index] = filename[index];
    }
    output[prefix_size + filename_size] = '\0';
    return 0;
}

struct p241_proc_reader {
    int fd;
};

static long p241_proc_read(void *context, void *buffer, size_t size) {
    struct p241_proc_reader *reader = (struct p241_proc_reader *)context;
    return sys_read(reader->fd, buffer, size);
}

static long p241_verify_module_prefix(size_t count) {
    const char *names[S22PLUS_O2_MODULE_PLAN_COUNT];
    unsigned char found[S22PLUS_O2_MODULE_PLAN_COUNT];
    struct s22plus_o2_proc_scan_result scan;
    struct p241_proc_reader context;
    struct s22plus_o2_reader reader = {
        .context = &context,
        .read = p241_proc_read,
    };
    for (size_t index = 0; index < count; ++index) {
        names[index] = s22plus_o2_module_plan[index].runtime_name;
    }
    long fd = sys_openat("/proc/modules", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    context.fd = (int)fd;
    int scan_rc = s22plus_o2_scan_proc_modules(
        &reader, names, count, found, &scan);
    long close_rc = sys_close((int)fd);
    if (scan_rc != S22PLUS_O2_OK) {
        return scan_rc == S22PLUS_O2_ERR_READ ? -EIO : -ENODEV;
    }
    if (close_rc != 0) {
        return close_rc;
    }
    if (!scan.eof_seen || scan.malformed || scan.found_count != count ||
        scan.lines_seen != count) {
        return -ENODEV;
    }
    for (size_t index = 0; index < count; ++index) {
        if (found[index] != 1U) {
            return -ENODEV;
        }
    }
    return 0;
}

static long p241_load_and_verify_module(size_t index) {
    char path[160];
    int path_rc = p241_build_module_path(
        path, sizeof(path), s22plus_o2_module_plan[index].filename);
    if (path_rc != 0) {
        return path_rc;
    }
    long fd = sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long finit_rc = p241_finit_module(
        (int)fd, s22plus_o2_module_plan[index].params);
    long close_rc = sys_close((int)fd);
    if (finit_rc != 0) {
        return finit_rc;
    }
    if (close_rc != 0) {
        return close_rc;
    }
    return p241_verify_module_prefix(index + 1U);
}

static int p241_basename_equals(
    const char *target, size_t target_size, const char *expected) {
    size_t start = target_size;
    while (start > 0U && target[start - 1U] != '/') {
        --start;
    }
    return token_equals(target + start, target_size - start, expected);
}

static long p241_check_driver_symlink(size_t index) {
    struct s22_p241_kernel_stat stat_buffer = {0};
    char target[S22_P241_SYMLINK_TARGET_MAX];
    const char *path = s22plus_o2_bind_gates[index].path;
    long stat_rc = p241_newfstatat(path, &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (stat_rc != 0) {
        return stat_rc == -ENOENT ? -ENODEV : stat_rc;
    }
    if ((stat_buffer.st_mode & S_IFMT) != S_IFLNK) {
        return -ENODEV;
    }
    long target_size = p241_readlinkat(path, target, sizeof(target));
    if (target_size == -ENOENT) {
        return -ENODEV;
    }
    if (target_size <= 0 || target_size >= (long)sizeof(target)) {
        return target_size < 0 ? target_size : -EIO;
    }
    return p241_basename_equals(
        target, (size_t)target_size, k_e2_gate_basenames[index])
        ? 0
        : -ENODEV;
}

static int p241_is_dot_name(const char *name, size_t length) {
    return (length == 1U && name[0] == '.') ||
        (length == 2U && name[0] == '.' && name[1] == '.');
}

static long p241_check_udc(void) {
    uint8_t buffer[S22_P241_DIRENT_BUFFER_SIZE];
    unsigned int entries = 0;
    unsigned int exact = 0;
    long fd = sys_openat("/sys/class/udc", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd == -ENOENT ? -ENODEV : fd;
    }
    for (;;) {
        long amount = p241_getdents64((int)fd, buffer, sizeof(buffer));
        if (amount < 0) {
            (void)sys_close((int)fd);
            return amount;
        }
        if (amount == 0) {
            break;
        }
        size_t cursor = 0;
        while (cursor < (size_t)amount) {
            struct s22_p241_linux_dirent64 *entry =
                (struct s22_p241_linux_dirent64 *)(buffer + cursor);
            size_t header_size = offsetof(
                struct s22_p241_linux_dirent64, d_name);
            if (entry->d_reclen < header_size + 2U ||
                cursor + entry->d_reclen > (size_t)amount) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            size_t name_capacity = entry->d_reclen - header_size;
            size_t name_size = 0;
            while (name_size < name_capacity &&
                   entry->d_name[name_size] != '\0') {
                ++name_size;
            }
            if (name_size == name_capacity || name_size == 0U) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            if (!p241_is_dot_name(entry->d_name, name_size)) {
                ++entries;
                if (token_equals(
                        entry->d_name, name_size, "a600000.dwc3")) {
                    ++exact;
                }
            }
            cursor += entry->d_reclen;
        }
    }
    long close_rc = sys_close((int)fd);
    if (close_rc != 0) {
        return close_rc;
    }
    return entries == 1U && exact == 1U ? 0 : -ENODEV;
}

static long p241_check_gate(size_t index) {
    if (index < 7U) {
        return p241_check_driver_symlink(index);
    }
    return p241_check_udc();
}

static __attribute__((noreturn)) void p241_run(void) {
    struct child_session child = {.pid = -1, .token_fd = -1, .exec_fd = -1};
    E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());
    E1_REQUIRE(S22_R4W1E_STAGE_SYS_MOUNTED, 0U, mount_sys());
    E1_REQUIRE(S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED, 0U, mount_dev());
    E1_REQUIRE(S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED, 0U, mount_run());
    E1_REQUIRE(
        S22_R4W1E_STAGE_DEV_NODES_VERIFIED,
        0U,
        setup_and_verify_dev_null());
    E1_REQUIRE(
        S22_R4W1E_STAGE_CHILD_EXEC_STARTED, 0U, child_start(&child));
    E1_REQUIRE(
        S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED,
        0U,
        child_verify_token(&child));
    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_reap(&child));

    for (size_t index = 0; index < S22PLUS_O2_MODULE_PLAN_COUNT; ++index) {
        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
    }

    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        fail_at(S22_P241_GATE_STAGE_BASE, 0U, -EIO);
    }
    deadline.tv_sec += S22_P241_GATE_TIMEOUT_SEC;
    size_t completed = 0;
    while (completed < S22PLUS_O2_BIND_GATE_COUNT) {
        for (size_t index = 0; index <= completed; ++index) {
            long gate_rc = p241_check_gate(index);
            if (index < completed) {
                if (gate_rc != 0) {
                    fail_at(
                        S22_P241_GATE_STAGE_BASE + (uint8_t)index,
                        (uint8_t)index,
                        gate_rc);
                }
                continue;
            }
            if (gate_rc == 0) {
                long checkpoint_rc = s22_r4w1e_checkpoint_progress(
                    &g_checkpoint,
                    S22_P241_GATE_STAGE_BASE + (uint8_t)index,
                    (uint8_t)index);
                if (checkpoint_rc != 0) {
                    quiet_park();
                }
                ++completed;
            } else if (gate_rc != -ENODEV) {
                fail_at(
                    S22_P241_GATE_STAGE_BASE + (uint8_t)index,
                    (uint8_t)index,
                    gate_rc);
            }
            break;
        }
        if (completed == S22PLUS_O2_BIND_GATE_COUNT) {
            break;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            fail_at(
                S22_P241_GATE_STAGE_BASE + (uint8_t)completed,
                (uint8_t)completed,
                -EIO);
        }
        if (!p241_timespec_before(&now, &deadline)) {
            fail_at(
                S22_P241_GATE_STAGE_BASE + (uint8_t)completed,
                (uint8_t)completed,
                -ETIMEDOUT);
        }
        (void)sys_nanosleep(S22_P241_GATE_POLL_NS);
    }
    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {
        quiet_park();
    }
    quiet_park();
}

__attribute__((noreturn)) void _start(void) {
    if (sys_getpid() != 1) {
        quiet_park();
    }
    if (s22_r4w1e_checkpoint_client_init(&g_checkpoint, k_run_id) != 0) {
        quiet_park();
    }
    p241_run();
}
