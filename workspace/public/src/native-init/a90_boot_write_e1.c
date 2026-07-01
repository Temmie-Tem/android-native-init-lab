/*
 * a90_boot_write_e1.c — §0.2 write-probe rung E1 (design §11.2): first actual boot-block pwrite.
 *
 * SAFETY MODEL (design §11, Codex-reviewed, UFS). Storage is UFS: an INTERRUPTED write is NOT
 * guaranteed safe even for identical bytes — the FTL erases/programs at a large internal granularity
 * and updates mapping metadata, so a tear can corrupt the target LBA AND neighbouring FTL metadata
 * that maps other LBAs (including boot content). We do NOT claim identity content makes a torn write
 * harmless. This rung is only LOW-RISK-BY-CONSTRUCTION and its failure class is EXTERNALLY
 * RECOVERABLE (boot-only): it writes to a 4096-byte sector that is (a) past the parsed boot-image
 * content, (b) >= 1 MiB before the partition end, and (c) CONFIRMED all-zero at write time — writing
 * the exact zero bytes it just read. A completed write is a no-op; a torn write is a recover-via-
 * Odin/TWRP event that the operator MUST have drilled before running this. All fds are
 * identity-guarded (block + rdev==sysfs + PARTNAME=boot + size==64MiB) and opened O_NOFOLLOW; the
 * write is verified by an O_DIRECT cache-bypassed region readback and an O_DIRECT full-partition SHA
 * before/after (to catch any cross-LBA change). Any anomaly is reported as A90BWE1 stop=... .
 * Token-gated. This is the only self-dd source file with a pwrite (exactly one).
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE /* O_DIRECT, posix_memalign */
#endif
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

#include "a90_boot_write_e1.h"
#include "a90_console.h"
#include "a90_helper.h"
#include "a90_util.h"

#define E1_TOKEN "BOOT-WRITE-PROBE-E1-TAILSLACK"
#define E1_PARTNAME "boot"
#define E1_BOOT_SIZE_BYTES (64ULL * 1024ULL * 1024ULL)
#define E1_SECTOR 4096u
#define E1_FOOTER_GUARD (1ULL * 1024ULL * 1024ULL) /* leave the last 1 MiB untouched (AVB footer) */
#define E1_SHA_HEX 65
#define E1_STREAM_CHUNK (1024u * 1024u)

/* Android boot header field offsets (bootimg.h v0/v1/v2). */
#define AH_KERNEL_SIZE 8
#define AH_RAMDISK_SIZE 16
#define AH_SECOND_SIZE 24
#define AH_PAGE_SIZE 36
#define AH_HEADER_VERSION 40
#define AH_RECOVERY_DTBO_SIZE 1632
#define AH_DTB_SIZE 1648

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif
#ifndef O_DIRECT
#define O_DIRECT 0
#endif

static void e1_uevent_key(const char *uevent, const char *key, char *out, size_t out_size) {
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

static int e1_resolve_boot(char *name_out, size_t name_sz, unsigned *maj_out, unsigned *min_out) {
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
        e1_uevent_key(buf, "PARTNAME=", partname, sizeof(partname));
        e1_uevent_key(buf, "DEVTYPE=", devtype, sizeof(devtype));
        if (strcmp(partname, E1_PARTNAME) != 0) {
            continue;
        }
        if (devtype[0] && strcmp(devtype, "partition") != 0) {
            continue;
        }
        if (matches == 0) {
            char maj_s[16];
            char min_s[16];
            e1_uevent_key(buf, "MAJOR=", maj_s, sizeof(maj_s));
            e1_uevent_key(buf, "MINOR=", min_s, sizeof(min_s));
            snprintf(name_out, name_sz, "%s", e->d_name);
            *maj_out = (unsigned)strtoul(maj_s, NULL, 10);
            *min_out = (unsigned)strtoul(min_s, NULL, 10);
        }
        matches++;
    }
    closedir(d);
    return matches;
}

static uint32_t e1_rd_u32le(const unsigned char *b, size_t off) {
    return (uint32_t)b[off] | ((uint32_t)b[off + 1] << 8) |
           ((uint32_t)b[off + 2] << 16) | ((uint32_t)b[off + 3] << 24);
}

static uint64_t e1_round_up(uint64_t v, uint64_t a) {
    if (a == 0) {
        return v;
    }
    return ((v + a - 1) / a) * a;
}

static void e1_hex(const unsigned char *digest, char *out) {
    static const char hexd[] = "0123456789abcdef";
    for (int i = 0; i < 32; ++i) {
        out[i * 2] = hexd[(digest[i] >> 4) & 0xf];
        out[i * 2 + 1] = hexd[digest[i] & 0xf];
    }
    out[64] = '\0';
}

/* Confirm fd is the boot partition: block, rdev==exp, PARTNAME=boot, size==64MiB. 1 pass / 0 refuse. */
static int e1_confirm(int fd, unsigned exp_maj, unsigned exp_min, int announce) {
    struct stat st;
    if (fstat(fd, &st) != 0) {
        a90_console_printf("A90BWE1 fstat=fail errno=%d\r\n", errno);
        return 0;
    }
    int ok = S_ISBLK(st.st_mode) ? 1 : 0;
    unsigned maj = (unsigned)major(st.st_rdev);
    unsigned min = (unsigned)minor(st.st_rdev);
    if (announce) {
        a90_console_printf("A90BWE1 rdev=%u:%u\r\n", maj, min);
    }
    if (maj != exp_maj || min != exp_min) {
        a90_console_printf("A90BWE1 rdev_mismatch=1 expected=%u:%u got=%u:%u\r\n",
                           exp_maj, exp_min, maj, min);
        ok = 0;
    }
    uint64_t size_bytes = 0;
    if (ioctl(fd, BLKGETSIZE64, &size_bytes) != 0 || size_bytes != E1_BOOT_SIZE_BYTES) {
        a90_console_printf("A90BWE1 size_mismatch=%llu expected=%llu\r\n",
                           (unsigned long long)size_bytes, (unsigned long long)E1_BOOT_SIZE_BYTES);
        ok = 0;
    }
    char sysbase[128];
    char path[192];
    char buf[4096];
    snprintf(sysbase, sizeof(sysbase), "/sys/dev/block/%u:%u", maj, min);
    snprintf(path, sizeof(path), "%s/uevent", sysbase);
    if (read_text_file(path, buf, sizeof(buf)) >= 0) {
        char partname[64];
        e1_uevent_key(buf, "PARTNAME=", partname, sizeof(partname));
        if (strcmp(partname, E1_PARTNAME) != 0) {
            a90_console_printf("A90BWE1 partname_mismatch=%s\r\n", partname[0] ? partname : "unknown");
            ok = 0;
        }
    } else {
        a90_console_printf("A90BWE1 partname=unreadable\r\n");
        ok = 0;
    }
    return ok;
}

/* Full-partition SHA-256 through a fresh O_DIRECT (cache-bypassed) fd whose identity is re-confirmed.
 * Returns 0 and fills out[65] on success, else -errno / -EPERM. */
static int e1_full_sha_odirect(const char *node, unsigned exp_maj, unsigned exp_min,
                               uint64_t size, char *out) {
    int fd = open(node, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (!e1_confirm(fd, exp_maj, exp_min, 0)) {
        close(fd);
        return -EPERM;
    }
    void *buf = NULL;
    if (posix_memalign(&buf, E1_SECTOR, E1_STREAM_CHUNK) != 0 || buf == NULL) {
        close(fd);
        return -ENOMEM;
    }
    struct a90_sha256_ctx ctx;
    a90_helper_sha256_init(&ctx);
    uint64_t off = 0;
    int rc = 0;
    while (off < size) {
        size_t want = E1_STREAM_CHUNK;
        if (size - off < (uint64_t)want) {
            want = (size_t)(size - off);
        }
        ssize_t rd = pread(fd, buf, want, (off_t)off);
        if (rd <= 0) {
            rc = (rd < 0) ? -errno : -EIO;
            break;
        }
        a90_helper_sha256_update(&ctx, (const unsigned char *)buf, (size_t)rd);
        off += (uint64_t)rd;
    }
    free(buf);
    close(fd);
    if (rc != 0) {
        return rc;
    }
    if (off != size) {
        return -EIO;
    }
    unsigned char digest[32];
    a90_helper_sha256_final(&ctx, digest);
    e1_hex(digest, out);
    return 0;
}

int a90_boot_write_e1_cmd(char **argv, int argc) {
    if (argc != 2 || strcmp(argv[1], E1_TOKEN) != 0) {
        a90_console_printf("usage: boot-write-e1 %s\r\n", E1_TOKEN);
        a90_console_printf("A90BWE1 refused=missing-or-wrong-token\r\n");
        return -EPERM;
    }

    a90_console_printf("A90BWE1 begin\r\n");
    a90_console_printf("A90BWE1 rung=E1 mode=read-then-write-identical scope=tail-slack-4096\r\n");

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("A90BWE1 resolve=%s\r\n", (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("A90BWE1 stop=resolve\r\n");
        a90_console_printf("A90BWE1 end rc=%d\r\n", -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("A90BWE1 target_node=%s resolve=sysfs-partname\r\n", node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("A90BWE1 mknod=fail errno=%d (%s)\r\n", e, strerror(e));
        a90_console_printf("A90BWE1 stop=mknod\r\n");
        a90_console_printf("A90BWE1 end rc=%d\r\n", -e);
        return -e;
    }

    int rc = 0;
    const char *stop = NULL;
    char sha_before[E1_SHA_HEX];
    unsigned char tbuf[E1_SECTOR];
    uint64_t target_off = 0;

    /* Read fd + identity confirmation. */
    int rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("A90BWE1 open_rdonly=fail errno=%d (%s)\r\n", e, strerror(e));
        stop = "open-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        close(rfd);
        goto cleanup;
    }

    /* Parse the Android boot header; FAIL CLOSED on missing magic / unsupported version. */
    {
        unsigned char hdr[E1_SECTOR];
        if (pread(rfd, hdr, sizeof(hdr), 0) != (ssize_t)sizeof(hdr)) {
            a90_console_printf("A90BWE1 header_read=fail errno=%d\r\n", errno);
            stop = "header-read";
            rc = -EIO;
            close(rfd);
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("A90BWE1 boot_header=absent stop=no-boot-magic\r\n");
            stop = "no-boot-magic";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("A90BWE1 boot_header=bad-page-size=%u stop=bad-page-size\r\n", page_size);
            stop = "bad-page-size";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("A90BWE1 boot_header=unsupported-version=%u stop=unsupported-header\r\n", hver);
            stop = "unsupported-header";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint64_t used_len = (uint64_t)page_size
                          + e1_round_up(e1_rd_u32le(hdr, AH_KERNEL_SIZE), page_size)
                          + e1_round_up(e1_rd_u32le(hdr, AH_RAMDISK_SIZE), page_size)
                          + e1_round_up(e1_rd_u32le(hdr, AH_SECOND_SIZE), page_size);
        if (hver >= 1) {
            used_len += e1_round_up(e1_rd_u32le(hdr, AH_RECOVERY_DTBO_SIZE), page_size);
        }
        if (hver >= 2) {
            used_len += e1_round_up(e1_rd_u32le(hdr, AH_DTB_SIZE), page_size);
        }
        a90_console_printf("A90BWE1 boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           hver, page_size, (unsigned long long)used_len);

        /* Slack window: past the parsed content, and >= FOOTER_GUARD before the partition end. */
        uint64_t slack_start = e1_round_up(used_len, E1_SECTOR);
        uint64_t slack_end = E1_BOOT_SIZE_BYTES - E1_FOOTER_GUARD; /* exclusive */
        a90_console_printf("A90BWE1 slack_start=%llu slack_end=%llu footer_guard=%llu\r\n",
                           (unsigned long long)slack_start, (unsigned long long)slack_end,
                           (unsigned long long)E1_FOOTER_GUARD);
        if (slack_start + E1_SECTOR > slack_end) {
            a90_console_printf("A90BWE1 stop=no-slack-window\r\n");
            stop = "no-slack";
            rc = -ENOSPC;
            close(rfd);
            goto cleanup;
        }
        /* Scan the slack window for the FIRST all-zero 4096B sector. This keeps BOTH safety layers:
         * the target is past parsed content AND confirmed-zero padding, so a torn write can only
         * disturb bytes the bootloader already ignores. tbuf holds the found zero sector. */
        uint64_t scanned = 0;
        int have_target = 0;
        for (uint64_t off = slack_start; off + E1_SECTOR <= slack_end; off += E1_SECTOR) {
            if (pread(rfd, tbuf, sizeof(tbuf), (off_t)off) != (ssize_t)sizeof(tbuf)) {
                a90_console_printf("A90BWE1 scan_read=fail off=%llu errno=%d\r\n",
                                   (unsigned long long)off, errno);
                stop = "scan-read";
                rc = -EIO;
                close(rfd);
                goto cleanup;
            }
            scanned++;
            int zero = 1;
            for (size_t i = 0; i < sizeof(tbuf); ++i) {
                if (tbuf[i] != 0) { zero = 0; break; }
            }
            if (zero) { target_off = off; have_target = 1; break; }
        }
        a90_console_printf("A90BWE1 slack_scanned=%llu have_zero_sector=%d\r\n",
                           (unsigned long long)scanned, have_target);
        if (!have_target) {
            a90_console_printf("A90BWE1 stop=no-zero-slack\r\n");
            stop = "no-zero-slack";
            rc = -ENOSPC;
            close(rfd);
            goto cleanup;
        }
        a90_console_printf("A90BWE1 target_off=%llu len=%u slack_zero=1\r\n",
                           (unsigned long long)target_off, E1_SECTOR);
    }
    /* tbuf holds the confirmed-zero target sector we will write back unchanged. */
    close(rfd);

    /* Full-partition SHA BEFORE (O_DIRECT, re-confirmed fd, cache-bypassed). */
    {
        int sr = e1_full_sha_odirect(node, maj, min, E1_BOOT_SIZE_BYTES, sha_before);
        if (sr != 0) {
            a90_console_printf("A90BWE1 sha_before=fail rc=%d\r\n", sr);
            stop = "sha-before";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("A90BWE1 full_sha_before=%s\r\n", sha_before);
    }

    /* Write fd (separate, re-guarded). Write the identical zero bytes we just read. */
    {
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("A90BWE1 open_wronly=fail errno=%d (%s)\r\n", e, strerror(e));
            stop = "open-wronly";
            rc = -e;
            goto verify_full;
        }
        if (!e1_confirm(wfd, maj, min, 0)) {
            a90_console_printf("A90BWE1 stop=identity-wfd\r\n");
            stop = "identity-wfd";
            rc = -EPERM;
            close(wfd);
            goto verify_full;
        }
        ssize_t wr = pwrite(wfd, tbuf, sizeof(tbuf), (off_t)target_off);
        int write_errno = errno;
        a90_console_printf("A90BWE1 pwrite_rc=%ld\r\n", (long)wr);
        if (wr != (ssize_t)sizeof(tbuf)) {
            a90_console_printf("A90BWE1 pwrite_errno=%d (%s)\r\n", write_errno, strerror(write_errno));
            stop = (wr < 0) ? "pwrite-error" : "pwrite-short";
            rc = (wr < 0) ? -write_errno : -EIO;
            close(wfd);
            goto verify_full;
        }
        if (fsync(wfd) != 0) {
            a90_console_printf("A90BWE1 fsync=fail errno=%d\r\n", errno);
            stop = "fsync";
            rc = -EIO;
            close(wfd);
            goto verify_full;
        }
        close(wfd);
        a90_console_printf("A90BWE1 pwrite=ok fsync=ok\r\n");
    }

    /* O_DIRECT cache-bypassed region readback; re-confirm the fd; memcmp to the bytes we wrote. */
    {
        int dfd = open(node, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
        if (dfd < 0) {
            a90_console_printf("A90BWE1 odirect_open=fail errno=%d\r\n", errno);
            if (!stop) { stop = "odirect-open"; rc = -EIO; }
        } else if (!e1_confirm(dfd, maj, min, 0)) {
            a90_console_printf("A90BWE1 stop=identity-dfd\r\n");
            if (!stop) { stop = "identity-dfd"; rc = -EPERM; }
            close(dfd);
        } else {
            void *abuf = NULL;
            if (posix_memalign(&abuf, E1_SECTOR, E1_SECTOR) != 0 || abuf == NULL) {
                a90_console_printf("A90BWE1 odirect_align=fail\r\n");
                if (!stop) { stop = "odirect-align"; rc = -ENOMEM; }
            } else {
                ssize_t rr = pread(dfd, abuf, E1_SECTOR, (off_t)target_off);
                int region_match = (rr == (ssize_t)E1_SECTOR) && memcmp(abuf, tbuf, E1_SECTOR) == 0;
                a90_console_printf("A90BWE1 readback_rc=%ld region_match=%d\r\n",
                                   (long)rr, region_match);
                if (!region_match && !stop) { stop = "region-mismatch"; rc = -EIO; }
                free(abuf);
            }
            close(dfd);
        }
    }

verify_full:;
    /* Full-partition SHA AFTER (O_DIRECT, re-confirmed fd); compare to before. */
    {
        char sha_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(node, maj, min, E1_BOOT_SIZE_BYTES, sha_after);
        if (sr != 0) {
            a90_console_printf("A90BWE1 sha_after=fail rc=%d\r\n", sr);
            if (!stop) { stop = "sha-after"; rc = sr; }
        } else {
            int full_match = strcmp(sha_before, sha_after) == 0;
            a90_console_printf("A90BWE1 full_sha_after=%s\r\n", sha_after);
            a90_console_printf("A90BWE1 full_match=%d\r\n", full_match);
            if (!full_match && !stop) { stop = "full-partition-changed"; rc = -EIO; }
        }
    }

cleanup:
    if (created) {
        unlink(node);
        a90_console_printf("A90BWE1 cleaned=1\r\n");
    }
    if (stop) {
        a90_console_printf("A90BWE1 stop=%s\r\n", stop);
    } else {
        a90_console_printf("A90BWE1 result=ok pwrite-permitted-identity-verified\r\n");
    }
    a90_console_printf("A90BWE1 end rc=%d\r\n", rc);
    return rc;
}
