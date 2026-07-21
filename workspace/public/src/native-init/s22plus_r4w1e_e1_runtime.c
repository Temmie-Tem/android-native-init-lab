// SPDX-License-Identifier: MIT
/* Fixed E1 userspace proof for Samsung S22+ FYG8 R4W1-E. */

#include "s22plus_r4w1e_checkpoint.h"

#include <stddef.h>
#include <stdint.h>

#ifndef S22_R4W1E_E1_RUN_ID_BYTES
#error "S22_R4W1E_E1_RUN_ID_BYTES must be supplied by the host manifest build"
#endif

#define AT_FDCWD (-100)

#define O_RDONLY 00000000
#define O_RDWR 00000002
#define O_NONBLOCK 00004000
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define MS_NOSUID 2UL
#define MS_NODEV 4UL
#define MS_NOEXEC 8UL

#define EIO 5
#define EAGAIN 11
#define EEXIST 17
#define ENODEV 19
#define EINVAL 22
#define ETIMEDOUT 110

#define SIGKILL 9
#define SIGCHLD 17
#define WNOHANG 1

#define NR_DUP3 24
#define NR_MKNODAT 33
#define NR_MKDIRAT 34
#define NR_MOUNT 40
#define NR_STATFS 43
#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_PIPE2 59
#define NR_READ 63
#define NR_WRITE 64
#define NR_EXIT 93
#define NR_NANOSLEEP 101
#define NR_KILL 129
#define NR_GETPID 172
#define NR_CLONE 220
#define NR_EXECVE 221
#define NR_WAIT4 260
#define NR_FINIT_MODULE 273

#define PROC_SUPER_MAGIC 0x00009fa0L
#define SYSFS_MAGIC 0x62656572L
#define TMPFS_MAGIC 0x01021994L

#define MODULE_COUNT 5U
#define PROC_MODULES_CAPACITY 32768U
#define CHILD_WAIT_LOOPS 50U

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct statfs_probe {
    int64_t f_type;
    uint8_t remainder[248];
};

struct module_spec {
    const char *file_name;
    const char *runtime_name;
};

struct child_session {
    long pid;
    int token_fd;
    int exec_fd;
};

static const uint8_t k_run_id[16] = S22_R4W1E_E1_RUN_ID_BYTES;
static const char k_child_path[] = "/s22-e1-child";
static const char k_child_token[] =
    "S22PLUS_R4W1E_E1_CHILD_OK:4c3e58c0785b\n";

static const struct module_spec k_modules[MODULE_COUNT] = {
    {"smem.ko", "smem"},
    {"minidump.ko", "minidump"},
    {"qcom-scm.ko", "qcom_scm"},
    {"qcom_wdt_core.ko", "qcom_wdt_core"},
    {"gh_virt_wdt.ko", "gh_virt_wdt"},
};

static struct s22_r4w1e_checkpoint_client g_checkpoint;

static inline long syscall6(
    long nr,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = nr;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
        : "memory");
    return x0;
}

static long sys_openat(const char *path, int flags, unsigned int mode) {
    return syscall6(
        NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, flags, mode, 0, 0);
}

static long sys_close(int fd) {
    return syscall6(NR_CLOSE, fd, 0, 0, 0, 0, 0);
}

static long sys_read(int fd, void *buffer, size_t count) {
    return syscall6(
        NR_READ, fd, (long)(uintptr_t)buffer, (long)count, 0, 0, 0);
}

static long sys_write(int fd, const void *buffer, size_t count) {
    return syscall6(
        NR_WRITE, fd, (long)(uintptr_t)buffer, (long)count, 0, 0, 0);
}

static long sys_mkdirat(const char *path, unsigned int mode) {
    return syscall6(
        NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, mode, 0, 0, 0);
}

static long sys_mknodat(const char *path, unsigned int mode, uint64_t dev) {
    return syscall6(
        NR_MKNODAT, AT_FDCWD, (long)(uintptr_t)path, mode, (long)dev, 0, 0);
}

static long sys_mount(
    const char *source,
    const char *target,
    const char *fstype,
    unsigned long flags,
    const char *data) {
    return syscall6(
        NR_MOUNT,
        (long)(uintptr_t)source,
        (long)(uintptr_t)target,
        (long)(uintptr_t)fstype,
        (long)flags,
        (long)(uintptr_t)data,
        0);
}

static long sys_statfs(const char *path, struct statfs_probe *probe) {
    return syscall6(
        NR_STATFS, (long)(uintptr_t)path, (long)(uintptr_t)probe, 0, 0, 0, 0);
}

static long sys_pipe2(int pipe_fds[2], int flags) {
    return syscall6(NR_PIPE2, (long)(uintptr_t)pipe_fds, flags, 0, 0, 0, 0);
}

static long sys_dup3(int old_fd, int new_fd, int flags) {
    return syscall6(NR_DUP3, old_fd, new_fd, flags, 0, 0, 0);
}

static long sys_clone(void) {
    return syscall6(NR_CLONE, SIGCHLD, 0, 0, 0, 0, 0);
}

static long sys_execve(
    const char *path, char *const argv[], char *const envp[]) {
    return syscall6(
        NR_EXECVE,
        (long)(uintptr_t)path,
        (long)(uintptr_t)argv,
        (long)(uintptr_t)envp,
        0,
        0,
        0);
}

static long sys_wait4(long pid, int *status, int options) {
    return syscall6(
        NR_WAIT4, pid, (long)(uintptr_t)status, options, 0, 0, 0);
}

static long sys_kill(long pid, int signal) {
    return syscall6(NR_KILL, pid, signal, 0, 0, 0, 0);
}

static long sys_finit_module(int fd) {
    return syscall6(NR_FINIT_MODULE, fd, (long)(uintptr_t)"", 0, 0, 0, 0);
}

static long sys_getpid(void) {
    return syscall6(NR_GETPID, 0, 0, 0, 0, 0, 0);
}

static long sys_nanosleep(int64_t nanoseconds) {
    struct timespec64 request = {
        .tv_sec = nanoseconds / 1000000000LL,
        .tv_nsec = nanoseconds % 1000000000LL,
    };
    return syscall6(
        NR_NANOSLEEP, (long)(uintptr_t)&request, 0, 0, 0, 0, 0);
}

__attribute__((noreturn)) static void sys_exit(int status) {
    (void)syscall6(NR_EXIT, status, 0, 0, 0, 0, 0);
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}

void *memset(void *destination, int value, size_t count) {
    uint8_t *output = (uint8_t *)destination;
    for (size_t index = 0; index < count; ++index) {
        output[index] = (uint8_t)value;
    }
    return destination;
}

static size_t cstr_len(const char *value) {
    size_t length = 0;
    while (value[length] != '\0') {
        ++length;
    }
    return length;
}

static int token_equals(
    const char *value, size_t value_length, const char *expected) {
    size_t expected_length = cstr_len(expected);
    if (value_length != expected_length) {
        return 0;
    }
    for (size_t index = 0; index < value_length; ++index) {
        if (value[index] != expected[index]) {
            return 0;
        }
    }
    return 1;
}

static uint64_t make_dev(unsigned int major_num, unsigned int minor_num) {
    return ((uint64_t)(minor_num & 0xffU)) |
           ((uint64_t)(major_num & 0xfffU) << 8) |
           ((uint64_t)(minor_num & ~0xffU) << 12) |
           ((uint64_t)(major_num & ~0xfffU) << 32);
}

static long ensure_dir(const char *path) {
    long result = sys_mkdirat(path, 0755);
    return result == 0 || result == -EEXIST ? 0 : result;
}

static long mount_and_verify(
    const char *source,
    const char *target,
    const char *fstype,
    unsigned long flags,
    const char *data,
    int64_t expected_magic) {
    struct statfs_probe probe = {0};
    long result = ensure_dir(target);
    if (result != 0) {
        return result;
    }
    result = sys_mount(source, target, fstype, flags, data);
    if (result != 0) {
        return result;
    }
    result = sys_statfs(target, &probe);
    if (result != 0) {
        return result;
    }
    return probe.f_type == expected_magic ? 0 : -ENODEV;
}

static long mount_proc(void) {
    return mount_and_verify(
        "proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "", PROC_SUPER_MAGIC);
}

static long mount_sys(void) {
    return mount_and_verify(
        "sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "", SYSFS_MAGIC);
}

static long mount_dev(void) {
    return mount_and_verify(
        "tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755", TMPFS_MAGIC);
}

static long mount_run(void) {
    return mount_and_verify(
        "tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "mode=0755", TMPFS_MAGIC);
}

static long setup_and_verify_dev_null(void) {
    char probe = 'N';
    long result = sys_mknodat(
        "/dev/null", S_IFCHR | 0600U, make_dev(1U, 3U));
    if (result != 0) {
        return result;
    }
    long fd = sys_openat("/dev/null", O_RDWR | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long written = sys_write((int)fd, &probe, 1U);
    long read_result = sys_read((int)fd, &probe, 1U);
    if (written != 1 || read_result != 0) {
        (void)sys_close((int)fd);
        return -EIO;
    }
    for (int target = 0; target <= 2; ++target) {
        if (fd != target && sys_dup3((int)fd, target, 0) != target) {
            (void)sys_close((int)fd);
            return -EIO;
        }
    }
    return fd > 2 ? sys_close((int)fd) : 0;
}

static void close_if_open(int *fd) {
    if (*fd >= 0) {
        (void)sys_close(*fd);
        *fd = -1;
    }
}

static void reap_after_kill(long pid) {
    int status = 0;
    if (pid <= 0) {
        return;
    }
    (void)sys_kill(pid, SIGKILL);
    for (unsigned int attempt = 0; attempt < CHILD_WAIT_LOOPS; ++attempt) {
        long waited = sys_wait4(pid, &status, WNOHANG);
        if (waited == pid || waited < 0) {
            return;
        }
        (void)sys_nanosleep(100000000LL);
    }
}

static long child_abort(struct child_session *child, long error) {
    close_if_open(&child->token_fd);
    close_if_open(&child->exec_fd);
    reap_after_kill(child->pid);
    child->pid = -1;
    return error != 0 ? error : -EIO;
}

__attribute__((noreturn)) static void child_exec(
    int token_pipe[2], int exec_pipe[2]) {
    char *const argv[] = {(char *)k_child_path, NULL};
    char *const envp[] = {NULL};
    (void)sys_close(token_pipe[0]);
    (void)sys_close(exec_pipe[0]);
    if (sys_dup3(token_pipe[1], 1, 0) != 1) {
        int error = EIO;
        (void)sys_write(exec_pipe[1], &error, sizeof(error));
        sys_exit(126);
    }
    (void)sys_close(token_pipe[1]);
    long result = sys_execve(k_child_path, argv, envp);
    int error = result < 0 ? (int)(-result) : EIO;
    (void)sys_write(exec_pipe[1], &error, sizeof(error));
    sys_exit(127);
}

static long wait_for_exec_result(struct child_session *child) {
    for (unsigned int attempt = 0; attempt < CHILD_WAIT_LOOPS; ++attempt) {
        int error = 0;
        long result = sys_read(child->exec_fd, &error, sizeof(error));
        if (result == 0) {
            close_if_open(&child->exec_fd);
            return 0;
        }
        if (result == (long)sizeof(error)) {
            close_if_open(&child->exec_fd);
            return error > 0 ? -error : -EIO;
        }
        if (result != -EAGAIN) {
            close_if_open(&child->exec_fd);
            return result < 0 ? result : -EIO;
        }
        (void)sys_nanosleep(100000000LL);
    }
    close_if_open(&child->exec_fd);
    return -ETIMEDOUT;
}

static long child_start(struct child_session *child) {
    int token_pipe[2] = {-1, -1};
    int exec_pipe[2] = {-1, -1};
    child->pid = -1;
    child->token_fd = -1;
    child->exec_fd = -1;
    long result = sys_pipe2(token_pipe, O_CLOEXEC | O_NONBLOCK);
    if (result != 0) {
        return result;
    }
    result = sys_pipe2(exec_pipe, O_CLOEXEC | O_NONBLOCK);
    if (result != 0) {
        (void)sys_close(token_pipe[0]);
        (void)sys_close(token_pipe[1]);
        return result;
    }
    long pid = sys_clone();
    if (pid == 0) {
        child_exec(token_pipe, exec_pipe);
    }
    if (pid < 0) {
        (void)sys_close(token_pipe[0]);
        (void)sys_close(token_pipe[1]);
        (void)sys_close(exec_pipe[0]);
        (void)sys_close(exec_pipe[1]);
        return pid;
    }
    child->pid = pid;
    child->token_fd = token_pipe[0];
    child->exec_fd = exec_pipe[0];
    (void)sys_close(token_pipe[1]);
    (void)sys_close(exec_pipe[1]);
    result = wait_for_exec_result(child);
    if (result != 0) {
        return child_abort(child, result);
    }
    return 0;
}

static long child_verify_token(struct child_session *child) {
    char token[128];
    size_t used = 0;
    for (unsigned int attempt = 0; attempt < CHILD_WAIT_LOOPS; ++attempt) {
        long result = sys_read(
            child->token_fd, token + used, sizeof(token) - used);
        if (result > 0) {
            used += (size_t)result;
            if (used == sizeof(token)) {
                return child_abort(child, -EIO);
            }
            continue;
        }
        if (result == 0) {
            close_if_open(&child->token_fd);
            if (!token_equals(token, used, k_child_token)) {
                return child_abort(child, -EIO);
            }
            return 0;
        }
        if (result != -EAGAIN) {
            return child_abort(child, result);
        }
        (void)sys_nanosleep(100000000LL);
    }
    return child_abort(child, -ETIMEDOUT);
}

static long child_reap(struct child_session *child) {
    int status = 0;
    for (unsigned int attempt = 0; attempt < CHILD_WAIT_LOOPS; ++attempt) {
        long waited = sys_wait4(child->pid, &status, WNOHANG);
        if (waited == child->pid) {
            child->pid = -1;
            return status == (23 << 8) ? 0 : -EIO;
        }
        if (waited < 0) {
            return child_abort(child, waited);
        }
        (void)sys_nanosleep(100000000LL);
    }
    return child_abort(child, -ETIMEDOUT);
}

static int build_module_path(char *output, size_t size, const char *file_name) {
    static const char prefix[] = "/lib/modules/";
    size_t prefix_length = sizeof(prefix) - 1U;
    size_t file_length = cstr_len(file_name);
    if (prefix_length + file_length + 1U > size) {
        return -EINVAL;
    }
    for (size_t index = 0; index < prefix_length; ++index) {
        output[index] = prefix[index];
    }
    for (size_t index = 0; index < file_length; ++index) {
        output[prefix_length + index] = file_name[index];
    }
    output[prefix_length + file_length] = '\0';
    return 0;
}

static long read_proc_modules(char *buffer, size_t capacity) {
    long fd = sys_openat("/proc/modules", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    size_t used = 0;
    while (used < capacity) {
        long result = sys_read((int)fd, buffer + used, capacity - used);
        if (result < 0) {
            (void)sys_close((int)fd);
            return result;
        }
        if (result == 0) {
            long closed = sys_close((int)fd);
            return closed == 0 ? (long)used : closed;
        }
        used += (size_t)result;
    }
    char overflow;
    long extra = sys_read((int)fd, &overflow, 1U);
    long closed = sys_close((int)fd);
    return extra == 0 && closed == 0 ? (long)used : -EIO;
}

static int module_index(const char *token, size_t length) {
    for (size_t index = 0; index < MODULE_COUNT; ++index) {
        if (token_equals(token, length, k_modules[index].runtime_name)) {
            return (int)index;
        }
    }
    return -1;
}

static long verify_module_prefix(size_t last_expected) {
    char contents[PROC_MODULES_CAPACITY];
    unsigned int seen[MODULE_COUNT] = {0};
    long size = read_proc_modules(contents, sizeof(contents));
    if (size <= 0) {
        return size < 0 ? size : -ENODEV;
    }
    size_t cursor = 0;
    size_t line_count = 0;
    while (cursor < (size_t)size) {
        size_t start = cursor;
        while (cursor < (size_t)size && contents[cursor] != '\n') {
            if (contents[cursor] == '\0') {
                return -EIO;
            }
            ++cursor;
        }
        size_t end = cursor;
        if (cursor < (size_t)size) {
            ++cursor;
        }
        if (end == start) {
            continue;
        }
        size_t token_end = start;
        while (token_end < end && contents[token_end] != ' ' &&
               contents[token_end] != '\t') {
            ++token_end;
        }
        int index = module_index(contents + start, token_end - start);
        if (index < 0 || (size_t)index > last_expected || seen[index] != 0U) {
            return -ENODEV;
        }
        seen[index] = 1U;
        ++line_count;
    }
    if (line_count != last_expected + 1U) {
        return -ENODEV;
    }
    for (size_t index = 0; index <= last_expected; ++index) {
        if (seen[index] != 1U) {
            return -ENODEV;
        }
    }
    return 0;
}

static long load_and_verify_module(size_t index) {
    char path[160];
    int path_result = build_module_path(
        path, sizeof(path), k_modules[index].file_name);
    if (path_result != 0) {
        return path_result;
    }
    long fd = sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long loaded = sys_finit_module((int)fd);
    long closed = sys_close((int)fd);
    if (loaded != 0) {
        return loaded;
    }
    if (closed != 0) {
        return closed;
    }
    return verify_module_prefix(index);
}

static long verify_exact_modules(void) {
    return verify_module_prefix(MODULE_COUNT - 1U);
}

__attribute__((noreturn)) static void quiet_park(void) {
    for (;;) {
        int status = 0;
        while (sys_wait4(-1, &status, WNOHANG) > 0) {
        }
        (void)sys_nanosleep(10000000000LL);
    }
}

__attribute__((noreturn)) static void fail_at(
    uint8_t stage, uint8_t item_index, long operation_error) {
    (void)s22_r4w1e_checkpoint_failure(
        &g_checkpoint, stage, item_index, operation_error);
    quiet_park();
}

#define E1_REQUIRE(stage, item_index, operation)             \
    do {                                                      \
        long e1_operation_result = (operation);               \
        if (e1_operation_result != 0) {                       \
            fail_at((stage), (item_index), e1_operation_result); \
        }                                                     \
        long e1_checkpoint_result =                           \
            s22_r4w1e_checkpoint_progress(                    \
                &g_checkpoint, (stage), (item_index));        \
        if (e1_checkpoint_result != 0) {                      \
            quiet_park();                                     \
        }                                                     \
    } while (0)

__attribute__((noreturn)) static void e1_run(void) {
    struct child_session child = {.pid = -1, .token_fd = -1, .exec_fd = -1};
    E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());
    E1_REQUIRE(S22_R4W1E_STAGE_SYS_MOUNTED, 0U, mount_sys());
    E1_REQUIRE(S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED, 0U, mount_dev());
    E1_REQUIRE(S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED, 0U, mount_run());
    E1_REQUIRE(S22_R4W1E_STAGE_DEV_NODES_VERIFIED, 0U, setup_and_verify_dev_null());
    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_EXEC_STARTED, 0U, child_start(&child));
    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED, 0U, child_verify_token(&child));
    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_reap(&child));
    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULE_0, 0U, load_and_verify_module(0U));
    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULE_1, 1U, load_and_verify_module(1U));
    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULE_2, 2U, load_and_verify_module(2U));
    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULE_3, 3U, load_and_verify_module(3U));
    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULE_4, 4U, load_and_verify_module(4U));
    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULES_VERIFIED, 0U, verify_exact_modules());
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
    e1_run();
}
