// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ FYG8 R4W1-C watchdog-managed direct-PID1 carrier.
 *
 * Load only the M31B-proven watchdog closure, prove the exact runtime module
 * set through /proc/modules, and park. This process never starts Android,
 * configures USB, writes a block device, or asks the kernel to reboot.
 */

#include <stddef.h>
#include <stdint.h>

#define AT_FDCWD (-100)

#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define MS_NOSUID 2UL
#define MS_NODEV 4UL
#define MS_NOEXEC 8UL

#define EBUSY 16

#define NR_MKNODAT 33
#define NR_MKDIRAT 34
#define NR_UNLINKAT 35
#define NR_MOUNT 40
#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_READ 63
#define NR_WRITE 64
#define NR_NANOSLEEP 101
#define NR_FINIT_MODULE 273

#define MODULE_COUNT 5U
#define PROC_MODULES_CAPACITY 32768U

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct sbuf {
    char data[512];
    size_t len;
};

struct module_spec {
    const char *file_name;
    const char *runtime_name;
};

static const struct module_spec k_modules[MODULE_COUNT] = {
    {"smem.ko", "smem"},
    {"minidump.ko", "minidump"},
    {"qcom-scm.ko", "qcom_scm"},
    {"qcom_wdt_core.ko", "qcom_wdt_core"},
    {"gh_virt_wdt.ko", "gh_virt_wdt"},
};

static const char k_marker[] =
    "S22_NATIVE_INIT_R4W1C_WDT_CARRIER version=0.1 pid1=direct "
    "runtime=freestanding raw_syscalls=1 module_count=5 "
    "module_source=stock_vendor_boot_ramdisk "
    "module_closure=m31b-derived exact_finit_rc=0 proc_modules_exact=1 "
    "watchdog_ownership=not_directly_proven "
    "no_android_handoff=1 no_configfs=1 no_usb_setup=1 "
    "no_persistent_mount=1 no_block_write=1 no_reboot_request=1\n";

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

static inline long syscall5(
    long nr, long a0, long a1, long a2, long a3, long a4) {
    return syscall6(nr, a0, a1, a2, a3, a4, 0);
}

static inline long syscall4(long nr, long a0, long a1, long a2, long a3) {
    return syscall6(nr, a0, a1, a2, a3, 0, 0);
}

static inline long syscall3(long nr, long a0, long a1, long a2) {
    return syscall6(nr, a0, a1, a2, 0, 0, 0);
}

static inline long syscall2(long nr, long a0, long a1) {
    return syscall6(nr, a0, a1, 0, 0, 0, 0);
}

static long sys_openat(const char *path, int flags, unsigned int mode) {
    return syscall4(NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, flags, mode);
}

static long sys_close(int fd) {
    return syscall2(NR_CLOSE, fd, 0);
}

static long sys_read(int fd, void *buf, size_t count) {
    return syscall3(NR_READ, fd, (long)(uintptr_t)buf, (long)count);
}

static long sys_write(int fd, const void *buf, size_t count) {
    return syscall3(NR_WRITE, fd, (long)(uintptr_t)buf, (long)count);
}

static long sys_mkdirat(const char *path, unsigned int mode) {
    return syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, mode);
}

static long sys_mknodat(
    const char *path, unsigned int mode, uint64_t dev) {
    return syscall4(
        NR_MKNODAT, AT_FDCWD, (long)(uintptr_t)path, mode, (long)dev);
}

static long sys_unlinkat(const char *path) {
    return syscall3(NR_UNLINKAT, AT_FDCWD, (long)(uintptr_t)path, 0);
}

static long sys_mount(
    const char *source,
    const char *target,
    const char *fstype,
    unsigned long flags,
    const char *data) {
    return syscall5(
        NR_MOUNT,
        (long)(uintptr_t)source,
        (long)(uintptr_t)target,
        (long)(uintptr_t)fstype,
        (long)flags,
        (long)(uintptr_t)data);
}

static long sys_sleep_sec(long sec) {
    struct timespec64 req = {
        .tv_sec = sec,
        .tv_nsec = 0,
    };
    return syscall2(NR_NANOSLEEP, (long)(uintptr_t)&req, 0);
}

static long sys_finit_module(int fd, const char *params, int flags) {
    return syscall3(NR_FINIT_MODULE, fd, (long)(uintptr_t)params, flags);
}

static size_t cstr_len(const char *value) {
    size_t length = 0;
    while (value[length] != '\0') {
        ++length;
    }
    return length;
}

void *memcpy(void *destination, const void *source, size_t count) {
    unsigned char *output = (unsigned char *)destination;
    const unsigned char *input = (const unsigned char *)source;
    for (size_t index = 0; index < count; ++index) {
        output[index] = input[index];
    }
    return destination;
}

static void copy_cstr(char *destination, size_t size, const char *source) {
    if (size == 0) {
        return;
    }
    size_t index = 0;
    while (index + 1 < size && source[index] != '\0') {
        destination[index] = source[index];
        ++index;
    }
    destination[index] = '\0';
}

static int token_equals(
    const char *token, size_t token_length, const char *expected) {
    size_t expected_length = cstr_len(expected);
    if (token_length != expected_length) {
        return 0;
    }
    for (size_t index = 0; index < token_length; ++index) {
        if (token[index] != expected[index]) {
            return 0;
        }
    }
    return 1;
}

static void sb_putc(struct sbuf *buffer, char value) {
    if (buffer->len + 1 < sizeof(buffer->data)) {
        buffer->data[buffer->len++] = value;
        buffer->data[buffer->len] = '\0';
    }
}

static void sb_puts(struct sbuf *buffer, const char *value) {
    for (size_t index = 0; value[index] != '\0'; ++index) {
        sb_putc(buffer, value[index]);
    }
}

static void sb_put_u64(struct sbuf *buffer, uint64_t value) {
    char digits[32];
    size_t count = 0;
    if (value == 0) {
        sb_putc(buffer, '0');
        return;
    }
    while (value > 0 && count < sizeof(digits)) {
        digits[count++] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    while (count > 0) {
        sb_putc(buffer, digits[--count]);
    }
}

static void sb_put_i64(struct sbuf *buffer, int64_t value) {
    if (value < 0) {
        sb_putc(buffer, '-');
        sb_put_u64(buffer, (uint64_t)(-(value + 1)) + 1U);
        return;
    }
    sb_put_u64(buffer, (uint64_t)value);
}

static int emit_buf(const struct sbuf *buffer) {
    long fd = sys_openat("/dev/kmsg", O_WRONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return -1;
    }
    long written = sys_write((int)fd, buffer->data, buffer->len);
    long closed = sys_close((int)fd);
    return written == (long)buffer->len && closed == 0 ? 0 : -1;
}

static int emit(const char *value) {
    struct sbuf buffer = {.data = {0}, .len = 0};
    sb_puts(&buffer, value);
    return emit_buf(&buffer);
}

static void mkdir_one(const char *path, unsigned int mode) {
    (void)sys_mkdirat(path, mode);
}

static void mkdir_p(const char *path, unsigned int mode) {
    char temporary[256];
    size_t length = cstr_len(path);
    if (length == 0 || length >= sizeof(temporary)) {
        return;
    }
    copy_cstr(temporary, sizeof(temporary), path);
    for (size_t index = 1; temporary[index] != '\0'; ++index) {
        if (temporary[index] == '/') {
            temporary[index] = '\0';
            mkdir_one(temporary, mode);
            temporary[index] = '/';
        }
    }
    mkdir_one(temporary, mode);
}

static uint64_t make_dev(unsigned int major_num, unsigned int minor_num) {
    return ((uint64_t)(minor_num & 0xffU)) |
           ((uint64_t)(major_num & 0xfffU) << 8) |
           ((uint64_t)(minor_num & ~0xffU) << 12) |
           ((uint64_t)(major_num & ~0xfffU) << 32);
}

static int ensure_kmsg(void) {
    (void)sys_unlinkat("/dev/kmsg");
    if (sys_mknodat("/dev/kmsg", S_IFCHR | 0600, make_dev(1, 11)) != 0) {
        return -1;
    }
    long fd = sys_openat("/dev/kmsg", O_WRONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return -1;
    }
    return sys_close((int)fd) == 0 ? 0 : -1;
}

static long mount_one(
    const char *source,
    const char *target,
    const char *fstype,
    unsigned long flags,
    const char *data) {
    long result = sys_mount(source, target, fstype, flags, data);
    return result == -EBUSY ? 0 : result;
}

static int setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);

    long proc_result =
        mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long sys_result =
        mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long dev_result =
        mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_result != 0) {
        dev_result =
            mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    long kmsg_result = dev_result == 0 ? ensure_kmsg() : -1;
    if (proc_result != 0 || sys_result != 0 || dev_result != 0 ||
        kmsg_result != 0) {
        struct sbuf buffer = {.data = {0}, .len = 0};
        sb_puts(&buffer, "S22_NATIVE_INIT_R4W1C_WDT_CARRIER phase=fs_failed proc_rc=");
        sb_put_i64(&buffer, proc_result);
        sb_puts(&buffer, " sys_rc=");
        sb_put_i64(&buffer, sys_result);
        sb_puts(&buffer, " dev_rc=");
        sb_put_i64(&buffer, dev_result);
        sb_puts(&buffer, " kmsg_rc=");
        sb_put_i64(&buffer, kmsg_result);
        sb_putc(&buffer, '\n');
        (void)emit_buf(&buffer);
        return -1;
    }
    return 0;
}

static int build_module_path(char *output, size_t size, const char *name) {
    const char prefix[] = "/lib/modules/";
    size_t prefix_length = sizeof(prefix) - 1;
    size_t name_length = cstr_len(name);
    if (prefix_length + name_length + 1 > size) {
        return -1;
    }
    for (size_t index = 0; index < prefix_length; ++index) {
        output[index] = prefix[index];
    }
    for (size_t index = 0; index < name_length; ++index) {
        output[prefix_length + index] = name[index];
    }
    output[prefix_length + name_length] = '\0';
    return 0;
}

static long load_one_module(const char *name) {
    char path[160];
    if (build_module_path(path, sizeof(path), name) != 0) {
        return -9999;
    }
    long fd = sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long result = sys_finit_module((int)fd, "", 0);
    long closed = sys_close((int)fd);
    return result != 0 ? result : closed;
}

static int emit_module_result(size_t index, long result) {
    struct sbuf buffer = {.data = {0}, .len = 0};
    sb_puts(&buffer, "S22_NATIVE_INIT_R4W1C_WDT_CARRIER phase=module_load index=");
    sb_put_u64(&buffer, index);
    sb_puts(&buffer, " file=");
    sb_puts(&buffer, k_modules[index].file_name);
    sb_puts(&buffer, " runtime=");
    sb_puts(&buffer, k_modules[index].runtime_name);
    sb_puts(&buffer, " rc=");
    sb_put_i64(&buffer, result);
    sb_putc(&buffer, '\n');
    return emit_buf(&buffer);
}

static int load_exact_modules(void) {
    for (size_t index = 0; index < MODULE_COUNT; ++index) {
        long result = load_one_module(k_modules[index].file_name);
        if (emit_module_result(index, result) != 0 || result != 0) {
            return -1;
        }
    }
    return emit(
        "S22_NATIVE_INIT_R4W1C_WDT_CARRIER "
        "phase=module_load_complete count=5\n");
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
            return closed == 0 ? (long)used : -9997;
        }
        used += (size_t)result;
    }
    char overflow_probe;
    long overflow = sys_read((int)fd, &overflow_probe, 1);
    long closed = sys_close((int)fd);
    return overflow == 0 && closed == 0 ? (long)used : -9998;
}

static int runtime_module_index(const char *token, size_t token_length) {
    for (size_t index = 0; index < MODULE_COUNT; ++index) {
        if (token_equals(token, token_length, k_modules[index].runtime_name)) {
            return (int)index;
        }
    }
    return -1;
}

static int verify_exact_proc_modules(void) {
    char contents[PROC_MODULES_CAPACITY];
    long size = read_proc_modules(contents, sizeof(contents));
    if (size <= 0) {
        return -1;
    }

    unsigned int seen[MODULE_COUNT] = {0};
    size_t line_count = 0;
    size_t cursor = 0;
    while (cursor < (size_t)size) {
        size_t line_start = cursor;
        while (cursor < (size_t)size && contents[cursor] != '\n') {
            if (contents[cursor] == '\0') {
                return -1;
            }
            ++cursor;
        }
        size_t line_end = cursor;
        if (cursor < (size_t)size && contents[cursor] == '\n') {
            ++cursor;
        }
        if (line_end == line_start) {
            continue;
        }
        size_t token_end = line_start;
        while (token_end < line_end && contents[token_end] != ' ' &&
               contents[token_end] != '\t') {
            ++token_end;
        }
        if (token_end == line_start || token_end == line_end) {
            return -1;
        }
        int index = runtime_module_index(
            contents + line_start, token_end - line_start);
        if (index < 0 || seen[index] != 0U) {
            return -1;
        }
        seen[index] = 1U;
        ++line_count;
    }
    if (line_count != MODULE_COUNT) {
        return -1;
    }
    for (size_t index = 0; index < MODULE_COUNT; ++index) {
        if (seen[index] != 1U) {
            return -1;
        }
    }
    return emit(
        "S22_NATIVE_INIT_R4W1C_WDT_CARRIER "
        "phase=proc_modules_verified count=5 exact=1\n");
}

__attribute__((noreturn)) static void park(const char *phase) {
    emit(phase);
    for (;;) {
        (void)sys_sleep_sec(10);
        asm volatile("wfe" ::: "memory");
    }
}

__attribute__((noreturn)) void _start(void) {
    if (setup_minimal_fs() != 0) {
        park("S22_NATIVE_INIT_R4W1C_WDT_CARRIER phase=fail_closed reason=fs\n");
    }
    if (emit(k_marker) != 0) {
        park(
            "S22_NATIVE_INIT_R4W1C_WDT_CARRIER "
            "phase=fail_closed reason=initial_log\n");
    }
    if (load_exact_modules() != 0) {
        park("S22_NATIVE_INIT_R4W1C_WDT_CARRIER phase=fail_closed reason=module_load\n");
    }
    if (verify_exact_proc_modules() != 0) {
        park("S22_NATIVE_INIT_R4W1C_WDT_CARRIER phase=fail_closed reason=proc_modules\n");
    }
    park(
        "S22_NATIVE_INIT_R4W1C_WDT_CARRIER phase=park_enter "
        "module_closure_visible=1 watchdog_ownership=not_directly_proven "
        "functional_proof=bounded_live_survival observation_target_sec=120\n");
}
