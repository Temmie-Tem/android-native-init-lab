// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ direct PID1 first-light proof init.
 *
 * This is deliberately not an Android or Magisk chainload wrapper.  It runs as
 * /init, emits bounded proof markers for recovery-side collection, waits long
 * enough for human/host observation, then asks the kernel to reboot to recovery.
 *
 * Safety boundary:
 * - no persistent partition mount;
 * - no block-device write;
 * - no module load;
 * - no GPIO/PMIC/backlight/control-surface mutation;
 * - no attempt to start Android.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

static const char k_marker[] =
    "S22_NATIVE_INIT_DIRECT_P3 version=0.1 pid1=direct "
    "proof=kmsg-last_kmsg auto_reboot=recovery no_android_handoff=1\n";

static void write_all(int fd, const char *buf, size_t len) {
    while (len > 0) {
        ssize_t rc = write(fd, buf, len);
        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        if (rc == 0) {
            return;
        }
        buf += (size_t)rc;
        len -= (size_t)rc;
    }
}

static void mkdir_one(const char *path, mode_t mode) {
    if (mkdir(path, mode) != 0 && errno != EEXIST) {
        return;
    }
    (void)chmod(path, mode);
}

static void mkdir_p(const char *path, mode_t mode) {
    char tmp[256];
    size_t len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return;
    }
    memcpy(tmp, path, len + 1);
    for (char *p = tmp + 1; *p; ++p) {
        if (*p == '/') {
            *p = '\0';
            mkdir_one(tmp, mode);
            *p = '/';
        }
    }
    mkdir_one(tmp, mode);
}

static void ensure_chr_node(const char *path, mode_t mode, unsigned int major_num, unsigned int minor_num) {
    struct stat st;
    if (stat(path, &st) == 0 && S_ISCHR(st.st_mode)) {
        return;
    }
    (void)unlink(path);
    (void)mknod(path, S_IFCHR | mode, makedev(major_num, minor_num));
}

static void write_file(const char *path, const char *msg) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0) {
        return;
    }
    write_all(fd, msg, strlen(msg));
    (void)fsync(fd);
    close(fd);
}

static void setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);
    mkdir_p("/run", 0755);
    mkdir_p("/tmp", 01777);
    mkdir_p("/debug_ramdisk", 0755);

    (void)mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    (void)mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    (void)mount("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    (void)mount("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);
}

static void write_kmsg(const char *msg) {
    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return;
    }
    write_all(fd, msg, strlen(msg));
    close(fd);
}

static void kmsgf(const char *fmt, ...) {
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n <= 0) {
        return;
    }
    if ((size_t)n >= sizeof(buf)) {
        n = (int)sizeof(buf) - 1;
        buf[n] = '\0';
    }
    write_kmsg(buf);
}

static void write_markers(void) {
    write_kmsg(k_marker);
    write_file("/s22_native_init_direct_p3_ran", k_marker);
    write_file("/debug_ramdisk/s22_native_init_direct_p3_ran", k_marker);
    write_file("/run/s22_native_init_direct_p3_ran", k_marker);
}

static void recovery_reboot_or_park(void) {
    write_kmsg("S22_NATIVE_INIT_DIRECT_P3 phase=recovery_reboot_attempt\n");
    sync();
    errno = 0;
    long rc = syscall(
        SYS_reboot,
        LINUX_REBOOT_MAGIC1,
        LINUX_REBOOT_MAGIC2,
        LINUX_REBOOT_CMD_RESTART2,
        "recovery");
    kmsgf("S22_NATIVE_INIT_DIRECT_P3 phase=recovery_reboot_return rc=%ld errno=%d\n", rc, errno);

    for (;;) {
        write_kmsg("S22_NATIVE_INIT_DIRECT_P3 phase=park recovery_reboot_failed=1\n");
        sleep(10);
    }
}

int main(int argc, char **argv, char **envp) {
    (void)argc;
    (void)argv;
    (void)envp;

    setup_minimal_fs();
    write_markers();

    for (int i = 0; i < 15; ++i) {
        kmsgf("S22_NATIVE_INIT_DIRECT_P3 phase=heartbeat sec=%d\n", i);
        sleep(1);
    }

    recovery_reboot_or_park();
}
