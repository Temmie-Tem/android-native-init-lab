#include "a90_helper.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_runtime.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdint.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

struct helper_sha256_ctx {
    uint32_t state[8];
    uint64_t bit_count;
    unsigned char buffer[64];
    size_t buffer_len;
};

static struct a90_helper_entry helper_entries[A90_HELPER_MAX_ENTRIES];
static int helper_count;
static int helper_warn_count;
static int helper_fail_count;
static bool helper_scanned;
static bool helper_manifest_present;
static char helper_manifest_path[PATH_MAX];
static char helper_deploy_log_path[PATH_MAX];
static char helper_summary_text[192];

static void helper_join(char *out, size_t out_size, const char *root, const char *name) {
    size_t used;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (root == NULL || name == NULL) {
        return;
    }
    snprintf(out, out_size, "%s", root);
    out[out_size - 1] = '\0';
    used = strlen(out);
    if (used + 1 < out_size) {
        out[used++] = '/';
        out[used] = '\0';
    }
    if (used < out_size) {
        strncat(out, name, out_size - used - 1);
    }
}

static bool helper_stat_regular(const char *path,
                                unsigned int *mode_out,
                                long long *size_out) {
    struct stat st;

    if (path == NULL || path[0] == '\0' || lstat(path, &st) < 0) {
        return false;
    }
    if (!S_ISREG(st.st_mode)) {
        return false;
    }
    if (mode_out != NULL) {
        *mode_out = (unsigned int)(st.st_mode & 0777);
    }
    if (size_out != NULL) {
        *size_out = (long long)st.st_size;
    }
    return true;
}

static bool helper_is_executable(const char *path) {
    unsigned int mode = 0;

    if (!helper_stat_regular(path, &mode, NULL)) {
        return false;
    }
    return (mode & 0111) != 0;
}

static uint32_t helper_sha_rotr(uint32_t value, unsigned int shift) {
    return (value >> shift) | (value << (32U - shift));
}

static uint32_t helper_sha_load32(const unsigned char *data) {
    return ((uint32_t)data[0] << 24) |
           ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) |
           (uint32_t)data[3];
}

static void helper_sha_store32(unsigned char *out, uint32_t value) {
    out[0] = (unsigned char)(value >> 24);
    out[1] = (unsigned char)(value >> 16);
    out[2] = (unsigned char)(value >> 8);
    out[3] = (unsigned char)value;
}

static void helper_sha256_transform(struct helper_sha256_ctx *ctx,
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
    uint32_t state_a = ctx->state[0];
    uint32_t state_b = ctx->state[1];
    uint32_t state_c = ctx->state[2];
    uint32_t state_d = ctx->state[3];
    uint32_t state_e = ctx->state[4];
    uint32_t state_f = ctx->state[5];
    uint32_t state_g = ctx->state[6];
    uint32_t state_h = ctx->state[7];
    size_t index;

    for (index = 0; index < 16; ++index) {
        words[index] = helper_sha_load32(block + index * 4);
    }
    for (index = 16; index < 64; ++index) {
        uint32_t sigma0 = helper_sha_rotr(words[index - 15], 7) ^
                          helper_sha_rotr(words[index - 15], 18) ^
                          (words[index - 15] >> 3);
        uint32_t sigma1 = helper_sha_rotr(words[index - 2], 17) ^
                          helper_sha_rotr(words[index - 2], 19) ^
                          (words[index - 2] >> 10);

        words[index] = words[index - 16] + sigma0 + words[index - 7] + sigma1;
    }

    for (index = 0; index < 64; ++index) {
        uint32_t sum1 = helper_sha_rotr(state_e, 6) ^
                        helper_sha_rotr(state_e, 11) ^
                        helper_sha_rotr(state_e, 25);
        uint32_t choose = (state_e & state_f) ^ ((~state_e) & state_g);
        uint32_t temp1 = state_h + sum1 + choose + constants[index] + words[index];
        uint32_t sum0 = helper_sha_rotr(state_a, 2) ^
                        helper_sha_rotr(state_a, 13) ^
                        helper_sha_rotr(state_a, 22);
        uint32_t majority = (state_a & state_b) ^
                            (state_a & state_c) ^
                            (state_b & state_c);
        uint32_t temp2 = sum0 + majority;

        state_h = state_g;
        state_g = state_f;
        state_f = state_e;
        state_e = state_d + temp1;
        state_d = state_c;
        state_c = state_b;
        state_b = state_a;
        state_a = temp1 + temp2;
    }

    ctx->state[0] += state_a;
    ctx->state[1] += state_b;
    ctx->state[2] += state_c;
    ctx->state[3] += state_d;
    ctx->state[4] += state_e;
    ctx->state[5] += state_f;
    ctx->state[6] += state_g;
    ctx->state[7] += state_h;
}

static void helper_sha256_init(struct helper_sha256_ctx *ctx) {
    ctx->state[0] = 0x6a09e667U;
    ctx->state[1] = 0xbb67ae85U;
    ctx->state[2] = 0x3c6ef372U;
    ctx->state[3] = 0xa54ff53aU;
    ctx->state[4] = 0x510e527fU;
    ctx->state[5] = 0x9b05688cU;
    ctx->state[6] = 0x1f83d9abU;
    ctx->state[7] = 0x5be0cd19U;
    ctx->bit_count = 0;
    ctx->buffer_len = 0;
}

static void helper_sha256_update(struct helper_sha256_ctx *ctx,
                                 const unsigned char *data,
                                 size_t len) {
    ctx->bit_count += (uint64_t)len * 8U;
    while (len > 0) {
        size_t available = sizeof(ctx->buffer) - ctx->buffer_len;
        size_t copy_len = len < available ? len : available;

        memcpy(ctx->buffer + ctx->buffer_len, data, copy_len);
        ctx->buffer_len += copy_len;
        data += copy_len;
        len -= copy_len;
        if (ctx->buffer_len == sizeof(ctx->buffer)) {
            helper_sha256_transform(ctx, ctx->buffer);
            ctx->buffer_len = 0;
        }
    }
}

static void helper_sha256_final(struct helper_sha256_ctx *ctx,
                                unsigned char digest[32]) {
    unsigned char length_block[8];
    size_t index;

    ctx->buffer[ctx->buffer_len++] = 0x80;
    if (ctx->buffer_len > 56) {
        while (ctx->buffer_len < sizeof(ctx->buffer)) {
            ctx->buffer[ctx->buffer_len++] = 0;
        }
        helper_sha256_transform(ctx, ctx->buffer);
        ctx->buffer_len = 0;
    }
    while (ctx->buffer_len < 56) {
        ctx->buffer[ctx->buffer_len++] = 0;
    }
    for (index = 0; index < sizeof(length_block); ++index) {
        length_block[7 - index] = (unsigned char)(ctx->bit_count >> (index * 8));
    }
    memcpy(ctx->buffer + 56, length_block, sizeof(length_block));
    helper_sha256_transform(ctx, ctx->buffer);

    for (index = 0; index < 8; ++index) {
        helper_sha_store32(digest + index * 4, ctx->state[index]);
    }
}

static int helper_sha256_file(const char *path, char *out, size_t out_size) {
    static const char hex[] = "0123456789abcdef";
    struct helper_sha256_ctx ctx;
    unsigned char digest[32];
    unsigned char buffer[4096];
    int fd;
    size_t index;

    if (path == NULL || out == NULL || out_size < 65) {
        errno = EINVAL;
        return -1;
    }

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -1;
    }
    helper_sha256_init(&ctx);
    for (;;) {
        ssize_t rd = read(fd, buffer, sizeof(buffer));

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            {
                int saved_errno = errno;

                close(fd);
                errno = saved_errno;
                return -1;
            }
        }
        if (rd == 0) {
            break;
        }
        helper_sha256_update(&ctx, buffer, (size_t)rd);
    }
    if (close(fd) < 0) {
        return -1;
    }
    helper_sha256_final(&ctx, digest);
    for (index = 0; index < sizeof(digest); ++index) {
        out[index * 2] = hex[digest[index] >> 4];
        out[index * 2 + 1] = hex[digest[index] & 0x0f];
    }
    out[64] = '\0';
    return 0;
}

static bool helper_path_has_prefix(const char *path, const char *prefix) {
    size_t prefix_len;

    if (path == NULL || prefix == NULL || prefix[0] == '\0') {
        return false;
    }
    prefix_len = strlen(prefix);
    return strncmp(path, prefix, prefix_len) == 0 &&
           (path[prefix_len] == '\0' || path[prefix_len] == '/');
}

static bool helper_manifest_path_allowed(const char *path) {
    struct a90_runtime_status runtime;

    if (path == NULL || path[0] != '/') {
        return false;
    }
    if (a90_runtime_get_status(&runtime) < 0 || runtime.root[0] == '\0') {
        return false;
    }
    return helper_path_has_prefix(path, runtime.root);
}

static bool helper_is_hex_sha256(const char *text) {
    size_t index;

    if (text == NULL || strlen(text) != 64) {
        return false;
    }
    for (index = 0; index < 64; ++index) {
        char ch = text[index];

        if (!((ch >= '0' && ch <= '9') ||
              (ch >= 'a' && ch <= 'f') ||
              (ch >= 'A' && ch <= 'F'))) {
            return false;
        }
    }
    return true;
}

static struct a90_helper_entry *helper_add(const char *name,
                                           const char *role,
                                           const char *fallback) {
    struct a90_runtime_status runtime;
    struct a90_helper_entry *entry;

    if (helper_count >= A90_HELPER_MAX_ENTRIES ||
        name == NULL ||
        name[0] == '\0') {
        return NULL;
    }
    entry = &helper_entries[helper_count++];
    memset(entry, 0, sizeof(*entry));
    snprintf(entry->name, sizeof(entry->name), "%s", name);
    snprintf(entry->role, sizeof(entry->role), "%s", role != NULL ? role : "helper");
    if (fallback != NULL) {
        snprintf(entry->fallback, sizeof(entry->fallback), "%s", fallback);
    }
    if (a90_runtime_get_status(&runtime) == 0 && runtime.bin[0] != '\0') {
        helper_join(entry->path, sizeof(entry->path), runtime.bin, name);
    } else {
        snprintf(entry->path, sizeof(entry->path), "%s/%s", A90_RUNTIME_CACHE_ROOT, name);
    }
    entry->expected_mode = 0755;
    entry->expected_size = 0;
    entry->manifest_path_allowed = true;
    entry->manifest_sha_valid = true;
    return entry;
}

static struct a90_helper_entry *helper_find_mutable(const char *name) {
    int index;

    if (name == NULL) {
        return NULL;
    }
    for (index = 0; index < helper_count; ++index) {
        if (strcmp(helper_entries[index].name, name) == 0) {
            return &helper_entries[index];
        }
    }
    return NULL;
}

static void helper_add_defaults(void) {
    (void)helper_add("a90_cpustress", "ramdisk-mirror", CPUSTRESS_HELPER);
    (void)helper_add("a90_usbnet", "net-helper", NETSERVICE_USB_HELPER);
    (void)helper_add("a90_tcpctl", "tcp-control", NETSERVICE_TCPCTL_HELPER);
    (void)helper_add("a90_rshell", "remote-shell", A90_RSHELL_RAMDISK_HELPER);
    (void)helper_add("busybox", "userland", A90_BUSYBOX_HELPER);
    (void)helper_add("toybox", "userland", NETSERVICE_TOYBOX);
    (void)helper_add("a90sleep", "test-helper", A90_SLEEP_HELPER);
}

static void helper_set_manifest_path(void) {
    struct a90_runtime_status runtime;

    helper_manifest_path[0] = '\0';
    helper_deploy_log_path[0] = '\0';
    if (a90_runtime_get_status(&runtime) == 0 && runtime.pkg[0] != '\0') {
        char legacy_path[PATH_MAX];

        if (runtime.pkg_manifests[0] != '\0') {
            helper_join(helper_manifest_path,
                        sizeof(helper_manifest_path),
                        runtime.pkg_manifests,
                        A90_HELPER_MANIFEST_NAME);
        }
        helper_join(legacy_path,
                    sizeof(legacy_path),
                    runtime.pkg,
                    A90_HELPER_MANIFEST_NAME);
        if (access(helper_manifest_path, R_OK) < 0 &&
            access(legacy_path, R_OK) == 0) {
            snprintf(helper_manifest_path, sizeof(helper_manifest_path), "%s", legacy_path);
        }
        if (runtime.helper_deploy_log[0] != '\0') {
            snprintf(helper_deploy_log_path,
                     sizeof(helper_deploy_log_path),
                     "%s",
                     runtime.helper_deploy_log);
        }
    } else {
        snprintf(helper_manifest_path,
                 sizeof(helper_manifest_path),
                 "%s/%s/%s/%s",
                 A90_RUNTIME_CACHE_ROOT,
                 A90_RUNTIME_PKG_DIR,
                 "manifests",
                 A90_HELPER_MANIFEST_NAME);
    }
    if (helper_deploy_log_path[0] == '\0') {
        snprintf(helper_deploy_log_path,
                 sizeof(helper_deploy_log_path),
                 "%s/%s/%s",
                 A90_RUNTIME_CACHE_ROOT,
                 A90_RUNTIME_LOGS_DIR,
                 A90_HELPER_DEPLOY_LOG_NAME);
    }
}

static void helper_apply_manifest_line(char *line) {
    char name[64];
    char path[PATH_MAX];
    char role[64];
    char required[16];
    char sha[65];
    char mode_text[32];
    char size_text[32];
    struct a90_helper_entry *entry;
    char *cursor = line;
    int fields;

    while (*cursor == ' ' || *cursor == '\t') {
        ++cursor;
    }
    if (*cursor == '\0' || *cursor == '#') {
        return;
    }

    memset(name, 0, sizeof(name));
    memset(path, 0, sizeof(path));
    memset(role, 0, sizeof(role));
    memset(required, 0, sizeof(required));
    memset(sha, 0, sizeof(sha));
    memset(mode_text, 0, sizeof(mode_text));
    memset(size_text, 0, sizeof(size_text));

    fields = sscanf(cursor,
                    "%63s %4095s %63s %15s %64s %31s %31s",
                    name,
                    path,
                    role,
                    required,
                    sha,
                    mode_text,
                    size_text);
    if (fields < 2) {
        return;
    }

    entry = helper_find_mutable(name);
    if (entry == NULL) {
        entry = helper_add(name, fields >= 3 ? role : "manifest", NULL);
    }
    if (entry == NULL) {
        return;
    }

    snprintf(entry->path, sizeof(entry->path), "%s", path);
    entry->manifest_path_allowed = helper_manifest_path_allowed(path);
    if (fields >= 3 && role[0] != '\0') {
        snprintf(entry->role, sizeof(entry->role), "%s", role);
    }
    if (fields >= 4) {
        entry->required = strcmp(required, "yes") == 0 ||
                          strcmp(required, "required") == 0 ||
                          strcmp(required, "1") == 0;
    }
    entry->manifest_sha_valid = true;
    if (fields >= 5 && strcmp(sha, "-") != 0 && strcmp(sha, "none") != 0) {
        if (helper_is_hex_sha256(sha)) {
            snprintf(entry->expected_sha256, sizeof(entry->expected_sha256), "%s", sha);
        } else {
            entry->expected_sha256[0] = '\0';
            entry->manifest_sha_valid = false;
        }
    }
    if (fields >= 6 && mode_text[0] != '\0' && strcmp(mode_text, "-") != 0) {
        entry->expected_mode = (unsigned int)strtoul(mode_text, NULL, 8);
    }
    if (fields >= 7 && size_text[0] != '\0' && strcmp(size_text, "-") != 0) {
        entry->expected_size = strtoll(size_text, NULL, 10);
    }
    entry->manifest_entry = true;
}

static void helper_load_manifest(void) {
    FILE *fp;
    int fd;
    char line[640];

    helper_manifest_present = false;
    fd = open(helper_manifest_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return;
    }
    fp = fdopen(fd, "r");
    if (fp == NULL) {
        close(fd);
        return;
    }
    helper_manifest_present = true;
    while (fgets(line, sizeof(line), fp) != NULL) {
        char *newline = strchr(line, '\n');

        if (newline != NULL) {
            *newline = '\0';
        }
        helper_apply_manifest_line(line);
    }
    fclose(fp);
}

static void helper_finalize_entry(struct a90_helper_entry *entry) {
    unsigned int mode = 0;
    long long size = 0;
    bool mode_bad = false;
    bool size_bad = false;
    bool runtime_candidate;
    bool trusted_runtime_candidate = false;

    entry->present = helper_stat_regular(entry->path, &mode, &size);
    entry->actual_mode = entry->present ? mode : 0;
    entry->actual_size = entry->present ? size : 0;
    entry->executable = entry->present && ((mode & 0111) != 0);
    entry->fallback_present = helper_is_executable(entry->fallback);
    entry->hash_checked = false;
    entry->hash_match = entry->expected_sha256[0] == '\0';
    snprintf(entry->actual_sha256,
             sizeof(entry->actual_sha256),
             "%s",
             entry->expected_sha256[0] != '\0' ? "unchecked" : "-");

    if (entry->present && entry->expected_mode != 0 &&
        entry->actual_mode != entry->expected_mode) {
        mode_bad = true;
    }
    if (entry->present && entry->expected_size > 0 &&
        entry->actual_size != entry->expected_size) {
        size_bad = true;
    }

    runtime_candidate = helper_manifest_path_allowed(entry->path);
    if (entry->present && entry->expected_sha256[0] != '\0') {
        if (helper_sha256_file(entry->path,
                               entry->actual_sha256,
                               sizeof(entry->actual_sha256)) == 0) {
            entry->hash_checked = true;
            entry->hash_match = strcasecmp(entry->actual_sha256, entry->expected_sha256) == 0;
        } else {
            int saved_errno = errno;

            snprintf(entry->actual_sha256,
                     sizeof(entry->actual_sha256),
                     "hash-error:%d",
                     saved_errno);
            entry->hash_checked = true;
            entry->hash_match = false;
        }
    }

    if (!entry->manifest_path_allowed) {
        snprintf(entry->warning,
                 sizeof(entry->warning),
                 "manifest path outside runtime root");
        ++helper_warn_count;
    } else if (!entry->manifest_sha_valid) {
        snprintf(entry->warning,
                 sizeof(entry->warning),
                 "manifest sha256 invalid");
        ++helper_warn_count;
    } else if (entry->present && mode_bad) {
        snprintf(entry->warning,
                 sizeof(entry->warning),
                 "mode mismatch expected=%04o actual=%04o",
                 entry->expected_mode,
                 entry->actual_mode);
        ++helper_warn_count;
    } else if (entry->present && size_bad) {
        snprintf(entry->warning,
                 sizeof(entry->warning),
                 "size mismatch expected=%lld actual=%lld",
                 entry->expected_size,
                 entry->actual_size);
        ++helper_warn_count;
    } else if (entry->present && entry->expected_sha256[0] == '\0' && runtime_candidate) {
        snprintf(entry->warning,
                 sizeof(entry->warning),
                 "runtime helper sha256 required before preference");
        ++helper_warn_count;
    } else if (entry->present &&
               entry->expected_sha256[0] != '\0' &&
               (!entry->hash_checked || !entry->hash_match)) {
        snprintf(entry->warning,
                 sizeof(entry->warning),
                 "sha256 mismatch expected=%s actual=%s",
                 entry->expected_sha256,
                 entry->actual_sha256);
        ++helper_warn_count;
    }

    trusted_runtime_candidate = entry->executable &&
                                runtime_candidate &&
                                entry->manifest_path_allowed &&
                                entry->manifest_sha_valid &&
                                !mode_bad &&
                                !size_bad &&
                                entry->expected_sha256[0] != '\0' &&
                                entry->hash_checked &&
                                entry->hash_match;

    if (trusted_runtime_candidate) {
        snprintf(entry->preferred, sizeof(entry->preferred), "%s", entry->path);
    } else if (entry->fallback_present) {
        snprintf(entry->preferred, sizeof(entry->preferred), "%s", entry->fallback);
    } else {
        entry->preferred[0] = '\0';
    }

    if (entry->required && entry->preferred[0] == '\0') {
        if (entry->warning[0] == '\0') {
            snprintf(entry->warning, sizeof(entry->warning), "required helper unavailable");
        }
        ++helper_fail_count;
    }
}

int a90_helper_scan(void) {
    int index;

    memset(helper_entries, 0, sizeof(helper_entries));
    helper_count = 0;
    helper_warn_count = 0;
    helper_fail_count = 0;
    helper_scanned = true;
    helper_add_defaults();
    helper_set_manifest_path();
    helper_load_manifest();

    for (index = 0; index < helper_count; ++index) {
        helper_finalize_entry(&helper_entries[index]);
    }

    snprintf(helper_summary_text,
             sizeof(helper_summary_text),
             "helpers: entries=%d warn=%d fail=%d manifest=%s path=%s",
             helper_count,
             helper_warn_count,
             helper_fail_count,
             helper_manifest_present ? "yes" : "no",
             helper_manifest_path[0] != '\0' ? "set" : "none");
    a90_logf("helper", "%s", helper_summary_text);
    return helper_fail_count > 0 ? -EIO : 0;
}

static void helper_scan_if_needed(void) {
    if (!helper_scanned) {
        (void)a90_helper_scan();
    }
}

int a90_helper_count(void) {
    helper_scan_if_needed();
    return helper_count;
}

int a90_helper_entry_at(int index, struct a90_helper_entry *out) {
    helper_scan_if_needed();
    if (out == NULL || index < 0 || index >= helper_count) {
        errno = EINVAL;
        return -EINVAL;
    }
    *out = helper_entries[index];
    return 0;
}

int a90_helper_find(const char *name, struct a90_helper_entry *out) {
    int index;

    helper_scan_if_needed();
    if (name == NULL || out == NULL) {
        errno = EINVAL;
        return -EINVAL;
    }
    for (index = 0; index < helper_count; ++index) {
        if (strcmp(helper_entries[index].name, name) == 0) {
            *out = helper_entries[index];
            return 0;
        }
    }
    errno = ENOENT;
    return -ENOENT;
}

const char *a90_helper_manifest_path(void) {
    helper_scan_if_needed();
    return helper_manifest_path;
}

const char *a90_helper_deploy_log_path(void) {
    helper_scan_if_needed();
    return helper_deploy_log_path;
}

const char *a90_helper_preferred_path(const char *name, const char *fallback) {
    static char selected[PATH_MAX];
    struct a90_helper_entry entry;

    if (a90_helper_find(name, &entry) == 0 && entry.preferred[0] != '\0') {
        snprintf(selected, sizeof(selected), "%s", entry.preferred);
        return selected;
    }
    snprintf(selected, sizeof(selected), "%s", fallback != NULL ? fallback : "");
    return selected;
}

void a90_helper_summary(char *out, size_t out_size) {
    helper_scan_if_needed();
    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out,
             out_size,
             "entries=%d warn=%d fail=%d manifest=%s",
             helper_count,
             helper_warn_count,
             helper_fail_count,
             helper_manifest_present ? "yes" : "no");
}

bool a90_helper_has_failures(void) {
    helper_scan_if_needed();
    return helper_fail_count > 0;
}

bool a90_helper_has_warnings(void) {
    helper_scan_if_needed();
    return helper_warn_count > 0;
}

int a90_helper_print_inventory(bool verbose) {
    int index;

    (void)a90_helper_scan();
    a90_console_printf("helpers: entries=%d warn=%d fail=%d manifest=%s\r\n",
            helper_count,
            helper_warn_count,
            helper_fail_count,
            helper_manifest_present ? "yes" : "no");
    a90_console_printf("helpers: manifest_path=%s\r\n", helper_manifest_path);
    a90_console_printf("helpers: deploy_log=%s\r\n", helper_deploy_log_path);
    if (!verbose) {
        return helper_fail_count > 0 ? -EIO : 0;
    }
    for (index = 0; index < helper_count; ++index) {
        const struct a90_helper_entry *entry = &helper_entries[index];

        a90_console_printf("helper: name=%s role=%s present=%s exec=%s required=%s path=%s\r\n",
                entry->name,
                entry->role,
                entry->present ? "yes" : "no",
                entry->executable ? "yes" : "no",
                entry->required ? "yes" : "no",
                entry->path);
        a90_console_printf("helper: name=%s preferred=%s fallback=%s fallback_present=%s mode=%04o size=%lld sha=%s hash_checked=%s hash_match=%s path_allowed=%s\r\n",
                entry->name,
                entry->preferred[0] != '\0' ? entry->preferred : "-",
                entry->fallback[0] != '\0' ? entry->fallback : "-",
                entry->fallback_present ? "yes" : "no",
                entry->actual_mode,
                entry->actual_size,
                entry->actual_sha256[0] != '\0' ? entry->actual_sha256 : "-",
                entry->hash_checked ? "yes" : "no",
                entry->hash_match ? "yes" : "no",
                entry->manifest_path_allowed ? "yes" : "no");
        if (entry->warning[0] != '\0') {
            a90_console_printf("helper: name=%s warning=%s\r\n",
                    entry->name,
                    entry->warning);
        }
    }
    return helper_fail_count > 0 ? -EIO : 0;
}

int a90_helper_print_manifest_template(void) {
    int index;

    (void)a90_helper_scan();
    a90_console_printf("helpers: manifest_path=%s present=%s\r\n",
            helper_manifest_path,
            helper_manifest_present ? "yes" : "no");
    a90_console_printf("helpers: deploy_log=%s\r\n", helper_deploy_log_path);
    a90_console_printf("helpers: line_format=name path role required sha256 mode size\r\n");
    for (index = 0; index < helper_count; ++index) {
        const struct a90_helper_entry *entry = &helper_entries[index];
        unsigned int mode = entry->present ? entry->actual_mode : entry->expected_mode;
        long long size = entry->present ? entry->actual_size : entry->expected_size;

        a90_console_printf("manifest: %s %s %s %s %s %04o %lld\r\n",
                entry->name,
                entry->path,
                entry->role,
                entry->required ? "yes" : "no",
                entry->expected_sha256[0] != '\0' ? entry->expected_sha256 : "-",
                mode,
                size);
        if (entry->preferred[0] != '\0' && strcmp(entry->preferred, entry->path) != 0) {
            a90_console_printf("deploy: %s copy_from=%s copy_to=%s\r\n",
                    entry->name,
                    entry->preferred,
                    entry->path);
        }
    }
    return helper_fail_count > 0 ? -EIO : 0;
}

int a90_helper_cmd_helpers(char **argv, int argc) {
    bool verbose = false;
    bool verify = false;
    struct a90_helper_entry entry;

    if (argc <= 1 ||
        strcmp(argv[1], "status") == 0) {
        return a90_helper_print_inventory(false);
    }
    if (strcmp(argv[1], "verbose") == 0) {
        return a90_helper_print_inventory(true);
    }
    if (strcmp(argv[1], "manifest") == 0 ||
        strcmp(argv[1], "plan") == 0) {
        return a90_helper_print_manifest_template();
    }
    if (strcmp(argv[1], "path") == 0) {
        if (argc != 3) {
            a90_console_printf("usage: helpers path <name>\r\n");
            return -EINVAL;
        }
        if (a90_helper_find(argv[2], &entry) < 0) {
            a90_console_printf("helpers: %s not found\r\n", argv[2]);
            return -ENOENT;
        }
        a90_console_printf("helper: name=%s preferred=%s path=%s fallback=%s\r\n",
                entry.name,
                entry.preferred[0] != '\0' ? entry.preferred : "-",
                entry.path,
                entry.fallback[0] != '\0' ? entry.fallback : "-");
        return entry.preferred[0] != '\0' ? 0 : -ENOENT;
    }
    if (strcmp(argv[1], "verify") == 0) {
        verify = true;
        verbose = true;
        if (argc == 3) {
            if (a90_helper_find(argv[2], &entry) < 0) {
                a90_console_printf("helpers: %s not found\r\n", argv[2]);
                return -ENOENT;
            }
            a90_console_printf("helper: name=%s present=%s exec=%s preferred=%s hash_checked=%s hash_match=%s warning=%s\r\n",
                    entry.name,
                    entry.present ? "yes" : "no",
                    entry.executable ? "yes" : "no",
                    entry.preferred[0] != '\0' ? entry.preferred : "-",
                    entry.hash_checked ? "yes" : "no",
                    entry.hash_match ? "yes" : "no",
                    entry.warning[0] != '\0' ? entry.warning : "-");
            return entry.required && entry.warning[0] != '\0' ? -EIO : 0;
        }
    }
    if (verify && argc == 2) {
        return a90_helper_print_inventory(verbose);
    }
    a90_console_printf("usage: helpers [status|verbose|manifest|plan|path <name>|verify [name]]\r\n");
    return -EINVAL;
}
