// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ M5B freestanding mount/reboot beacon.
 *
 * Purpose: split the front of M5 after the v0.4 USB-ACM no-transport result.
 * This keeps the proven freestanding/raw-syscall runtime shape, mounts only
 * the virtual filesystems M5 needs at the front, emits a marker, then requests
 * reboot("download"). It does not insert modules or create a USB gadget.
 */

#include <stddef.h>
#include <stdint.h>

#define AT_FDCWD (-100)

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
#define NR_WRITE 64
#define NR_NANOSLEEP 101
#define NR_REBOOT 142

#define LINUX_REBOOT_MAGIC1 0xfee1deadUL
#define LINUX_REBOOT_MAGIC2 0x28121969UL
#define LINUX_REBOOT_CMD_RESTART2 0xa1b2c3d4UL

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

static const char k_marker[] =
    "S22_NATIVE_INIT_MOUNT_REBOOT_M5B version=0.1 pid1=direct "
    "runtime=freestanding raw_syscalls=1 mounts=dev,proc,sys,config "
    "no_modules=1 no_usb_gadget=1 reboot_download=1\n";

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

static size_t cstr_len(const char *s) {
    size_t n = 0;
    while (s[n] != '\0') {
        ++n;
    }
    return n;
}

static long sys_openat(int dirfd, const char *path, int flags, unsigned int mode) {
    return syscall4(NR_OPENAT, dirfd, (long)(uintptr_t)path, flags, mode);
}

static long sys_close(int fd) {
    return syscall2(NR_CLOSE, fd, 0);
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

static long sys_reboot_download(void) {
    return syscall4(
        NR_REBOOT,
        (long)LINUX_REBOOT_MAGIC1,
        (long)LINUX_REBOOT_MAGIC2,
        (long)LINUX_REBOOT_CMD_RESTART2,
        (long)(uintptr_t)"download");
}

static uint64_t make_dev(unsigned int major_num, unsigned int minor_num) {
    return ((uint64_t)(minor_num & 0xffU)) | ((uint64_t)(major_num & 0xfffU) << 8) |
           ((uint64_t)(minor_num & ~0xffU) << 12) | ((uint64_t)(major_num & ~0xfffU) << 32);
}

static void mkdir_one(const char *path, unsigned int mode) {
    (void)sys_mkdirat(path, mode);
}

static void mkdir_p(const char *path, unsigned int mode) {
    char tmp[128];
    size_t len = cstr_len(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return;
    }
    for (size_t i = 0; i <= len; ++i) {
        tmp[i] = path[i];
    }
    for (size_t i = 1; tmp[i] != '\0'; ++i) {
        if (tmp[i] == '/') {
            tmp[i] = '\0';
            mkdir_one(tmp, mode);
            tmp[i] = '/';
        }
    }
    mkdir_one(tmp, mode);
}

static long mount_one(const char *source, const char *target, const char *fstype, unsigned long flags, const char *data) {
    long rc = sys_mount(source, target, fstype, flags, data);
    return rc == -EBUSY ? 0 : rc;
}

static void ensure_chr_node(const char *path, unsigned int mode, unsigned int major_num, unsigned int minor_num) {
    (void)sys_unlinkat(path);
    (void)sys_mknodat(path, S_IFCHR | mode, make_dev(major_num, minor_num));
}

static void emit(const char *msg) {
    long fd = sys_openat(AT_FDCWD, "/dev/kmsg", O_WRONLY | O_CLOEXEC, 0);
    if (fd >= 0) {
        (void)sys_write((int)fd, msg, cstr_len(msg));
        (void)sys_close((int)fd);
    }
}

static void mount_virtual_filesystems(void) {
    mkdir_p("/dev", 0755);
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/config", 0755);

    long dev_rc = mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_rc != 0) {
        dev_rc = mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    (void)dev_rc;

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);

    emit(k_marker);
    emit("S22_NATIVE_INIT_MOUNT_REBOOT_M5B phase=mounts_start\n");
    (void)mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    (void)mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    (void)mount_one("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    emit("S22_NATIVE_INIT_MOUNT_REBOOT_M5B phase=mounts_done reboot_download_next=1\n");
}

static void m5b_main(void) {
    mount_virtual_filesystems();
    (void)sys_sleep_ms(100);
    long rc = sys_reboot_download();
    (void)rc;
    emit("S22_NATIVE_INIT_MOUNT_REBOOT_M5B phase=reboot_returned park=1\n");
}

__attribute__((noreturn)) void _start(void) {
    m5b_main();
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}
