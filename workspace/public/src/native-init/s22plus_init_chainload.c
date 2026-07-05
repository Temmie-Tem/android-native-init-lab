// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ first-stage init proof wrapper.
 *
 * Installed as /init in the boot ramdisk with the stock Android init moved to
 * /init.stock.  The wrapper emits low-risk proof markers, then immediately
 * execs the stock init with the original argv/envp.  It intentionally avoids
 * mounting persistent partitions or changing hardware state.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

static const char k_marker[] =
    "S22_NATIVE_INIT_WRAPPER version=0.1 target=/init.stock action=exec\n";

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

static void write_marker_file(const char *path) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0) {
        return;
    }
    write_all(fd, k_marker, sizeof(k_marker) - 1);
    fsync(fd);
    close(fd);
}

static void ensure_kmsg_node(void) {
    struct stat st;
    if (stat("/dev/kmsg", &st) == 0 && S_ISCHR(st.st_mode)) {
        return;
    }
    (void)mknod("/dev/kmsg", S_IFCHR | 0600, makedev(1, 11));
}

static void write_kmsg(const char *msg) {
    ensure_kmsg_node();
    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return;
    }
    write_all(fd, msg, strlen(msg));
    close(fd);
}

static char *k_fallback_argv[] = {"/init", NULL};

int main(int argc, char **argv, char **envp) {
    (void)argc;

    write_marker_file("/s22_native_init_wrapper_ran");
    write_marker_file("/debug_ramdisk/s22_native_init_wrapper_ran");
    write_kmsg(k_marker);

    if (argv == NULL || argv[0] == NULL) {
        argv = k_fallback_argv;
    }

    execve("/init.stock", argv, envp);

    write_kmsg("S22_NATIVE_INIT_WRAPPER exec_failed target=/init.stock\n");
    for (;;) {
        pause();
    }
}
