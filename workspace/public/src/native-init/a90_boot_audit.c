/*
 * a90_boot_audit.c — read-only boot-target auditor (§7.1).
 *
 * NO PARTITION WRITE PATH. Everything here is O_RDONLY on the block device / read-only ioctls /
 * sysfs reads. The only filesystem mutation is materializing a /dev block *node* (mknod) for the
 * boot partition when native-init has not created one, and unlinking that node again afterwards —
 * this creates a device node in /dev (tmpfs), it never writes partition bytes. It exists to:
 *   (1) answer whether native-init (normal boot, PID1, under RKP) can open+read the boot partition,
 *   (2) report the fd-derived identity the host-side boot-target guard needs to CONFIRM its pin
 *       (rdev major:minor, canonical path, size, logical/physical sector, PARTNAME, diskseq).
 *
 * Resolution (matches how TWRP's ueventd finds boot): native-init has no /dev/block/by-name/boot
 * symlink and no boot devnode, but sysfs exposes every partition's uevent PARTNAME. With no explicit
 * target we scan /sys/class/block/<X>/uevent for the SINGLE partition with PARTNAME=boot, take its
 * MAJOR:MINOR, materialize /dev/block/<X> via mknod, audit it O_RDONLY, and unlink it. A duplicate
 * PARTNAME=boot (>1 match) is refused fail-closed (ambiguous). Identity is taken from the OPENED fd
 * (fstat st_rdev, BLKGETSIZE64) and cross-checked against the sysfs-resolved rdev. Output lines are
 * "A90BOOTAUDIT key=value\r\n". Only an authoritative resolution (by-name or single sysfs
 * PARTNAME=boot) with a matching rdev may report authoritative=1; the host wrapper proposes a write
 * pin only then.
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

#include "a90_boot_audit.h"
#include "a90_console.h"
#include "a90_util.h"

#define BOOT_AUDIT_DEFAULT_TARGET "/dev/block/by-name/boot"
#define BOOT_AUDIT_PARTNAME "boot"

/* Extract "<key>=..." (key includes the trailing '=') from a sysfs uevent blob into out. */
static void parse_uevent_key(const char *uevent, const char *key, char *out, size_t out_size) {
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

/*
 * Scan /sys/class/block for partitions with PARTNAME=boot. Fills name_out/maj_out/min_out with the
 * FIRST match and returns the total match count: 0 = none, 1 = unique (authoritative-eligible),
 * >1 = ambiguous/duplicate label (caller must refuse). Read-only sysfs traversal.
 */
static int resolve_boot_from_sysfs(char *name_out, size_t name_sz,
                                   unsigned *maj_out, unsigned *min_out) {
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
        parse_uevent_key(buf, "PARTNAME=", partname, sizeof(partname));
        parse_uevent_key(buf, "DEVTYPE=", devtype, sizeof(devtype));
        if (strcmp(partname, BOOT_AUDIT_PARTNAME) != 0) {
            continue;
        }
        if (devtype[0] && strcmp(devtype, "partition") != 0) {
            continue;
        }
        if (matches == 0) {
            char maj_s[16];
            char min_s[16];
            parse_uevent_key(buf, "MAJOR=", maj_s, sizeof(maj_s));
            parse_uevent_key(buf, "MINOR=", min_s, sizeof(min_s));
            snprintf(name_out, name_sz, "%s", e->d_name);
            *maj_out = (unsigned)strtoul(maj_s, NULL, 10);
            *min_out = (unsigned)strtoul(min_s, NULL, 10);
        }
        matches++;
    }
    closedir(d);
    return matches;
}

/*
 * Open target O_RDONLY and print its fd-derived identity. *authoritative starts at the caller's
 * proposed value and is DOWNGRADED to 0 on any failure or, when have_expected, on an rdev mismatch
 * against the sysfs-resolved major:minor (defends against a pre-existing wrong node). Returns 0 on a
 * successful open+report, or -errno.
 */
static int audit_report(const char *target, int *authoritative,
                        int have_expected, unsigned exp_maj, unsigned exp_min) {
    char canonical[PATH_MAX];
    if (realpath(target, canonical) != NULL && canonical[0] == '/') {
        a90_console_printf("A90BOOTAUDIT canonical=%s\r\n", canonical);
    } else {
        a90_console_printf("A90BOOTAUDIT canonical=unresolved errno=%d\r\n", errno);
    }

    /* O_NONBLOCK avoids blocking forever if an explicit target arg is a FIFO/socket with no writer;
     * block devices ignore it. */
    int fd = open(target, O_RDONLY | O_CLOEXEC | O_NONBLOCK);
    if (fd < 0) {
        int e = errno;
        a90_console_printf("A90BOOTAUDIT open=fail errno=%d (%s)\r\n", e, strerror(e));
        *authoritative = 0;
        a90_console_printf("A90BOOTAUDIT authoritative=0\r\n");
        return -e;
    }
    a90_console_printf("A90BOOTAUDIT open=ok\r\n");

    struct stat st;
    if (fstat(fd, &st) != 0) {
        a90_console_printf("A90BOOTAUDIT fstat=fail errno=%d\r\n", errno);
        *authoritative = 0;
        a90_console_printf("A90BOOTAUDIT authoritative=0\r\n");
        close(fd);
        return -EIO;
    }
    a90_console_printf("A90BOOTAUDIT is_block=%d\r\n", S_ISBLK(st.st_mode) ? 1 : 0);
    a90_console_printf("A90BOOTAUDIT rdev=%u:%u\r\n",
                       (unsigned)major(st.st_rdev), (unsigned)minor(st.st_rdev));

    if (have_expected &&
        ((unsigned)major(st.st_rdev) != exp_maj || (unsigned)minor(st.st_rdev) != exp_min)) {
        a90_console_printf("A90BOOTAUDIT rdev_mismatch=1\r\n");
        a90_console_printf("A90BOOTAUDIT rdev_expected=%u:%u\r\n", exp_maj, exp_min);
        *authoritative = 0;
    }
    a90_console_printf("A90BOOTAUDIT authoritative=%d\r\n", *authoritative);

    uint64_t size_bytes = 0;
    if (ioctl(fd, BLKGETSIZE64, &size_bytes) == 0) {
        a90_console_printf("A90BOOTAUDIT size_bytes=%llu\r\n", (unsigned long long)size_bytes);
    } else {
        a90_console_printf("A90BOOTAUDIT size_bytes=unknown errno=%d\r\n", errno);
    }

    int lbs = 0, pbs = 0;
    if (ioctl(fd, BLKSSZGET, &lbs) == 0) {
        a90_console_printf("A90BOOTAUDIT logical_sector=%d\r\n", lbs);
    }
    if (ioctl(fd, BLKPBSZGET, &pbs) == 0) {
        a90_console_printf("A90BOOTAUDIT physical_sector=%d\r\n", pbs);
    }

    /* §0.1 feasibility: actually READ the first block. Open success alone does not prove RKP allows
     * reading the boot partition. We read up to 4096 bytes at offset 0 (never printing the contents)
     * and report only the byte count / errno. */
    {
        unsigned char probe[4096];
        ssize_t rn = pread(fd, probe, sizeof(probe), 0);
        if (rn >= 0) {
            a90_console_printf("A90BOOTAUDIT read=ok bytes=%ld\r\n", (long)rn);
        } else {
            a90_console_printf("A90BOOTAUDIT read=fail errno=%d (%s)\r\n", errno, strerror(errno));
        }
    }

    /* sysfs facts resolved from the fd's rdev (not the path string). */
    char sysbase[128];
    snprintf(sysbase, sizeof(sysbase), "/sys/dev/block/%u:%u",
             (unsigned)major(st.st_rdev), (unsigned)minor(st.st_rdev));
    a90_console_printf("A90BOOTAUDIT sysfs=%s\r\n", sysbase);

    char path[192];
    char buf[4096];

    snprintf(path, sizeof(path), "%s/uevent", sysbase);
    if (read_text_file(path, buf, sizeof(buf)) >= 0) {
        char partname[64];
        parse_uevent_key(buf, "PARTNAME=", partname, sizeof(partname));
        a90_console_printf("A90BOOTAUDIT partname=%s\r\n", partname[0] ? partname : "unknown");
    } else {
        a90_console_printf("A90BOOTAUDIT partname=unreadable\r\n");
    }

    snprintf(path, sizeof(path), "%s/diskseq", sysbase);
    if (read_trimmed_text_file(path, buf, sizeof(buf)) >= 0 && buf[0]) {
        a90_console_printf("A90BOOTAUDIT diskseq=%s\r\n", buf);
    } else {
        a90_console_printf("A90BOOTAUDIT diskseq=absent\r\n");
    }

    snprintf(path, sizeof(path), "%s/size", sysbase);
    if (read_trimmed_text_file(path, buf, sizeof(buf)) >= 0 && buf[0]) {
        a90_console_printf("A90BOOTAUDIT sysfs_sectors=%s\r\n", buf);
    }

    close(fd);
    return 0;
}

int a90_boot_audit_cmd(char **argv, int argc) {
    if (argc > 2) {
        a90_console_printf("usage: boot-audit [target-path]\r\n");
        return -EINVAL;
    }

    a90_console_printf("A90BOOTAUDIT begin\r\n");

    const char *target;
    char canonical_target[PATH_MAX];
    int authoritative;
    const char *resolve;
    int have_expected = 0;
    unsigned exp_maj = 0, exp_min = 0;
    int created = 0;

    if (argc == 2) {
        /* Explicit path: read-only diagnostic of any partition. Never materializes, never
         * authoritative unless it is exactly the default by-name target. */
        target = argv[1];
        authoritative = (strcmp(target, BOOT_AUDIT_DEFAULT_TARGET) == 0) ? 1 : 0;
        resolve = "explicit-path";
    } else if (access(BOOT_AUDIT_DEFAULT_TARGET, F_OK) == 0) {
        /* by-name symlink present (e.g. under Android/recovery ueventd): use it authoritatively. */
        target = BOOT_AUDIT_DEFAULT_TARGET;
        authoritative = 1;
        resolve = "by-name";
    } else {
        /* native-init: no by-name symlink and no boot devnode. Resolve from sysfs PARTNAME=boot. */
        char name[256];
        unsigned maj = 0, min = 0;
        int n = resolve_boot_from_sysfs(name, sizeof(name), &maj, &min);
        if (n != 1) {
            a90_console_printf("A90BOOTAUDIT target=%s\r\n", BOOT_AUDIT_DEFAULT_TARGET);
            a90_console_printf("A90BOOTAUDIT resolve=%s\r\n", (n <= 0) ? "none" : "ambiguous");
            a90_console_printf("A90BOOTAUDIT authoritative=0\r\n");
            a90_console_printf("A90BOOTAUDIT end rc=%d\r\n", -ENODEV);
            return -ENODEV;
        }
        snprintf(canonical_target, sizeof(canonical_target), "/dev/block/%s", name);
        target = canonical_target;
        authoritative = 1;
        resolve = "sysfs-partname";
        have_expected = 1;
        exp_maj = maj;
        exp_min = min;
        /* Materialize the boot node (device node in /dev tmpfs, NOT a partition write). */
        int mrc = mknod(target, S_IFBLK | 0600, makedev(maj, min));
        if (mrc == 0) {
            created = 1;
        } else if (errno != EEXIST) {
            int e = errno;
            a90_console_printf("A90BOOTAUDIT target=%s\r\n", target);
            a90_console_printf("A90BOOTAUDIT resolve=%s\r\n", resolve);
            a90_console_printf("A90BOOTAUDIT authoritative=0\r\n");
            a90_console_printf("A90BOOTAUDIT mknod=fail errno=%d (%s)\r\n", e, strerror(e));
            a90_console_printf("A90BOOTAUDIT end rc=%d\r\n", -e);
            return -e;
        }
        /* EEXIST: a node already existed at this path; keep created=0 (do not unlink someone
         * else's node) and rely on the rdev cross-check in audit_report to validate it. */
    }

    a90_console_printf("A90BOOTAUDIT target=%s\r\n", target);
    a90_console_printf("A90BOOTAUDIT resolve=%s\r\n", resolve);
    if (have_expected) {
        a90_console_printf("A90BOOTAUDIT materialized=%d\r\n", created);
    }

    int authv = authoritative;
    int rc = audit_report(target, &authv, have_expected, exp_maj, exp_min);

    if (created) {
        unlink(target);
        a90_console_printf("A90BOOTAUDIT cleaned=1\r\n");
    }
    a90_console_printf("A90BOOTAUDIT end rc=%d\r\n", rc);
    return rc;
}
