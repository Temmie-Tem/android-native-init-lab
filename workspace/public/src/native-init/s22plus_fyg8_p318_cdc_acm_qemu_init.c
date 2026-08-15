// SPDX-License-Identifier: MIT
/* Minimal PID 1 for the P3.18 dummy_hcd -> real Python observer control. */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static __attribute__((noreturn)) void p318_fail(const char *stage, int detail) {
    dprintf(
        STDOUT_FILENO,
        "P318_QEMU result=FAIL stage=%s detail=%d\n",
        stage,
        detail);
    sync();
    for (;;) {
        pause();
    }
}

static void p318_mkdir(const char *path) {
    if (mkdir(path, 0755) != 0 && errno != EEXIST) {
        p318_fail("mkdir", -errno);
    }
}

static void p318_mount_base(void) {
    p318_mkdir("/proc");
    p318_mkdir("/sys");
    p318_mkdir("/dev");
    p318_mkdir("/config");
    p318_mkdir("/run");
    if (mount("proc", "/proc", "proc", 0, "") != 0 && errno != EBUSY) {
        p318_fail("mount-proc", -errno);
    }
    if (mount("sysfs", "/sys", "sysfs", 0, "") != 0 && errno != EBUSY) {
        p318_fail("mount-sysfs", -errno);
    }
    if (
        mount("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755") != 0
        && errno != EBUSY
    ) {
        p318_fail("mount-devtmpfs", -errno);
    }
}

static void p318_load_module(const char *name) {
    char path[192];
    int length = snprintf(path, sizeof(path), "/modules/%s.ko", name);
    if (length <= 0 || (size_t)length >= sizeof(path)) {
        p318_fail("module-path", -EOVERFLOW);
    }
    int descriptor = open(path, O_RDONLY | O_CLOEXEC);
    if (descriptor < 0) {
        p318_fail(name, -errno);
    }
    long result = syscall(SYS_finit_module, descriptor, "", 0);
    int saved_errno = errno;
    close(descriptor);
    if (result != 0 && saved_errno != EEXIST) {
        p318_fail(name, -saved_errno);
    }
    dprintf(STDOUT_FILENO, "P318_QEMU module=%s status=PASS\n", name);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    p318_mount_base();

    static const char *const modules[] = {
        "usb-common",
        "usbcore",
        "configfs",
        "udc-core",
        "libcomposite",
        "dummy_hcd",
        "u_serial",
        "usb_f_acm",
        "cdc-acm",
    };
    for (size_t index = 0; index < sizeof(modules) / sizeof(modules[0]); ++index) {
        p318_load_module(modules[index]);
    }
    if (mount("configfs", "/config", "configfs", 0, "") != 0) {
        p318_fail("mount-configfs", -errno);
    }

    char *const arguments[] = {
        "/usr/bin/python3.13",
        "-I",
        "-B",
        "/s22plus_fyg8_p318_cdc_acm_qemu_guest.py",
        NULL,
    };
    char *const environment[] = {
        "LC_ALL=C",
        "PATH=/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE=1",
        NULL,
    };
    execve(arguments[0], arguments, environment);
    p318_fail("exec-python", -errno);
}
