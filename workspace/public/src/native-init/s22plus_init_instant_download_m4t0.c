// SPDX-License-Identifier: MIT
/*
 * S22+ M4 TEST 0 instant-download direct PID1 probe.
 *
 * The first userspace action is the download reboot syscall.  There is no
 * marker write before the syscall by design: this floor probe uses behavior,
 * not retained logs, to answer whether the kernel reached and executed /init.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

static const char k_marker[] =
    "S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0 version=0.1 pid1=direct "
    "proof=first-action-download-reboot ramdisk_format=legacy-lz4 "
    "no_marker_before_reboot=1 no_usb_modules=1 no_configfs=1 no_android_handoff=1\n";

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

static void ensure_chr_node(const char *path, mode_t mode, unsigned int major_num, unsigned int minor_num) {
    struct stat st;
    if (stat(path, &st) == 0 && S_ISCHR(st.st_mode)) {
        return;
    }
    if (errno == ENOENT) {
        (void)mknod(path, S_IFCHR | mode, makedev(major_num, minor_num));
    }
}

static void setup_late_nodes(void) {
    (void)mkdir("/dev", 0755);
    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/pmsg0", 0222, 507, 0);
}

static void emit(const char *msg) {
    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
    fd = open("/dev/pmsg0", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
}

static void emitf(const char *fmt, ...) {
    char buf[384];
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
    emit(buf);
}

int main(int argc, char **argv, char **envp) {
    (void)argc;
    (void)argv;
    (void)envp;

    errno = 0;
    long rc = syscall(
        SYS_reboot,
        LINUX_REBOOT_MAGIC1,
        LINUX_REBOOT_MAGIC2,
        LINUX_REBOOT_CMD_RESTART2,
        "download");
    int saved_errno = errno;

    setup_late_nodes();
    emit(k_marker);
    emitf("S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0 phase=reboot_return rc=%ld errno=%d\n", rc, saved_errno);

    for (unsigned int tick = 0;; ++tick) {
        emitf("S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0 phase=park reboot_failed=1 tick=%u\n", tick);
        sleep(5);
    }
}
