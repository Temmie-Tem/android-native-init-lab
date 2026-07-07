// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M8 timed-download module-bisect probe.
 *
 * M8 is not a USB-ACM milestone candidate. It loads a bounded M7-only module
 * delta batch from the boot ramdisk, then immediately requests Samsung
 * download mode. Seeing download mode proves PID1 survived the batch without
 * depending on configfs, UDC binding, ttyGS0, or host serial I/O.
 */

#include <stdint.h>
#include <stddef.h>

#define AT_FDCWD (-100)

#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define MS_NOSUID 2UL
#define MS_NODEV 4UL
#define MS_NOEXEC 8UL

#define EINTR 4
#define EEXIST 17
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
#define NR_REBOOT 142
#define NR_FINIT_MODULE 273

#define MODULE_BATCH_BUF 4096
#define MODULE_NAME_BUF 128
#define EXPECTED_MODULE_COUNT 18U

#define LINUX_REBOOT_MAGIC1 0xfee1deadUL
#define LINUX_REBOOT_MAGIC2 0x28121969UL
#define LINUX_REBOOT_CMD_RESTART2 0xa1b2c3d4UL

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct sbuf {
    char data[768];
    size_t len;
};

struct batch_result {
    unsigned int count;
    unsigned int ok_count;
    unsigned int fail_count;
};

static const char k_marker[] =
    "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD version=0.1 pid1=direct "
    "runtime=freestanding raw_syscalls=1 "
    "module_batch=/s22plus_m8_delta_batch.modules "
    "module_source=stock_vendor_boot_ramdisk module_list=boot_ramdisk_m7_delta_batch "
    "module_injection=list_only batch_strategy=m7_only_first_half "
    "expected_module_count=18 no_usb_acm=1 no_configfs=1 "
    "auto_reboot_download_after_batch=1 no_android_handoff=1\n";

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

static long sys_openat(int dirfd, const char *path, int flags, unsigned int mode) {
    return syscall4(NR_OPENAT, dirfd, (long)(uintptr_t)path, flags, mode);
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

static long sys_sleep_ms(long ms) {
    struct timespec64 req = {
        .tv_sec = ms / 1000,
        .tv_nsec = (ms % 1000) * 1000000,
    };
    return syscall2(NR_NANOSLEEP, (long)(uintptr_t)&req, 0);
}

static long sys_finit_module(int fd, const char *params, int flags) {
    return syscall3(NR_FINIT_MODULE, fd, (long)(uintptr_t)params, flags);
}

static long sys_reboot_download(void) {
    return syscall4(
        NR_REBOOT,
        (long)LINUX_REBOOT_MAGIC1,
        (long)LINUX_REBOOT_MAGIC2,
        (long)LINUX_REBOOT_CMD_RESTART2,
        (long)(uintptr_t)"download");
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

void *memset(void *dst, int value, size_t n) {
    unsigned char *d = (unsigned char *)dst;
    for (size_t i = 0; i < n; ++i) {
        d[i] = (unsigned char)value;
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
    long fd = sys_openat(AT_FDCWD, "/dev/kmsg", O_WRONLY | O_CLOEXEC, 0);
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

    long proc_rc = mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long sys_rc = mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long dev_rc = mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_rc != 0) {
        dev_rc = mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    long run_rc = mount_one("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=mounts proc_rc=");
    sb_put_i64(&sb, proc_rc);
    sb_puts(&sb, " sys_rc=");
    sb_put_i64(&sb, sys_rc);
    sb_puts(&sb, " dev_rc=");
    sb_put_i64(&sb, dev_rc);
    sb_puts(&sb, " run_rc=");
    sb_put_i64(&sb, run_rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static int build_module_path(char *out, size_t size, const char *name) {
    const char prefix[] = "/lib/modules/";
    size_t prefix_len = sizeof(prefix) - 1;
    size_t name_len = cstr_len(name);
    if (prefix_len + name_len + 1 > size) {
        return 0;
    }
    for (size_t i = 0; i < prefix_len; ++i) {
        out[i] = prefix[i];
    }
    for (size_t i = 0; i < name_len; ++i) {
        out[prefix_len + i] = name[i];
    }
    out[prefix_len + name_len] = '\0';
    return 1;
}

static int is_line_space(char ch) {
    return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n';
}

static int module_ok(long finit_rc) {
    return finit_rc == 0 || finit_rc == -EEXIST;
}

static int load_one_module(unsigned int index, const char *name) {
    char path[256];
    long open_rc = -1;
    long finit_rc = -1;
    if (build_module_path(path, sizeof(path), name)) {
        long fd = sys_openat(AT_FDCWD, path, O_RDONLY | O_CLOEXEC, 0);
        open_rc = fd;
        if (fd >= 0) {
            finit_rc = sys_finit_module((int)fd, "", 0);
            (void)sys_close((int)fd);
        }
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=module index=");
    sb_put_u64(&sb, index);
    sb_puts(&sb, " name=");
    sb_puts(&sb, name);
    sb_puts(&sb, " open_rc=");
    sb_put_i64(&sb, open_rc);
    sb_puts(&sb, " finit_rc=");
    sb_put_i64(&sb, finit_rc);
    sb_puts(&sb, " ok=");
    sb_put_u64(&sb, module_ok(finit_rc) ? 1U : 0U);
    sb_putc(&sb, '\n');
    emit_buf(&sb);

    return module_ok(finit_rc);
}

static struct batch_result load_module_batch(void) {
    struct batch_result result = {0, 0, 0};
    static char text[MODULE_BATCH_BUF];
    long fd = sys_openat(AT_FDCWD, "/s22plus_m8_delta_batch.modules", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=module_batch open_rc=");
        sb_put_i64(&sb, fd);
        sb_putc(&sb, '\n');
        emit_buf(&sb);
        return result;
    }
    long n = sys_read((int)fd, text, MODULE_BATCH_BUF - 1);
    (void)sys_close((int)fd);
    if (n < 0) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=module_batch read_rc=");
        sb_put_i64(&sb, n);
        sb_putc(&sb, '\n');
        emit_buf(&sb);
        return result;
    }
    text[n] = '\0';

    size_t pos = 0;
    while (pos < (size_t)n) {
        while (pos < (size_t)n && is_line_space(text[pos])) {
            ++pos;
        }
        if (pos >= (size_t)n) {
            break;
        }
        char name[MODULE_NAME_BUF];
        size_t out = 0;
        while (pos < (size_t)n && !is_line_space(text[pos]) && out + 1 < sizeof(name)) {
            char ch = text[pos++];
            if (ch == '/') {
                out = 0;
                continue;
            }
            name[out++] = ch;
        }
        name[out] = '\0';
        while (pos < (size_t)n && text[pos] != '\n') {
            ++pos;
        }
        if (name[0] == '\0' || name[0] == '#') {
            continue;
        }
        ++result.count;
        if (load_one_module(result.count, name)) {
            ++result.ok_count;
        } else {
            ++result.fail_count;
        }
        if ((result.count % 4U) == 0U) {
            (void)sys_sleep_ms(10);
        }
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=module_batch_done count=");
    sb_put_u64(&sb, result.count);
    sb_puts(&sb, " ok_count=");
    sb_put_u64(&sb, result.ok_count);
    sb_puts(&sb, " fail_count=");
    sb_put_u64(&sb, result.fail_count);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
    return result;
}

static void request_download_or_park(struct batch_result result) {
    if (result.count != EXPECTED_MODULE_COUNT) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=count_mismatch expected=");
        sb_put_u64(&sb, EXPECTED_MODULE_COUNT);
        sb_puts(&sb, " actual=");
        sb_put_u64(&sb, result.count);
        sb_puts(&sb, " auto_download=0\n");
        emit_buf(&sb);
        return;
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=timed_download requested=1 count=");
    sb_put_u64(&sb, result.count);
    sb_puts(&sb, " ok_count=");
    sb_put_u64(&sb, result.ok_count);
    sb_puts(&sb, " fail_count=");
    sb_put_u64(&sb, result.fail_count);
    sb_puts(&sb, " sleep_ms=250\n");
    emit_buf(&sb);

    (void)sys_sleep_ms(250);
    long rc = sys_reboot_download();

    struct sbuf rb = {.data = {0}, .len = 0};
    sb_puts(&rb, "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD phase=reboot_download rc=");
    sb_put_i64(&rb, rc);
    sb_puts(&rb, " returned=1\n");
    emit_buf(&rb);
}

static void m8_main(void) {
    setup_minimal_fs();
    emit(k_marker);
    struct batch_result result = load_module_batch();
    request_download_or_park(result);
}

__attribute__((noreturn)) void _start(void) {
    m8_main();
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}
