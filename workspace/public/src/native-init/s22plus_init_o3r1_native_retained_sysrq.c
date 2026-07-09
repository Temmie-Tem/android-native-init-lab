// SPDX-License-Identifier: MIT
/* S22+ O3R1 native-PID1 retained SysRq positive control. */

#include <stddef.h>
#include <stdint.h>

#define O3R1_MARKER "S22_NATIVE_INIT_O3R1_RETAINED_SYSRQ"
#define O3R1_VERSION "0.1"

#define AT_FDCWD (-100)
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

struct o3r1_sbuf {
    char data[384];
    size_t length;
};

void *memcpy(void *destination, const void *source, size_t size) {
    unsigned char *output = (unsigned char *)destination;
    const unsigned char *input = (const unsigned char *)source;
    size_t index;

    for (index = 0; index < size; ++index) {
        output[index] = input[index];
    }
    return destination;
}

static inline long o3r1_syscall6(
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

static inline long o3r1_syscall5(long number, long a0, long a1, long a2, long a3, long a4) {
    return o3r1_syscall6(number, a0, a1, a2, a3, a4, 0);
}

static inline long o3r1_syscall4(long number, long a0, long a1, long a2, long a3) {
    return o3r1_syscall6(number, a0, a1, a2, a3, 0, 0);
}

static inline long o3r1_syscall3(long number, long a0, long a1, long a2) {
    return o3r1_syscall6(number, a0, a1, a2, 0, 0, 0);
}

static inline long o3r1_syscall2(long number, long a0, long a1) {
    return o3r1_syscall6(number, a0, a1, 0, 0, 0, 0);
}

static long o3r1_mkdir(const char *path, unsigned int mode) {
    return o3r1_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, mode);
}

static uint64_t o3r1_make_dev(unsigned int major_number, unsigned int minor_number) {
    return ((uint64_t)(minor_number & 0xffU)) |
           ((uint64_t)(major_number & 0xfffU) << 8) |
           ((uint64_t)(minor_number & ~0xffU) << 12) |
           ((uint64_t)(major_number & ~0xfffU) << 32);
}

static long o3r1_mknod(
    const char *path,
    unsigned int mode,
    unsigned int major_number,
    unsigned int minor_number
) {
    return o3r1_syscall4(
        NR_MKNODAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        S_IFCHR | mode,
        (long)o3r1_make_dev(major_number, minor_number)
    );
}

static long o3r1_mount(
    const char *source,
    const char *target,
    const char *type,
    unsigned long flags,
    const char *data
) {
    return o3r1_syscall5(
        NR_MOUNT,
        (long)(uintptr_t)source,
        (long)(uintptr_t)target,
        (long)(uintptr_t)type,
        (long)flags,
        (long)(uintptr_t)data
    );
}

static long o3r1_open(const char *path, int flags) {
    return o3r1_syscall4(NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, flags, 0);
}

static long o3r1_close(int fd) {
    return o3r1_syscall2(NR_CLOSE, fd, 0);
}

static long o3r1_write(int fd, const void *data, size_t size) {
    return o3r1_syscall3(NR_WRITE, fd, (long)(uintptr_t)data, (long)size);
}

__attribute__((noreturn)) static void o3r1_exit_group(int status) {
    (void)o3r1_syscall2(NR_EXIT_GROUP, status, 0);
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}

static void o3r1_sb_putc(struct o3r1_sbuf *buffer, char value) {
    if (buffer->length + 1U < sizeof(buffer->data)) {
        buffer->data[buffer->length++] = value;
        buffer->data[buffer->length] = '\0';
    }
}

static void o3r1_sb_puts(struct o3r1_sbuf *buffer, const char *text) {
    size_t index;
    for (index = 0; text[index] != '\0'; ++index) {
        o3r1_sb_putc(buffer, text[index]);
    }
}

static void o3r1_sb_put_u64(struct o3r1_sbuf *buffer, uint64_t value) {
    char digits[32];
    size_t count = 0;
    if (value == 0) {
        o3r1_sb_putc(buffer, '0');
        return;
    }
    while (value != 0 && count < sizeof(digits)) {
        digits[count++] = (char)('0' + value % 10U);
        value /= 10U;
    }
    while (count != 0) {
        o3r1_sb_putc(buffer, digits[--count]);
    }
}

static void o3r1_sb_put_i64(struct o3r1_sbuf *buffer, int64_t value) {
    if (value < 0) {
        o3r1_sb_putc(buffer, '-');
        o3r1_sb_put_u64(buffer, (uint64_t)(-(value + 1)) + 1U);
    } else {
        o3r1_sb_put_u64(buffer, (uint64_t)value);
    }
}

static long o3r1_write_all(int fd, const char *text, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        long amount = o3r1_write(fd, text + offset, size - offset);
        if (amount <= 0) {
            return amount;
        }
        offset += (size_t)amount;
    }
    return 0;
}

static long o3r1_emit(const char *phase, long rc, const char *action) {
    struct o3r1_sbuf output = {{0}, 0};
    long fd;
    long write_rc;
    o3r1_sb_puts(&output, O3R1_MARKER " version=" O3R1_VERSION " phase=");
    o3r1_sb_puts(&output, phase);
    o3r1_sb_puts(&output, " rc=");
    o3r1_sb_put_i64(&output, rc);
    o3r1_sb_puts(&output, " action=");
    o3r1_sb_puts(&output, action);
    o3r1_sb_putc(&output, '\n');
    fd = o3r1_open("/dev/kmsg", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        return fd;
    }
    write_rc = o3r1_write_all((int)fd, output.data, output.length);
    (void)o3r1_close((int)fd);
    return write_rc;
}

__attribute__((noreturn)) static void o3r1_fail_to_init_panic(
    const char *phase,
    long rc,
    int exit_code
) {
    (void)o3r1_emit(phase, rc, "pid1-exit-group-panic");
    o3r1_exit_group(exit_code);
}

__attribute__((noreturn)) void _start(void) {
    static const char sysrq_crash = 'c';
    long dev_dir_rc = o3r1_mkdir("/dev", 0755);
    long kmsg_node_rc;
    long proc_dir_rc;
    long proc_mount_rc;
    long marker_rc;
    long sysrq_fd;
    long sysrq_rc;

    if (dev_dir_rc != 0 && dev_dir_rc != -EEXIST) {
        o3r1_exit_group(101);
    }
    kmsg_node_rc = o3r1_mknod("/dev/kmsg", 0600, 1, 11);
    if (kmsg_node_rc != 0 && kmsg_node_rc != -EEXIST) {
        o3r1_exit_group(102);
    }
    marker_rc = o3r1_emit("entry-pre-proc", kmsg_node_rc, "mount-proc-next");
    if (marker_rc != 0) {
        o3r1_exit_group(103);
    }

    proc_dir_rc = o3r1_mkdir("/proc", 0755);
    if (proc_dir_rc != 0 && proc_dir_rc != -EEXIST) {
        o3r1_fail_to_init_panic("proc-mkdir-fail", proc_dir_rc, 104);
    }
    proc_mount_rc = o3r1_mount(
        "proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, ""
    );
    if (proc_mount_rc == -EBUSY) {
        proc_mount_rc = 0;
    }
    (void)o3r1_emit("proc-mount", proc_mount_rc, "open-sysrq-trigger-next");
    if (proc_mount_rc != 0) {
        o3r1_fail_to_init_panic("proc-mount-fail", proc_mount_rc, 105);
    }

    sysrq_fd = o3r1_open("/proc/sysrq-trigger", O_WRONLY | O_CLOEXEC);
    (void)o3r1_emit("sysrq-open", sysrq_fd, "sysrq-c-next");
    if (sysrq_fd < 0) {
        o3r1_fail_to_init_panic("sysrq-open-fail", sysrq_fd, 106);
    }
    marker_rc = o3r1_emit("before-sysrq-c", 0, "intentional-kernel-panic");
    if (marker_rc != 0) {
        (void)o3r1_close((int)sysrq_fd);
        o3r1_exit_group(107);
    }
    sysrq_rc = o3r1_write_all((int)sysrq_fd, &sysrq_crash, 1U);
    (void)o3r1_close((int)sysrq_fd);
    o3r1_fail_to_init_panic("sysrq-returned", sysrq_rc, 108);
}
