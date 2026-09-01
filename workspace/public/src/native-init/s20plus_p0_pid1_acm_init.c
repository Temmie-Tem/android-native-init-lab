// SPDX-License-Identifier: MIT
/* S20+ G986N P0 direct-PID1 ACM first-light witness. */

#include <stddef.h>
#include <stdint.h>

#define AT_FDCWD (-100L)

#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_RDWR 00000002
#define O_NONBLOCK 00004000
#define O_CLOEXEC 02000000
#define O_NOCTTY 00000400

#define S_IFCHR 0020000

#define MS_NOSUID 2UL
#define MS_NOEXEC 8UL

#define EBUSY 16L
#define EEXIST 17L

#define NR_MKNODAT 33L
#define NR_MKDIRAT 34L
#define NR_SYMLINKAT 36L
#define NR_MOUNT 40L
#define NR_OPENAT 56L
#define NR_CLOSE 57L
#define NR_READ 63L
#define NR_WRITE 64L
#define NR_EXIT_GROUP 94L
#define NR_NANOSLEEP 101L
#define NR_GETPID 172L

#define P0_UDC "a600000.dwc3"
#define P0_UDC_CLASS "/sys/class/udc/a600000.dwc3"
#define P0_GADGET "/config/usb_gadget/s20plus_p0"
#define P0_FUNCTION P0_GADGET "/functions/acm.usb0"
#define P0_FUNCTION_PORT P0_FUNCTION "/port_num"
#define P0_CONFIG P0_GADGET "/configs/b.1"
#define P0_UDC_FILE P0_GADGET "/UDC"

#define P0_BANNER "S20PLUS_P0_PID1_ACM_V1;pid=00000001;stage=ACM_READY\n"
#define P0_BANNER_SIZE (sizeof(P0_BANNER) - 1U)

struct p0_timespec {
    int64_t tv_sec;
    int64_t tv_nsec;
};

enum p0_stage {
    P0_STAGE_START = 0,
    P0_STAGE_PID1 = 1,
    P0_STAGE_VOLATILE = 2,
    P0_STAGE_CONFIGFS = 3,
    P0_STAGE_ACM = 4,
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

__attribute__((always_inline)) static inline long p0_syscall6(
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

__attribute__((always_inline)) static inline long p0_syscall5(
    long number,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4
) {
    return p0_syscall6(number, a0, a1, a2, a3, a4, 0);
}

__attribute__((always_inline)) static inline long p0_syscall4(
    long number,
    long a0,
    long a1,
    long a2,
    long a3
) {
    return p0_syscall6(number, a0, a1, a2, a3, 0, 0);
}

__attribute__((always_inline)) static inline long p0_syscall3(long number, long a0, long a1, long a2) {
    return p0_syscall6(number, a0, a1, a2, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p0_syscall2(long number, long a0, long a1) {
    return p0_syscall6(number, a0, a1, 0, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p0_syscall1(long number, long a0) {
    return p0_syscall6(number, a0, 0, 0, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p0_syscall0(long number) {
    return p0_syscall6(number, 0, 0, 0, 0, 0, 0);
}

static long p0_getpid(void) {
    return p0_syscall0(NR_GETPID);
}

static long p0_mkdir(const char *path, unsigned int mode) {
    return p0_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, mode);
}

static long p0_open(const char *path, int flags) {
    return p0_syscall4(
        NR_OPENAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        flags,
        0
    );
}

static long p0_close(int descriptor) {
    return p0_syscall1(NR_CLOSE, descriptor);
}

static long p0_read(int descriptor, void *buffer, size_t size) {
    return p0_syscall3(
        NR_READ,
        descriptor,
        (long)(uintptr_t)buffer,
        (long)size
    );
}

static long p0_write(int descriptor, const void *buffer, size_t size) {
    return p0_syscall3(
        NR_WRITE,
        descriptor,
        (long)(uintptr_t)buffer,
        (long)size
    );
}

static long p0_mount(
    const char *source,
    const char *target,
    const char *type,
    unsigned long flags,
    const char *data
) {
    return p0_syscall5(
        NR_MOUNT,
        (long)(uintptr_t)source,
        (long)(uintptr_t)target,
        (long)(uintptr_t)type,
        (long)flags,
        (long)(uintptr_t)data
    );
}

static uint64_t p0_make_dev(
    unsigned int major_number,
    unsigned int minor_number
) {
    return ((uint64_t)(minor_number & 0xffU)) |
           ((uint64_t)(major_number & 0xfffU) << 8) |
           ((uint64_t)(minor_number & ~0xffU) << 12) |
           ((uint64_t)(major_number & ~0xfffU) << 32);
}

static long p0_mknod_char(
    const char *path,
    unsigned int mode,
    unsigned int major_number,
    unsigned int minor_number
) {
    return p0_syscall4(
        NR_MKNODAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        S_IFCHR | mode,
        (long)p0_make_dev(major_number, minor_number)
    );
}

static long p0_symlink(const char *target, const char *path) {
    return p0_syscall3(
        NR_SYMLINKAT,
        (long)(uintptr_t)target,
        AT_FDCWD,
        (long)(uintptr_t)path
    );
}

static void p0_sleep_ms(long milliseconds) {
    struct p0_timespec request;
    request.tv_sec = milliseconds / 1000L;
    request.tv_nsec = (milliseconds % 1000L) * 1000000L;
    (void)p0_syscall2(
        NR_NANOSLEEP,
        (long)(uintptr_t)&request,
        0
    );
}

static size_t p0_strlen(const char *value) {
    size_t size = 0;
    while (value[size] != '\0') {
        ++size;
    }
    return size;
}

static int p0_write_all(int descriptor, const char *value, size_t size) {
    size_t written = 0;
    while (written < size) {
        long rc = p0_write(descriptor, value + written, size - written);
        if (rc <= 0) {
            return 0;
        }
        written += (size_t)rc;
    }
    return 1;
}

static int p0_write_file(const char *path, const char *value) {
    long descriptor = p0_open(path, O_WRONLY | O_CLOEXEC);
    int ok;
    long close_rc;
    if (descriptor < 0) {
        return 0;
    }
    ok = p0_write_all((int)descriptor, value, p0_strlen(value));
    close_rc = p0_close((int)descriptor);
    return ok && close_rc == 0;
}

static int p0_ensure_dir(const char *path, unsigned int mode) {
    long rc = p0_mkdir(path, mode);
    return rc == 0 || rc == -EEXIST;
}

static int p0_wait_readable(const char *path, int attempts) {
    int attempt;
    for (attempt = 0; attempt < attempts; ++attempt) {
        long descriptor = p0_open(path, O_RDONLY | O_CLOEXEC);
        if (descriptor >= 0) {
            if (p0_close((int)descriptor) == 0) {
                return 1;
            }
            return 0;
        }
        p0_sleep_ms(50);
    }
    return 0;
}

static int p0_read_small(const char *path, char *buffer, size_t capacity) {
    long descriptor;
    long amount;
    long extra;
    long close_rc;
    if (capacity < 2U) {
        return -1;
    }
    descriptor = p0_open(path, O_RDONLY | O_CLOEXEC);
    if (descriptor < 0) {
        return -1;
    }
    amount = p0_read((int)descriptor, buffer, capacity - 1U);
    if (amount <= 0 || (size_t)amount >= capacity) {
        (void)p0_close((int)descriptor);
        return -1;
    }
    extra = p0_read((int)descriptor, buffer + amount, 1U);
    close_rc = p0_close((int)descriptor);
    if (extra != 0 || close_rc != 0) {
        return -1;
    }
    buffer[amount] = '\0';
    return (int)amount;
}

static int p0_parse_unsigned(
    const char *buffer,
    size_t size,
    size_t *cursor,
    unsigned int *value
) {
    unsigned int parsed = 0;
    size_t start = *cursor;
    while (*cursor < size && buffer[*cursor] >= '0' && buffer[*cursor] <= '9') {
        unsigned int digit = (unsigned int)(buffer[*cursor] - '0');
        if (parsed > (1048575U - digit) / 10U) {
            return 0;
        }
        parsed = parsed * 10U + digit;
        ++*cursor;
    }
    if (*cursor == start) {
        return 0;
    }
    *value = parsed;
    return 1;
}

static int p0_parse_dev(
    const char *buffer,
    size_t size,
    unsigned int *major_number,
    unsigned int *minor_number
) {
    size_t cursor = 0;
    if (!p0_parse_unsigned(buffer, size, &cursor, major_number)) {
        return 0;
    }
    if (cursor >= size || buffer[cursor++] != ':') {
        return 0;
    }
    if (!p0_parse_unsigned(buffer, size, &cursor, minor_number)) {
        return 0;
    }
    if (cursor < size && buffer[cursor] == '\n') {
        ++cursor;
    }
    return cursor == size && *major_number <= 4095U && *minor_number <= 1048575U;
}

static int p0_port(const char *buffer, size_t size, unsigned int *port) {
    if (size == 2U && buffer[1] == '\n') {
        size = 1U;
    }
    if (size != 1U || buffer[0] < '0' || buffer[0] > '3') {
        return 0;
    }
    *port = (unsigned int)(buffer[0] - '0');
    return 1;
}

static int p0_tty_paths(
    unsigned int port,
    char *sysfs_path,
    size_t sysfs_capacity,
    char *device_path,
    size_t device_capacity
) {
    static const char sysfs_template[] = "/sys/class/tty/ttyGS0/dev";
    static const char device_template[] = "/dev/ttyGS0";
    size_t index;
    if (port > 3U || sysfs_capacity < sizeof(sysfs_template) ||
        device_capacity < sizeof(device_template)) {
        return 0;
    }
    for (index = 0; index < sizeof(sysfs_template); ++index) {
        sysfs_path[index] = sysfs_template[index];
    }
    for (index = 0; index < sizeof(device_template); ++index) {
        device_path[index] = device_template[index];
    }
    sysfs_path[20] = (char)('0' + port);
    device_path[10] = (char)('0' + port);
    return 1;
}

static int p0_volatile_runtime(void) {
    long rc;
    if (!p0_ensure_dir("/proc", 0755) ||
        !p0_ensure_dir("/sys", 0755) ||
        !p0_ensure_dir("/dev", 0755) ||
        !p0_ensure_dir("/config", 0755)) {
        return 0;
    }
    rc = p0_mount("proc", "/proc", "proc", MS_NOSUID | MS_NOEXEC, "");
    if (rc != 0 && rc != -EBUSY) {
        return 0;
    }
    rc = p0_mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NOEXEC, "");
    if (rc != 0 && rc != -EBUSY) {
        return 0;
    }
    rc = p0_mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_NOEXEC, "mode=0755");
    if (rc != 0 && rc != -EBUSY) {
        return 0;
    }
    (void)p0_mknod_char("/dev/kmsg", 0600, 1U, 11U);
    return 1;
}

static int p0_mount_configfs(void) {
    long rc = p0_mount("configfs", "/config", "configfs", MS_NOSUID | MS_NOEXEC, "");
    return rc == 0 || rc == -EBUSY;
}

static int p0_create_gadget(unsigned int *port) {
    char value[32];
    int amount;
    if (!p0_wait_readable(P0_UDC_CLASS, 200)) {
        return 0;
    }
    if (p0_mkdir(P0_GADGET, 0755) != 0 ||
        !p0_write_file(P0_GADGET "/idVendor", "0x04e8") ||
        !p0_write_file(P0_GADGET "/idProduct", "0x6861") ||
        !p0_write_file(P0_GADGET "/bcdUSB", "0x0200") ||
        !p0_write_file(P0_GADGET "/bcdDevice", "0x0100") ||
        !p0_ensure_dir(P0_GADGET "/strings", 0755) ||
        !p0_ensure_dir(P0_GADGET "/strings/0x409", 0755) ||
        !p0_write_file(P0_GADGET "/strings/0x409/manufacturer", "Samsung") ||
        !p0_write_file(P0_GADGET "/strings/0x409/product", "S20Plus-P0-PID1") ||
        !p0_ensure_dir(P0_GADGET "/functions", 0755) ||
        p0_mkdir(P0_FUNCTION, 0755) != 0 ||
        !p0_ensure_dir(P0_GADGET "/configs", 0755) ||
        p0_mkdir(P0_CONFIG, 0755) != 0 ||
        !p0_ensure_dir(P0_CONFIG "/strings", 0755) ||
        p0_mkdir(P0_CONFIG "/strings/0x409", 0755) != 0 ||
        !p0_write_file(P0_CONFIG "/strings/0x409/configuration", "P0 PID1 ACM") ||
        !p0_write_file(P0_CONFIG "/MaxPower", "250") ||
        p0_symlink("../../functions/acm.usb0", P0_CONFIG "/f1") != 0) {
        return 0;
    }
    amount = p0_read_small(P0_FUNCTION_PORT, value, sizeof(value));
    if (amount <= 0 || !p0_port(value, (size_t)amount, port)) {
        return 0;
    }
    return p0_write_file(P0_UDC_FILE, P0_UDC);
}

static int p0_open_acm(unsigned int port) {
    char sysfs_path[32];
    char device_path[16];
    char value[32];
    unsigned int major_number;
    unsigned int minor_number;
    int amount;
    int attempt;
    if (!p0_tty_paths(
            port,
            sysfs_path,
            sizeof(sysfs_path),
            device_path,
            sizeof(device_path))) {
        return -1;
    }
    for (attempt = 0; attempt < 200; ++attempt) {
        amount = p0_read_small(sysfs_path, value, sizeof(value));
        if (amount > 0 && p0_parse_dev(
                value,
                (size_t)amount,
                &major_number,
                &minor_number)) {
            long rc = p0_mknod_char(
                device_path,
                0600,
                major_number,
                minor_number
            );
            if (rc == 0 || rc == -EEXIST) {
                long descriptor = p0_open(
                    device_path,
                    O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC
                );
                if (descriptor >= 0) {
                    return (int)descriptor;
                }
            }
        }
        p0_sleep_ms(50);
    }
    return -1;
}

__attribute__((unused)) static enum p0_stage p0_simulate(
    long pid,
    int volatile_ok,
    int configfs_ok,
    int acm_ok
) {
    enum p0_stage stage = P0_STAGE_START;
    if (pid != 1) {
        return stage;
    }
    stage = P0_STAGE_PID1;
    if (!volatile_ok) {
        return stage;
    }
    stage = P0_STAGE_VOLATILE;
    if (!configfs_ok) {
        return stage;
    }
    stage = P0_STAGE_CONFIGFS;
    if (!acm_ok) {
        return stage;
    }
    return P0_STAGE_ACM;
}

__attribute__((noreturn)) static void p0_park(void) {
    for (;;) {
        p0_sleep_ms(60000);
    }
}

#ifdef S20PLUS_P0_SELFTEST_ONLY

__attribute__((noreturn)) void _start(void) {
    unsigned int major_number = 0;
    unsigned int minor_number = 0;
    unsigned int port = 9;
    char sysfs_path[32];
    char device_path[16];
    int ok = 1;
    ok = ok && p0_parse_dev("240:7\n", 6U, &major_number, &minor_number);
    ok = ok && major_number == 240U && minor_number == 7U;
    ok = ok && !p0_parse_dev("240:x\n", 6U, &major_number, &minor_number);
    ok = ok && p0_port("3\n", 2U, &port) && port == 3U;
    ok = ok && !p0_port("4\n", 2U, &port);
    ok = ok && p0_tty_paths(
        3U,
        sysfs_path,
        sizeof(sysfs_path),
        device_path,
        sizeof(device_path)
    );
    ok = ok && sysfs_path[20] == '3' && device_path[10] == '3';
    ok = ok && p0_simulate(2, 1, 1, 1) == P0_STAGE_START;
    ok = ok && p0_simulate(1, 0, 1, 1) == P0_STAGE_PID1;
    ok = ok && p0_simulate(1, 1, 0, 1) == P0_STAGE_VOLATILE;
    ok = ok && p0_simulate(1, 1, 1, 0) == P0_STAGE_CONFIGFS;
    ok = ok && p0_simulate(1, 1, 1, 1) == P0_STAGE_ACM;
    (void)p0_syscall1(NR_EXIT_GROUP, ok ? 0 : 1);
    for (;;) {
    }
}

#else

__attribute__((noreturn)) void _start(void) {
    long pid = p0_getpid();
    unsigned int port = 0;
    int descriptor;
    if (pid != 1) {
        p0_park();
    }
    if (!p0_volatile_runtime()) {
        p0_park();
    }
    if (!p0_mount_configfs()) {
        p0_park();
    }
    if (!p0_create_gadget(&port)) {
        p0_park();
    }
    descriptor = p0_open_acm(port);
    if (descriptor < 0) {
        p0_park();
    }
    for (;;) {
        (void)p0_write_all(descriptor, P0_BANNER, P0_BANNER_SIZE);
        p0_sleep_ms(250);
    }
}

#endif
