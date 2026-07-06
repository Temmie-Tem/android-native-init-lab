// SPDX-License-Identifier: MIT
/*
 * S22+ M4A fast-dwell direct PID1 probe.
 *
 * This is a watchdog-hypothesis test.  M3.2's long dark window may have let the
 * Qualcomm/Samsung watchdog reset the SoC before the candidate's planned
 * download reboot.  M4A writes the same earliest kmsg/pmsg marker style, waits
 * only two seconds, then immediately requests download mode.
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
    "S22_NATIVE_INIT_FAST_DWELL_M4A version=0.1 pid1=direct "
    "proof=watchdog-hypothesis-fast-self-download ramdisk_format=legacy-lz4 "
    "fallback_pmsg_major=507 no_usb_modules=1 no_configfs=1 "
    "download_reboot_after_sec=2 watchdog_open_if_present=1 no_android_handoff=1\n";

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

static void setup_early_nodes(void) {
    (void)mkdir("/dev", 0755);
    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/pmsg0", 0222, 507, 0);
}

static void write_kmsg(const char *msg) {
    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
}

static void write_pmsg(const char *msg) {
    int fd = open("/dev/pmsg0", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
}

static void emit(const char *msg) {
    write_kmsg(msg);
    write_pmsg(msg);
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

static void pet_watchdog_if_present(void) {
    int fd = open("/dev/watchdog", O_WRONLY | O_CLOEXEC);
    int saved_errno = errno;
    if (fd < 0) {
        emitf("S22_NATIVE_INIT_FAST_DWELL_M4A phase=watchdog path=/dev/watchdog open_rc=-1 errno=%d\n", saved_errno);
        fd = open("/dev/watchdog0", O_WRONLY | O_CLOEXEC);
        saved_errno = errno;
        if (fd < 0) {
            emitf("S22_NATIVE_INIT_FAST_DWELL_M4A phase=watchdog path=/dev/watchdog0 open_rc=-1 errno=%d\n", saved_errno);
            return;
        }
    }
    const char keepalive = 'K';
    ssize_t wr = write(fd, &keepalive, 1);
    saved_errno = errno;
    emitf("S22_NATIVE_INIT_FAST_DWELL_M4A phase=watchdog write_rc=%ld errno=%d\n", (long)wr, saved_errno);
    close(fd);
}

static void download_reboot_or_park(void) {
    emit("S22_NATIVE_INIT_FAST_DWELL_M4A phase=download_reboot_attempt target=download\n");
    sync();
    errno = 0;
    long rc = syscall(
        SYS_reboot,
        LINUX_REBOOT_MAGIC1,
        LINUX_REBOOT_MAGIC2,
        LINUX_REBOOT_CMD_RESTART2,
        "download");
    emitf("S22_NATIVE_INIT_FAST_DWELL_M4A phase=download_reboot_return rc=%ld errno=%d\n", rc, errno);

    for (unsigned int tick = 0;; ++tick) {
        emitf("S22_NATIVE_INIT_FAST_DWELL_M4A phase=park download_reboot_failed=1 tick=%u\n", tick);
        sleep(5);
    }
}

int main(int argc, char **argv, char **envp) {
    (void)argc;
    (void)argv;
    (void)envp;

    setup_early_nodes();
    emit(k_marker);
    pet_watchdog_if_present();

    for (unsigned int tick = 0; tick < 2; ++tick) {
        emitf("S22_NATIVE_INIT_FAST_DWELL_M4A phase=heartbeat tick=%u\n", tick);
        sleep(1);
    }

    download_reboot_or_park();
}
