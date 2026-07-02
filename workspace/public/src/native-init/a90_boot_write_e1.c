/*
 * a90_boot_write_e1.c — §0.2 write-probe rungs E1..E5 (design §11.2): boot-block identity pwrite,
 * plus F0/F1/F2/F3 (design §12): read-only content-changing source-plan, gated paired roundtrip,
 * gated self-written candidate boot preparation, and gated self-rollback preparation.
 *
 * SAFETY MODEL (design §11, Codex-reviewed, UFS). Storage is UFS: an INTERRUPTED write is NOT
 * guaranteed safe even for identical bytes — the FTL erases/programs at a large internal granularity
 * and updates mapping metadata, so a tear can corrupt the target LBA AND neighbouring FTL metadata
 * that maps other LBAs (including boot content). We do NOT claim identity content makes a torn write
 * harmless. This rung is only LOW-RISK-BY-CONSTRUCTION and its failure class is EXTERNALLY
 * RECOVERABLE (boot-only): it writes only past the parsed boot-image content and >= 1 MiB before the
 * partition end. E1/E2/E3a require confirmed-zero sectors; E3b requires a contiguous 1 MiB slack
 * block that contains non-zero bytes. Every rung writes the exact bytes it just read. E1 writes one
 * zero sector; E2 writes four zero sectors; E3a writes sixteen zero sectors; E3b writes one 1 MiB
 * non-zero slack block. E4 writes the 4 KiB Android boot-header sector at offset 0. E5 streams the
 * full 64 MiB boot partition back to itself in 1 MiB identity chunks.
 * A completed write is a no-op; a torn write is a recover-via-Odin/TWRP event that the operator MUST
 * have drilled before running this. All fds are
 * identity-guarded (block + rdev==sysfs + PARTNAME=boot + size==64MiB) and opened O_NOFOLLOW; the
 * write is verified by an O_DIRECT cache-bypassed region readback and an O_DIRECT full-partition SHA
 * before/after (to catch any cross-LBA change). Any anomaly is reported as A90BWE* stop=... .
 * Token-gated for write rungs. F0 performs no write and reports A90BWF0 would_write=0. F1 writes a
 * content-changing target.full, verifies it, then restores before.full before any reboot. F2/F3
 * write and verify target.full, return cleanly for a host-controlled reboot into the written target,
 * and restore before.full only on a target-write failure.
 * This is the only self-dd source file with a pwrite call site.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE /* O_DIRECT, posix_memalign */
#endif
#include <ctype.h>
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

#include "a90_config.h"
#include "a90_boot_write_e1.h"
#include "a90_console.h"
#include "a90_helper.h"
#include "a90_util.h"

#define E1_TOKEN "BOOT-WRITE-PROBE-E1-TAILSLACK"
#define E2_TOKEN "BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK"
#define E3A_TOKEN "BOOT-WRITE-PROBE-E3A-SPARSE-TAILSLACK"
#define E3B_TOKEN "BOOT-WRITE-PROBE-E3B-1MIB-SLACK"
#define E4_TOKEN "BOOT-WRITE-PROBE-E4-HEADER-SECTOR"
#define E5_TOKEN "BOOT-WRITE-PROBE-E5-FULL-IDENTITY"
#define E1_PARTNAME "boot"
#define E1_BOOT_SIZE_BYTES (64ULL * 1024ULL * 1024ULL)
#define E1_SECTOR 4096u
#define E1_FOOTER_GUARD (1ULL * 1024ULL * 1024ULL) /* leave the last 1 MiB untouched (AVB footer) */
#define E1_SHA_HEX 65
#define E1_STREAM_CHUNK (1024u * 1024u)
#define E2_TARGET_COUNT 4u
#define E3A_TARGET_COUNT 16u
#define E_MAX_TARGETS E3A_TARGET_COUNT
#define E_MAX_ZERO_CANDIDATES 1024u
#define E3B_BYTES (1024u * 1024u)
#define F0_TAG "A90BWF0"
#define F0_COMMAND "boot-flash-plan"
#define F0_STAGE_SD_ROOT SD_WORKSPACE_DIR "/flash-staging/"
#define F0_STAGE_CACHE_ROOT A90_RUNTIME_CACHE_ROOT "/flash-staging/"
#define F0_MAX_MARKER 128u
#define F1_TAG "A90BWF1"
#define F1_COMMAND "boot-flash-f1"
#define F1_TOKEN "BOOT-FLASH-F1-PAIRED-ROUNDTRIP"
#define F1_SNAPSHOT_PATH F0_STAGE_SD_ROOT "boot-flash-f1-before.full"
#define F1_SNAPSHOT_TMP F0_STAGE_SD_ROOT ".boot-flash-f1-before.full.tmp"
#define F2_TAG "A90BWF2"
#define F2_COMMAND "boot-flash-f2"
#define F2_TOKEN "BOOT-FLASH-F2-BOOT-CANDIDATE"
#define F2_SNAPSHOT_PATH F0_STAGE_SD_ROOT "boot-flash-f2-before.full"
#define F2_SNAPSHOT_TMP F0_STAGE_SD_ROOT ".boot-flash-f2-before.full.tmp"
#define F3_TAG "A90BWF3"
#define F3_COMMAND "boot-flash-f3"
#define F3_TOKEN "BOOT-FLASH-F3-SELF-ROLLBACK"
#define F3_SNAPSHOT_PATH F0_STAGE_SD_ROOT "boot-flash-f3-before.full"
#define F3_SNAPSHOT_TMP F0_STAGE_SD_ROOT ".boot-flash-f3-before.full.tmp"

struct e1_probe_spec {
    const char *tag;
    const char *command;
    const char *token;
    const char *rung;
    const char *scope;
    unsigned target_count;
    int spread_targets;
};

struct e1_target {
    uint64_t off;
    unsigned char bytes[E1_SECTOR];
};

struct e3b_probe_spec {
    const char *tag;
    const char *command;
    const char *token;
    const char *rung;
    const char *scope;
    uint32_t len;
    int require_nonzero;
};

struct e_fixed_probe_spec {
    const char *tag;
    const char *command;
    const char *token;
    const char *rung;
    const char *scope;
    uint64_t off;
    uint32_t len;
    int require_android_magic;
};

struct e_stream_probe_spec {
    const char *tag;
    const char *command;
    const char *token;
    const char *rung;
    const char *scope;
    uint64_t len;
    uint32_t chunk_len;
    int require_android_magic;
};

struct f_leave_target_spec {
    const char *tag;
    const char *command;
    const char *token;
    const char *mode;
    const char *snapshot_path;
    const char *snapshot_tmp;
    const char *success_restore_skipped_line;
    const char *success_result_line;
};

static const struct e1_probe_spec E1_SPEC = {
    "A90BWE1",
    "boot-write-e1",
    E1_TOKEN,
    "E1",
    "tail-slack-4096",
    1u,
    0,
};

static const struct e1_probe_spec E2_SPEC = {
    "A90BWE2",
    "boot-write-e2",
    E2_TOKEN,
    "E2",
    "tail-slack-4x4096-zero-population",
    E2_TARGET_COUNT,
    1,
};

static const struct e1_probe_spec E3A_SPEC = {
    "A90BWE3A",
    "boot-write-e3a",
    E3A_TOKEN,
    "E3A",
    "tail-slack-16x4096-zero-population-sparse",
    E3A_TARGET_COUNT,
    1,
};

static const struct e3b_probe_spec E3B_SPEC = {
    "A90BWE3B",
    "boot-write-e3b",
    E3B_TOKEN,
    "E3B",
    "tail-slack-contiguous-1mib-nonzero-identity",
    E3B_BYTES,
    1,
};

static const struct e_fixed_probe_spec E4_SPEC = {
    "A90BWE4",
    "boot-write-e4",
    E4_TOKEN,
    "E4",
    "header-sector-4096-identity",
    0,
    E1_SECTOR,
    1,
};

static const struct e_stream_probe_spec E5_SPEC = {
    "A90BWE5",
    "boot-write-e5",
    E5_TOKEN,
    "E5",
    "full-partition-64mib-identity-stream",
    E1_BOOT_SIZE_BYTES,
    E1_STREAM_CHUNK,
    1,
};

static const struct f_leave_target_spec F2_LEAVE_TARGET_SPEC = {
    F2_TAG,
    F2_COMMAND,
    F2_TOKEN,
    "boot-candidate-write",
    F2_SNAPSHOT_PATH,
    F2_SNAPSHOT_TMP,
    "restore_skipped=target-verified-host-reboot-required",
    "result=ok target-written-ready-to-reboot",
};

static const struct f_leave_target_spec F3_LEAVE_TARGET_SPEC = {
    F3_TAG,
    F3_COMMAND,
    F3_TOKEN,
    "self-rollback-write",
    F3_SNAPSHOT_PATH,
    F3_SNAPSHOT_TMP,
    "restore_skipped=rollback-verified-host-reboot-required",
    "result=ok rollback-written-ready-to-reboot",
};

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
#ifndef O_DIRECTORY
#define O_DIRECTORY 0
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

static void e1_sha256_bytes(const unsigned char *buf, size_t len, char *out) {
    struct a90_sha256_ctx ctx;
    unsigned char digest[32];
    a90_helper_sha256_init(&ctx);
    a90_helper_sha256_update(&ctx, buf, len);
    a90_helper_sha256_final(&ctx, digest);
    e1_hex(digest, out);
}

/* Confirm fd is the boot partition: block, rdev==exp, PARTNAME=boot, size==64MiB. 1 pass / 0 refuse. */
static int e1_confirm(const char *tag, int fd, unsigned exp_maj, unsigned exp_min, int announce) {
    struct stat st;
    if (fstat(fd, &st) != 0) {
        a90_console_printf("%s fstat=fail errno=%d\r\n", tag, errno);
        return 0;
    }
    int ok = S_ISBLK(st.st_mode) ? 1 : 0;
    unsigned maj = (unsigned)major(st.st_rdev);
    unsigned min = (unsigned)minor(st.st_rdev);
    if (announce) {
        a90_console_printf("%s rdev=%u:%u\r\n", tag, maj, min);
    }
    if (maj != exp_maj || min != exp_min) {
        a90_console_printf("%s rdev_mismatch=1 expected=%u:%u got=%u:%u\r\n",
                           tag, exp_maj, exp_min, maj, min);
        ok = 0;
    }
    uint64_t size_bytes = 0;
    if (ioctl(fd, BLKGETSIZE64, &size_bytes) != 0 || size_bytes != E1_BOOT_SIZE_BYTES) {
        a90_console_printf("%s size_mismatch=%llu expected=%llu\r\n",
                           tag, (unsigned long long)size_bytes,
                           (unsigned long long)E1_BOOT_SIZE_BYTES);
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
            a90_console_printf("%s partname_mismatch=%s\r\n", tag,
                               partname[0] ? partname : "unknown");
            ok = 0;
        }
    } else {
        a90_console_printf("%s partname=unreadable\r\n", tag);
        ok = 0;
    }
    return ok;
}

/* Full-partition SHA-256 through a fresh O_DIRECT (cache-bypassed) fd whose identity is re-confirmed.
 * Returns 0 and fills out[65] on success, else -errno / -EPERM. */
static int e1_full_sha_odirect(const char *tag, const char *node, unsigned exp_maj, unsigned exp_min,
                               uint64_t size, char *out) {
    int fd = open(node, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (!e1_confirm(tag, fd, exp_maj, exp_min, 0)) {
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

static int e1_fd_sha_stream(int fd, uint64_t size, char *out) {
    void *buf = NULL;
    if (posix_memalign(&buf, E1_SECTOR, E1_STREAM_CHUNK) != 0 || buf == NULL) {
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
        if (rd != (ssize_t)want) {
            rc = (rd < 0) ? -errno : -EIO;
            break;
        }
        a90_helper_sha256_update(&ctx, (const unsigned char *)buf, (size_t)rd);
        off += (uint64_t)rd;
    }
    free(buf);
    if (rc != 0) {
        return rc;
    }
    unsigned char digest[32];
    a90_helper_sha256_final(&ctx, digest);
    e1_hex(digest, out);
    return 0;
}

static int e1_is_zero_sector(const unsigned char *buf, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        if (buf[i] != 0) {
            return 0;
        }
    }
    return 1;
}

static int f0_hex64_is_valid(const char *s) {
    if (s == NULL || strlen(s) != 64) {
        return 0;
    }
    for (size_t i = 0; i < 64; ++i) {
        if (!isxdigit((unsigned char)s[i])) {
            return 0;
        }
    }
    return 1;
}

static int f0_sha_equal(const char *a, const char *b) {
    if (a == NULL || b == NULL) {
        return 0;
    }
    for (size_t i = 0; i < 64; ++i) {
        int ca = tolower((unsigned char)a[i]);
        int cb = tolower((unsigned char)b[i]);
        if (ca != cb) {
            return 0;
        }
    }
    return a[64] == '\0' && b[64] == '\0';
}

static int f0_path_has_prefix(const char *path, const char *prefix) {
    size_t n = strlen(prefix);
    return strncmp(path, prefix, n) == 0;
}

static int f0_path_has_dotdot(const char *path) {
    const char *p = path;
    while (p != NULL && *p != '\0') {
        if (p[0] == '/' && p[1] == '.' && p[2] == '.' &&
            (p[3] == '/' || p[3] == '\0')) {
            return 1;
        }
        ++p;
    }
    return 0;
}

static int f0_stage_path_allowed(const char *path) {
    if (path == NULL || path[0] != '/' || f0_path_has_dotdot(path)) {
        return 0;
    }
    return f0_path_has_prefix(path, F0_STAGE_SD_ROOT) ||
           f0_path_has_prefix(path, F0_STAGE_CACHE_ROOT);
}

static int f0_mem_contains(const unsigned char *hay, size_t hay_len,
                           const char *needle, size_t needle_len) {
    if (needle_len == 0) {
        return 1;
    }
    if (hay_len < needle_len) {
        return 0;
    }
    for (size_t i = 0; i + needle_len <= hay_len; ++i) {
        if (memcmp(hay + i, needle, needle_len) == 0) {
            return 1;
        }
    }
    return 0;
}

static int f0_scan_candidate(int fd, uint64_t size, const char *expected_marker,
                             char *sha_out, int *marker_found) {
    size_t marker_len = strlen(expected_marker);
    if (marker_len == 0 || marker_len > F0_MAX_MARKER) {
        return -EINVAL;
    }
    unsigned char *buf = malloc(E1_STREAM_CHUNK);
    if (buf == NULL) {
        return -ENOMEM;
    }
    unsigned char overlap[F0_MAX_MARKER * 2u];
    unsigned char tail[F0_MAX_MARKER];
    size_t tail_len = 0;
    *marker_found = 0;

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
        if (rd != (ssize_t)want) {
            rc = (rd < 0) ? -errno : -EIO;
            break;
        }
        a90_helper_sha256_update(&ctx, buf, want);
        if (!*marker_found) {
            if (f0_mem_contains(buf, want, expected_marker, marker_len)) {
                *marker_found = 1;
            } else if (tail_len > 0) {
                size_t head_len = marker_len - 1u;
                if (head_len > want) {
                    head_len = want;
                }
                memcpy(overlap, tail, tail_len);
                memcpy(overlap + tail_len, buf, head_len);
                if (f0_mem_contains(overlap, tail_len + head_len,
                                    expected_marker, marker_len)) {
                    *marker_found = 1;
                }
            }
        }
        if (marker_len > 1u) {
            size_t keep = marker_len - 1u;
            if (keep > F0_MAX_MARKER) {
                keep = F0_MAX_MARKER;
            }
            if (want >= keep) {
                memcpy(tail, buf + want - keep, keep);
                tail_len = keep;
            } else {
                unsigned char merged[F0_MAX_MARKER * 2u];
                size_t merged_len = tail_len + want;
                memcpy(merged, tail, tail_len);
                memcpy(merged + tail_len, buf, want);
                if (merged_len > keep) {
                    memcpy(tail, merged + merged_len - keep, keep);
                    tail_len = keep;
                } else {
                    memcpy(tail, merged, merged_len);
                    tail_len = merged_len;
                }
            }
        }
        off += (uint64_t)want;
    }
    free(buf);
    if (rc != 0) {
        return rc;
    }
    unsigned char digest[32];
    a90_helper_sha256_final(&ctx, digest);
    e1_hex(digest, sha_out);
    return 0;
}

static int f0_compute_target_plan(int boot_fd, int cand_fd, uint64_t candidate_size,
                                  char *target_sha, char *current_sha,
                                  uint64_t *changed_bytes, unsigned *changed_chunks) {
    unsigned char *boot_buf = malloc(E1_STREAM_CHUNK);
    unsigned char *target_buf = malloc(E1_STREAM_CHUNK);
    if (boot_buf == NULL || target_buf == NULL) {
        free(boot_buf);
        free(target_buf);
        return -ENOMEM;
    }
    struct a90_sha256_ctx target_ctx;
    struct a90_sha256_ctx current_ctx;
    a90_helper_sha256_init(&target_ctx);
    a90_helper_sha256_init(&current_ctx);
    *changed_bytes = 0;
    *changed_chunks = 0;

    int rc = 0;
    for (uint64_t off = 0; off < E1_BOOT_SIZE_BYTES; off += E1_STREAM_CHUNK) {
        size_t want = E1_STREAM_CHUNK;
        if (E1_BOOT_SIZE_BYTES - off < (uint64_t)want) {
            want = (size_t)(E1_BOOT_SIZE_BYTES - off);
        }
        ssize_t br = pread(boot_fd, boot_buf, want, (off_t)off);
        if (br != (ssize_t)want) {
            rc = (br < 0) ? -errno : -EIO;
            break;
        }
        memcpy(target_buf, boot_buf, want);
        if (off < candidate_size) {
            size_t cand_want = want;
            if (candidate_size - off < (uint64_t)cand_want) {
                cand_want = (size_t)(candidate_size - off);
            }
            ssize_t cr = pread(cand_fd, target_buf, cand_want, (off_t)off);
            if (cr != (ssize_t)cand_want) {
                rc = (cr < 0) ? -errno : -EIO;
                break;
            }
        }
        int chunk_changed = 0;
        for (size_t i = 0; i < want; ++i) {
            if (target_buf[i] != boot_buf[i]) {
                (*changed_bytes)++;
                chunk_changed = 1;
            }
        }
        if (chunk_changed) {
            (*changed_chunks)++;
        }
        a90_helper_sha256_update(&current_ctx, boot_buf, want);
        a90_helper_sha256_update(&target_ctx, target_buf, want);
    }
    free(boot_buf);
    free(target_buf);
    if (rc != 0) {
        return rc;
    }
    unsigned char digest[32];
    a90_helper_sha256_final(&current_ctx, digest);
    e1_hex(digest, current_sha);
    a90_helper_sha256_final(&target_ctx, digest);
    e1_hex(digest, target_sha);
    return 0;
}

static int e_pwrite_exact(const char *tag, int fd, const void *buf, size_t len, uint64_t off,
                          int indexed, unsigned index, const char **stop, int *rc);

static int f1_write_all_exact(int fd, const unsigned char *buf, size_t len) {
    size_t off = 0;
    while (off < len) {
        ssize_t wr = write(fd, buf + off, len - off);
        if (wr <= 0) {
            return (wr < 0) ? -errno : -EIO;
        }
        off += (size_t)wr;
    }
    return 0;
}

static void f1_fsync_snapshot_dir(const char *tag) {
    int dfd = open(F0_STAGE_SD_ROOT, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (dfd < 0) {
        a90_console_printf("%s snapshot_dir_fsync=skip errno=%d\r\n", tag, errno);
        return;
    }
    if (fsync(dfd) != 0) {
        a90_console_printf("%s snapshot_dir_fsync=fail errno=%d\r\n", tag, errno);
    } else {
        a90_console_printf("%s snapshot_dir_fsync=ok\r\n", tag);
    }
    close(dfd);
}

static int f1_capture_before_snapshot(const char *tag, int boot_fd, const char *expected_sha,
                                      const char *snapshot_path, const char *snapshot_tmp,
                                      char *snapshot_sha_out) {
    unsigned char *buf = malloc(E1_STREAM_CHUNK);
    if (buf == NULL) {
        return -ENOMEM;
    }
    struct stat existing;
    if (lstat(snapshot_path, &existing) == 0) {
        free(buf);
        a90_console_printf("%s snapshot_existing=%s refused=preserve-retained-snapshot\r\n",
                           tag, snapshot_path);
        return -EEXIST;
    }
    if (errno != ENOENT) {
        int e = errno;
        free(buf);
        a90_console_printf("%s snapshot_lstat=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        return -e;
    }
    if (unlink(snapshot_tmp) != 0 && errno != ENOENT) {
        int e = errno;
        free(buf);
        a90_console_printf("%s snapshot_tmp_unlink=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        return -e;
    }
    int out_fd = open(snapshot_tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (out_fd < 0) {
        int e = errno;
        free(buf);
        a90_console_printf("%s snapshot_open=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        return -e;
    }

    struct a90_sha256_ctx ctx;
    a90_helper_sha256_init(&ctx);
    uint64_t off = 0;
    int rc = 0;
    while (off < E1_BOOT_SIZE_BYTES) {
        size_t want = E1_STREAM_CHUNK;
        if (E1_BOOT_SIZE_BYTES - off < (uint64_t)want) {
            want = (size_t)(E1_BOOT_SIZE_BYTES - off);
        }
        ssize_t rd = pread(boot_fd, buf, want, (off_t)off);
        if (rd != (ssize_t)want) {
            rc = (rd < 0) ? -errno : -EIO;
            a90_console_printf("%s snapshot_read=fail off=%llu rc=%ld errno=%d\r\n",
                               tag, (unsigned long long)off, (long)rd, errno);
            break;
        }
        rc = f1_write_all_exact(out_fd, buf, want);
        if (rc != 0) {
            a90_console_printf("%s snapshot_write=fail off=%llu rc=%d\r\n",
                               tag, (unsigned long long)off, rc);
            break;
        }
        a90_helper_sha256_update(&ctx, buf, want);
        off += (uint64_t)want;
    }
    free(buf);

    if (rc == 0 && fsync(out_fd) != 0) {
        rc = -errno;
        a90_console_printf("%s snapshot_fsync=fail errno=%d\r\n", tag, errno);
    }
    close(out_fd);
    if (rc != 0) {
        unlink(snapshot_tmp);
        return rc;
    }

    unsigned char digest[32];
    a90_helper_sha256_final(&ctx, digest);
    e1_hex(digest, snapshot_sha_out);
    int snapshot_match = f0_sha_equal(snapshot_sha_out, expected_sha);
    a90_console_printf("%s snapshot_tmp_path=%s snapshot_bytes=%llu snapshot_sha=%s snapshot_match_before=%d\r\n",
                       tag, snapshot_tmp, (unsigned long long)off, snapshot_sha_out,
                       snapshot_match);
    if (!snapshot_match) {
        unlink(snapshot_tmp);
        return -EIO;
    }
    if (rename(snapshot_tmp, snapshot_path) != 0) {
        int e = errno;
        a90_console_printf("%s snapshot_rename=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        unlink(snapshot_tmp);
        return -e;
    }
    f1_fsync_snapshot_dir(tag);
    a90_console_printf("%s snapshot_path=%s snapshot_ready=1\r\n", tag, snapshot_path);
    return 0;
}

static int f1_write_full_image_chunks(const char *tag, const char *phase, int wfd,
                                      int snapshot_fd, int candidate_fd, uint64_t candidate_size,
                                      const char **stop, int *rc) {
    void *chunk = NULL;
    if (posix_memalign(&chunk, E1_SECTOR, E1_STREAM_CHUNK) != 0 || chunk == NULL) {
        a90_console_printf("%s %s_align=fail\r\n", tag, phase);
        *stop = "chunk-align";
        *rc = -ENOMEM;
        return -ENOMEM;
    }
    unsigned wrote = 0;
    a90_console_printf("%s %s_begin=1 len=%llu chunk_len=%u\r\n",
                       tag, phase, (unsigned long long)E1_BOOT_SIZE_BYTES, E1_STREAM_CHUNK);
    for (uint64_t off = 0; off < E1_BOOT_SIZE_BYTES; off += E1_STREAM_CHUNK) {
        size_t want = E1_STREAM_CHUNK;
        if (E1_BOOT_SIZE_BYTES - off < (uint64_t)want) {
            want = (size_t)(E1_BOOT_SIZE_BYTES - off);
        }
        ssize_t sr = pread(snapshot_fd, chunk, want, (off_t)off);
        if (sr != (ssize_t)want) {
            a90_console_printf("%s %s_snapshot_read%u_rc=%ld off=%llu errno=%d\r\n",
                               tag, phase, wrote, (long)sr, (unsigned long long)off, errno);
            *stop = "snapshot-read";
            *rc = (sr < 0) ? -errno : -EIO;
            free(chunk);
            return *rc;
        }
        if (candidate_fd >= 0 && off < candidate_size) {
            size_t cand_want = want;
            if (candidate_size - off < (uint64_t)cand_want) {
                cand_want = (size_t)(candidate_size - off);
            }
            ssize_t cr = pread(candidate_fd, chunk, cand_want, (off_t)off);
            if (cr != (ssize_t)cand_want) {
                a90_console_printf("%s %s_candidate_read%u_rc=%ld off=%llu errno=%d\r\n",
                                   tag, phase, wrote, (long)cr, (unsigned long long)off, errno);
                *stop = "candidate-read";
                *rc = (cr < 0) ? -errno : -EIO;
                free(chunk);
                return *rc;
            }
        }
        if (!e_pwrite_exact(tag, wfd, chunk, want, off, 1, wrote, stop, rc)) {
            free(chunk);
            return *rc;
        }
        wrote++;
    }
    if (fsync(wfd) != 0) {
        a90_console_printf("%s %s_fsync=fail errno=%d\r\n", tag, phase, errno);
        *stop = "fsync";
        *rc = -EIO;
        free(chunk);
        return *rc;
    }
    a90_console_printf("%s %s_pwrite_count=%u %s_fsync=ok\r\n",
                       tag, phase, wrote, phase);
    free(chunk);
    return 0;
}

static int e1_find_zero_sector(const char *tag, int rfd, uint64_t start, uint64_t end,
                               struct e1_target *target, uint64_t *scanned) {
    for (uint64_t off = start; off + E1_SECTOR <= end; off += E1_SECTOR) {
        if (pread(rfd, target->bytes, sizeof(target->bytes), (off_t)off) !=
            (ssize_t)sizeof(target->bytes)) {
            a90_console_printf("%s scan_read=fail off=%llu errno=%d\r\n",
                               tag, (unsigned long long)off, errno);
            return -EIO;
        }
        (*scanned)++;
        if (e1_is_zero_sector(target->bytes, sizeof(target->bytes))) {
            target->off = off;
            return 1;
        }
    }
    return 0;
}

static unsigned e_select_spread_index(unsigned zero_count, unsigned target_count, unsigned target_index,
                                      unsigned previous_index) {
    unsigned remaining = target_count - target_index;
    unsigned min_index = (target_index == 0) ? 0 : previous_index + 1u;
    unsigned max_index = zero_count - remaining;
    unsigned desired = (target_count <= 1u || zero_count <= 1u)
                     ? 0u
                     : (unsigned)(((uint64_t)target_index * (uint64_t)(zero_count - 1u)) /
                                  (uint64_t)(target_count - 1u));
    if (desired < min_index) {
        desired = min_index;
    }
    if (desired > max_index) {
        desired = max_index;
    }
    return desired;
}

static int e_pwrite_exact(const char *tag, int fd, const void *buf, size_t len, uint64_t off,
                          int indexed, unsigned index, const char **stop, int *rc) {
    errno = 0;
    ssize_t wr = pwrite(fd, buf, len, (off_t)off);
    int write_errno = errno;
    if (indexed) {
        a90_console_printf("%s pwrite%u_rc=%ld\r\n", tag, index, (long)wr);
    } else {
        a90_console_printf("%s pwrite_rc=%ld\r\n", tag, (long)wr);
    }
    if (wr != (ssize_t)len) {
        int e = write_errno != 0 ? write_errno : EIO;
        a90_console_printf("%s pwrite_errno=%d (%s)\r\n", tag, e, strerror(e));
        *stop = (wr < 0) ? "pwrite-error" : "pwrite-short";
        *rc = (wr < 0) ? -e : -EIO;
        return 0;
    }
    return 1;
}

static int a90_boot_write_identity_cmd(const struct e1_probe_spec *spec, char **argv, int argc) {
    const char *tag = spec->tag;
    if (argc != 2 || strcmp(argv[1], spec->token) != 0) {
        a90_console_printf("usage: %s %s\r\n", spec->command, spec->token);
        a90_console_printf("%s refused=missing-or-wrong-token\r\n", tag);
        return -EPERM;
    }
    if (spec->target_count == 0 || spec->target_count > E_MAX_TARGETS) {
        a90_console_printf("%s refused=bad-target-count count=%u\r\n", tag, spec->target_count);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s rung=%s mode=read-then-write-identical scope=%s\r\n",
                       tag, spec->rung, spec->scope);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    const char *stop = NULL;
    char sha_before[E1_SHA_HEX];
    struct e1_target targets[E_MAX_TARGETS];
    memset(targets, 0, sizeof(targets));

    /* Read fd + identity confirmation. */
    int rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        close(rfd);
        goto cleanup;
    }

    /* Parse the Android boot header; FAIL CLOSED on missing magic / unsupported version. */
    {
        unsigned char hdr[E1_SECTOR];
        if (pread(rfd, hdr, sizeof(hdr), 0) != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s header_read=fail errno=%d\r\n", tag, errno);
            stop = "header-read";
            rc = -EIO;
            close(rfd);
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s boot_header=absent stop=no-boot-magic\r\n", tag);
            stop = "no-boot-magic";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s boot_header=bad-page-size=%u stop=bad-page-size\r\n",
                               tag, page_size);
            stop = "bad-page-size";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s boot_header=unsupported-version=%u stop=unsupported-header\r\n",
                               tag, hver);
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
        a90_console_printf("%s boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);

        /* Slack window: past the parsed content, and >= FOOTER_GUARD before the partition end. */
        uint64_t slack_start = e1_round_up(used_len, E1_SECTOR);
        uint64_t slack_end = E1_BOOT_SIZE_BYTES - E1_FOOTER_GUARD; /* exclusive */
        a90_console_printf("%s slack_start=%llu slack_end=%llu footer_guard=%llu\r\n",
                           tag, (unsigned long long)slack_start, (unsigned long long)slack_end,
                           (unsigned long long)E1_FOOTER_GUARD);
        if (slack_start + E1_SECTOR > slack_end) {
            a90_console_printf("%s stop=no-slack-window\r\n", tag);
            stop = "no-slack";
            rc = -ENOSPC;
            close(rfd);
            goto cleanup;
        }

        /* Scan only tail slack and require every selected sector to be confirmed all-zero. Multi-target
         * rungs build a zero-sector population across the whole slack window, then pick spread indices
         * from that population. This avoids the V3350 failure mode where a fixed quarter-band had no
         * zeros even though later slack did. */
        uint64_t scanned = 0;
        unsigned found = 0;
        if (!spec->spread_targets) {
            int fr = e1_find_zero_sector(tag, rfd, slack_start, slack_end, &targets[0], &scanned);
            if (fr < 0) {
                stop = "scan-read";
                rc = fr;
                close(rfd);
                goto cleanup;
            }
            if (fr > 0) {
                found = 1;
            }
        } else {
            uint64_t zero_offsets[E_MAX_ZERO_CANDIDATES];
            unsigned zero_stored = 0;
            uint64_t zero_total = 0;
            unsigned char scan_buf[E1_SECTOR];
            for (uint64_t off = slack_start; off + E1_SECTOR <= slack_end; off += E1_SECTOR) {
                if (pread(rfd, scan_buf, sizeof(scan_buf), (off_t)off) !=
                    (ssize_t)sizeof(scan_buf)) {
                    a90_console_printf("%s scan_read=fail off=%llu errno=%d\r\n",
                                       tag, (unsigned long long)off, errno);
                    stop = "scan-read";
                    rc = -EIO;
                    close(rfd);
                    goto cleanup;
                }
                scanned++;
                if (!e1_is_zero_sector(scan_buf, sizeof(scan_buf))) {
                    continue;
                }
                zero_total++;
                if (zero_stored >= E_MAX_ZERO_CANDIDATES) {
                    a90_console_printf("%s zero_candidate_overflow limit=%u\r\n",
                                       tag, E_MAX_ZERO_CANDIDATES);
                    stop = "zero-candidate-overflow";
                    rc = -E2BIG;
                    close(rfd);
                    goto cleanup;
                }
                zero_offsets[zero_stored++] = off;
            }
            a90_console_printf("%s zero_candidates=%llu zero_stored=%u target_count=%u\r\n",
                               tag, (unsigned long long)zero_total, zero_stored, spec->target_count);
            if (zero_stored < spec->target_count) {
                found = zero_stored;
            } else {
                unsigned previous_index = 0;
                for (unsigned i = 0; i < spec->target_count; ++i) {
                    unsigned idx = e_select_spread_index(zero_stored, spec->target_count, i,
                                                         previous_index);
                    previous_index = idx;
                    targets[i].off = zero_offsets[idx];
                    if (pread(rfd, targets[i].bytes, sizeof(targets[i].bytes),
                              (off_t)targets[i].off) != (ssize_t)sizeof(targets[i].bytes)) {
                        a90_console_printf("%s selected%u_read=fail off=%llu errno=%d\r\n",
                                           tag, i, (unsigned long long)targets[i].off, errno);
                        stop = "selected-read";
                        rc = -EIO;
                        close(rfd);
                        goto cleanup;
                    }
                    if (!e1_is_zero_sector(targets[i].bytes, sizeof(targets[i].bytes))) {
                        a90_console_printf("%s selected%u_zero_recheck=0 off=%llu\r\n",
                                           tag, i, (unsigned long long)targets[i].off);
                        stop = "selected-zero-recheck";
                        rc = -EIO;
                        close(rfd);
                        goto cleanup;
                    }
                    a90_console_printf("%s selected%u_index=%u selected%u_off=%llu\r\n",
                                       tag, i, idx, i, (unsigned long long)targets[i].off);
                    found++;
                }
            }
        }
        a90_console_printf("%s slack_scanned=%llu have_zero_sector=%d target_count=%u\r\n",
                           tag, (unsigned long long)scanned, found == spec->target_count,
                           spec->target_count);
        if (found != spec->target_count) {
            a90_console_printf("%s stop=no-zero-slack\r\n", tag);
            stop = "no-zero-slack";
            rc = -ENOSPC;
            close(rfd);
            goto cleanup;
        }
        for (unsigned i = 0; i < spec->target_count; ++i) {
            if (spec->target_count == 1u) {
                a90_console_printf("%s target_off=%llu len=%u slack_zero=1\r\n",
                                   tag, (unsigned long long)targets[i].off, E1_SECTOR);
            } else {
                a90_console_printf("%s target%u_off=%llu len=%u slack_zero=1\r\n",
                                   tag, i, (unsigned long long)targets[i].off, E1_SECTOR);
            }
        }
    }
    /* targets[] holds the confirmed-zero sectors we will write back unchanged. */
    close(rfd);

    /* Full-partition SHA BEFORE (O_DIRECT, re-confirmed fd, cache-bypassed). */
    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_before);
        if (sr != 0) {
            a90_console_printf("%s sha_before=fail rc=%d\r\n", tag, sr);
            stop = "sha-before";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("%s full_sha_before=%s\r\n", tag, sha_before);
    }

    /* Write fd (separate, re-guarded). Write the identical zero bytes we just read. */
    {
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
            stop = "open-wronly";
            rc = -e;
            goto verify_full;
        }
        if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s stop=identity-wfd\r\n", tag);
            stop = "identity-wfd";
            rc = -EPERM;
            close(wfd);
            goto verify_full;
        }
        unsigned wrote = 0;
        for (unsigned i = 0; i < spec->target_count; ++i) {
            if (!e_pwrite_exact(tag, wfd, targets[i].bytes, sizeof(targets[i].bytes),
                                targets[i].off, spec->target_count != 1u, i, &stop, &rc)) {
                close(wfd);
                goto verify_full;
            }
            wrote++;
        }
        if (fsync(wfd) != 0) {
            a90_console_printf("%s fsync=fail errno=%d\r\n", tag, errno);
            stop = "fsync";
            rc = -EIO;
            close(wfd);
            goto verify_full;
        }
        close(wfd);
        a90_console_printf("%s pwrite_count=%u pwrite=ok fsync=ok\r\n", tag, wrote);
    }

    /* O_DIRECT cache-bypassed region readback; re-confirm the fd; memcmp to the bytes we wrote. */
    {
        int dfd = open(node, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
        if (dfd < 0) {
            a90_console_printf("%s odirect_open=fail errno=%d\r\n", tag, errno);
            if (!stop) { stop = "odirect-open"; rc = -EIO; }
        } else if (!e1_confirm(tag, dfd, maj, min, 0)) {
            a90_console_printf("%s stop=identity-dfd\r\n", tag);
            if (!stop) { stop = "identity-dfd"; rc = -EPERM; }
            close(dfd);
        } else {
            void *abuf = NULL;
            if (posix_memalign(&abuf, E1_SECTOR, E1_SECTOR) != 0 || abuf == NULL) {
                a90_console_printf("%s odirect_align=fail\r\n", tag);
                if (!stop) { stop = "odirect-align"; rc = -ENOMEM; }
            } else {
                int all_match = 1;
                for (unsigned i = 0; i < spec->target_count; ++i) {
                    ssize_t rr = pread(dfd, abuf, E1_SECTOR, (off_t)targets[i].off);
                    int region_match = (rr == (ssize_t)E1_SECTOR) &&
                                       memcmp(abuf, targets[i].bytes, E1_SECTOR) == 0;
                    if (spec->target_count == 1u) {
                        a90_console_printf("%s readback_rc=%ld region_match=%d\r\n",
                                           tag, (long)rr, region_match);
                    } else {
                        a90_console_printf("%s readback%u_rc=%ld region%u_match=%d\r\n",
                                           tag, i, (long)rr, i, region_match);
                    }
                    if (!region_match) {
                        all_match = 0;
                    }
                }
                a90_console_printf("%s region_match_all=%d\r\n", tag, all_match);
                if (!all_match && !stop) { stop = "region-mismatch"; rc = -EIO; }
                free(abuf);
            }
            close(dfd);
        }
    }

verify_full:;
    /* Full-partition SHA AFTER (O_DIRECT, re-confirmed fd); compare to before. */
    {
        char sha_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_after);
        if (sr != 0) {
            a90_console_printf("%s sha_after=fail rc=%d\r\n", tag, sr);
            if (!stop) { stop = "sha-after"; rc = sr; }
        } else {
            int full_match = strcmp(sha_before, sha_after) == 0;
            a90_console_printf("%s full_sha_after=%s\r\n", tag, sha_after);
            a90_console_printf("%s full_match=%d\r\n", tag, full_match);
            if (!full_match && !stop) { stop = "full-partition-changed"; rc = -EIO; }
        }
    }

cleanup:
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s result=ok pwrite-permitted-identity-verified\r\n", tag);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

static int a90_boot_write_contiguous_cmd(const struct e3b_probe_spec *spec, char **argv, int argc) {
    const char *tag = spec->tag;
    if (argc != 2 || strcmp(argv[1], spec->token) != 0) {
        a90_console_printf("usage: %s %s\r\n", spec->command, spec->token);
        a90_console_printf("%s refused=missing-or-wrong-token\r\n", tag);
        return -EPERM;
    }
    if (spec->len == 0 || (spec->len % E1_SECTOR) != 0) {
        a90_console_printf("%s refused=bad-len len=%u\r\n", tag, spec->len);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s rung=%s mode=read-then-write-identical scope=%s\r\n",
                       tag, spec->rung, spec->scope);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    const char *stop = NULL;
    char sha_before[E1_SHA_HEX];
    uint64_t target_off = 0;
    void *src_buf = NULL;

    int rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        close(rfd);
        goto cleanup;
    }

    {
        unsigned char hdr[E1_SECTOR];
        if (pread(rfd, hdr, sizeof(hdr), 0) != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s header_read=fail errno=%d\r\n", tag, errno);
            stop = "header-read";
            rc = -EIO;
            close(rfd);
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s boot_header=absent stop=no-boot-magic\r\n", tag);
            stop = "no-boot-magic";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s boot_header=bad-page-size=%u stop=bad-page-size\r\n",
                               tag, page_size);
            stop = "bad-page-size";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s boot_header=unsupported-version=%u stop=unsupported-header\r\n",
                               tag, hver);
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
        a90_console_printf("%s boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);

        uint64_t slack_start = e1_round_up(used_len, E1_SECTOR);
        uint64_t slack_end = E1_BOOT_SIZE_BYTES - E1_FOOTER_GUARD;
        a90_console_printf("%s slack_start=%llu slack_end=%llu footer_guard=%llu\r\n",
                           tag, (unsigned long long)slack_start, (unsigned long long)slack_end,
                           (unsigned long long)E1_FOOTER_GUARD);
        if (slack_start + spec->len > slack_end) {
            a90_console_printf("%s stop=no-contiguous-slack len=%u\r\n", tag, spec->len);
            stop = "no-contiguous-slack";
            rc = -ENOSPC;
            close(rfd);
            goto cleanup;
        }

        target_off = slack_start;
        if (posix_memalign(&src_buf, E1_SECTOR, spec->len) != 0 || src_buf == NULL) {
            a90_console_printf("%s source_align=fail\r\n", tag);
            stop = "source-align";
            rc = -ENOMEM;
            close(rfd);
            goto cleanup;
        }
        ssize_t rd = pread(rfd, src_buf, spec->len, (off_t)target_off);
        if (rd != (ssize_t)spec->len) {
            a90_console_printf("%s source_read_rc=%ld errno=%d\r\n", tag, (long)rd, errno);
            stop = "source-read";
            rc = (rd < 0) ? -errno : -EIO;
            close(rfd);
            goto cleanup;
        }
        const unsigned char *bytes = (const unsigned char *)src_buf;
        uint64_t nonzero_bytes = 0;
        unsigned nonzero_sectors = 0;
        unsigned zero_sectors = 0;
        for (uint32_t sector = 0; sector < spec->len / E1_SECTOR; ++sector) {
            const unsigned char *base = bytes + ((size_t)sector * E1_SECTOR);
            int sector_nonzero = 0;
            for (uint32_t i = 0; i < E1_SECTOR; ++i) {
                if (base[i] != 0) {
                    nonzero_bytes++;
                    sector_nonzero = 1;
                }
            }
            if (sector_nonzero) {
                nonzero_sectors++;
            } else {
                zero_sectors++;
            }
        }
        a90_console_printf("%s target_off=%llu len=%u nonzero_bytes=%llu nonzero_sectors=%u zero_sectors=%u\r\n",
                           tag, (unsigned long long)target_off, spec->len,
                           (unsigned long long)nonzero_bytes, nonzero_sectors, zero_sectors);
        if (spec->require_nonzero && nonzero_bytes == 0) {
            a90_console_printf("%s stop=no-nonzero-in-target\r\n", tag);
            stop = "no-nonzero-in-target";
            rc = -ENODATA;
            close(rfd);
            goto cleanup;
        }
    }
    close(rfd);

    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_before);
        if (sr != 0) {
            a90_console_printf("%s sha_before=fail rc=%d\r\n", tag, sr);
            stop = "sha-before";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("%s full_sha_before=%s\r\n", tag, sha_before);
    }

    {
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
            stop = "open-wronly";
            rc = -e;
            goto verify_full;
        }
        if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s stop=identity-wfd\r\n", tag);
            stop = "identity-wfd";
            rc = -EPERM;
            close(wfd);
            goto verify_full;
        }
        if (!e_pwrite_exact(tag, wfd, src_buf, spec->len, target_off, 0, 0, &stop, &rc)) {
            close(wfd);
            goto verify_full;
        }
        if (fsync(wfd) != 0) {
            a90_console_printf("%s fsync=fail errno=%d\r\n", tag, errno);
            stop = "fsync";
            rc = -EIO;
            close(wfd);
            goto verify_full;
        }
        close(wfd);
        a90_console_printf("%s pwrite_count=1 pwrite=ok fsync=ok\r\n", tag);
    }

    {
        int dfd = open(node, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
        if (dfd < 0) {
            a90_console_printf("%s odirect_open=fail errno=%d\r\n", tag, errno);
            if (!stop) { stop = "odirect-open"; rc = -EIO; }
        } else if (!e1_confirm(tag, dfd, maj, min, 0)) {
            a90_console_printf("%s stop=identity-dfd\r\n", tag);
            if (!stop) { stop = "identity-dfd"; rc = -EPERM; }
            close(dfd);
        } else {
            void *readback = NULL;
            if (posix_memalign(&readback, E1_SECTOR, spec->len) != 0 || readback == NULL) {
                a90_console_printf("%s odirect_align=fail\r\n", tag);
                if (!stop) { stop = "odirect-align"; rc = -ENOMEM; }
            } else {
                ssize_t rr = pread(dfd, readback, spec->len, (off_t)target_off);
                int region_match = (rr == (ssize_t)spec->len) &&
                                   memcmp(readback, src_buf, spec->len) == 0;
                a90_console_printf("%s readback_rc=%ld region_match=%d\r\n",
                                   tag, (long)rr, region_match);
                a90_console_printf("%s region_match_all=%d\r\n", tag, region_match);
                if (!region_match && !stop) { stop = "region-mismatch"; rc = -EIO; }
                free(readback);
            }
            close(dfd);
        }
    }

verify_full:;
    {
        char sha_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_after);
        if (sr != 0) {
            a90_console_printf("%s sha_after=fail rc=%d\r\n", tag, sr);
            if (!stop) { stop = "sha-after"; rc = sr; }
        } else {
            int full_match = strcmp(sha_before, sha_after) == 0;
            a90_console_printf("%s full_sha_after=%s\r\n", tag, sha_after);
            a90_console_printf("%s full_match=%d\r\n", tag, full_match);
            if (!full_match && !stop) { stop = "full-partition-changed"; rc = -EIO; }
        }
    }

cleanup:
    if (src_buf != NULL) {
        free(src_buf);
    }
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s result=ok pwrite-permitted-identity-verified\r\n", tag);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

static int a90_boot_write_fixed_cmd(const struct e_fixed_probe_spec *spec, char **argv, int argc) {
    const char *tag = spec->tag;
    if (argc != 2 || strcmp(argv[1], spec->token) != 0) {
        a90_console_printf("usage: %s %s\r\n", spec->command, spec->token);
        a90_console_printf("%s refused=missing-or-wrong-token\r\n", tag);
        return -EPERM;
    }
    if (spec->len == 0 || (spec->len % E1_SECTOR) != 0 || (spec->off % E1_SECTOR) != 0 ||
        spec->off + spec->len > E1_BOOT_SIZE_BYTES) {
        a90_console_printf("%s refused=bad-range off=%llu len=%u\r\n",
                           tag, (unsigned long long)spec->off, spec->len);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s rung=%s mode=read-then-write-identical scope=%s\r\n",
                       tag, spec->rung, spec->scope);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    const char *stop = NULL;
    char sha_before[E1_SHA_HEX];
    char source_sha[E1_SHA_HEX];
    void *src_buf = NULL;

    if (posix_memalign(&src_buf, E1_SECTOR, spec->len) != 0 || src_buf == NULL) {
        a90_console_printf("%s source_align=fail\r\n", tag);
        stop = "source-align";
        rc = -ENOMEM;
        goto cleanup;
    }

    int rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        close(rfd);
        goto cleanup;
    }
    ssize_t rd = pread(rfd, src_buf, spec->len, (off_t)spec->off);
    if (rd != (ssize_t)spec->len) {
        a90_console_printf("%s source_read_rc=%ld errno=%d\r\n", tag, (long)rd, errno);
        stop = "source-read";
        rc = (rd < 0) ? -errno : -EIO;
        close(rfd);
        goto cleanup;
    }
    const unsigned char *bytes = (const unsigned char *)src_buf;
    if (spec->require_android_magic && memcmp(bytes, "ANDROID!", 8) != 0) {
        a90_console_printf("%s boot_header=absent stop=no-boot-magic\r\n", tag);
        stop = "no-boot-magic";
        rc = -EINVAL;
        close(rfd);
        goto cleanup;
    }
    if (spec->require_android_magic) {
        uint32_t page_size = e1_rd_u32le(bytes, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s boot_header=bad-page-size=%u stop=bad-page-size\r\n",
                               tag, page_size);
            stop = "bad-page-size";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(bytes, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s boot_header=unsupported-version=%u stop=unsupported-header\r\n",
                               tag, hver);
            stop = "unsupported-header";
            rc = -EINVAL;
            close(rfd);
            goto cleanup;
        }
        uint64_t used_len = (uint64_t)page_size
                          + e1_round_up(e1_rd_u32le(bytes, AH_KERNEL_SIZE), page_size)
                          + e1_round_up(e1_rd_u32le(bytes, AH_RAMDISK_SIZE), page_size)
                          + e1_round_up(e1_rd_u32le(bytes, AH_SECOND_SIZE), page_size);
        if (hver >= 1) {
            used_len += e1_round_up(e1_rd_u32le(bytes, AH_RECOVERY_DTBO_SIZE), page_size);
        }
        if (hver >= 2) {
            used_len += e1_round_up(e1_rd_u32le(bytes, AH_DTB_SIZE), page_size);
        }
        a90_console_printf("%s boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
    }
    close(rfd);

    e1_sha256_bytes(bytes, spec->len, source_sha);
    a90_console_printf("%s target_off=%llu len=%u header_magic=%s source_sha=%s\r\n",
                       tag, (unsigned long long)spec->off, spec->len,
                       spec->require_android_magic ? "ANDROID" : "unchecked", source_sha);

    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_before);
        if (sr != 0) {
            a90_console_printf("%s sha_before=fail rc=%d\r\n", tag, sr);
            stop = "sha-before";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("%s full_sha_before=%s\r\n", tag, sha_before);
    }

    {
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
            stop = "open-wronly";
            rc = -e;
            goto verify_full;
        }
        if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s stop=identity-wfd\r\n", tag);
            stop = "identity-wfd";
            rc = -EPERM;
            close(wfd);
            goto verify_full;
        }
        if (!e_pwrite_exact(tag, wfd, src_buf, spec->len, spec->off, 0, 0, &stop, &rc)) {
            close(wfd);
            goto verify_full;
        }
        if (fsync(wfd) != 0) {
            a90_console_printf("%s fsync=fail errno=%d\r\n", tag, errno);
            stop = "fsync";
            rc = -EIO;
            close(wfd);
            goto verify_full;
        }
        close(wfd);
        a90_console_printf("%s pwrite_count=1 pwrite=ok fsync=ok\r\n", tag);
    }

    {
        int dfd = open(node, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
        if (dfd < 0) {
            a90_console_printf("%s odirect_open=fail errno=%d\r\n", tag, errno);
            if (!stop) { stop = "odirect-open"; rc = -EIO; }
        } else if (!e1_confirm(tag, dfd, maj, min, 0)) {
            a90_console_printf("%s stop=identity-dfd\r\n", tag);
            if (!stop) { stop = "identity-dfd"; rc = -EPERM; }
            close(dfd);
        } else {
            void *readback = NULL;
            if (posix_memalign(&readback, E1_SECTOR, spec->len) != 0 || readback == NULL) {
                a90_console_printf("%s odirect_align=fail\r\n", tag);
                if (!stop) { stop = "odirect-align"; rc = -ENOMEM; }
            } else {
                char readback_sha[E1_SHA_HEX];
                ssize_t rr = pread(dfd, readback, spec->len, (off_t)spec->off);
                int region_match = (rr == (ssize_t)spec->len) &&
                                   memcmp(readback, src_buf, spec->len) == 0;
                if (rr == (ssize_t)spec->len) {
                    e1_sha256_bytes((const unsigned char *)readback, spec->len, readback_sha);
                } else {
                    snprintf(readback_sha, sizeof(readback_sha), "unavailable");
                }
                a90_console_printf("%s readback_rc=%ld region_match=%d readback_sha=%s\r\n",
                                   tag, (long)rr, region_match, readback_sha);
                a90_console_printf("%s sector_sha_match=%d\r\n",
                                   tag, strcmp(source_sha, readback_sha) == 0);
                a90_console_printf("%s region_match_all=%d\r\n", tag, region_match);
                if (!region_match && !stop) { stop = "region-mismatch"; rc = -EIO; }
                free(readback);
            }
            close(dfd);
        }
    }

verify_full:;
    {
        char sha_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_after);
        if (sr != 0) {
            a90_console_printf("%s sha_after=fail rc=%d\r\n", tag, sr);
            if (!stop) { stop = "sha-after"; rc = sr; }
        } else {
            int full_match = strcmp(sha_before, sha_after) == 0;
            a90_console_printf("%s full_sha_after=%s\r\n", tag, sha_after);
            a90_console_printf("%s full_match=%d\r\n", tag, full_match);
            if (!full_match && !stop) { stop = "full-partition-changed"; rc = -EIO; }
        }
    }

cleanup:
    if (src_buf != NULL) {
        free(src_buf);
    }
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s result=ok pwrite-permitted-identity-verified\r\n", tag);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

static int a90_boot_write_stream_cmd(const struct e_stream_probe_spec *spec, char **argv, int argc) {
    const char *tag = spec->tag;
    if (argc != 2 || strcmp(argv[1], spec->token) != 0) {
        a90_console_printf("usage: %s %s\r\n", spec->command, spec->token);
        a90_console_printf("%s refused=missing-or-wrong-token\r\n", tag);
        return -EPERM;
    }
    if (spec->len != E1_BOOT_SIZE_BYTES || spec->chunk_len == 0 ||
        (spec->chunk_len % E1_SECTOR) != 0 || (spec->len % spec->chunk_len) != 0) {
        a90_console_printf("%s refused=bad-stream len=%llu chunk_len=%u\r\n",
                           tag, (unsigned long long)spec->len, spec->chunk_len);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s rung=%s mode=read-then-write-identical scope=%s\r\n",
                       tag, spec->rung, spec->scope);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    const char *stop = NULL;
    char sha_before[E1_SHA_HEX];
    char sha_after[E1_SHA_HEX];
    char source_sha[E1_SHA_HEX];
    int have_sha_before = 0;
    int rfd = -1;
    int wfd = -1;
    void *chunk = NULL;
    unsigned wrote = 0;

    rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        goto cleanup;
    }

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(rfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s header_read=fail rc=%ld errno=%d\r\n", tag, (long)rd, errno);
            stop = "header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (spec->require_android_magic && memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s boot_header=absent stop=no-boot-magic\r\n", tag);
            stop = "no-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s boot_header=bad-page-size=%u stop=bad-page-size\r\n",
                               tag, page_size);
            stop = "bad-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s boot_header=unsupported-version=%u stop=unsupported-header\r\n",
                               tag, hver);
            stop = "unsupported-header";
            rc = -EINVAL;
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
        a90_console_printf("%s boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
    }

    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_before);
        if (sr != 0) {
            a90_console_printf("%s sha_before=fail rc=%d\r\n", tag, sr);
            stop = "sha-before";
            rc = sr;
            goto cleanup;
        }
        have_sha_before = 1;
        a90_console_printf("%s full_sha_before=%s\r\n", tag, sha_before);
    }

    {
        int sr = e1_fd_sha_stream(rfd, spec->len, source_sha);
        if (sr != 0) {
            a90_console_printf("%s source_sha=fail rc=%d\r\n", tag, sr);
            stop = "source-sha";
            rc = sr;
            goto cleanup;
        }
        int source_match_before = strcmp(source_sha, sha_before) == 0;
        a90_console_printf("%s source_sha=%s source_match_before=%d\r\n",
                           tag, source_sha, source_match_before);
        if (!source_match_before) {
            stop = "source-before-mismatch";
            rc = -EIO;
            goto cleanup;
        }
    }

    wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (wfd < 0) {
        int e = errno;
        a90_console_printf("%s open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-wronly";
        rc = -e;
        goto verify_full;
    }
    if (!e1_confirm(tag, wfd, maj, min, 0)) {
        a90_console_printf("%s stop=identity-wfd\r\n", tag);
        stop = "identity-wfd";
        rc = -EPERM;
        goto verify_full;
    }
    if (posix_memalign(&chunk, E1_SECTOR, spec->chunk_len) != 0 || chunk == NULL) {
        a90_console_printf("%s chunk_align=fail\r\n", tag);
        stop = "chunk-align";
        rc = -ENOMEM;
        goto verify_full;
    }

    unsigned expected_chunks = (unsigned)(spec->len / spec->chunk_len);
    a90_console_printf("%s target_off=0 len=%llu chunk_len=%u expected_chunks=%u\r\n",
                       tag, (unsigned long long)spec->len, spec->chunk_len, expected_chunks);
    for (uint64_t off = 0; off < spec->len; off += spec->chunk_len) {
        ssize_t rd = pread(rfd, chunk, spec->chunk_len, (off_t)off);
        if (rd != (ssize_t)spec->chunk_len) {
            a90_console_printf("%s chunk%u_read_rc=%ld off=%llu errno=%d\r\n",
                               tag, wrote, (long)rd, (unsigned long long)off, errno);
            stop = "chunk-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto verify_full;
        }
        if (!e_pwrite_exact(tag, wfd, chunk, spec->chunk_len, off, 1, wrote, &stop, &rc)) {
            goto verify_full;
        }
        wrote++;
    }
    if (fsync(wfd) != 0) {
        a90_console_printf("%s fsync=fail errno=%d\r\n", tag, errno);
        stop = "fsync";
        rc = -EIO;
        goto verify_full;
    }
    close(wfd);
    wfd = -1;
    a90_console_printf("%s pwrite_count=%u pwrite=ok fsync=ok\r\n", tag, wrote);

verify_full:
    if (have_sha_before) {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, sha_after);
        if (sr != 0) {
            a90_console_printf("%s sha_after=fail rc=%d\r\n", tag, sr);
            if (!stop) { stop = "sha-after"; rc = sr; }
        } else {
            int full_match = strcmp(sha_before, sha_after) == 0;
            a90_console_printf("%s full_sha_after=%s\r\n", tag, sha_after);
            a90_console_printf("%s full_match=%d\r\n", tag, full_match);
            a90_console_printf("%s region_match_all=%d\r\n", tag, full_match);
            if (!full_match && !stop) { stop = "full-partition-changed"; rc = -EIO; }
        }
    }

cleanup:
    if (chunk != NULL) {
        free(chunk);
    }
    if (wfd >= 0) {
        close(wfd);
    }
    if (rfd >= 0) {
        close(rfd);
    }
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s result=ok pwrite-permitted-identity-verified\r\n", tag);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

int a90_boot_flash_plan_cmd(char **argv, int argc) {
    const char *tag = F0_TAG;
    if (argc != 4) {
        a90_console_printf("usage: %s <candidate-path> <expected-sha256> <expected-version>\r\n",
                           F0_COMMAND);
        a90_console_printf("%s refused=bad-argc argc=%d\r\n", tag, argc);
        return -EINVAL;
    }
    const char *candidate_path = argv[1];
    const char *expected_sha = argv[2];
    const char *expected_version = argv[3];
    if (!f0_stage_path_allowed(candidate_path)) {
        a90_console_printf("%s refused=path-outside-approved-staging path=%s\r\n",
                           tag, candidate_path);
        return -EPERM;
    }
    if (!f0_hex64_is_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", tag);
        return -EINVAL;
    }
    size_t marker_len = strlen(expected_version);
    if (marker_len == 0 || marker_len > F0_MAX_MARKER) {
        a90_console_printf("%s refused=bad-expected-version-len len=%u\r\n",
                           tag, (unsigned)marker_len);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s mode=read-only-source-plan would_write=0\r\n", tag);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    const char *stop = NULL;
    int rfd = -1;
    int cfd = -1;
    char before_sha[E1_SHA_HEX];
    char candidate_sha[E1_SHA_HEX];
    char target_sha[E1_SHA_HEX];
    char current_sha[E1_SHA_HEX];

    rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_boot_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-boot-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        goto cleanup;
    }

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(rfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s current_header_read=fail rc=%ld errno=%d\r\n",
                               tag, (long)rd, errno);
            stop = "current-header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s current_boot_header=absent stop=no-current-boot-magic\r\n", tag);
            stop = "no-current-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s current_boot_header=bad-page-size=%u stop=bad-current-page-size\r\n",
                               tag, page_size);
            stop = "bad-current-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s current_boot_header=unsupported-version=%u stop=bad-current-header\r\n",
                               tag, hver);
            stop = "bad-current-header";
            rc = -EINVAL;
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
        a90_console_printf("%s current_boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
    }

    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, before_sha);
        if (sr != 0) {
            a90_console_printf("%s before_full_sha=fail rc=%d\r\n", tag, sr);
            stop = "before-sha";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("%s before_full_sha=%s\r\n", tag, before_sha);
    }

    cfd = open(candidate_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (cfd < 0) {
        int e = errno;
        a90_console_printf("%s candidate_open=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "candidate-open";
        rc = -e;
        goto cleanup;
    }
    struct stat cst;
    if (fstat(cfd, &cst) != 0) {
        int e = errno;
        a90_console_printf("%s candidate_fstat=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "candidate-fstat";
        rc = -e;
        goto cleanup;
    }
    if (!S_ISREG(cst.st_mode)) {
        a90_console_printf("%s candidate_regular=0\r\n", tag);
        stop = "candidate-not-regular";
        rc = -EINVAL;
        goto cleanup;
    }
    uint64_t candidate_size = (uint64_t)cst.st_size;
    if (candidate_size < E1_SECTOR || candidate_size > E1_BOOT_SIZE_BYTES) {
        a90_console_printf("%s candidate_size=%llu stop=bad-candidate-size\r\n",
                           tag, (unsigned long long)candidate_size);
        stop = "bad-candidate-size";
        rc = -EINVAL;
        goto cleanup;
    }
    a90_console_printf("%s candidate_path=%s\r\n", tag, candidate_path);
    a90_console_printf("%s candidate_size=%llu\r\n", tag, (unsigned long long)candidate_size);

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(cfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s candidate_header_read=fail rc=%ld errno=%d\r\n",
                               tag, (long)rd, errno);
            stop = "candidate-header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s candidate_header=absent stop=no-candidate-boot-magic\r\n", tag);
            stop = "no-candidate-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s candidate_header=bad-page-size=%u stop=bad-candidate-page-size\r\n",
                               tag, page_size);
            stop = "bad-candidate-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s candidate_header=unsupported-version=%u stop=bad-candidate-header\r\n",
                               tag, hver);
            stop = "bad-candidate-header";
            rc = -EINVAL;
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
        a90_console_printf("%s candidate_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
        if (used_len > candidate_size) {
            a90_console_printf("%s candidate_used_within_file=0\r\n", tag);
            stop = "candidate-used-len";
            rc = -EINVAL;
            goto cleanup;
        }
        a90_console_printf("%s candidate_used_within_file=1\r\n", tag);
    }

    {
        int marker_found = 0;
        int sr = f0_scan_candidate(cfd, candidate_size, expected_version,
                                   candidate_sha, &marker_found);
        if (sr != 0) {
            a90_console_printf("%s candidate_sha=fail rc=%d\r\n", tag, sr);
            stop = "candidate-sha";
            rc = sr;
            goto cleanup;
        }
        int sha_match = f0_sha_equal(candidate_sha, expected_sha);
        a90_console_printf("%s candidate_sha=%s expected_sha_match=%d\r\n",
                           tag, candidate_sha, sha_match);
        a90_console_printf("%s expected_version=%s version_marker_found=%d\r\n",
                           tag, expected_version, marker_found);
        if (!sha_match) {
            stop = "candidate-sha-mismatch";
            rc = -EIO;
            goto cleanup;
        }
        if (!marker_found) {
            stop = "version-marker-missing";
            rc = -ENOENT;
            goto cleanup;
        }
    }

    {
        uint64_t changed_bytes = 0;
        unsigned changed_chunks = 0;
        int pr = f0_compute_target_plan(rfd, cfd, candidate_size, target_sha, current_sha,
                                        &changed_bytes, &changed_chunks);
        if (pr != 0) {
            a90_console_printf("%s target_plan=fail rc=%d\r\n", tag, pr);
            stop = "target-plan";
            rc = pr;
            goto cleanup;
        }
        int current_match = strcmp(current_sha, before_sha) == 0;
        a90_console_printf("%s current_stream_sha=%s current_match_before=%d\r\n",
                           tag, current_sha, current_match);
        a90_console_printf("%s target_full_sha=%s\r\n", tag, target_sha);
        a90_console_printf("%s changed_chunks=%u changed_bytes=%llu chunk_len=%u\r\n",
                           tag, changed_chunks, (unsigned long long)changed_bytes, E1_STREAM_CHUNK);
        if (!current_match) {
            stop = "current-before-mismatch";
            rc = -EIO;
            goto cleanup;
        }
    }

cleanup:
    if (cfd >= 0) {
        close(cfd);
    }
    if (rfd >= 0) {
        close(rfd);
    }
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    a90_console_printf("%s would_write=0\r\n", tag);
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s result=ok source-plan-only\r\n", tag);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

int a90_boot_flash_f1_cmd(char **argv, int argc) {
    const char *tag = F1_TAG;
    if (argc != 5 || strcmp(argv[1], F1_TOKEN) != 0) {
        a90_console_printf("usage: %s %s <candidate-path> <expected-sha256> <expected-version>\r\n",
                           F1_COMMAND, F1_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n", tag, argc);
        return -EPERM;
    }
    const char *candidate_path = argv[2];
    const char *expected_sha = argv[3];
    const char *expected_version = argv[4];
    if (!f0_stage_path_allowed(candidate_path)) {
        a90_console_printf("%s refused=path-outside-approved-staging path=%s\r\n",
                           tag, candidate_path);
        return -EPERM;
    }
    if (!f0_hex64_is_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", tag);
        return -EINVAL;
    }
    size_t marker_len = strlen(expected_version);
    if (marker_len == 0 || marker_len > F0_MAX_MARKER) {
        a90_console_printf("%s refused=bad-expected-version-len len=%u\r\n",
                           tag, (unsigned)marker_len);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s token=accepted mode=paired-content-roundtrip reboot_candidate=0\r\n", tag);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    int target_rc = 0;
    int restore_rc = 0;
    int target_write_started = 0;
    int target_written = 0;
    int restore_attempted = 0;
    const char *stop = NULL;
    const char *target_stop = NULL;
    const char *restore_stop = NULL;
    int rfd = -1;
    int cfd = -1;
    int sfd = -1;
    char before_sha[E1_SHA_HEX];
    char snapshot_sha[E1_SHA_HEX];
    char snapshot_reopen_sha[E1_SHA_HEX];
    char candidate_sha[E1_SHA_HEX];
    char target_sha[E1_SHA_HEX];
    char current_sha[E1_SHA_HEX];
    uint64_t candidate_size = 0;
    uint64_t changed_bytes = 0;
    unsigned changed_chunks = 0;

    rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_boot_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-boot-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        goto cleanup;
    }

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(rfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s current_header_read=fail rc=%ld errno=%d\r\n",
                               tag, (long)rd, errno);
            stop = "current-header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s current_boot_header=absent stop=no-current-boot-magic\r\n", tag);
            stop = "no-current-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s current_boot_header=bad-page-size=%u stop=bad-current-page-size\r\n",
                               tag, page_size);
            stop = "bad-current-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s current_boot_header=unsupported-version=%u stop=bad-current-header\r\n",
                               tag, hver);
            stop = "bad-current-header";
            rc = -EINVAL;
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
        a90_console_printf("%s current_boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
    }

    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, before_sha);
        if (sr != 0) {
            a90_console_printf("%s before_full_sha=fail rc=%d\r\n", tag, sr);
            stop = "before-sha";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("%s before_full_sha=%s\r\n", tag, before_sha);
    }

    cfd = open(candidate_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (cfd < 0) {
        int e = errno;
        a90_console_printf("%s candidate_open=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "candidate-open";
        rc = -e;
        goto cleanup;
    }
    struct stat cst;
    if (fstat(cfd, &cst) != 0) {
        int e = errno;
        a90_console_printf("%s candidate_fstat=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "candidate-fstat";
        rc = -e;
        goto cleanup;
    }
    if (!S_ISREG(cst.st_mode)) {
        a90_console_printf("%s candidate_regular=0\r\n", tag);
        stop = "candidate-not-regular";
        rc = -EINVAL;
        goto cleanup;
    }
    candidate_size = (uint64_t)cst.st_size;
    if (candidate_size < E1_SECTOR || candidate_size > E1_BOOT_SIZE_BYTES) {
        a90_console_printf("%s candidate_size=%llu stop=bad-candidate-size\r\n",
                           tag, (unsigned long long)candidate_size);
        stop = "bad-candidate-size";
        rc = -EINVAL;
        goto cleanup;
    }
    a90_console_printf("%s candidate_path=%s\r\n", tag, candidate_path);
    a90_console_printf("%s candidate_size=%llu\r\n", tag, (unsigned long long)candidate_size);

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(cfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s candidate_header_read=fail rc=%ld errno=%d\r\n",
                               tag, (long)rd, errno);
            stop = "candidate-header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s candidate_header=absent stop=no-candidate-boot-magic\r\n", tag);
            stop = "no-candidate-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s candidate_header=bad-page-size=%u stop=bad-candidate-page-size\r\n",
                               tag, page_size);
            stop = "bad-candidate-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s candidate_header=unsupported-version=%u stop=bad-candidate-header\r\n",
                               tag, hver);
            stop = "bad-candidate-header";
            rc = -EINVAL;
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
        a90_console_printf("%s candidate_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
        if (used_len > candidate_size) {
            a90_console_printf("%s candidate_used_within_file=0\r\n", tag);
            stop = "candidate-used-len";
            rc = -EINVAL;
            goto cleanup;
        }
        a90_console_printf("%s candidate_used_within_file=1\r\n", tag);
    }

    {
        int marker_found = 0;
        int sr = f0_scan_candidate(cfd, candidate_size, expected_version,
                                   candidate_sha, &marker_found);
        if (sr != 0) {
            a90_console_printf("%s candidate_sha=fail rc=%d\r\n", tag, sr);
            stop = "candidate-sha";
            rc = sr;
            goto cleanup;
        }
        int sha_match = f0_sha_equal(candidate_sha, expected_sha);
        a90_console_printf("%s candidate_sha=%s expected_sha_match=%d\r\n",
                           tag, candidate_sha, sha_match);
        a90_console_printf("%s expected_version=%s version_marker_found=%d\r\n",
                           tag, expected_version, marker_found);
        if (!sha_match) {
            stop = "candidate-sha-mismatch";
            rc = -EIO;
            goto cleanup;
        }
        if (!marker_found) {
            stop = "version-marker-missing";
            rc = -ENOENT;
            goto cleanup;
        }
    }

    {
        int pr = f0_compute_target_plan(rfd, cfd, candidate_size, target_sha, current_sha,
                                        &changed_bytes, &changed_chunks);
        if (pr != 0) {
            a90_console_printf("%s target_plan=fail rc=%d\r\n", tag, pr);
            stop = "target-plan";
            rc = pr;
            goto cleanup;
        }
        int current_match = strcmp(current_sha, before_sha) == 0;
        a90_console_printf("%s current_stream_sha=%s current_match_before=%d\r\n",
                           tag, current_sha, current_match);
        a90_console_printf("%s target_full_sha=%s\r\n", tag, target_sha);
        a90_console_printf("%s changed_chunks=%u changed_bytes=%llu chunk_len=%u\r\n",
                           tag, changed_chunks, (unsigned long long)changed_bytes, E1_STREAM_CHUNK);
        if (!current_match) {
            stop = "current-before-mismatch";
            rc = -EIO;
            goto cleanup;
        }
        if (changed_bytes == 0) {
            stop = "no-content-change";
            rc = -ENODATA;
            goto cleanup;
        }
    }

    {
        int sr = f1_capture_before_snapshot(tag, rfd, before_sha, F1_SNAPSHOT_PATH,
                                            F1_SNAPSHOT_TMP, snapshot_sha);
        if (sr != 0) {
            a90_console_printf("%s snapshot_capture=fail rc=%d\r\n", tag, sr);
            stop = "snapshot-capture";
            rc = sr;
            goto cleanup;
        }
    }

    sfd = open(F1_SNAPSHOT_PATH, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (sfd < 0) {
        int e = errno;
        a90_console_printf("%s snapshot_reopen=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "snapshot-reopen";
        rc = -e;
        goto cleanup;
    }
    {
        int sr = e1_fd_sha_stream(sfd, E1_BOOT_SIZE_BYTES, snapshot_reopen_sha);
        int snapshot_reopen_match = (sr == 0) && f0_sha_equal(snapshot_reopen_sha, before_sha);
        a90_console_printf("%s snapshot_reopen_sha=%s snapshot_reopen_match_before=%d\r\n",
                           tag, sr == 0 ? snapshot_reopen_sha : "unavailable", snapshot_reopen_match);
        if (!snapshot_reopen_match) {
            stop = "snapshot-reopen-sha";
            rc = (sr != 0) ? sr : -EIO;
            goto cleanup;
        }
    }

    {
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s target_open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
            target_stop = "target-open-wronly";
            target_rc = -e;
        } else if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s target_stop=identity-wfd\r\n", tag);
            target_stop = "target-identity-wfd";
            target_rc = -EPERM;
            close(wfd);
        } else {
            target_write_started = 1;
            target_rc = f1_write_full_image_chunks(tag, "target", wfd, sfd, cfd, candidate_size,
                                                   &target_stop, &target_rc);
            if (target_rc == 0) {
                target_written = 1;
            }
            close(wfd);
        }
    }
    if (target_rc == 0) {
        char target_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, target_after);
        int target_match = (sr == 0) && f0_sha_equal(target_after, target_sha);
        a90_console_printf("%s target_full_sha_after=%s target_full_match=%d\r\n",
                           tag, sr == 0 ? target_after : "unavailable", target_match);
        if (!target_match) {
            target_stop = "target-full-sha-mismatch";
            target_rc = (sr != 0) ? sr : -EIO;
        }
    }

    if (!target_write_started) {
        a90_console_printf("%s restore_skipped=no-target-pwrite-started\r\n", tag);
    } else {
        restore_attempted = 1;
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s restore_open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
            restore_stop = "restore-open-wronly";
            restore_rc = -e;
        } else if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s restore_stop=identity-wfd\r\n", tag);
            restore_stop = "restore-identity-wfd";
            restore_rc = -EPERM;
            close(wfd);
        } else {
            restore_rc = f1_write_full_image_chunks(tag, "restore", wfd, sfd, -1, 0,
                                                    &restore_stop, &restore_rc);
            close(wfd);
        }
    }
    if (restore_attempted && restore_rc == 0) {
        char restore_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, restore_after);
        int restore_match = (sr == 0) && f0_sha_equal(restore_after, before_sha);
        a90_console_printf("%s restore_full_sha_after=%s restore_full_match=%d\r\n",
                           tag, sr == 0 ? restore_after : "unavailable", restore_match);
        if (!restore_match) {
            restore_stop = "restore-full-sha-mismatch";
            restore_rc = (sr != 0) ? sr : -EIO;
        }
    }
    a90_console_printf("%s target_written=%d restore_attempted=%d\r\n",
                       tag, target_written, restore_attempted);
    if (target_rc != 0) {
        stop = target_stop ? target_stop : "target-write";
        rc = target_rc;
    }
    if (restore_rc != 0) {
        stop = restore_stop ? restore_stop : "restore-write";
        rc = restore_rc;
    }

cleanup:
    if (sfd >= 0) {
        close(sfd);
    }
    if (cfd >= 0) {
        close(cfd);
    }
    if (rfd >= 0) {
        close(rfd);
    }
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    unlink(F1_SNAPSHOT_TMP);
    if (rc == 0) {
        if (unlink(F1_SNAPSHOT_PATH) == 0) {
            a90_console_printf("%s snapshot_cleaned=1\r\n", tag);
        } else if (errno != ENOENT) {
            a90_console_printf("%s snapshot_cleaned=0 errno=%d\r\n", tag, errno);
        }
    } else {
        a90_console_printf("%s snapshot_retained=%s\r\n", tag, F1_SNAPSHOT_PATH);
    }
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s result=ok paired-roundtrip-restored\r\n", tag);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

static int a90_boot_flash_leave_target_cmd(const struct f_leave_target_spec *spec,
                                           char **argv, int argc) {
    const char *tag = spec->tag;
    if (argc != 5 || strcmp(argv[1], spec->token) != 0) {
        a90_console_printf("usage: %s %s <candidate-path> <expected-sha256> <expected-version>\r\n",
                           spec->command, spec->token);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n", tag, argc);
        return -EPERM;
    }
    const char *candidate_path = argv[2];
    const char *expected_sha = argv[3];
    const char *expected_version = argv[4];
    if (!f0_stage_path_allowed(candidate_path)) {
        a90_console_printf("%s refused=path-outside-approved-staging path=%s\r\n",
                           tag, candidate_path);
        return -EPERM;
    }
    if (!f0_hex64_is_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", tag);
        return -EINVAL;
    }
    size_t marker_len = strlen(expected_version);
    if (marker_len == 0 || marker_len > F0_MAX_MARKER) {
        a90_console_printf("%s refused=bad-expected-version-len len=%u\r\n",
                           tag, (unsigned)marker_len);
        return -EINVAL;
    }

    a90_console_printf("%s begin\r\n", tag);
    a90_console_printf("%s token=accepted mode=%s reboot_candidate=host-controlled\r\n",
                       tag, spec->mode);

    char name[256];
    unsigned maj = 0, min = 0;
    int n = e1_resolve_boot(name, sizeof(name), &maj, &min);
    if (n != 1) {
        a90_console_printf("%s resolve=%s\r\n", tag, (n <= 0) ? "none" : "ambiguous");
        a90_console_printf("%s stop=resolve\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -ENODEV);
        return -ENODEV;
    }
    char node[PATH_MAX];
    snprintf(node, sizeof(node), "/dev/block/%s", name);
    a90_console_printf("%s target_node=%s resolve=sysfs-partname\r\n", tag, node);

    int created = 0;
    int mrc = mknod(node, S_IFBLK | 0600, makedev(maj, min));
    if (mrc == 0) {
        created = 1;
    } else if (errno != EEXIST) {
        int e = errno;
        a90_console_printf("%s mknod=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        a90_console_printf("%s stop=mknod\r\n", tag);
        a90_console_printf("%s end rc=%d\r\n", tag, -e);
        return -e;
    }

    int rc = 0;
    int target_rc = 0;
    int restore_rc = 0;
    int target_write_started = 0;
    int target_written = 0;
    int restore_attempted = 0;
    const char *stop = NULL;
    const char *target_stop = NULL;
    const char *restore_stop = NULL;
    int rfd = -1;
    int cfd = -1;
    int sfd = -1;
    char before_sha[E1_SHA_HEX];
    char snapshot_sha[E1_SHA_HEX];
    char snapshot_reopen_sha[E1_SHA_HEX];
    char candidate_sha[E1_SHA_HEX];
    char target_sha[E1_SHA_HEX];
    char current_sha[E1_SHA_HEX];
    uint64_t candidate_size = 0;
    uint64_t changed_bytes = 0;
    unsigned changed_chunks = 0;

    rfd = open(node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (rfd < 0) {
        int e = errno;
        a90_console_printf("%s open_boot_rdonly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "open-boot-rdonly";
        rc = -e;
        goto cleanup;
    }
    if (!e1_confirm(tag, rfd, maj, min, 1)) {
        stop = "identity-rfd";
        rc = -EPERM;
        goto cleanup;
    }

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(rfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s current_header_read=fail rc=%ld errno=%d\r\n",
                               tag, (long)rd, errno);
            stop = "current-header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s current_boot_header=absent stop=no-current-boot-magic\r\n", tag);
            stop = "no-current-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s current_boot_header=bad-page-size=%u stop=bad-current-page-size\r\n",
                               tag, page_size);
            stop = "bad-current-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s current_boot_header=unsupported-version=%u stop=bad-current-header\r\n",
                               tag, hver);
            stop = "bad-current-header";
            rc = -EINVAL;
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
        a90_console_printf("%s current_boot_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
    }

    {
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, before_sha);
        if (sr != 0) {
            a90_console_printf("%s before_full_sha=fail rc=%d\r\n", tag, sr);
            stop = "before-sha";
            rc = sr;
            goto cleanup;
        }
        a90_console_printf("%s before_full_sha=%s\r\n", tag, before_sha);
    }

    cfd = open(candidate_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (cfd < 0) {
        int e = errno;
        a90_console_printf("%s candidate_open=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "candidate-open";
        rc = -e;
        goto cleanup;
    }
    struct stat cst;
    if (fstat(cfd, &cst) != 0) {
        int e = errno;
        a90_console_printf("%s candidate_fstat=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "candidate-fstat";
        rc = -e;
        goto cleanup;
    }
    if (!S_ISREG(cst.st_mode)) {
        a90_console_printf("%s candidate_regular=0\r\n", tag);
        stop = "candidate-not-regular";
        rc = -EINVAL;
        goto cleanup;
    }
    candidate_size = (uint64_t)cst.st_size;
    if (candidate_size < E1_SECTOR || candidate_size > E1_BOOT_SIZE_BYTES) {
        a90_console_printf("%s candidate_size=%llu stop=bad-candidate-size\r\n",
                           tag, (unsigned long long)candidate_size);
        stop = "bad-candidate-size";
        rc = -EINVAL;
        goto cleanup;
    }
    a90_console_printf("%s candidate_path=%s\r\n", tag, candidate_path);
    a90_console_printf("%s candidate_size=%llu\r\n", tag, (unsigned long long)candidate_size);

    {
        unsigned char hdr[E1_SECTOR];
        ssize_t rd = pread(cfd, hdr, sizeof(hdr), 0);
        if (rd != (ssize_t)sizeof(hdr)) {
            a90_console_printf("%s candidate_header_read=fail rc=%ld errno=%d\r\n",
                               tag, (long)rd, errno);
            stop = "candidate-header-read";
            rc = (rd < 0) ? -errno : -EIO;
            goto cleanup;
        }
        if (memcmp(hdr, "ANDROID!", 8) != 0) {
            a90_console_printf("%s candidate_header=absent stop=no-candidate-boot-magic\r\n", tag);
            stop = "no-candidate-boot-magic";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t page_size = e1_rd_u32le(hdr, AH_PAGE_SIZE);
        if (page_size < 512 || page_size > (1u << 20)) {
            a90_console_printf("%s candidate_header=bad-page-size=%u stop=bad-candidate-page-size\r\n",
                               tag, page_size);
            stop = "bad-candidate-page-size";
            rc = -EINVAL;
            goto cleanup;
        }
        uint32_t hver = e1_rd_u32le(hdr, AH_HEADER_VERSION);
        if (hver > 2) {
            a90_console_printf("%s candidate_header=unsupported-version=%u stop=bad-candidate-header\r\n",
                               tag, hver);
            stop = "bad-candidate-header";
            rc = -EINVAL;
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
        a90_console_printf("%s candidate_header=ok version=%u page_size=%u used_len=%llu\r\n",
                           tag, hver, page_size, (unsigned long long)used_len);
        if (used_len > candidate_size) {
            a90_console_printf("%s candidate_used_within_file=0\r\n", tag);
            stop = "candidate-used-len";
            rc = -EINVAL;
            goto cleanup;
        }
        a90_console_printf("%s candidate_used_within_file=1\r\n", tag);
    }

    {
        int marker_found = 0;
        int sr = f0_scan_candidate(cfd, candidate_size, expected_version,
                                   candidate_sha, &marker_found);
        if (sr != 0) {
            a90_console_printf("%s candidate_sha=fail rc=%d\r\n", tag, sr);
            stop = "candidate-sha";
            rc = sr;
            goto cleanup;
        }
        int sha_match = f0_sha_equal(candidate_sha, expected_sha);
        a90_console_printf("%s candidate_sha=%s expected_sha_match=%d\r\n",
                           tag, candidate_sha, sha_match);
        a90_console_printf("%s expected_version=%s version_marker_found=%d\r\n",
                           tag, expected_version, marker_found);
        if (!sha_match) {
            stop = "candidate-sha-mismatch";
            rc = -EIO;
            goto cleanup;
        }
        if (!marker_found) {
            stop = "version-marker-missing";
            rc = -ENOENT;
            goto cleanup;
        }
    }

    {
        int pr = f0_compute_target_plan(rfd, cfd, candidate_size, target_sha, current_sha,
                                        &changed_bytes, &changed_chunks);
        if (pr != 0) {
            a90_console_printf("%s target_plan=fail rc=%d\r\n", tag, pr);
            stop = "target-plan";
            rc = pr;
            goto cleanup;
        }
        int current_match = strcmp(current_sha, before_sha) == 0;
        a90_console_printf("%s current_stream_sha=%s current_match_before=%d\r\n",
                           tag, current_sha, current_match);
        a90_console_printf("%s target_full_sha=%s\r\n", tag, target_sha);
        a90_console_printf("%s changed_chunks=%u changed_bytes=%llu chunk_len=%u\r\n",
                           tag, changed_chunks, (unsigned long long)changed_bytes, E1_STREAM_CHUNK);
        if (!current_match) {
            stop = "current-before-mismatch";
            rc = -EIO;
            goto cleanup;
        }
        if (changed_bytes == 0) {
            stop = "no-content-change";
            rc = -ENODATA;
            goto cleanup;
        }
    }

    {
        int sr = f1_capture_before_snapshot(tag, rfd, before_sha, spec->snapshot_path,
                                            spec->snapshot_tmp, snapshot_sha);
        if (sr != 0) {
            a90_console_printf("%s snapshot_capture=fail rc=%d\r\n", tag, sr);
            stop = "snapshot-capture";
            rc = sr;
            goto cleanup;
        }
    }

    sfd = open(spec->snapshot_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (sfd < 0) {
        int e = errno;
        a90_console_printf("%s snapshot_reopen=fail errno=%d (%s)\r\n", tag, e, strerror(e));
        stop = "snapshot-reopen";
        rc = -e;
        goto cleanup;
    }
    {
        int sr = e1_fd_sha_stream(sfd, E1_BOOT_SIZE_BYTES, snapshot_reopen_sha);
        int snapshot_reopen_match = (sr == 0) && f0_sha_equal(snapshot_reopen_sha, before_sha);
        a90_console_printf("%s snapshot_reopen_sha=%s snapshot_reopen_match_before=%d\r\n",
                           tag, sr == 0 ? snapshot_reopen_sha : "unavailable", snapshot_reopen_match);
        if (!snapshot_reopen_match) {
            stop = "snapshot-reopen-sha";
            rc = (sr != 0) ? sr : -EIO;
            goto cleanup;
        }
    }

    {
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s target_open_wronly=fail errno=%d (%s)\r\n", tag, e, strerror(e));
            target_stop = "target-open-wronly";
            target_rc = -e;
        } else if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s target_stop=identity-wfd\r\n", tag);
            target_stop = "target-identity-wfd";
            target_rc = -EPERM;
            close(wfd);
        } else {
            target_write_started = 1;
            target_rc = f1_write_full_image_chunks(tag, "target", wfd, sfd, cfd, candidate_size,
                                                   &target_stop, &target_rc);
            if (target_rc == 0) {
                target_written = 1;
            }
            close(wfd);
        }
    }
    if (target_rc == 0) {
        char target_after[E1_SHA_HEX];
        int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, target_after);
        int target_match = (sr == 0) && f0_sha_equal(target_after, target_sha);
        a90_console_printf("%s target_full_sha_after=%s target_full_match=%d\r\n",
                           tag, sr == 0 ? target_after : "unavailable", target_match);
        if (!target_match) {
            target_stop = "target-full-sha-mismatch";
            target_rc = (sr != 0) ? sr : -EIO;
        }
    }

    if (target_rc != 0 && target_write_started) {
        restore_attempted = 1;
        int wfd = open(node, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (wfd < 0) {
            int e = errno;
            a90_console_printf("%s failure_restore_open_wronly=fail errno=%d (%s)\r\n",
                               tag, e, strerror(e));
            restore_stop = "failure-restore-open-wronly";
            restore_rc = -e;
        } else if (!e1_confirm(tag, wfd, maj, min, 0)) {
            a90_console_printf("%s failure_restore_stop=identity-wfd\r\n", tag);
            restore_stop = "failure-restore-identity-wfd";
            restore_rc = -EPERM;
            close(wfd);
        } else {
            restore_rc = f1_write_full_image_chunks(tag, "failure_restore", wfd, sfd, -1, 0,
                                                    &restore_stop, &restore_rc);
            close(wfd);
        }
        if (restore_rc == 0) {
            char restore_after[E1_SHA_HEX];
            int sr = e1_full_sha_odirect(tag, node, maj, min, E1_BOOT_SIZE_BYTES, restore_after);
            int restore_match = (sr == 0) && f0_sha_equal(restore_after, before_sha);
            a90_console_printf("%s failure_restore_full_sha_after=%s failure_restore_full_match=%d\r\n",
                               tag, sr == 0 ? restore_after : "unavailable", restore_match);
            if (!restore_match) {
                restore_stop = "failure-restore-full-sha-mismatch";
                restore_rc = (sr != 0) ? sr : -EIO;
            }
        }
    } else if (!target_write_started) {
        a90_console_printf("%s restore_skipped=no-target-pwrite-started\r\n", tag);
    } else {
        a90_console_printf("%s %s\r\n", tag, spec->success_restore_skipped_line);
    }
    a90_console_printf("%s target_written=%d restore_attempted=%d\r\n",
                       tag, target_written, restore_attempted);
    if (target_rc != 0) {
        stop = target_stop ? target_stop : "target-write";
        rc = target_rc;
    }
    if (restore_rc != 0) {
        stop = restore_stop ? restore_stop : "failure-restore-write";
        rc = restore_rc;
    }

cleanup:
    if (sfd >= 0) {
        close(sfd);
    }
    if (cfd >= 0) {
        close(cfd);
    }
    if (rfd >= 0) {
        close(rfd);
    }
    if (created) {
        unlink(node);
        a90_console_printf("%s cleaned=1\r\n", tag);
    }
    unlink(spec->snapshot_tmp);
    a90_console_printf("%s snapshot_retained=%s\r\n", tag, spec->snapshot_path);
    if (stop) {
        a90_console_printf("%s stop=%s\r\n", tag, stop);
    } else {
        a90_console_printf("%s reboot_required=1 host_must_reboot_now=1\r\n", tag);
        a90_console_printf("%s %s\r\n", tag, spec->success_result_line);
    }
    a90_console_printf("%s end rc=%d\r\n", tag, rc);
    return rc;
}

int a90_boot_flash_f2_cmd(char **argv, int argc) {
    return a90_boot_flash_leave_target_cmd(&F2_LEAVE_TARGET_SPEC, argv, argc);
}

int a90_boot_flash_f3_cmd(char **argv, int argc) {
    return a90_boot_flash_leave_target_cmd(&F3_LEAVE_TARGET_SPEC, argv, argc);
}

int a90_boot_write_e1_cmd(char **argv, int argc) {
    return a90_boot_write_identity_cmd(&E1_SPEC, argv, argc);
}

int a90_boot_write_e2_cmd(char **argv, int argc) {
    return a90_boot_write_identity_cmd(&E2_SPEC, argv, argc);
}

int a90_boot_write_e3a_cmd(char **argv, int argc) {
    return a90_boot_write_identity_cmd(&E3A_SPEC, argv, argc);
}

int a90_boot_write_e3b_cmd(char **argv, int argc) {
    return a90_boot_write_contiguous_cmd(&E3B_SPEC, argv, argc);
}

int a90_boot_write_e4_cmd(char **argv, int argc) {
    return a90_boot_write_fixed_cmd(&E4_SPEC, argv, argc);
}

int a90_boot_write_e5_cmd(char **argv, int argc) {
    return a90_boot_write_stream_cmd(&E5_SPEC, argv, argc);
}
