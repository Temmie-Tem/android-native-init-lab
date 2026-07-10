// SPDX-License-Identifier: MIT
/* S22+ V3432 direct-PID1 retained-marker keystone. */

#include <stddef.h>
#include <stdint.h>

#include "s22plus_v3432_pid1_keystone.generated.h"

#define AT_FDCWD (-100L)
#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_NONBLOCK 00004000
#define O_CLOEXEC 02000000
#define S_IFCHR 0020000
#define MS_NOSUID 2UL
#define MS_NODEV 4UL
#define MS_NOEXEC 8UL
#define EBUSY 16L
#define EEXIST 17L

#define NR_MKNODAT 33L
#define NR_MKDIRAT 34L
#define NR_MOUNT 40L
#define NR_OPENAT 56L
#define NR_CLOSE 57L
#define NR_WRITE 64L
#define NR_EXIT_GROUP 94L
#define NR_NANOSLEEP 101L
#define NR_GETPID 172L
#define NR_FINIT_MODULE 273L

#define V3432_MODULE_PATH "/observer/sec_log_buf.ko"
#define V3432_AP_KLOG_PATH "/proc/ap_klog"
#define V3432_LAST_KMSG_PATH "/proc/last_kmsg"

enum v3432_stage {
    V3432_STAGE_START = 0,
    V3432_STAGE_PID1 = 1,
    V3432_STAGE_VOLATILE_READY = 2,
    V3432_STAGE_MODULE_LIVE = 3,
    V3432_STAGE_OBSERVER_READY = 4,
    V3432_STAGE_MARKER_WRITTEN = 5,
};

struct v3432_timespec {
    int64_t tv_sec;
    int64_t tv_nsec;
};

void *memcpy(void *destination, const void *source, size_t size) {
    uint8_t *output = (uint8_t *)destination;
    const uint8_t *input = (const uint8_t *)source;
    size_t index;
    for (index = 0; index < size; ++index) {
        output[index] = input[index];
    }
    return destination;
}

static int v3432_bytes_equal(const void *left, const void *right, size_t size) {
    const uint8_t *a = (const uint8_t *)left;
    const uint8_t *b = (const uint8_t *)right;
    size_t index;
    for (index = 0; index < size; ++index) {
        if (a[index] != b[index]) {
            return 0;
        }
    }
    return 1;
}

static inline long v3432_syscall6(
    long number,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5
) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = number;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
        : "memory"
    );
    return x0;
}

static inline long v3432_syscall5(
    long number,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4
) {
    return v3432_syscall6(number, a0, a1, a2, a3, a4, 0);
}

static inline long v3432_syscall4(
    long number,
    long a0,
    long a1,
    long a2,
    long a3
) {
    return v3432_syscall6(number, a0, a1, a2, a3, 0, 0);
}

static inline long v3432_syscall3(long number, long a0, long a1, long a2) {
    return v3432_syscall6(number, a0, a1, a2, 0, 0, 0);
}

static inline long v3432_syscall2(long number, long a0, long a1) {
    return v3432_syscall6(number, a0, a1, 0, 0, 0, 0);
}

static inline long v3432_syscall0(long number) {
    return v3432_syscall6(number, 0, 0, 0, 0, 0, 0);
}

static long v3432_getpid(void) {
    return v3432_syscall0(NR_GETPID);
}

static long v3432_mkdir(const char *path, unsigned int mode) {
    return v3432_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, mode);
}

static uint64_t v3432_make_dev(
    unsigned int major_number,
    unsigned int minor_number
) {
    return ((uint64_t)(minor_number & 0xffU)) |
           ((uint64_t)(major_number & 0xfffU) << 8) |
           ((uint64_t)(minor_number & ~0xffU) << 12) |
           ((uint64_t)(major_number & ~0xfffU) << 32);
}

static long v3432_mknod(
    const char *path,
    unsigned int mode,
    unsigned int major_number,
    unsigned int minor_number
) {
    return v3432_syscall4(
        NR_MKNODAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        S_IFCHR | mode,
        (long)v3432_make_dev(major_number, minor_number)
    );
}

static long v3432_mount(
    const char *source,
    const char *target,
    const char *type,
    unsigned long flags
) {
    return v3432_syscall5(
        NR_MOUNT,
        (long)(uintptr_t)source,
        (long)(uintptr_t)target,
        (long)(uintptr_t)type,
        (long)flags,
        (long)(uintptr_t)""
    );
}

static long v3432_open(const char *path, int flags) {
    return v3432_syscall4(
        NR_OPENAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        flags,
        0
    );
}

static long v3432_close(int fd) {
    return v3432_syscall2(NR_CLOSE, fd, 0);
}

static long v3432_write(int fd, const void *buffer, size_t size) {
    return v3432_syscall3(
        NR_WRITE,
        fd,
        (long)(uintptr_t)buffer,
        (long)size
    );
}

static long v3432_finit_module(int fd) {
    return v3432_syscall3(NR_FINIT_MODULE, fd, (long)(uintptr_t)"", 0);
}

static long v3432_sleep_ms(long milliseconds) {
    struct v3432_timespec request;
    request.tv_sec = milliseconds / 1000L;
    request.tv_nsec = (milliseconds % 1000L) * 1000000L;
    return v3432_syscall2(NR_NANOSLEEP, (long)(uintptr_t)&request, 0);
}

static int v3432_advance(
    enum v3432_stage *stage,
    enum v3432_stage expected,
    int condition
) {
    if (*stage != expected || !condition) {
        return 0;
    }
    *stage = (enum v3432_stage)((unsigned int)expected + 1U);
    return 1;
}

static int v3432_prepare_volatile_runtime(void) {
    long rc;
    rc = v3432_mkdir("/dev", 0755);
    if (rc != 0 && rc != -EEXIST) {
        return 0;
    }
    rc = v3432_mknod("/dev/kmsg", 0600, 1U, 11U);
    if (rc != 0 && rc != -EEXIST) {
        return 0;
    }
    rc = v3432_mkdir("/proc", 0755);
    if (rc != 0 && rc != -EEXIST) {
        return 0;
    }
    rc = v3432_mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC);
    if (rc != 0 && rc != -EBUSY) {
        return 0;
    }
    rc = v3432_mkdir("/sys", 0755);
    if (rc != 0 && rc != -EEXIST) {
        return 0;
    }
    rc = v3432_mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC);
    return rc == 0 || rc == -EBUSY;
}

static int v3432_load_observer(void) {
    long fd = v3432_open(V3432_MODULE_PATH, O_RDONLY | O_CLOEXEC);
    long load_rc;
    long close_rc;
    if (fd < 0) {
        return 0;
    }
    load_rc = v3432_finit_module((int)fd);
    close_rc = v3432_close((int)fd);
    return load_rc == 0 && close_rc == 0;
}

static int v3432_file_openable(const char *path) {
    long fd = v3432_open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return 0;
    }
    return v3432_close((int)fd) == 0;
}

static int v3432_observer_ready(void) {
    return v3432_file_openable(V3432_LAST_KMSG_PATH) &&
           v3432_file_openable(V3432_AP_KLOG_PATH);
}

static size_t v3432_render_marker(char *output, size_t output_size, uint32_t pid) {
    static const char hex[] = "0123456789abcdef";
    size_t index;
    if (output_size < V3432_EXPECTED_FRAME_LEN) {
        return 0;
    }
    memcpy(output, V3432_EXPECTED_FRAME, V3432_EXPECTED_FRAME_LEN);
    for (index = 0; index < 8U; ++index) {
        output[V3432_PID_HEX_OFFSET + 7U - index] = hex[pid & 0xfU];
        pid >>= 4U;
    }
    return V3432_EXPECTED_FRAME_LEN;
}

static int v3432_emit_marker(long pid) {
    char output[V3432_EXPECTED_FRAME_LEN + 1U];
    size_t frame_size = v3432_render_marker(output, sizeof(output), (uint32_t)pid);
    long fd;
    long amount;
    if (frame_size != V3432_EXPECTED_FRAME_LEN ||
        !v3432_bytes_equal(
            output,
            V3432_EXPECTED_FRAME,
            V3432_EXPECTED_FRAME_LEN
        )) {
        return 0;
    }
    output[frame_size] = '\n';
    fd = v3432_open("/dev/kmsg", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        return 0;
    }
    amount = v3432_write((int)fd, output, frame_size + 1U);
    return v3432_close((int)fd) == 0 && amount == (long)(frame_size + 1U);
}

__attribute__((noreturn)) static void v3432_quiet_park(void) {
    for (;;) {
        (void)v3432_sleep_ms(1000L);
        asm volatile("wfe" ::: "memory");
    }
}

#if defined(V3432_SELFTEST_ONLY)
static enum v3432_stage v3432_simulate(
    long pid,
    int volatile_ready,
    int module_live,
    int observer_ready,
    int marker_written
) {
    enum v3432_stage stage = V3432_STAGE_START;
    if (!v3432_advance(&stage, V3432_STAGE_START, pid == 1)) {
        return stage;
    }
    if (!v3432_advance(&stage, V3432_STAGE_PID1, volatile_ready)) {
        return stage;
    }
    if (!v3432_advance(&stage, V3432_STAGE_VOLATILE_READY, module_live)) {
        return stage;
    }
    if (!v3432_advance(&stage, V3432_STAGE_MODULE_LIVE, observer_ready)) {
        return stage;
    }
    (void)v3432_advance(&stage, V3432_STAGE_OBSERVER_READY, marker_written);
    return stage;
}

__attribute__((noreturn)) void _start(void) {
    char pid1[V3432_EXPECTED_FRAME_LEN];
    char pid2[V3432_EXPECTED_FRAME_LEN];
    size_t pid1_size = v3432_render_marker(pid1, sizeof(pid1), 1U);
    size_t pid2_size = v3432_render_marker(pid2, sizeof(pid2), 2U);
    int pass =
        pid1_size == V3432_EXPECTED_FRAME_LEN &&
        pid2_size == V3432_EXPECTED_FRAME_LEN &&
        v3432_bytes_equal(pid1, V3432_EXPECTED_FRAME, pid1_size) &&
        !v3432_bytes_equal(pid1, pid2, pid1_size) &&
        v3432_simulate(1, 1, 1, 1, 1) == V3432_STAGE_MARKER_WRITTEN &&
        v3432_simulate(2, 1, 1, 1, 1) == V3432_STAGE_START &&
        v3432_simulate(1, 0, 1, 1, 1) == V3432_STAGE_PID1 &&
        v3432_simulate(1, 1, 0, 1, 1) == V3432_STAGE_VOLATILE_READY &&
        v3432_simulate(1, 1, 1, 0, 1) == V3432_STAGE_MODULE_LIVE &&
        v3432_simulate(1, 1, 1, 1, 0) == V3432_STAGE_OBSERVER_READY;
    (void)v3432_syscall2(NR_EXIT_GROUP, pass ? 0 : 1, 0);
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}
#else
__attribute__((noreturn)) void _start(void) {
    enum v3432_stage stage = V3432_STAGE_START;
    long pid = v3432_getpid();

    if (!v3432_advance(&stage, V3432_STAGE_START, pid == 1)) {
        v3432_quiet_park();
    }
    if (!v3432_advance(
            &stage,
            V3432_STAGE_PID1,
            v3432_prepare_volatile_runtime()
        )) {
        v3432_quiet_park();
    }
    if (!v3432_advance(
            &stage,
            V3432_STAGE_VOLATILE_READY,
            v3432_load_observer()
        )) {
        v3432_quiet_park();
    }
    if (!v3432_advance(
            &stage,
            V3432_STAGE_MODULE_LIVE,
            v3432_observer_ready()
        )) {
        v3432_quiet_park();
    }
    if (!v3432_advance(
            &stage,
            V3432_STAGE_OBSERVER_READY,
            v3432_emit_marker(pid)
        )) {
        v3432_quiet_park();
    }
    v3432_quiet_park();
}
#endif
