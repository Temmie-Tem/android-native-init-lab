/*
 * S20+ G986N TWRP identical-resident boot write/readback qualification backend.
 *
 * H0 SOURCE ONLY: compiling this file grants no connected or block authority.
 * A future separately reviewed owner may stage this exact static executable and
 * the exact resident boot image in TWRP tmpfs.  The executable accepts no
 * arguments and can reach pwrite only after all fixed source, preimage, opened-
 * fd target, sysfs, and geometry checks pass.  It never reboots or touches a
 * path other than the fixed tmpfs stage, direct boot node, and its fixed sysfs
 * identity.  A torn UFS write remains a real boot-corruption hazard requiring
 * the separately armed Download/Odin recovery path; identical bytes do not
 * make interruption safe.
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif
#ifndef O_DIRECT
#define O_DIRECT 0
#endif
#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define Q0_SCHEMA "s20plus_g986n_twrp_identical_resident_write_backend_v1"
#define Q0_STAGE_DIR "/tmp/s20plus-g986n-identical-resident-q0"
#define Q0_BACKEND_NAME "s20plus_twrp_boot_write_q0"
#define Q0_SOURCE_NAME "resident-boot.img"
#define Q0_TARGET_PATH "/dev/block/sda23"
#define Q0_SYSFS_UEVENT "/sys/dev/block/259:7/uevent"
#define Q0_SYSFS_DEV "/sys/dev/block/259:7/dev"
#define Q0_SYSFS_PARTITION "/sys/dev/block/259:7/partition"
#define Q0_SYSFS_SIZE "/sys/dev/block/259:7/size"
#define Q0_EXPECTED_MAJOR 259U
#define Q0_EXPECTED_MINOR 7U
#define Q0_EXPECTED_PARTITION 23U
#define Q0_EXPECTED_SECTORS 131072ULL
#define Q0_EXPECTED_SIZE 67108864ULL
#define Q0_CHUNK (1024U * 1024U)
#define Q0_MAX_SYSFS 8192U
#define Q0_SOURCE_MODE 0400U
#define Q0_BACKEND_MODE 0500U
#define Q0_STAGE_MODE 0700U
#define Q0_EXPECTED_SHA256 \
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"

struct q0_sha256_ctx {
    uint32_t state[8];
    uint64_t bit_count;
    unsigned char buffer[64];
    size_t buffer_len;
};

struct q0_source_identity {
    dev_t dev;
    ino_t ino;
    off_t size;
    mode_t mode;
    uid_t uid;
    gid_t gid;
    nlink_t nlink;
    struct timespec mtime;
    struct timespec ctime;
};

struct q0_effect_state {
    int write_started;
    uint64_t bytes_written;
    int fsync_attempted;
    int fsync_succeeded;
};

static uint32_t q0_rotr(uint32_t value, unsigned int shift) {
    return (value >> shift) | (value << (32U - shift));
}

static uint32_t q0_load32(const unsigned char *data) {
    return ((uint32_t)data[0] << 24) |
           ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) |
           (uint32_t)data[3];
}

static void q0_store32(unsigned char *out, uint32_t value) {
    out[0] = (unsigned char)(value >> 24);
    out[1] = (unsigned char)(value >> 16);
    out[2] = (unsigned char)(value >> 8);
    out[3] = (unsigned char)value;
}

static void q0_sha256_transform(struct q0_sha256_ctx *ctx,
                                const unsigned char block[64]) {
    static const uint32_t constants[64] = {
        0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
        0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
        0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
        0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
        0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
        0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
        0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
        0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
        0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
        0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
        0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
        0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
        0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
        0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
        0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
        0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
    };
    uint32_t words[64];
    uint32_t a = ctx->state[0];
    uint32_t b = ctx->state[1];
    uint32_t c = ctx->state[2];
    uint32_t d = ctx->state[3];
    uint32_t e = ctx->state[4];
    uint32_t f = ctx->state[5];
    uint32_t g = ctx->state[6];
    uint32_t h = ctx->state[7];
    size_t index;

    for (index = 0; index < 16; ++index) {
        words[index] = q0_load32(block + index * 4U);
    }
    for (index = 16; index < 64; ++index) {
        uint32_t sigma0 = q0_rotr(words[index - 15], 7) ^
                          q0_rotr(words[index - 15], 18) ^
                          (words[index - 15] >> 3);
        uint32_t sigma1 = q0_rotr(words[index - 2], 17) ^
                          q0_rotr(words[index - 2], 19) ^
                          (words[index - 2] >> 10);
        words[index] = words[index - 16] + sigma0 + words[index - 7] + sigma1;
    }
    for (index = 0; index < 64; ++index) {
        uint32_t sum1 = q0_rotr(e, 6) ^ q0_rotr(e, 11) ^ q0_rotr(e, 25);
        uint32_t choose = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + sum1 + choose + constants[index] + words[index];
        uint32_t sum0 = q0_rotr(a, 2) ^ q0_rotr(a, 13) ^ q0_rotr(a, 22);
        uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = sum0 + majority;
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }
    ctx->state[0] += a;
    ctx->state[1] += b;
    ctx->state[2] += c;
    ctx->state[3] += d;
    ctx->state[4] += e;
    ctx->state[5] += f;
    ctx->state[6] += g;
    ctx->state[7] += h;
}

static void q0_sha256_init(struct q0_sha256_ctx *ctx) {
    static const uint32_t initial[8] = {
        0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
        0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U,
    };
    memcpy(ctx->state, initial, sizeof(initial));
    ctx->bit_count = 0;
    ctx->buffer_len = 0;
}

static void q0_sha256_update(struct q0_sha256_ctx *ctx,
                             const unsigned char *data, size_t length) {
    ctx->bit_count += (uint64_t)length * 8U;
    while (length > 0) {
        size_t available = sizeof(ctx->buffer) - ctx->buffer_len;
        size_t amount = length < available ? length : available;
        memcpy(ctx->buffer + ctx->buffer_len, data, amount);
        ctx->buffer_len += amount;
        data += amount;
        length -= amount;
        if (ctx->buffer_len == sizeof(ctx->buffer)) {
            q0_sha256_transform(ctx, ctx->buffer);
            ctx->buffer_len = 0;
        }
    }
}

static void q0_sha256_final(struct q0_sha256_ctx *ctx,
                            unsigned char digest[32]) {
    size_t index;
    uint64_t bits = ctx->bit_count;
    ctx->buffer[ctx->buffer_len++] = 0x80U;
    if (ctx->buffer_len > 56U) {
        while (ctx->buffer_len < 64U) {
            ctx->buffer[ctx->buffer_len++] = 0;
        }
        q0_sha256_transform(ctx, ctx->buffer);
        ctx->buffer_len = 0;
    }
    while (ctx->buffer_len < 56U) {
        ctx->buffer[ctx->buffer_len++] = 0;
    }
    for (index = 0; index < 8U; ++index) {
        ctx->buffer[63U - index] = (unsigned char)(bits >> (index * 8U));
    }
    q0_sha256_transform(ctx, ctx->buffer);
    for (index = 0; index < 8U; ++index) {
        q0_store32(digest + index * 4U, ctx->state[index]);
    }
}

static void q0_sha256_hex(const unsigned char digest[32], char out[65]) {
    static const char hex[] = "0123456789abcdef";
    size_t index;
    for (index = 0; index < 32U; ++index) {
        out[index * 2U] = hex[(digest[index] >> 4) & 0x0fU];
        out[index * 2U + 1U] = hex[digest[index] & 0x0fU];
    }
    out[64] = '\0';
}

static int q0_power_of_two(unsigned int value) {
    return value >= 512U && value <= Q0_CHUNK && (value & (value - 1U)) == 0U;
}

static int q0_read_small(const char *path, char *output, size_t capacity) {
    int descriptor;
    size_t used = 0;
    if (capacity < 2U) {
        return -EINVAL;
    }
    descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (descriptor < 0) {
        return -errno;
    }
    for (;;) {
        ssize_t amount = read(descriptor, output + used, capacity - 1U - used);
        if (amount < 0) {
            int saved = errno;
            if (saved == EINTR) {
                continue;
            }
            close(descriptor);
            return -saved;
        }
        if (amount == 0) {
            break;
        }
        used += (size_t)amount;
        if (used == capacity - 1U) {
            char extra;
            ssize_t more = read(descriptor, &extra, 1U);
            if (more != 0) {
                close(descriptor);
                return -EOVERFLOW;
            }
            break;
        }
    }
    if (close(descriptor) != 0) {
        return -errno;
    }
    output[used] = '\0';
    if (memchr(output, '\0', used) != NULL || memchr(output, '\r', used) != NULL) {
        return -EINVAL;
    }
    return (int)used;
}

static int q0_text_equals(const char *path, const char *expected) {
    char value[128];
    int amount = q0_read_small(path, value, sizeof(value));
    size_t expected_size = strlen(expected);
    return amount == (int)expected_size && memcmp(value, expected, expected_size) == 0;
}

static int q0_check_uevent(void) {
    static const struct {
        const char *key;
        const char *value;
    } required[] = {
        {"MAJOR", "259"},
        {"MINOR", "7"},
        {"DEVNAME", "sda23"},
        {"DEVTYPE", "partition"},
        {"PARTN", "23"},
        {"PARTNAME", "boot"},
    };
    unsigned int seen[sizeof(required) / sizeof(required[0])] = {0};
    char value[Q0_MAX_SYSFS];
    char *cursor;
    char *save = NULL;
    size_t index;
    int amount = q0_read_small(Q0_SYSFS_UEVENT, value, sizeof(value));
    if (amount <= 0 || value[amount - 1] != '\n') {
        return 0;
    }
    cursor = strtok_r(value, "\n", &save);
    while (cursor != NULL) {
        char *equals = strchr(cursor, '=');
        if (equals == NULL || equals == cursor || equals[1] == '\0') {
            return 0;
        }
        *equals = '\0';
        for (index = 0; index < sizeof(required) / sizeof(required[0]); ++index) {
            if (strcmp(cursor, required[index].key) == 0) {
                seen[index] += 1U;
                if (seen[index] != 1U || strcmp(equals + 1, required[index].value) != 0) {
                    return 0;
                }
            }
        }
        cursor = strtok_r(NULL, "\n", &save);
    }
    for (index = 0; index < sizeof(required) / sizeof(required[0]); ++index) {
        if (seen[index] != 1U) {
            return 0;
        }
    }
    return 1;
}

static int q0_guard_target_fd(int descriptor, size_t *alignment_out) {
    struct stat state;
    uint64_t size = 0;
    unsigned int logical = 0;
    unsigned int physical = 0;
    size_t alignment;
    if (fstat(descriptor, &state) != 0 || !S_ISBLK(state.st_mode)) {
        return 0;
    }
    if ((unsigned int)major(state.st_rdev) != Q0_EXPECTED_MAJOR ||
        (unsigned int)minor(state.st_rdev) != Q0_EXPECTED_MINOR) {
        return 0;
    }
    if (ioctl(descriptor, BLKGETSIZE64, &size) != 0 || size != Q0_EXPECTED_SIZE) {
        return 0;
    }
    if (ioctl(descriptor, BLKSSZGET, &logical) != 0 ||
        ioctl(descriptor, BLKPBSZGET, &physical) != 0 ||
        !q0_power_of_two(logical) || !q0_power_of_two(physical)) {
        return 0;
    }
    alignment = logical > physical ? logical : physical;
    if (alignment < 4096U) {
        alignment = 4096U;
    }
    if (Q0_CHUNK % alignment != 0U || Q0_EXPECTED_SIZE % alignment != 0U) {
        return 0;
    }
    if (!q0_check_uevent() ||
        !q0_text_equals(Q0_SYSFS_DEV, "259:7\n") ||
        !q0_text_equals(Q0_SYSFS_PARTITION, "23\n") ||
        !q0_text_equals(Q0_SYSFS_SIZE, "131072\n")) {
        return 0;
    }
    *alignment_out = alignment;
    return 1;
}

static int q0_same_source_identity(const struct stat *state,
                                   const struct q0_source_identity *expected) {
    return S_ISREG(state->st_mode) &&
           state->st_dev == expected->dev && state->st_ino == expected->ino &&
           state->st_size == expected->size && state->st_mode == expected->mode &&
           state->st_uid == expected->uid && state->st_gid == expected->gid &&
           state->st_nlink == expected->nlink &&
           state->st_mtim.tv_sec == expected->mtime.tv_sec &&
           state->st_mtim.tv_nsec == expected->mtime.tv_nsec &&
           state->st_ctim.tv_sec == expected->ctime.tv_sec &&
           state->st_ctim.tv_nsec == expected->ctime.tv_nsec;
}

static int q0_open_stage(int *directory_out, int *source_out,
                         struct q0_source_identity *identity_out) {
    int directory = -1;
    int source = -1;
    DIR *stream = NULL;
    struct dirent *entry;
    struct stat directory_state;
    struct stat backend_state;
    struct stat executable_state;
    struct stat source_state;
    unsigned int backend_seen = 0;
    unsigned int source_seen = 0;

    directory = open(Q0_STAGE_DIR, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (directory < 0 || fstat(directory, &directory_state) != 0 ||
        !S_ISDIR(directory_state.st_mode) || directory_state.st_uid != 0 ||
        directory_state.st_gid != 0 ||
        (directory_state.st_mode & 07777U) != Q0_STAGE_MODE) {
        goto fail;
    }
    stream = fdopendir(dup(directory));
    if (stream == NULL) {
        goto fail;
    }
    while ((entry = readdir(stream)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        if (strcmp(entry->d_name, Q0_BACKEND_NAME) == 0) {
            backend_seen += 1U;
        } else if (strcmp(entry->d_name, Q0_SOURCE_NAME) == 0) {
            source_seen += 1U;
        } else {
            goto fail;
        }
    }
    if (closedir(stream) != 0) {
        stream = NULL;
        goto fail;
    }
    stream = NULL;
    if (backend_seen != 1U || source_seen != 1U) {
        goto fail;
    }
    if (fstatat(directory, Q0_BACKEND_NAME, &backend_state, AT_SYMLINK_NOFOLLOW) != 0 ||
        !S_ISREG(backend_state.st_mode) || backend_state.st_uid != 0 ||
        backend_state.st_gid != 0 || backend_state.st_nlink != 1 ||
        (backend_state.st_mode & 07777U) != Q0_BACKEND_MODE ||
        stat("/proc/self/exe", &executable_state) != 0 ||
        executable_state.st_dev != backend_state.st_dev ||
        executable_state.st_ino != backend_state.st_ino) {
        goto fail;
    }
    source = openat(directory, Q0_SOURCE_NAME, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (source < 0 || fstat(source, &source_state) != 0 ||
        !S_ISREG(source_state.st_mode) || source_state.st_uid != 0 ||
        source_state.st_gid != 0 || source_state.st_nlink != 1 ||
        (source_state.st_mode & 07777U) != Q0_SOURCE_MODE ||
        (uint64_t)source_state.st_size != Q0_EXPECTED_SIZE) {
        goto fail;
    }
    identity_out->dev = source_state.st_dev;
    identity_out->ino = source_state.st_ino;
    identity_out->size = source_state.st_size;
    identity_out->mode = source_state.st_mode;
    identity_out->uid = source_state.st_uid;
    identity_out->gid = source_state.st_gid;
    identity_out->nlink = source_state.st_nlink;
    identity_out->mtime = source_state.st_mtim;
    identity_out->ctime = source_state.st_ctim;
    *directory_out = directory;
    *source_out = source;
    return 1;

fail:
    if (stream != NULL) {
        closedir(stream);
    }
    if (source >= 0) {
        close(source);
    }
    if (directory >= 0) {
        close(directory);
    }
    return 0;
}

static int q0_hash_fd(int descriptor, uint64_t size, size_t alignment,
                      unsigned char *buffer, char output[65]) {
    struct q0_sha256_ctx context;
    uint64_t offset = 0;
    q0_sha256_init(&context);
    while (offset < size) {
        size_t wanted = Q0_CHUNK;
        size_t received = 0;
        if (size - offset < (uint64_t)wanted) {
            wanted = (size_t)(size - offset);
        }
        if (wanted % alignment != 0U || offset % alignment != 0U) {
            return 0;
        }
        while (received < wanted) {
            ssize_t amount = pread(descriptor, buffer + received,
                                   wanted - received, (off_t)(offset + received));
            if (amount < 0 && errno == EINTR) {
                continue;
            }
            if (amount <= 0) {
                return 0;
            }
            received += (size_t)amount;
        }
        q0_sha256_update(&context, buffer, wanted);
        offset += wanted;
    }
    {
        unsigned char digest[32];
        q0_sha256_final(&context, digest);
        q0_sha256_hex(digest, output);
    }
    return 1;
}

static int q0_write_exact(int source, int target, unsigned char *buffer,
                          struct q0_effect_state *effect, char source_sha[65]) {
    struct q0_sha256_ctx context;
    uint64_t offset = 0;
    q0_sha256_init(&context);
    while (offset < Q0_EXPECTED_SIZE) {
        size_t wanted = Q0_CHUNK;
        size_t received = 0;
        size_t written = 0;
        if (Q0_EXPECTED_SIZE - offset < (uint64_t)wanted) {
            wanted = (size_t)(Q0_EXPECTED_SIZE - offset);
        }
        while (received < wanted) {
            ssize_t amount = pread(source, buffer + received,
                                   wanted - received, (off_t)(offset + received));
            if (amount < 0 && errno == EINTR) {
                continue;
            }
            if (amount <= 0) {
                return 0;
            }
            received += (size_t)amount;
        }
        q0_sha256_update(&context, buffer, wanted);
        while (written < wanted) {
            ssize_t amount;
            effect->write_started = 1;
            amount = pwrite(target, buffer + written, wanted - written,
                            (off_t)(offset + written));
            if (amount < 0 && errno == EINTR) {
                continue;
            }
            if (amount <= 0) {
                return 0;
            }
            written += (size_t)amount;
            effect->bytes_written += (uint64_t)amount;
        }
        offset += wanted;
    }
    {
        unsigned char digest[32];
        q0_sha256_final(&context, digest);
        q0_sha256_hex(digest, source_sha);
    }
    return effect->bytes_written == Q0_EXPECTED_SIZE;
}

static void q0_block_host_signals(void) {
    sigset_t blocked;
    sigfillset(&blocked);
    (void)sigprocmask(SIG_BLOCK, &blocked, NULL);
}

static int q0_failure(const char *stage, int error,
                      const struct q0_effect_state *effect) {
    if (error < 0) {
        error = -error;
    }
    printf("schema=%s\n", Q0_SCHEMA);
    printf("verdict=STOP_IDENTICAL_RESIDENT_WRITE_QUALIFICATION\n");
    printf("stage=%s\n", stage);
    printf("errno=%d\n", error);
    printf("write_started=%d\n", effect->write_started);
    printf("write_bytes=%llu\n", (unsigned long long)effect->bytes_written);
    printf("fsync_attempted=%d\n", effect->fsync_attempted);
    printf("fsync_succeeded=%d\n", effect->fsync_succeeded);
    printf("reboot_count=0\n");
    printf("other_partition_writes=0\n");
    (void)fflush(stdout);
    return 70;
}

int main(int argc, char **argv) {
    int stage_directory = -1;
    int source = -1;
    int preimage = -1;
    int target = -1;
    int readback = -1;
    int result = 70;
    size_t preimage_alignment = 0;
    size_t target_alignment = 0;
    size_t readback_alignment = 0;
    size_t buffer_alignment = 4096U;
    unsigned char *buffer = NULL;
    char source_before_sha[65];
    char source_during_sha[65];
    char preimage_sha[65];
    char readback_sha[65];
    struct stat source_after;
    struct q0_source_identity source_identity;
    struct q0_effect_state effect = {0, 0, 0, 0};

    (void)argv;
    q0_block_host_signals();
    (void)signal(SIGPIPE, SIG_IGN);
    (void)umask(077);
    if (argc != 1) {
        return q0_failure("arguments", EINVAL, &effect);
    }
    if (!q0_open_stage(&stage_directory, &source, &source_identity)) {
        return q0_failure("stage", errno == 0 ? EPERM : errno, &effect);
    }
    preimage = open(Q0_TARGET_PATH, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
    if (preimage < 0 || !q0_guard_target_fd(preimage, &preimage_alignment)) {
        result = q0_failure("preimage-target-guard", errno == 0 ? EPERM : errno, &effect);
        goto out;
    }
    buffer_alignment = preimage_alignment;
    if (posix_memalign((void **)&buffer, buffer_alignment, Q0_CHUNK) != 0 ||
        buffer == NULL) {
        result = q0_failure("buffer", ENOMEM, &effect);
        goto out;
    }
    if (!q0_hash_fd(source, Q0_EXPECTED_SIZE, 4096U, buffer, source_before_sha) ||
        strcmp(source_before_sha, Q0_EXPECTED_SHA256) != 0) {
        result = q0_failure("source-hash", EILSEQ, &effect);
        goto out;
    }
    if (!q0_hash_fd(preimage, Q0_EXPECTED_SIZE, preimage_alignment, buffer,
                    preimage_sha) ||
        strcmp(preimage_sha, Q0_EXPECTED_SHA256) != 0) {
        result = q0_failure("preimage-hash", EILSEQ, &effect);
        goto out;
    }
    if (close(preimage) != 0) {
        preimage = -1;
        result = q0_failure("preimage-close", errno, &effect);
        goto out;
    }
    preimage = -1;
    if (fstat(source, &source_after) != 0 ||
        !q0_same_source_identity(&source_after, &source_identity)) {
        result = q0_failure("source-drift-before-write", ESTALE, &effect);
        goto out;
    }

    target = open(Q0_TARGET_PATH, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (target < 0 || !q0_guard_target_fd(target, &target_alignment) ||
        target_alignment != preimage_alignment) {
        result = q0_failure("write-target-guard", errno == 0 ? EPERM : errno, &effect);
        goto out;
    }
    if (!q0_write_exact(source, target, buffer, &effect, source_during_sha)) {
        effect.fsync_attempted = effect.write_started;
        if (effect.fsync_attempted && fsync(target) == 0) {
            effect.fsync_succeeded = 1;
        }
        result = q0_failure("write", EIO, &effect);
        goto out;
    }
    effect.fsync_attempted = 1;
    {
        int fsync_result = fsync(target);
        int fsync_error = errno;
        if (fsync_result == 0) {
            effect.fsync_succeeded = 1;
        }
        if (strcmp(source_during_sha, Q0_EXPECTED_SHA256) != 0 ||
            fsync_result != 0) {
            result = q0_failure(
                "write-fsync",
                fsync_result == 0 ? EILSEQ : fsync_error,
                &effect
            );
            goto out;
        }
    }
    if (close(target) != 0) {
        target = -1;
        result = q0_failure("write-close", errno, &effect);
        goto out;
    }
    target = -1;
    if (fstat(source, &source_after) != 0 ||
        !q0_same_source_identity(&source_after, &source_identity)) {
        result = q0_failure("source-drift-after-write", ESTALE, &effect);
        goto out;
    }

    readback = open(Q0_TARGET_PATH, O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW);
    if (readback < 0 || !q0_guard_target_fd(readback, &readback_alignment) ||
        readback_alignment != target_alignment) {
        result = q0_failure("readback-target-guard", errno == 0 ? EPERM : errno, &effect);
        goto out;
    }
    if (!q0_hash_fd(readback, Q0_EXPECTED_SIZE, readback_alignment, buffer,
                    readback_sha) ||
        strcmp(readback_sha, Q0_EXPECTED_SHA256) != 0) {
        result = q0_failure("readback-hash", EILSEQ, &effect);
        goto out;
    }
    printf("schema=%s\n", Q0_SCHEMA);
    printf("verdict=PROVED_IDENTICAL_RESIDENT_WRITE_READBACK\n");
    printf("target=%s\n", Q0_TARGET_PATH);
    printf("rdev=%u:%u\n", Q0_EXPECTED_MAJOR, Q0_EXPECTED_MINOR);
    printf("partname=boot\n");
    printf("partition=%u\n", Q0_EXPECTED_PARTITION);
    printf("size_bytes=%llu\n", (unsigned long long)Q0_EXPECTED_SIZE);
    printf("source_sha256=%s\n", source_during_sha);
    printf("preimage_sha256=%s\n", preimage_sha);
    printf("write_bytes=%llu\n", (unsigned long long)effect.bytes_written);
    printf("fsync_succeeded=%d\n", effect.fsync_succeeded);
    printf("readback_sha256=%s\n", readback_sha);
    printf("write_attempts=1\n");
    printf("reboot_count=0\n");
    printf("other_partition_writes=0\n");
    (void)fflush(stdout);
    result = 0;

out:
    free(buffer);
    if (readback >= 0) {
        close(readback);
    }
    if (target >= 0) {
        close(target);
    }
    if (preimage >= 0) {
        close(preimage);
    }
    if (source >= 0) {
        close(source);
    }
    if (stage_directory >= 0) {
        close(stage_directory);
    }
    return result;
}
