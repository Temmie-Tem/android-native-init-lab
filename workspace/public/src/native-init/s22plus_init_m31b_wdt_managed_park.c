// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M31B watchdog-managed park candidate.
 *
 * This candidate only tests whether loading the stock watchdog dependency
 * closure removes the bare-PID1 PMIC/PON reset ceiling. It does not request
 * Download mode, create USB/configfs, start Android/Magisk, or touch persistent
 * partitions.
 */

#include <stdint.h>
#include <stddef.h>

#ifndef M31B_MODULE_LIMIT
#define M31B_MODULE_LIMIT 0
#endif

#define STR_INNER(x) #x
#define STR(x) STR_INNER(x)

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

#define MODULES_LOAD_BUF 1024
#define MODULE_NAME_BUF 96

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct sbuf {
    char data[512];
    size_t len;
};

static const char k_marker[] =
    "S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK version=0.1 pid1=direct "
    "runtime=freestanding raw_syscalls=1 "
    "modules_dep_complete=/s22plus_m31b_wdt_managed.modules module_count=" STR(M31B_MODULE_LIMIT) " "
    "module_source=stock_vendor_boot_ramdisk module_list=watchdog_dependency_closure "
    "observation=watchdog-managed-park no_android_handoff=1 no_configfs=1 no_acm=1 "
    "no_reboot_request=1 no_download_beacon=1\n";

static inline long syscall6(long nr, long a0, long a1, long a2, long a3, long a4, long a5) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = nr;
    asm volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8) : "memory");
    return x0;
}

static inline long syscall5(long nr, long a0, long a1, long a2, long a3, long a4) {
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

static long sys_mknodat(const char *path, unsigned int mode, uint64_t dev) {
    return syscall4(NR_MKNODAT, AT_FDCWD, (long)(uintptr_t)path, mode, (long)dev);
}

static long sys_unlinkat(const char *path) {
    return syscall3(NR_UNLINKAT, AT_FDCWD, (long)(uintptr_t)path, 0);
}

static long sys_mount(const char *source, const char *target, const char *fstype, unsigned long flags, const char *data) {
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

static size_t cstr_len(const char *s) {
    size_t n = 0;
    while (s[n] != '\0') {
        ++n;
    }
    return n;
}

void *memcpy(void *dst, const void *src, size_t n) {
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    for (size_t i = 0; i < n; ++i) {
        d[i] = s[i];
    }
    return dst;
}

static void copy_cstr(char *dst, size_t size, const char *src) {
    if (size == 0) {
        return;
    }
    size_t i = 0;
    while (i + 1 < size && src[i] != '\0') {
        dst[i] = src[i];
        ++i;
    }
    dst[i] = '\0';
}

static void sb_putc(struct sbuf *sb, char ch) {
    if (sb->len + 1 < sizeof(sb->data)) {
        sb->data[sb->len++] = ch;
        sb->data[sb->len] = '\0';
    }
}

static void sb_puts(struct sbuf *sb, const char *s) {
    for (size_t i = 0; s[i] != '\0'; ++i) {
        sb_putc(sb, s[i]);
    }
}

static void sb_put_u64(struct sbuf *sb, uint64_t value) {
    char tmp[32];
    size_t n = 0;
    if (value == 0) {
        sb_putc(sb, '0');
        return;
    }
    while (value > 0 && n < sizeof(tmp)) {
        tmp[n++] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    while (n > 0) {
        sb_putc(sb, tmp[--n]);
    }
}

static void sb_put_i64(struct sbuf *sb, int64_t value) {
    if (value < 0) {
        sb_putc(sb, '-');
        sb_put_u64(sb, (uint64_t)(-value));
        return;
    }
    sb_put_u64(sb, (uint64_t)value);
}

static void emit_buf(const struct sbuf *sb) {
    long fd = sys_openat("/dev/kmsg", O_WRONLY | O_CLOEXEC, 0);
    if (fd >= 0) {
        (void)sys_write((int)fd, sb->data, sb->len);
        (void)sys_close((int)fd);
    }
}

static void emit(const char *s) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, s);
    emit_buf(&sb);
}

static void mkdir_one(const char *path, unsigned int mode) {
    (void)sys_mkdirat(path, mode);
}

static void mkdir_p(const char *path, unsigned int mode) {
    char tmp[256];
    size_t len = cstr_len(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return;
    }
    copy_cstr(tmp, sizeof(tmp), path);
    for (size_t i = 1; tmp[i] != '\0'; ++i) {
        if (tmp[i] == '/') {
            tmp[i] = '\0';
            mkdir_one(tmp, mode);
            tmp[i] = '/';
        }
    }
    mkdir_one(tmp, mode);
}

static uint64_t make_dev(unsigned int major_num, unsigned int minor_num) {
    return ((uint64_t)(minor_num & 0xffU)) | ((uint64_t)(major_num & 0xfffU) << 8) |
           ((uint64_t)(minor_num & ~0xffU) << 12) | ((uint64_t)(major_num & ~0xfffU) << 32);
}

static void ensure_chr_node(const char *path, unsigned int mode, unsigned int major_num, unsigned int minor_num) {
    (void)sys_unlinkat(path);
    (void)sys_mknodat(path, S_IFCHR | mode, make_dev(major_num, minor_num));
}

static long mount_one(const char *source, const char *target, const char *fstype, unsigned long flags, const char *data) {
    long rc = sys_mount(source, target, fstype, flags, data);
    if (rc == -EBUSY) {
        return 0;
    }
    return rc;
}

static void setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);
    mkdir_p("/run", 0755);

    (void)mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    (void)mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long dev_rc = mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_rc != 0) {
        (void)mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    (void)mount_one("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);
}

static int build_module_path(char *out, size_t size, const char *name) {
    const char prefix[] = "/lib/modules/";
    size_t prefix_len = sizeof(prefix) - 1;
    size_t name_len = cstr_len(name);
    if (prefix_len + name_len + 1 > size) {
        return -1;
    }
    for (size_t i = 0; i < prefix_len; ++i) {
        out[i] = prefix[i];
    }
    for (size_t i = 0; i < name_len; ++i) {
        out[prefix_len + i] = name[i];
    }
    out[prefix_len + name_len] = '\0';
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
    long rc = sys_finit_module((int)fd, "", 0);
    (void)sys_close((int)fd);
    return rc;
}

static void emit_module_result(const char *name, long rc) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK phase=module name=");
    sb_puts(&sb, name);
    sb_puts(&sb, " rc=");
    sb_put_i64(&sb, rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static void load_modules_from_list(void) {
    char buf[MODULES_LOAD_BUF];
    long fd = sys_openat("/s22plus_m31b_wdt_managed.modules", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        emit("S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK phase=modules_open_failed\n");
        return;
    }
    long n = sys_read((int)fd, buf, sizeof(buf) - 1);
    (void)sys_close((int)fd);
    if (n <= 0) {
        emit("S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK phase=modules_read_failed\n");
        return;
    }
    buf[n] = '\0';

    char name[MODULE_NAME_BUF];
    size_t name_len = 0;
    unsigned int loaded = 0;
    for (long i = 0; i <= n; ++i) {
        char ch = buf[i];
        if (ch == '\n' || ch == '\0') {
            if (name_len > 0) {
                name[name_len] = '\0';
                long rc = load_one_module(name);
                emit_module_result(name, rc);
                ++loaded;
                name_len = 0;
            }
            if (ch == '\0') {
                break;
            }
            continue;
        }
        if (name_len + 1 < sizeof(name)) {
            name[name_len++] = ch;
        }
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK phase=modules_load_done loaded=");
    sb_put_u64(&sb, loaded);
    sb_puts(&sb, " expected=");
    sb_put_u64(&sb, M31B_MODULE_LIMIT);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

__attribute__((noreturn)) static void park_forever(void) {
    emit("S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK phase=park_enter dwell_target_sec=120\n");
    for (;;) {
        (void)sys_sleep_sec(10);
        asm volatile("wfe" ::: "memory");
    }
}

__attribute__((noreturn)) void _start(void) {
    setup_minimal_fs();
    emit(k_marker);
    load_modules_from_list();
    park_forever();
}
