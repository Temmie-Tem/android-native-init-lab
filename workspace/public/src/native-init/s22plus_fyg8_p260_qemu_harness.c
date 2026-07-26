// SPDX-License-Identifier: MIT
/*
 * Generic-arm64 execution harness for the P2.60 E3 userspace sequence.
 *
 * This is deliberately not an S22+ emulator. It reuses the exact P2.60
 * configfs/ACM helpers and replaces only the Qualcomm role/UDC boundary with
 * dummy_hcd inside a disposable QEMU guest.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/stat.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define S22PLUS_O2_BIND_GATE_COUNT 12U
#define S22_P248_DETAIL_REGRESSION_BASE 0x800L
#define S22_P248_DETAIL_READ_ERROR_BASE 0x900L
#define S22_P258_UDC_GATE_INDEX 11U

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct statfs_probe {
    int64_t f_type;
    int64_t opaque[15];
};

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
    int64_t atime_seconds;
    uint64_t atime_nanoseconds;
    int64_t mtime_seconds;
    uint64_t mtime_nanoseconds;
    int64_t ctime_seconds;
    uint64_t ctime_nanoseconds;
    uint32_t unused4;
    uint32_t unused5;
};

struct p260_qemu_checkpoint {
    unsigned int unused;
};

static struct p260_qemu_checkpoint g_checkpoint;
static const uint8_t k_run_id[16] = {
    0x50, 0x32, 0x36, 0x30, 0x51, 0x45, 0x4d, 0x55,
    0x45, 0x33, 0x48, 0x41, 0x52, 0x4e, 0x45, 0x53,
};
static int g_qemu_trace_configfs;

static int qemu_path_is_configfs(const char *path) {
    static const char prefix[] = "/config/";
    if (path == NULL) {
        return 0;
    }
    for (size_t index = 0; index < sizeof(prefix) - 1U; ++index) {
        if (path[index] != prefix[index]) {
            return 0;
        }
    }
    return 1;
}

static size_t cstr_len(const char *text) {
    size_t length = 0;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

static long syscall6(
    long number,
    long argument0,
    long argument1,
    long argument2,
    long argument3,
    long argument4,
    long argument5) {
    const char *symlink_target =
        number == 36 ? (const char *)(uintptr_t)argument0 : NULL;
    long result = syscall(
        number,
        argument0,
        argument1,
        argument2,
        argument3,
        argument4,
        argument5);
    int saved_errno = result < 0 ? errno : 0;
    long normalized = result < 0 ? -saved_errno : result;
    if (g_qemu_trace_configfs && number == 36) {
        dprintf(
            STDOUT_FILENO,
            "P260_QEMU trace=symlinkat target=%s path=%s rc=%ld\n",
            symlink_target,
            (const char *)(uintptr_t)argument2,
            normalized);
    }
    return normalized;
}

static long sys_openat(const char *path, int flags, unsigned int mode) {
    int fd = openat(AT_FDCWD, path, flags, mode);
    long result = fd < 0 ? -errno : fd;
    if (g_qemu_trace_configfs && qemu_path_is_configfs(path)) {
        dprintf(
            STDOUT_FILENO,
            "P260_QEMU trace=open path=%s flags=0x%x rc=%ld\n",
            path,
            flags,
            result);
    }
    return result;
}

static long sys_close(int fd) {
    return close(fd) == 0 ? 0 : -errno;
}

static long sys_read(int fd, void *buffer, size_t size) {
    ssize_t amount = read(fd, buffer, size);
    return amount < 0 ? -errno : amount;
}

static long sys_write(int fd, const void *buffer, size_t size) {
    ssize_t amount = write(fd, buffer, size);
    long result = amount < 0 ? -errno : amount;
    if (g_qemu_trace_configfs) {
        dprintf(
            STDOUT_FILENO,
            "P260_QEMU trace=write fd=%d size=%zu rc=%ld\n",
            fd,
            size,
            result);
    }
    return result;
}

static long sys_mkdirat(const char *path, unsigned int mode) {
    long result = mkdirat(AT_FDCWD, path, mode) == 0 ? 0 : -errno;
    if (g_qemu_trace_configfs && qemu_path_is_configfs(path)) {
        dprintf(
            STDOUT_FILENO,
            "P260_QEMU trace=mkdir path=%s rc=%ld\n",
            path,
            result);
    }
    return result;
}

static long sys_mknodat(
    const char *path, unsigned int mode, uint64_t device) {
    return mknodat(AT_FDCWD, path, mode, (dev_t)device) == 0 ? 0 : -errno;
}

static long sys_mount(
    const char *source,
    const char *target,
    const char *filesystem,
    unsigned long flags,
    const char *data) {
    return mount(source, target, filesystem, flags, data) == 0 ? 0 : -errno;
}

static long sys_statfs(const char *path, struct statfs_probe *probe) {
    struct statfs value;
    if (statfs(path, &value) != 0) {
        return -errno;
    }
    probe->f_type = value.f_type;
    return 0;
}

static long sys_nanosleep(int64_t nanoseconds) {
    struct timespec request = {
        .tv_sec = nanoseconds / 1000000000LL,
        .tv_nsec = nanoseconds % 1000000000LL,
    };
    while (nanosleep(&request, &request) != 0) {
        if (errno != EINTR) {
            return -errno;
        }
    }
    return 0;
}

static long p241_clock_gettime(struct timespec64 *value) {
    struct timespec current;
    if (clock_gettime(CLOCK_MONOTONIC, &current) != 0) {
        return -errno;
    }
    value->tv_sec = current.tv_sec;
    value->tv_nsec = current.tv_nsec;
    return 0;
}

static int p241_timespec_before(
    const struct timespec64 *left, const struct timespec64 *right) {
    return left->tv_sec < right->tv_sec
        || (left->tv_sec == right->tv_sec
            && left->tv_nsec < right->tv_nsec);
}

static long p241_newfstatat(
    const char *path,
    struct s22_p241_kernel_stat *result,
    int flags) {
    struct stat value;
    if (fstatat(AT_FDCWD, path, &value, flags) != 0) {
        return -errno;
    }
    result->st_mode = value.st_mode;
    result->st_rdev = value.st_rdev;
    return 0;
}

static long p241_readlinkat(
    const char *path, char *buffer, size_t capacity) {
    ssize_t amount = readlinkat(AT_FDCWD, path, buffer, capacity);
    long result = amount < 0 ? -errno : amount;
    if (g_qemu_trace_configfs && qemu_path_is_configfs(path)) {
        dprintf(
            STDOUT_FILENO,
            "P260_QEMU trace=readlink path=%s rc=%ld target=%.*s\n",
            path,
            result,
            amount > 0 ? (int)amount : 0,
            buffer);
    }
    return result;
}

static long p241_check_gate(size_t index) {
    return index < S22PLUS_O2_BIND_GATE_COUNT ? 0 : -EINVAL;
}

static int s22_r4w1e_checkpoint_progress(
    struct p260_qemu_checkpoint *checkpoint,
    uint8_t stage,
    uint8_t item) {
    (void)checkpoint;
    (void)stage;
    (void)item;
    return 0;
}

static int s22_r4w1e_checkpoint_success(
    struct p260_qemu_checkpoint *checkpoint) {
    (void)checkpoint;
    return 0;
}

static __attribute__((noreturn)) void quiet_park(void) {
    for (;;) {
        pause();
    }
}

static __attribute__((noreturn)) void fail_at(
    uint8_t stage, uint8_t item, long detail) {
    dprintf(
        STDOUT_FILENO,
        "P260_QEMU result=FAIL stage=0x%02x item=%u detail=%ld\n",
        stage,
        item,
        detail);
    sync();
    quiet_park();
}

#define memcpy p260_qemu_memcpy
#include "s22plus_fyg8_p260_e3_runtime.inc.c"
#undef memcpy

static const char k_qemu_udc_name[] = "dummy_udc.0";
static const char k_qemu_udc_root[] = "/sys/class/udc/dummy_udc.0";

static void qemu_log_stage(uint8_t stage, const char *name) {
    dprintf(
        STDOUT_FILENO,
        "P260_QEMU stage=0x%02x status=PASS name=%s\n",
        stage,
        name);
}

static __attribute__((noreturn)) void qemu_fail(
    uint8_t stage, const char *name, long detail) {
    dprintf(
        STDOUT_FILENO,
        "P260_QEMU result=FAIL stage=0x%02x name=%s detail=%ld\n",
        stage,
        name,
        detail);
    sync();
    quiet_park();
}

static void qemu_mkdir(const char *path) {
    if (mkdir(path, 0755) != 0 && errno != EEXIST) {
        qemu_fail(0, "mkdir", -errno);
    }
}

static void qemu_mount_base(void) {
    qemu_mkdir("/proc");
    qemu_mkdir("/sys");
    qemu_mkdir("/dev");
    if (mount("proc", "/proc", "proc", 0, "") != 0 && errno != EBUSY) {
        qemu_fail(0, "mount-proc", -errno);
    }
    if (mount("sysfs", "/sys", "sysfs", 0, "") != 0 && errno != EBUSY) {
        qemu_fail(0, "mount-sysfs", -errno);
    }
    if (
        mount("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755") != 0
        && errno != EBUSY
    ) {
        qemu_fail(0, "mount-devtmpfs", -errno);
    }
}

static void qemu_load_module(const char *name) {
    char path[160];
    int length = snprintf(path, sizeof(path), "/modules/%s.ko", name);
    if (length <= 0 || (size_t)length >= sizeof(path)) {
        qemu_fail(0, "module-path", -EOVERFLOW);
    }
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        qemu_fail(0, name, -errno);
    }
    long rc = syscall(SYS_finit_module, fd, "", 0);
    int saved_errno = errno;
    close(fd);
    if (rc != 0 && saved_errno != EEXIST) {
        qemu_fail(0, name, -saved_errno);
    }
    dprintf(STDOUT_FILENO, "P260_QEMU module=%s status=PASS\n", name);
}

static long qemu_wait_configured(void) {
    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        return -EIO;
    }
    deadline.tv_sec += P260_CONFIGURED_TIMEOUT_SEC;
    for (;;) {
        char state[32];
        char speed[32];
        char state_path[128];
        char speed_path[128];
        size_t state_length = 0;
        size_t speed_length = 0;
        snprintf(state_path, sizeof(state_path), "%s/state", k_qemu_udc_root);
        snprintf(
            speed_path,
            sizeof(speed_path),
            "%s/current_speed",
            k_qemu_udc_root);
        long state_rc = p260_read_value(
            state_path, state, sizeof(state), &state_length);
        long speed_rc = p260_read_value(
            speed_path, speed, sizeof(speed), &speed_length);
        if (state_rc != 0) {
            return state_rc;
        }
        if (speed_rc != 0) {
            return speed_rc;
        }
        int configured = state_length == 10U
            && p260_bytes_equal(state, "configured", 10U);
        int high_speed = speed_length == 10U
            && p260_bytes_equal(speed, "high-speed", 10U);
        if (configured) {
            return high_speed ? 0 : -P260_EPROTO;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            return -EIO;
        }
        if (!p241_timespec_before(&now, &deadline)) {
            return -ETIMEDOUT;
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

static int qemu_observe_banner(int output_fd) {
    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        return EIO;
    }
    deadline.tv_sec += P260_CONFIGURED_TIMEOUT_SEC;
    int fd = -1;
    char observed[sizeof(p260_banner)] = {0};
    size_t used = 0;
    for (;;) {
        if (fd < 0) {
            fd = open(
                "/dev/ttyACM0",
                O_RDONLY | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
        }
        if (fd >= 0 && used < sizeof(p260_banner) - 1U) {
            ssize_t amount = read(
                fd,
                observed + used,
                sizeof(p260_banner) - 1U - used);
            if (amount > 0) {
                used += (size_t)amount;
            } else if (amount < 0 && errno != EAGAIN && errno != EINTR) {
                close(fd);
                return errno;
            }
        }
        if (
            used == sizeof(p260_banner) - 1U
            && p260_bytes_equal(
                observed, p260_banner, sizeof(p260_banner) - 1U)
        ) {
            ssize_t amount = write(output_fd, observed, used);
            if (fd >= 0) {
                close(fd);
            }
            return amount == (ssize_t)used ? 0 : EIO;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            if (fd >= 0) {
                close(fd);
            }
            return EIO;
        }
        if (!p241_timespec_before(&now, &deadline)) {
            if (fd >= 0) {
                close(fd);
            }
            return ETIMEDOUT;
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    qemu_mount_base();

    static const char *const modules[] = {
        "usb-common",
        "usbcore",
        "configfs",
        "udc-core",
        "libcomposite",
        "dummy_hcd",
        "u_serial",
        "usb_f_acm",
        "cdc-acm",
    };
    for (size_t index = 0; index < sizeof(modules) / sizeof(modules[0]); ++index) {
        qemu_load_module(modules[index]);
    }

    p260_derive_identity();
    long rc = p260_mount_configfs();
    if (rc != 0) {
        qemu_fail(P260_CONFIG_STAGE, "configfs", rc);
    }
    qemu_log_stage(P260_CONFIG_STAGE, "configfs");

    g_qemu_trace_configfs = 1;
    rc = p260_create_gadget();
    g_qemu_trace_configfs = 0;
    if (rc != 0) {
        qemu_fail(P260_GADGET_STAGE, "gadget", rc);
    }
    qemu_log_stage(P260_GADGET_STAGE, "gadget");

    unsigned int major_number = 0;
    unsigned int minor_number = 0;
    rc = p260_wait_tty_dev(&major_number, &minor_number);
    if (rc != 0) {
        qemu_fail(P260_TTY_CLASS_STAGE, "tty-class", rc);
    }
    qemu_log_stage(P260_TTY_CLASS_STAGE, "tty-class");

    int tty_fd = -1;
    rc = p260_prepare_tty_node(major_number, minor_number);
    if (rc == 0) {
        rc = p260_open_raw_tty(&tty_fd);
    }
    if (rc != 0) {
        qemu_fail(P260_TTY_RAW_STAGE, "tty-raw", rc);
    }
    qemu_log_stage(P260_TTY_RAW_STAGE, "tty-raw");

    int observer_pipe[2];
    if (pipe(observer_pipe) != 0) {
        qemu_fail(P260_BANNER_STAGE, "observer-pipe", -errno);
    }
    pid_t observer = fork();
    if (observer < 0) {
        qemu_fail(P260_BANNER_STAGE, "observer-fork", -errno);
    }
    if (observer == 0) {
        close(observer_pipe[0]);
        int observer_rc = qemu_observe_banner(observer_pipe[1]);
        close(observer_pipe[1]);
        _exit(observer_rc == 0 ? 0 : observer_rc);
    }
    close(observer_pipe[1]);

    rc = p260_write_all(
        tty_fd, p260_banner, sizeof(p260_banner) - 1U, 1);
    if (rc != 0) {
        qemu_fail(P260_BANNER_STAGE, "pre-bind-banner", rc);
    }
    qemu_log_stage(P260_BANNER_STAGE, "pre-bind-banner");

    if (access(k_qemu_udc_root, F_OK) != 0) {
        qemu_fail(P260_ROLE_UDC_STAGE, "dummy-udc", -errno);
    }
    qemu_log_stage(P260_ROLE_UDC_STAGE, "dummy-udc-adapter");

    rc = p260_write_and_verify(
        "/config/usb_gadget/g1/UDC",
        k_qemu_udc_name,
        k_qemu_udc_name);
    if (rc != 0) {
        qemu_fail(P260_UDC_BIND_STAGE, "dummy-udc-bind", rc);
    }
    qemu_log_stage(P260_UDC_BIND_STAGE, "dummy-udc-bind");

    rc = qemu_wait_configured();
    if (rc != 0) {
        qemu_fail(P260_CONFIGURED_STAGE, "dummy-configured", rc);
    }
    qemu_log_stage(P260_CONFIGURED_STAGE, "dummy-configured");

    char observed[sizeof(p260_banner)] = {0};
    size_t used = 0;
    while (used < sizeof(p260_banner) - 1U) {
        ssize_t amount = read(
            observer_pipe[0],
            observed + used,
            sizeof(p260_banner) - 1U - used);
        if (amount > 0) {
            used += (size_t)amount;
            continue;
        }
        if (amount < 0 && errno == EINTR) {
            continue;
        }
        break;
    }
    close(observer_pipe[0]);
    int status = 0;
    if (waitpid(observer, &status, 0) != observer) {
        qemu_fail(P260_CONFIGURED_STAGE, "observer-wait", -errno);
    }
    if (
        !WIFEXITED(status)
        || WEXITSTATUS(status) != 0
        || used != sizeof(p260_banner) - 1U
        || !p260_bytes_equal(
            observed, p260_banner, sizeof(p260_banner) - 1U)
    ) {
        long detail = WIFEXITED(status) ? WEXITSTATUS(status) : EIO;
        qemu_fail(P260_CONFIGURED_STAGE, "banner-observer", -detail);
    }

    close(tty_fd);
    static const char verdict[] =
        "PASS_P260_E3_GENERIC_QEMU_HOST_ONLY";
    dprintf(
        STDOUT_FILENO,
        "P260_QEMU result=PASS verdict=%s banner_bytes=%zu\n",
        verdict,
        used);
    sync();
    quiet_park();
}
