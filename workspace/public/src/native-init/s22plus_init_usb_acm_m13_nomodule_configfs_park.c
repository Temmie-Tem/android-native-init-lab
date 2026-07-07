// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M13 no-module configfs/role-force park candidate.
 *
 * M13 is the first shrink below the M12 live boot loop. It keeps the
 * freestanding PID1, minimal filesystem setup, configfs ss_acm.0 gadget
 * attempt, USB role-force attempt, and no-reboot park loop, but removes all
 * runtime module insertion and removes the boot-ramdisk module-list payload.
 */

#include <stdint.h>
#include <stddef.h>

#define AT_FDCWD (-100)

#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_RDWR 00000002
#define O_NOCTTY 00000400
#define O_NONBLOCK 00004000
#define O_DIRECTORY 00200000
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define MS_NOSUID 2UL
#define MS_NODEV 4UL
#define MS_NOEXEC 8UL

#define EINTR 4
#define EAGAIN 11
#define EEXIST 17
#define EBUSY 16

#define NR_MKNODAT 33
#define NR_MKDIRAT 34
#define NR_UNLINKAT 35
#define NR_SYMLINKAT 36
#define NR_MOUNT 40
#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_GETDENTS64 61
#define NR_READ 63
#define NR_WRITE 64
#define NR_NANOSLEEP 101

struct linux_dirent64 {
    uint64_t d_ino;
    int64_t d_off;
    unsigned short d_reclen;
    unsigned char d_type;
    char d_name[];
};

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct sbuf {
    char data[640];
    size_t len;
};

static const char k_marker[] =
    "S22_NATIVE_INIT_USB_ACM_M13 version=0.1 pid1=direct "
    "runtime=freestanding raw_syscalls=1 "
    "module_insertions=absent module_list_payload=absent "
    "configfs_runtime_gadget=ss_acm.0 udc=a600000.dwc3 "
    "gadget=ss_acm.0 tty=/dev/ttyGS0 role_force=device "
    "no_android_handoff=1 no_auto_reboot=1 no_reboot_beacon=1 acm_cmd_status=1\n";

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

static long sys_symlinkat(const char *oldpath, const char *newpath) {
    return syscall3(NR_SYMLINKAT, (long)(uintptr_t)oldpath, AT_FDCWD, (long)(uintptr_t)newpath);
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

static long sys_getdents64(int fd, void *buf, size_t count) {
    return syscall3(NR_GETDENTS64, fd, (long)(uintptr_t)buf, (long)count);
}

static long sys_sleep_ms(long ms) {
    struct timespec64 req = {
        .tv_sec = ms / 1000,
        .tv_nsec = (ms % 1000) * 1000000,
    };
    return syscall2(NR_NANOSLEEP, (long)(uintptr_t)&req, 0);
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

static int cstr_eq(const char *a, const char *b) {
    size_t i = 0;
    while (a[i] != '\0' && b[i] != '\0') {
        if (a[i] != b[i]) {
            return 0;
        }
        ++i;
    }
    return a[i] == b[i];
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

static long write_all(int fd, const char *buf, size_t len) {
    while (len > 0) {
        long rc = sys_write(fd, buf, len);
        if (rc == -EINTR) {
            continue;
        }
        if (rc <= 0) {
            return rc == 0 ? -1 : rc;
        }
        buf += (size_t)rc;
        len -= (size_t)rc;
    }
    return 0;
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

static long read_trim(const char *path, char *buf, size_t size) {
    if (size == 0) {
        return -1;
    }
    long fd = sys_openat(AT_FDCWD, path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        buf[0] = '\0';
        return fd;
    }
    long n = sys_read((int)fd, buf, size - 1);
    (void)sys_close((int)fd);
    if (n < 0) {
        buf[0] = '\0';
        return n;
    }
    buf[n] = '\0';
    while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r' || buf[n - 1] == ' ' || buf[n - 1] == '\t')) {
        buf[n - 1] = '\0';
        --n;
    }
    return 0;
}

static void setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);
    mkdir_p("/run", 0755);
    mkdir_p("/config", 0755);

    long proc_rc = mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long sys_rc = mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long dev_rc = mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_rc != 0) {
        dev_rc = mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    long run_rc = mount_one("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");
    long configfs_rc = mount_one("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=mounts proc_rc=");
    sb_put_i64(&sb, proc_rc);
    sb_puts(&sb, " sys_rc=");
    sb_put_i64(&sb, sys_rc);
    sb_puts(&sb, " dev_rc=");
    sb_put_i64(&sb, dev_rc);
    sb_puts(&sb, " run_rc=");
    sb_put_i64(&sb, run_rc);
    sb_puts(&sb, " configfs_rc=");
    sb_put_i64(&sb, configfs_rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static long write_attr(const char *path, const char *value) {
    long fd = sys_openat(AT_FDCWD, path, O_WRONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=write path=");
        sb_puts(&sb, path);
        sb_puts(&sb, " open_rc=");
        sb_put_i64(&sb, fd);
        sb_putc(&sb, '\n');
        emit_buf(&sb);
        return fd;
    }
    long rc = write_all((int)fd, value, cstr_len(value));
    (void)sys_close((int)fd);
    if (rc != 0) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=write path=");
        sb_puts(&sb, path);
        sb_puts(&sb, " write_rc=");
        sb_put_i64(&sb, rc);
        sb_putc(&sb, '\n');
        emit_buf(&sb);
    }
    return rc;
}

static void force_usb_roles_device(void) {
    long fd = sys_openat(AT_FDCWD, "/sys/class/usb_role", O_RDONLY | O_DIRECTORY | O_CLOEXEC, 0);
    if (fd < 0) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=usb_role open_rc=");
        sb_put_i64(&sb, fd);
        sb_putc(&sb, '\n');
        emit_buf(&sb);
        return;
    }
    char dents[1024];
    unsigned int count = 0;
    for (;;) {
        long nread = sys_getdents64((int)fd, dents, sizeof(dents));
        if (nread <= 0) {
            break;
        }
        long pos = 0;
        while (pos < nread) {
            struct linux_dirent64 *de = (struct linux_dirent64 *)(void *)(dents + pos);
            const char *name = de->d_name;
            if (!cstr_eq(name, ".") && !cstr_eq(name, "..")) {
                char role_path[192] = "/sys/class/usb_role/";
                size_t base = cstr_len(role_path);
                size_t nlen = cstr_len(name);
                if (base + nlen + sizeof("/role") < sizeof(role_path)) {
                    for (size_t i = 0; i < nlen; ++i) {
                        role_path[base + i] = name[i];
                    }
                    role_path[base + nlen] = '\0';
                    const char suffix[] = "/role";
                    for (size_t i = 0; i < sizeof(suffix); ++i) {
                        role_path[base + nlen + i] = suffix[i];
                    }
                    long rc = write_attr(role_path, "device");
                    struct sbuf sb = {.data = {0}, .len = 0};
                    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=usb_role name=");
                    sb_puts(&sb, name);
                    sb_puts(&sb, " rc=");
                    sb_put_i64(&sb, rc);
                    sb_putc(&sb, '\n');
                    emit_buf(&sb);
                    ++count;
                }
            }
            if (de->d_reclen == 0) {
                break;
            }
            pos += de->d_reclen;
        }
    }
    (void)sys_close((int)fd);
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=usb_role_done count=");
    sb_put_u64(&sb, count);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static int choose_real_udc(char *buf, size_t size) {
    long fd = sys_openat(AT_FDCWD, "/sys/class/udc", O_RDONLY | O_DIRECTORY | O_CLOEXEC, 0);
    if (fd < 0) {
        buf[0] = '\0';
        return 0;
    }
    char dents[1024];
    for (;;) {
        long nread = sys_getdents64((int)fd, dents, sizeof(dents));
        if (nread <= 0) {
            break;
        }
        long pos = 0;
        while (pos < nread) {
            struct linux_dirent64 *de = (struct linux_dirent64 *)(void *)(dents + pos);
            const char *name = de->d_name;
            if (cstr_eq(name, "a600000.dwc3")) {
                copy_cstr(buf, size, name);
                (void)sys_close((int)fd);
                return 1;
            }
            if (de->d_reclen == 0) {
                break;
            }
            pos += de->d_reclen;
        }
    }
    (void)sys_close((int)fd);
    buf[0] = '\0';
    return 0;
}

static void emit_gadget(long symlink_rc, int have_udc, const char *udc, long udc_rc) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=acm_gadget symlink_rc=");
    sb_put_i64(&sb, symlink_rc);
    sb_puts(&sb, " have_udc=");
    sb_put_u64(&sb, have_udc ? 1U : 0U);
    sb_puts(&sb, " udc=");
    sb_puts(&sb, udc);
    sb_puts(&sb, " udc_rc=");
    sb_put_i64(&sb, udc_rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static int create_acm_gadget(void) {
    char current_udc[128] = "";
    if (read_trim("/config/usb_gadget/g1/UDC", current_udc, sizeof(current_udc)) == 0 && current_udc[0] != '\0') {
        emit("S22_NATIVE_INIT_USB_ACM_M13 phase=acm_gadget already_bound=1\n");
        return 1;
    }

    mkdir_p("/config/usb_gadget/g1", 0755);
    mkdir_p("/config/usb_gadget/g1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/functions/ss_acm.0", 0755);

    (void)write_attr("/config/usb_gadget/g1/idVendor", "0x04e8");
    (void)write_attr("/config/usb_gadget/g1/idProduct", "0x685d");
    (void)write_attr("/config/usb_gadget/g1/bcdUSB", "0x0320");
    (void)write_attr("/config/usb_gadget/g1/bcdDevice", "0x0006");
    (void)write_attr("/config/usb_gadget/g1/bDeviceClass", "0xef");
    (void)write_attr("/config/usb_gadget/g1/bDeviceSubClass", "0x02");
    (void)write_attr("/config/usb_gadget/g1/bDeviceProtocol", "0x01");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/manufacturer", "Codex");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/product", "S22 Native Init M13 ACM");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/serialnumber", "S22M13ACM0001");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/MaxPower", "500");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/bmAttributes", "0x80");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "acm");

    long symlink_rc = sys_symlinkat("../../functions/ss_acm.0", "/config/usb_gadget/g1/configs/b.1/f1");
    if (symlink_rc == -EEXIST) {
        symlink_rc = 0;
    }

    force_usb_roles_device();
    (void)sys_sleep_ms(200);

    char udc[128] = "";
    int have_udc = choose_real_udc(udc, sizeof(udc));
    long udc_rc = -1;
    if (have_udc) {
        udc_rc = write_attr("/config/usb_gadget/g1/UDC", udc);
    }
    emit_gadget(symlink_rc, have_udc, udc, udc_rc);
    return udc_rc == 0;
}

static int parse_u32_pair(const char *text, unsigned int *major_num, unsigned int *minor_num) {
    unsigned int a = 0;
    unsigned int b = 0;
    size_t i = 0;
    if (text[i] < '0' || text[i] > '9') {
        return 0;
    }
    while (text[i] >= '0' && text[i] <= '9') {
        a = a * 10U + (unsigned int)(text[i] - '0');
        ++i;
    }
    if (text[i] != ':') {
        return 0;
    }
    ++i;
    if (text[i] < '0' || text[i] > '9') {
        return 0;
    }
    while (text[i] >= '0' && text[i] <= '9') {
        b = b * 10U + (unsigned int)(text[i] - '0');
        ++i;
    }
    *major_num = a;
    *minor_num = b;
    return 1;
}

static int ensure_ttygs0(void) {
    char dev_text[64] = "";
    unsigned int major_num = 0;
    unsigned int minor_num = 0;
    if (read_trim("/sys/class/tty/ttyGS0/dev", dev_text, sizeof(dev_text)) == 0 &&
        parse_u32_pair(dev_text, &major_num, &minor_num)) {
        ensure_chr_node("/dev/ttyGS0", 0600, major_num, minor_num);
    }
    long fd = sys_openat(AT_FDCWD, "/dev/ttyGS0", O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC, 0);
    if (fd >= 0) {
        (void)sys_close((int)fd);
        return 1;
    }
    return 0;
}

static void handle_command(const char *cmd, int fd) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=acm_command cmd=");
    sb_puts(&sb, cmd);
    sb_putc(&sb, '\n');
    emit_buf(&sb);

    const char ack[] = "S22_NATIVE_INIT_USB_ACM_M13 ACK status park\n";
    (void)write_all(fd, ack, sizeof(ack) - 1);
}

static void read_serial_commands(int fd, char *cmd_buf, size_t *cmd_len, size_t cmd_cap) {
    char buf[128];
    for (;;) {
        long n = sys_read(fd, buf, sizeof(buf));
        if (n == -EINTR) {
            continue;
        }
        if (n == -EAGAIN || n == 0) {
            return;
        }
        if (n < 0) {
            struct sbuf sb = {.data = {0}, .len = 0};
            sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=acm_read rc=");
            sb_put_i64(&sb, n);
            sb_putc(&sb, '\n');
            emit_buf(&sb);
            return;
        }
        for (long i = 0; i < n; ++i) {
            char ch = buf[i];
            if (ch == '\r' || ch == '\n') {
                if (*cmd_len > 0) {
                    cmd_buf[*cmd_len] = '\0';
                    handle_command(cmd_buf, fd);
                    *cmd_len = 0;
                }
                continue;
            }
            if (*cmd_len + 1 < cmd_cap) {
                cmd_buf[*cmd_len] = ch;
                ++(*cmd_len);
            } else {
                cmd_buf[cmd_cap - 1] = '\0';
                emit("S22_NATIVE_INIT_USB_ACM_M13 phase=acm_command_overflow\n");
                *cmd_len = 0;
            }
        }
    }
}

static void emit_park(unsigned int tick, int bound, int tty_ready, long open_rc) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M13 phase=park tick=");
    sb_put_u64(&sb, tick);
    sb_puts(&sb, " bound=");
    sb_put_u64(&sb, bound ? 1U : 0U);
    sb_puts(&sb, " tty_ready=");
    sb_put_u64(&sb, tty_ready ? 1U : 0U);
    sb_puts(&sb, " tty_open_rc=");
    sb_put_i64(&sb, open_rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static void serial_probe_loop(void) {
    char cmd_buf[128];
    size_t cmd_len = 0;
    for (unsigned int tick = 0;; ++tick) {
        int bound = 0;
        if ((tick % 3U) == 0U) {
            bound = create_acm_gadget();
        }
        int tty_ready = ensure_ttygs0();
        long fd = sys_openat(AT_FDCWD, "/dev/ttyGS0", O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC, 0);
        if (fd >= 0) {
            const char banner[] = "S22_NATIVE_INIT_USB_ACM_M13 READY\n";
            (void)write_all((int)fd, banner, sizeof(banner) - 1);
            read_serial_commands((int)fd, cmd_buf, &cmd_len, sizeof(cmd_buf));
            (void)sys_close((int)fd);
        }
        emit_park(tick, bound, tty_ready, fd >= 0 ? 0 : fd);
        (void)sys_sleep_ms(2000);
    }
}

static void m13_main(void) {
    setup_minimal_fs();
    emit(k_marker);
    force_usb_roles_device();
    (void)create_acm_gadget();
    serial_probe_loop();
}

__attribute__((noreturn)) void _start(void) {
    m13_main();
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}
