/* Fixed-profile ext4 metadata and witness validation; no device I/O. */
#ifndef S22PLUS_NATIVE_EXT4_CORE_V1_H
#define S22PLUS_NATIVE_EXT4_CORE_V1_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define FS1_BLOCK 4096U
#define FS1_FIRST_LBA 12115456ULL
#define FS1_LAST_LBA 62305023ULL
#define FS1_BLOCKS (FS1_LAST_LBA - FS1_FIRST_LBA + 1ULL)
#define FS1_BYTES (FS1_BLOCKS * FS1_BLOCK)
#define FS1_GPT_BLOCKS 62305280ULL
#define FS1_GPT_BYTES (15U * FS1_BLOCK)
#define FS1_COMPAT 0x2cU
#define FS1_INCOMPAT 0x2c2U
#define FS1_RO_COMPAT 0x46bU
#define FS1_WITNESS_NAME ".s22-native-ext4-witness-v1"

static uint16_t fs1_u16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | (uint16_t)p[1] << 8);
}
static uint32_t fs1_u32(const uint8_t *p) {
    return (uint32_t)fs1_u16(p) | (uint32_t)fs1_u16(p + 2) << 16;
}
static uint64_t fs1_u64(const uint8_t *p) {
    return (uint64_t)fs1_u32(p) | (uint64_t)fs1_u32(p + 4) << 32;
}
static uint32_t fs1_crc32c(const uint8_t *p, size_t n) {
    uint32_t value = UINT32_MAX;
    for (size_t i = 0; i < n; ++i) {
        value ^= p[i];
        for (unsigned b = 0; b < 8; ++b)
            value = (value >> 1) ^ ((value & 1U) ? 0x82f63b78U : 0U);
    }
    return value;
}

/* A clean primary superblock is a prerequisite, not whole-filesystem proof.
 * The fixed e2fsck -fn and actual mount/file checks establish other properties.
 * RECOVER and every undeclared feature are excluded by exact bit equality. */
static int fs1_superblock(const uint8_t *s, size_t length,
                         const uint8_t uuid[16], uint64_t blocks) {
    static const uint8_t zero[16] = {0};
    static const uint8_t label[16] = "S22DEBIAN";
    return length == 1024U && fs1_u16(s + 0x38) == 0xef53U &&
        (fs1_u32(s + 4) | ((uint64_t)fs1_u32(s + 0x150) << 32)) == blocks &&
        fs1_u32(s + 0x14) == 0 && fs1_u32(s + 0x18) == 2 &&
        fs1_u32(s + 0x1c) == 2 && fs1_u16(s + 0x58) == 256 &&
        fs1_u32(s + 0x48) == 0 && fs1_u32(s + 0x4c) == 1 &&
        fs1_u16(s + 0x3a) == 1 && fs1_u32(s + 0xe8) == 0 &&
        fs1_u16(s + 0x3c) == 2 && fs1_u32(s + 0x5c) == FS1_COMPAT &&
        fs1_u32(s + 0x60) == FS1_INCOMPAT && fs1_u32(s + 0x64) == FS1_RO_COMPAT &&
        !memcmp(s + 0x68, uuid, 16) && !memcmp(s + 0x78, label, 16) &&
        fs1_u32(s + 0xe0) == 8 && fs1_u32(s + 0xe4) == 0 &&
        !memcmp(s + 0xd0, zero, 16) && fs1_u16(s + 0xfe) == 64 &&
        s[0x175] == 1 && fs1_u32(s + 0x194) == 0 &&
        fs1_u32(s + 0x3fc) == fs1_crc32c(s, 0x3fc);
}

static void fs1_witness(uint8_t output[FS1_BLOCK]) {
    static const char tag[] = "S22PLUS_NATIVE_EXT4_V1\n";
    memcpy(output, tag, sizeof(tag) - 1U);
    for (size_t i = sizeof(tag) - 1U; i < FS1_BLOCK; ++i)
        output[i] = (uint8_t)((i - (sizeof(tag) - 1U)) * 17U + 31U);
}

enum fs1_mode { FS1_INSPECT = 0, FS1_INITIALIZE = 1, FS1_VERIFY = 2 };
enum fs1_step {
    FS1_BIND = 1, FS1_FORMAT = 2, FS1_SUPER = 3, FS1_CHECK = 4,
    FS1_MOUNT = 5, FS1_FILE = 6, FS1_SYNC = 7, FS1_UNMOUNT = 8,
    FS1_FINAL = 9
};
struct fs1_result {
    unsigned last_completed, failed_step, formatted, mounted, witness_verified;
    unsigned synchronized, unmounted, cleanup_attempted, cleanup_failed;
    int error;
};
struct fs1_io {
    void *context;
    int (*step)(void *, enum fs1_step, enum fs1_mode);
    void (*record)(void *, enum fs1_step, int);
};

/* No operation retries. Only a known owned mount is eligible for the one
 * local cleanup call after a completed synchronous failure. A process-level
 * timeout/unknown writer never enters another invocation of this function. */
static int fs1_execute(enum fs1_mode mode, const struct fs1_io *io,
                       struct fs1_result *r) {
    memset(r, 0, sizeof(*r));
    if (mode < FS1_INSPECT || mode > FS1_VERIFY) return -1;
    for (enum fs1_step step = FS1_BIND; step <= FS1_FINAL; ++step) {
        if (step == FS1_FORMAT && mode != FS1_INITIALIZE) continue;
        if (mode == FS1_INSPECT && step > FS1_BIND) break;
        if (step == FS1_SYNC && mode == FS1_VERIFY) continue;
        int rc = io->step(io->context, step, mode);
        io->record(io->context, step, rc);
        if (rc) {
            r->failed_step = (unsigned)step;
            r->error = rc;
            if (r->mounted && !r->unmounted && step != FS1_UNMOUNT) {
                r->cleanup_attempted = 1;
                int cleanup = io->step(io->context, FS1_UNMOUNT, mode);
                io->record(io->context, FS1_UNMOUNT, cleanup);
                if (cleanup) r->cleanup_failed = 1;
                else r->unmounted = 1;
            }
            return -1;
        }
        r->last_completed = (unsigned)step;
        if (step == FS1_FORMAT) r->formatted = 1;
        if (step == FS1_MOUNT) r->mounted = 1;
        if (step == FS1_FILE) r->witness_verified = 1;
        if (step == FS1_SYNC) r->synchronized = 1;
        if (step == FS1_UNMOUNT) r->unmounted = 1;
    }
    return 0;
}
#endif
