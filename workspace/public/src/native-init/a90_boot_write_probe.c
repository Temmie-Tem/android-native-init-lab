/*
 * a90_boot_write_probe.c — §0.2 write-probe rung E-open (design §11.2).
 *
 * NO WRITE PRIMITIVE. This file contains no write()/pwrite()/dd/O_TRUNC/O_CREAT/BLKDISCARD. It opens
 * the boot block O_WRONLY and immediately closes it — proving only whether RKP/the kernel permits a
 * writable open of the boot partition from normal-boot PID1, with zero bytes written. It resolves the
 * boot partition from sysfs PARTNAME=boot (single match only; ambiguous is refused), materializes the
 * /dev block node (device node in /dev tmpfs, not a partition write), confirms the fd identity
 * (rdev/PARTNAME/size), and unlinks the node. Token-gated. Output lines are "A90BWOPEN key=value".
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include <linux/fs.h>

#include "a90_boot_write_probe.h"
#include "a90_console.h"
#include "a90_util.h"

/* Exact operator approval token for the zero-write E-open rung. */
#define BWOPEN_TOKEN "BOOT-WRITE-OPEN-PROBE-E-OPEN"
#define BWOPEN_PARTNAME "boot"
#define BWOPEN_BOOT_SIZE_BYTES (64ULL * 1024ULL * 1024ULL)

/* Extract "<key>=..." (key includes trailing '=') from a sysfs uevent blob into out. */
static void bwopen_uevent_key(const char *uevent, const char *key, char *out, size_t out_size) {
    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    size_t klen = strlen(key);
    const char *p = uevent;
    while (p && *p) {
        if (strncmp(p, key, klen) == 0) {
            p += klen;
            size_t i = 0;
            while (p[i] && p[i] != '\n' && p[i] != '\r' && i + 1 < out_size) {
                out[i] = p[i];
                i++;
            }
            out[i] = '\0';
            return;
        }
        const char *nl = strchr(p, '\n');
        if (!nl) {
            break;
        }
        p = nl + 1;
    }
}

/* Scan /sys/class/block for partitions with PARTNAME=boot. Fills the FIRST match; returns the match
 * count (0 none, 1 unique, >1 ambiguous). Read-only sysfs traversal. */
static int bwopen_resolve_boot(char *name_out, size_t name_sz, unsigned *maj_out, unsigned *min_out) {
    DIR *d = opendir("/sys/class/block");
    if (!d) {
        return -1;
    }
    int matches = 0;
    struct dirent *e;
    char path[320];
    char buf[4096];
    while ((e = readdir(d)) != NULL) {
        if (e->d_name[0] == '.') {
            continue;
        }
        snprintf(path, sizeof(path), "/sys/class/block/%s/uevent", e->d_name);
        if (read_text_file(path, buf, sizeof(buf)) < 0) {
            continue;
        }
        char partname[64];
        char devtype[32];
        bwopen_uevent_key(buf, "PARTNAME=", partname, sizeof(partname));
        bwopen_uevent_key(buf, "DEVTYPE=", devtype, sizeof(devtype));
        if (strcmp(partname, BWOPEN_PARTNAME) != 0) {
            continue;
        }
        if (devtype[0] && strcmp(devtype, "partition") != 0) {
            continue;
        }
        if (matches == 0) {
            char maj_s[16];
            char min_s[16];
            bwopen_uevent_key(buf, "MAJOR=", maj_s, sizeof(maj_s));
            bwopen_uevent_key(buf, "MINOR=", min_s, sizeof(min_s));
            snprintf(name_out, name_sz, "%s", e->d_name);
            *maj_out = (unsigned)strtoul(maj_s, NULL, 10);
            *min_out = (unsigned)strtoul(min_s, NULL, 10);
        }
        matches++;
    }
    closedir(d);
    return matches;
}

/* Confirm the opened fd is really the boot partition: block device, rdev == sysfs-resolved
 * major:minor, sysfs PARTNAME=boot, size == 64 MiB. Returns 1 on pass, 0 on refuse; prints facts. */
static int bwopen_confirm_identity(int fd, unsigned exp_maj, unsigned exp_min) {
    struct stat st;
    if (fstat(fd, &st) != 0) {
        a90_console_printf("A90BWOPEN fstat=fail errno=%d\r\n", errno);
        return 0;
    }
    int is_block = S_ISBLK(st.st_mode) ? 1 : 0;
    unsigned maj = (unsigned)major(st.st_rdev);
    unsigned min = (unsigned)minor(st.st_rdev);
    a90_console_printf("A90BWOPEN is_block=%d\r\n", is_block);
    a90_console_printf("A90BWOPEN rdev=%u:%u\r\n", maj, min);

    int ok = is_block && maj == exp_maj && min == exp_min;
    if (maj != exp_maj || min != exp_min) {
        a90_console_printf("A90BWOPEN rdev_mismatch=1 expected=%u:%u\r\n", exp_maj, exp_min);
    }

    uint64_t size_bytes = 0;
    if (ioctl(fd, BLKGETSIZE64, &size_bytes) == 0) {
        a90_console_printf("A90BWOPEN size_bytes=%llu\r\n", (unsigned long long)size_bytes);
        if (size_bytes != BWOPEN_BOOT_SIZE_BYTES) {
            ok = 0;
        }
    } else {
        a90_console_printf("A90BWOPEN size_bytes=unknown errno=%d\r\n", errno);
        ok = 0;
    }

    char sysbase[128];
    char path[192];
    char buf[4096];
    snprintf(sysbase, sizeof(sysbase), "/sys/dev/block/%u:%u", maj, min);
    snprintf(path, sizeof(path), "%s/uevent", sysbase);
    if (read_text_file(path, buf, sizeof(buf)) >= 0) {
        char partname[64];
        bwopen_uevent_key(buf, "PARTNAME=", partname, sizeof(partname));
        a90_console_printf("A90BWOPEN partname=%s\r\n", partname[0] ? partname : "unknown");
        if (strcmp(partname, BWOPEN_PARTNAME) != 0) {
            ok = 0;
        }
    } else {
        a90_console_printf("A90BWOPEN partname=unreadable\r\n");
        ok = 0;
    }
    return ok;
}

int a90_boot_write_open_probe_cmd(char **argv, int argc) {
    if (argc != 2 || strcmp(argv[1], BWOPEN_TOKEN) != 0) {
        a90_console_printf("usage: boot-write-open-probe %s\r\n", BWOPEN_TOKEN);
        a90_console_printf("A90BWOPEN refused=missing-or-wrong-token\r\n");
        return -EPERM;
    }

    a90_console_printf("A90BWOPEN begin\r\n");
    a90_console_printf("A90BWOPEN rung=E-open no_write_primitive=1\r\n");

    char name[256];
    unsigned maj = 0, min = 0;
    int n = bwopen_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("A90BWOPEN resolve=%s\r\n", (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("A90BWOPEN end rc=%d\r\n", -ENODEV);
        return -ENODEV;
    }

    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("A90BWOPEN target=%s\r\n", node);
    a90_console_printf("A90BWOPEN resolve=sysfs-partname\r\n");

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("A90BWOPEN mknod=fail errno=%d (%s)\r\n", e, strerror(e));
        a90_console_printf("A90BWOPEN end rc=%d\r\n", -e);
        return -e;
    }
    a90_console_printf("A90BWOPEN materialized=%d\r\n", created);

    /* THE probe: open the boot block O_WRONLY. No write() follows. O_NONBLOCK is harmless on a block
     * device. Deliberately NO O_TRUNC / O_CREAT — nothing that could alter partition contents. */
    int rc = 0;
    int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NONBLOCK);
    if (wfd < 0) {
        int e = errno;
        a90_console_printf("A90BWOPEN open_wronly=fail errno=%d (%s)\r\n", e, strerror(e));
        rc = -e;
    } else {
        a90_console_printf("A90BWOPEN open_wronly=ok\r\n");
        int confirmed = bwopen_confirm_identity(wfd, maj, min);
        a90_console_printf("A90BWOPEN identity_confirmed=%d\r\n", confirmed);
        a90_console_printf("A90BWOPEN no_write_performed=1\r\n");
        close(wfd);
    }

    if (created) {
        unlink(node);
        a90_console_printf("A90BWOPEN cleaned=1\r\n");
    }
    a90_console_printf("A90BWOPEN end rc=%d\r\n", rc);
    return rc;
}
