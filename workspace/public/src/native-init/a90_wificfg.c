#include "a90_wificfg.h"

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#include <unistd.h>

#include "a90_console.h"
#include "a90_log.h"
#include "a90_util.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#ifndef O_DIRECTORY
#define O_DIRECTORY 0
#endif

#define WIFICFG_PRIMARY_ROOT "/mnt/sdext/a90/config/wifi"
#define WIFICFG_PRIMARY_AUTOCONNECT WIFICFG_PRIMARY_ROOT "/autoconnect.conf"
#define WIFICFG_PRIMARY_PROFILES WIFICFG_PRIMARY_ROOT "/profiles"
#define WIFICFG_PRIMARY_SECRET_ROOT "/mnt/sdext/a90/secrets/wifi"
#define WIFICFG_PRIMARY_A90_ROOT "/mnt/sdext/a90"
#define WIFICFG_PRIMARY_CONFIG_ROOT "/mnt/sdext/a90/config"
#define WIFICFG_PRIMARY_SECRET_PARENT "/mnt/sdext/a90/secrets"
#define WIFICFG_CACHE_ROOT "/cache/a90-wifi/config"
#define WIFICFG_CACHE_AUTOCONNECT WIFICFG_CACHE_ROOT "/autoconnect.conf"
#define WIFICFG_CACHE_PROFILES WIFICFG_CACHE_ROOT "/profiles"
#define WIFICFG_RUNTIME_ROOT "/cache/a90-wifi"
#define WIFICFG_SUPPLICANT_TMP "/cache/a90-wifi/wpa_supplicant.conf.tmp"
#define WIFICFG_SUPPLICANT_CTRL_DIR "/cache/a90-wifi/sockets"
#define WIFICFG_ENOSPC_INPLACE_FALLBACK_MARKER "wifi-config-enospc-inplace-fallback"
#define WIFICFG_WIFI_UID 1010
#define WIFICFG_WIFI_GID 1010

#define WIFICFG_MAX_TEXT 8192
#define WIFICFG_MAX_VALUE 192
#define WIFICFG_MAX_PATH 384
#define WIFICFG_PROFILE_LIST_MAX 64
#define WIFICFG_SECRET_MAX_TEXT 256
#define WIFICFG_PSK_HEX_LEN 64

struct wificfg_sha1_ctx {
    uint32_t state[5];
    uint64_t bit_count;
    unsigned char buffer[64];
    size_t buffer_len;
};

struct wificfg_file_info {
    bool exists;
    bool is_regular;
    bool is_dir;
    bool is_symlink;
    bool path_components_safe;
    bool mode_owner_only;
    bool openable;
    mode_t mode;
    off_t size;
};

struct wificfg_global_config {
    bool exists;
    bool parsed;
    bool from_primary;
    bool from_cache;
    bool version_set;
    bool autoconnect_set;
    bool default_profile_set;
    bool connect_timeout_set;
    bool dhcp_set;
    bool external_ping_set;
    bool scan_before_connect_set;
    bool retry_count_set;
    int version;
    int autoconnect;
    int connect_timeout_sec;
    int dhcp;
    int external_ping;
    int scan_before_connect;
    int retry_count;
    int invalid_lines;
    int unknown_keys;
    char default_profile[WIFICFG_MAX_VALUE];
};

struct wificfg_profile_config {
    bool exists;
    bool parsed;
    bool from_primary;
    bool from_cache;
    bool version_set;
    bool enabled_set;
    bool ssid_file_set;
    bool psk_file_set;
    bool band_set;
    bool priority_set;
    bool key_mgmt_set;
    bool inline_secret_key_seen;
    int version;
    int enabled;
    int priority;
    int invalid_lines;
    int unknown_keys;
    char ssid_file[WIFICFG_MAX_PATH];
    char psk_file[WIFICFG_MAX_PATH];
    char band[WIFICFG_MAX_VALUE];
    char key_mgmt[WIFICFG_MAX_VALUE];
};

static uint32_t wificfg_sha1_rotl(uint32_t value, unsigned int shift) {
    return (value << shift) | (value >> (32U - shift));
}

static uint32_t wificfg_sha1_load32(const unsigned char *data) {
    return ((uint32_t)data[0] << 24) |
           ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) |
           (uint32_t)data[3];
}

static void wificfg_sha1_store32(unsigned char *out, uint32_t value) {
    out[0] = (unsigned char)(value >> 24);
    out[1] = (unsigned char)(value >> 16);
    out[2] = (unsigned char)(value >> 8);
    out[3] = (unsigned char)value;
}

static void wificfg_sha1_transform(struct wificfg_sha1_ctx *ctx,
                                   const unsigned char block[64]) {
    uint32_t words[80];
    uint32_t state_a = ctx->state[0];
    uint32_t state_b = ctx->state[1];
    uint32_t state_c = ctx->state[2];
    uint32_t state_d = ctx->state[3];
    uint32_t state_e = ctx->state[4];
    size_t index;

    for (index = 0; index < 16; ++index) {
        words[index] = wificfg_sha1_load32(block + index * 4);
    }
    for (index = 16; index < 80; ++index) {
        words[index] = wificfg_sha1_rotl(words[index - 3] ^
                                         words[index - 8] ^
                                         words[index - 14] ^
                                         words[index - 16],
                                         1);
    }

    for (index = 0; index < 80; ++index) {
        uint32_t function_value;
        uint32_t constant;
        uint32_t temp;

        if (index < 20) {
            function_value = (state_b & state_c) | ((~state_b) & state_d);
            constant = 0x5a827999U;
        } else if (index < 40) {
            function_value = state_b ^ state_c ^ state_d;
            constant = 0x6ed9eba1U;
        } else if (index < 60) {
            function_value = (state_b & state_c) | (state_b & state_d) | (state_c & state_d);
            constant = 0x8f1bbcdcU;
        } else {
            function_value = state_b ^ state_c ^ state_d;
            constant = 0xca62c1d6U;
        }

        temp = wificfg_sha1_rotl(state_a, 5) + function_value + state_e + constant + words[index];
        state_e = state_d;
        state_d = state_c;
        state_c = wificfg_sha1_rotl(state_b, 30);
        state_b = state_a;
        state_a = temp;
    }

    ctx->state[0] += state_a;
    ctx->state[1] += state_b;
    ctx->state[2] += state_c;
    ctx->state[3] += state_d;
    ctx->state[4] += state_e;
}

static void wificfg_sha1_init(struct wificfg_sha1_ctx *ctx) {
    ctx->state[0] = 0x67452301U;
    ctx->state[1] = 0xefcdab89U;
    ctx->state[2] = 0x98badcfeU;
    ctx->state[3] = 0x10325476U;
    ctx->state[4] = 0xc3d2e1f0U;
    ctx->bit_count = 0;
    ctx->buffer_len = 0;
}

static void wificfg_sha1_update(struct wificfg_sha1_ctx *ctx,
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
            wificfg_sha1_transform(ctx, ctx->buffer);
            ctx->buffer_len = 0;
        }
    }
}

static void wificfg_sha1_final(struct wificfg_sha1_ctx *ctx,
                               unsigned char digest[20]) {
    unsigned char length_block[8];
    size_t index;

    for (index = 0; index < 8; ++index) {
        length_block[7 - index] = (unsigned char)(ctx->bit_count >> (index * 8));
    }

    ctx->buffer[ctx->buffer_len++] = 0x80;
    if (ctx->buffer_len > 56) {
        while (ctx->buffer_len < sizeof(ctx->buffer)) {
            ctx->buffer[ctx->buffer_len++] = 0;
        }
        wificfg_sha1_transform(ctx, ctx->buffer);
        ctx->buffer_len = 0;
    }
    while (ctx->buffer_len < 56) {
        ctx->buffer[ctx->buffer_len++] = 0;
    }
    memcpy(ctx->buffer + 56, length_block, sizeof(length_block));
    wificfg_sha1_transform(ctx, ctx->buffer);

    for (index = 0; index < 5; ++index) {
        wificfg_sha1_store32(digest + index * 4, ctx->state[index]);
    }
}

static void wificfg_hmac_sha1(const unsigned char *key,
                              size_t key_len,
                              const unsigned char *data_a,
                              size_t data_a_len,
                              const unsigned char *data_b,
                              size_t data_b_len,
                              unsigned char digest[20]) {
    unsigned char normalized_key[64];
    unsigned char key_hash[20];
    unsigned char ipad[64];
    unsigned char opad[64];
    unsigned char inner_digest[20];
    struct wificfg_sha1_ctx ctx;
    size_t index;

    memset(normalized_key, 0, sizeof(normalized_key));
    if (key_len > sizeof(normalized_key)) {
        wificfg_sha1_init(&ctx);
        wificfg_sha1_update(&ctx, key, key_len);
        wificfg_sha1_final(&ctx, key_hash);
        memcpy(normalized_key, key_hash, sizeof(key_hash));
    } else if (key_len > 0) {
        memcpy(normalized_key, key, key_len);
    }

    for (index = 0; index < sizeof(normalized_key); ++index) {
        ipad[index] = normalized_key[index] ^ 0x36U;
        opad[index] = normalized_key[index] ^ 0x5cU;
    }

    wificfg_sha1_init(&ctx);
    wificfg_sha1_update(&ctx, ipad, sizeof(ipad));
    if (data_a != NULL && data_a_len > 0) {
        wificfg_sha1_update(&ctx, data_a, data_a_len);
    }
    if (data_b != NULL && data_b_len > 0) {
        wificfg_sha1_update(&ctx, data_b, data_b_len);
    }
    wificfg_sha1_final(&ctx, inner_digest);

    wificfg_sha1_init(&ctx);
    wificfg_sha1_update(&ctx, opad, sizeof(opad));
    wificfg_sha1_update(&ctx, inner_digest, sizeof(inner_digest));
    wificfg_sha1_final(&ctx, digest);
}

static void wificfg_pbkdf2_sha1(const unsigned char *passphrase,
                                size_t passphrase_len,
                                const unsigned char *ssid,
                                size_t ssid_len,
                                unsigned char out[32]) {
    unsigned char block_index_bytes[4];
    unsigned char digest[20];
    unsigned char xor_digest[20];
    size_t block_index;
    size_t output_offset = 0;

    for (block_index = 1; output_offset < 32; ++block_index) {
        size_t digest_index;
        unsigned int iteration;
        size_t copy_len;

        block_index_bytes[0] = (unsigned char)(block_index >> 24);
        block_index_bytes[1] = (unsigned char)(block_index >> 16);
        block_index_bytes[2] = (unsigned char)(block_index >> 8);
        block_index_bytes[3] = (unsigned char)block_index;

        wificfg_hmac_sha1(passphrase,
                          passphrase_len,
                          ssid,
                          ssid_len,
                          block_index_bytes,
                          sizeof(block_index_bytes),
                          digest);
        memcpy(xor_digest, digest, sizeof(xor_digest));

        for (iteration = 1; iteration < 4096; ++iteration) {
            wificfg_hmac_sha1(passphrase,
                              passphrase_len,
                              digest,
                              sizeof(digest),
                              NULL,
                              0,
                              digest);
            for (digest_index = 0; digest_index < sizeof(xor_digest); ++digest_index) {
                xor_digest[digest_index] ^= digest[digest_index];
            }
        }

        copy_len = (32 - output_offset) < sizeof(xor_digest) ? (32 - output_offset) : sizeof(xor_digest);
        memcpy(out + output_offset, xor_digest, copy_len);
        output_offset += copy_len;
    }
}

static void wificfg_hex_encode(const unsigned char *data,
                               size_t data_len,
                               char *out,
                               size_t out_size) {
    static const char hex_chars[] = "0123456789abcdef";
    size_t index;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (out_size < data_len * 2 + 1) {
        return;
    }
    for (index = 0; index < data_len; ++index) {
        out[index * 2] = hex_chars[(data[index] >> 4) & 0x0fU];
        out[index * 2 + 1] = hex_chars[data[index] & 0x0fU];
    }
    out[data_len * 2] = '\0';
}

static void wificfg_defaults(struct wificfg_global_config *config) {
    memset(config, 0, sizeof(*config));
    config->version = 1;
    config->autoconnect = 0;
    config->connect_timeout_sec = 35;
    config->dhcp = 0;
    config->external_ping = 0;
    config->scan_before_connect = 1;
    config->retry_count = 1;
}

static void wificfg_profile_defaults(struct wificfg_profile_config *profile) {
    memset(profile, 0, sizeof(*profile));
    profile->version = 1;
    profile->enabled = 1;
    profile->priority = 0;
    snprintf(profile->band, sizeof(profile->band), "%s", "any");
    snprintf(profile->key_mgmt, sizeof(profile->key_mgmt), "%s", "WPA-PSK");
}

static bool wificfg_path_components_safe(const char *path, bool include_final);

static void wificfg_stat_path(const char *path, struct wificfg_file_info *info) {
    struct stat statbuf;

    memset(info, 0, sizeof(*info));
    info->path_components_safe = wificfg_path_components_safe(path, true);
    if (!info->path_components_safe) {
        return;
    }
    if (lstat(path, &statbuf) < 0) {
        return;
    }

    info->exists = true;
    info->mode = statbuf.st_mode & 07777;
    info->size = statbuf.st_size;
    info->is_regular = S_ISREG(statbuf.st_mode);
    info->is_dir = S_ISDIR(statbuf.st_mode);
    info->is_symlink = S_ISLNK(statbuf.st_mode);
    info->mode_owner_only = (info->mode & 0077) == 0;
}

static int wificfg_read_regular_text(const char *path, char *buf, size_t buf_size) {
    struct stat statbuf;
    int fd;
    ssize_t bytes_read;

    if (buf_size == 0) {
        errno = EINVAL;
        return -1;
    }
    if (!wificfg_path_components_safe(path, true)) {
        errno = ELOOP;
        return -1;
    }
    if (lstat(path, &statbuf) < 0) {
        return -1;
    }
    if (!S_ISREG(statbuf.st_mode) || S_ISLNK(statbuf.st_mode)) {
        errno = EINVAL;
        return -1;
    }

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -1;
    }
    bytes_read = read(fd, buf, buf_size - 1);
    close(fd);
    if (bytes_read < 0) {
        return -1;
    }
    buf[bytes_read] = '\0';
    return 0;
}

static char *wificfg_trim(char *text) {
    char *end;

    while (*text != '\0' && isspace((unsigned char)*text)) {
        ++text;
    }
    end = text + strlen(text);
    while (end > text && isspace((unsigned char)end[-1])) {
        --end;
    }
    *end = '\0';
    return text;
}

static bool wificfg_parse_boolish(const char *value, int *out) {
    if (strcmp(value, "1") == 0 ||
        strcmp(value, "true") == 0 ||
        strcmp(value, "yes") == 0 ||
        strcmp(value, "on") == 0) {
        *out = 1;
        return true;
    }
    if (strcmp(value, "0") == 0 ||
        strcmp(value, "false") == 0 ||
        strcmp(value, "no") == 0 ||
        strcmp(value, "off") == 0) {
        *out = 0;
        return true;
    }
    return false;
}

static bool wificfg_parse_int(const char *value, int min_value, int max_value, int *out) {
    char *end = NULL;
    long parsed;

    errno = 0;
    parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return false;
    }
    if (parsed < min_value || parsed > max_value) {
        return false;
    }
    *out = (int)parsed;
    return true;
}

static bool wificfg_copy_value(char *destination, size_t destination_size, const char *value) {
    size_t value_len = strlen(value);

    if (destination_size == 0 || value_len >= destination_size) {
        return false;
    }
    memcpy(destination, value, value_len + 1);
    return true;
}

static bool wificfg_profile_name_valid(const char *name) {
    size_t index;

    if (name == NULL || name[0] == '\0' || strlen(name) >= 96) {
        return false;
    }
    for (index = 0; name[index] != '\0'; ++index) {
        unsigned char character = (unsigned char)name[index];

        if (!(isalnum(character) || character == '_' || character == '-' || character == '.')) {
            return false;
        }
    }
    return true;
}

static bool wificfg_path_has_prefix(const char *path, const char *prefix) {
    size_t prefix_len = strlen(prefix);

    return strncmp(path, prefix, prefix_len) == 0 &&
           (path[prefix_len] == '\0' || path[prefix_len] == '/');
}

static bool wificfg_path_has_suffix(const char *path, const char *suffix) {
    size_t path_len = strlen(path);
    size_t suffix_len = strlen(suffix);

    return path_len >= suffix_len &&
           strcmp(path + path_len - suffix_len, suffix) == 0;
}

static bool wificfg_path_components_safe(const char *path, bool include_final) {
    char current[WIFICFG_MAX_PATH];
    size_t path_len;
    size_t index;

    if (path == NULL || path[0] != '/') {
        return false;
    }
    path_len = strlen(path);
    if (path_len == 0 || path_len >= sizeof(current)) {
        return false;
    }
    if (strstr(path, "/../") != NULL ||
        strstr(path, "/./") != NULL ||
        strstr(path, "//") != NULL ||
        wificfg_path_has_suffix(path, "/..") ||
        wificfg_path_has_suffix(path, "/.")) {
        return false;
    }

    for (index = 1; index <= path_len; ++index) {
        struct stat statbuf;

        if (path[index] != '/' && path[index] != '\0') {
            continue;
        }
        if (path[index] == '\0' && !include_final) {
            break;
        }
        if (index >= sizeof(current)) {
            return false;
        }
        memcpy(current, path, index);
        current[index] = '\0';
        if (lstat(current, &statbuf) < 0) {
            if (errno == ENOENT || errno == ENOTDIR) {
                return true;
            }
            return false;
        }
        if (S_ISLNK(statbuf.st_mode)) {
            errno = ELOOP;
            return false;
        }
    }
    return true;
}

static bool wificfg_secret_path_safe(const char *path) {
    if (path == NULL || path[0] != '/' || strstr(path, "/../") != NULL) {
        return false;
    }
    if (strstr(path, "/./") != NULL ||
        strstr(path, "//") != NULL ||
        wificfg_path_has_suffix(path, "/..") ||
        wificfg_path_has_suffix(path, "/.")) {
        return false;
    }
    if (!wificfg_path_components_safe(path, true)) {
        return false;
    }
    return wificfg_path_has_prefix(path, WIFICFG_PRIMARY_SECRET_ROOT) ||
           wificfg_path_has_prefix(path, WIFICFG_CACHE_ROOT);
}

static void wificfg_join_profile_path(char *destination,
                                      size_t destination_size,
                                      const char *root,
                                      const char *profile_name) {
    snprintf(destination, destination_size, "%s/%s.conf", root, profile_name);
}

static bool wificfg_parse_global_pair(struct wificfg_global_config *config,
                                      const char *key,
                                      const char *value) {
    int parsed_int;

    if (strcmp(key, "version") == 0) {
        if (!wificfg_parse_int(value, 1, 99, &parsed_int)) {
            return false;
        }
        config->version = parsed_int;
        config->version_set = true;
        return true;
    }
    if (strcmp(key, "autoconnect") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->autoconnect = parsed_int;
        config->autoconnect_set = true;
        return true;
    }
    if (strcmp(key, "default_profile") == 0) {
        if (!wificfg_profile_name_valid(value) ||
            !wificfg_copy_value(config->default_profile, sizeof(config->default_profile), value)) {
            return false;
        }
        config->default_profile_set = true;
        return true;
    }
    if (strcmp(key, "connect_timeout_sec") == 0) {
        if (!wificfg_parse_int(value, 5, 180, &parsed_int)) {
            return false;
        }
        config->connect_timeout_sec = parsed_int;
        config->connect_timeout_set = true;
        return true;
    }
    if (strcmp(key, "dhcp") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->dhcp = parsed_int;
        config->dhcp_set = true;
        return true;
    }
    if (strcmp(key, "external_ping") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->external_ping = parsed_int;
        config->external_ping_set = true;
        return true;
    }
    if (strcmp(key, "scan_before_connect") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->scan_before_connect = parsed_int;
        config->scan_before_connect_set = true;
        return true;
    }
    if (strcmp(key, "retry_count") == 0) {
        if (!wificfg_parse_int(value, 0, 5, &parsed_int)) {
            return false;
        }
        config->retry_count = parsed_int;
        config->retry_count_set = true;
        return true;
    }

    config->unknown_keys++;
    return true;
}

static bool wificfg_parse_profile_pair(struct wificfg_profile_config *profile,
                                       const char *key,
                                       const char *value) {
    int parsed_int;

    if (strcmp(key, "version") == 0) {
        if (!wificfg_parse_int(value, 1, 99, &parsed_int)) {
            return false;
        }
        profile->version = parsed_int;
        profile->version_set = true;
        return true;
    }
    if (strcmp(key, "enabled") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        profile->enabled = parsed_int;
        profile->enabled_set = true;
        return true;
    }
    if (strcmp(key, "ssid_file") == 0) {
        if (!wificfg_copy_value(profile->ssid_file, sizeof(profile->ssid_file), value)) {
            return false;
        }
        profile->ssid_file_set = true;
        return true;
    }
    if (strcmp(key, "psk_file") == 0) {
        if (!wificfg_copy_value(profile->psk_file, sizeof(profile->psk_file), value)) {
            return false;
        }
        profile->psk_file_set = true;
        return true;
    }
    if (strcmp(key, "band") == 0) {
        if (!(strcmp(value, "2.4g") == 0 ||
              strcmp(value, "5g") == 0 ||
              strcmp(value, "6g") == 0 ||
              strcmp(value, "any") == 0) ||
            !wificfg_copy_value(profile->band, sizeof(profile->band), value)) {
            return false;
        }
        profile->band_set = true;
        return true;
    }
    if (strcmp(key, "priority") == 0) {
        if (!wificfg_parse_int(value, -1000, 1000, &parsed_int)) {
            return false;
        }
        profile->priority = parsed_int;
        profile->priority_set = true;
        return true;
    }
    if (strcmp(key, "key_mgmt") == 0) {
        if (!(strcmp(value, "WPA-PSK") == 0 ||
              strcmp(value, "SAE") == 0 ||
              strcmp(value, "WPA-PSK SAE") == 0) ||
            !wificfg_copy_value(profile->key_mgmt, sizeof(profile->key_mgmt), value)) {
            return false;
        }
        profile->key_mgmt_set = true;
        return true;
    }
    if (strcmp(key, "ssid") == 0 ||
        strcmp(key, "psk") == 0 ||
        strcmp(key, "password") == 0) {
        profile->inline_secret_key_seen = true;
        return true;
    }

    profile->unknown_keys++;
    return true;
}

static int wificfg_parse_lines(char *text,
                               bool profile_mode,
                               struct wificfg_global_config *global_config,
                               struct wificfg_profile_config *profile_config) {
    char *saveptr = NULL;
    char *line = strtok_r(text, "\n", &saveptr);

    while (line != NULL) {
        char *trimmed = wificfg_trim(line);
        char *separator;
        char *key;
        char *value;
        bool parsed;

        trim_newline(trimmed);
        if (trimmed[0] == '\0' || trimmed[0] == '#' || trimmed[0] == ';') {
            line = strtok_r(NULL, "\n", &saveptr);
            continue;
        }

        separator = strchr(trimmed, '=');
        if (separator == NULL) {
            if (profile_mode) {
                profile_config->invalid_lines++;
            } else {
                global_config->invalid_lines++;
            }
            line = strtok_r(NULL, "\n", &saveptr);
            continue;
        }

        *separator = '\0';
        key = wificfg_trim(trimmed);
        value = wificfg_trim(separator + 1);
        if (key[0] == '\0') {
            if (profile_mode) {
                profile_config->invalid_lines++;
            } else {
                global_config->invalid_lines++;
            }
            line = strtok_r(NULL, "\n", &saveptr);
            continue;
        }

        parsed = profile_mode ?
            wificfg_parse_profile_pair(profile_config, key, value) :
            wificfg_parse_global_pair(global_config, key, value);
        if (!parsed) {
            if (profile_mode) {
                profile_config->invalid_lines++;
            } else {
                global_config->invalid_lines++;
            }
        }

        line = strtok_r(NULL, "\n", &saveptr);
    }

    return 0;
}

static int wificfg_load_global(struct wificfg_global_config *config) {
    char text[WIFICFG_MAX_TEXT];

    wificfg_defaults(config);
    if (wificfg_read_regular_text(WIFICFG_PRIMARY_AUTOCONNECT, text, sizeof(text)) == 0) {
        config->exists = true;
        config->from_primary = true;
        wificfg_parse_lines(text, false, config, NULL);
        config->parsed = config->invalid_lines == 0;
        return 0;
    }
    if (wificfg_read_regular_text(WIFICFG_CACHE_AUTOCONNECT, text, sizeof(text)) == 0) {
        config->exists = true;
        config->from_cache = true;
        wificfg_parse_lines(text, false, config, NULL);
        config->parsed = config->invalid_lines == 0;
        return 0;
    }
    return -ENOENT;
}

static int wificfg_load_profile_by_name(const char *profile_name,
                                        struct wificfg_profile_config *profile,
                                        char *profile_path,
                                        size_t profile_path_size) {
    char text[WIFICFG_MAX_TEXT];

    wificfg_profile_defaults(profile);
    if (!wificfg_profile_name_valid(profile_name)) {
        return -EINVAL;
    }

    wificfg_join_profile_path(profile_path, profile_path_size, WIFICFG_PRIMARY_PROFILES, profile_name);
    if (wificfg_read_regular_text(profile_path, text, sizeof(text)) == 0) {
        profile->exists = true;
        profile->from_primary = true;
        wificfg_parse_lines(text, true, NULL, profile);
        profile->parsed = profile->invalid_lines == 0;
        return 0;
    }

    wificfg_join_profile_path(profile_path, profile_path_size, WIFICFG_CACHE_PROFILES, profile_name);
    if (wificfg_read_regular_text(profile_path, text, sizeof(text)) == 0) {
        profile->exists = true;
        profile->from_cache = true;
        wificfg_parse_lines(text, true, NULL, profile);
        profile->parsed = profile->invalid_lines == 0;
        return 0;
    }

    return -ENOENT;
}

static int wificfg_load_profile(const struct wificfg_global_config *config,
                                struct wificfg_profile_config *profile,
                                char *profile_path,
                                size_t profile_path_size) {
    wificfg_profile_defaults(profile);
    if (!config->default_profile_set) {
        return -EINVAL;
    }
    return wificfg_load_profile_by_name(config->default_profile, profile, profile_path, profile_path_size);
}

static const char *wificfg_source_name(const struct wificfg_global_config *config) {
    if (config->from_primary) {
        return "primary";
    }
    if (config->from_cache) {
        return "cache";
    }
    return "none";
}

static const char *wificfg_profile_source_name(const struct wificfg_profile_config *profile) {
    if (profile->from_primary) {
        return "primary";
    }
    if (profile->from_cache) {
        return "cache";
    }
    return "none";
}

static const char *wificfg_path_kind(const struct wificfg_file_info *info) {
    if (!info->path_components_safe) {
        return "unsafe";
    }
    if (!info->exists) {
        return "missing";
    }
    if (info->is_symlink) {
        return "symlink";
    }
    if (info->is_dir) {
        return "dir";
    }
    if (info->is_regular) {
        return "file";
    }
    return "other";
}

static void wificfg_print_path_info(const char *label, const char *path, bool show_path) {
    struct wificfg_file_info info;

    wificfg_stat_path(path, &info);
    if (show_path) {
        a90_console_printf("%s.path=%s\r\n", label, path);
    }
    a90_console_printf("%s.path_components_safe=%d\r\n",
                       label,
                       info.path_components_safe ? 1 : 0);
    a90_console_printf("%s.kind=%s\r\n", label, wificfg_path_kind(&info));
    if (info.exists) {
        a90_console_printf("%s.mode=0%03o\r\n", label, (unsigned int)info.mode);
        a90_console_printf("%s.owner_only=%d\r\n", label, info.mode_owner_only ? 1 : 0);
    }
}

static bool wificfg_secret_status(const char *label, const char *path, bool configured) {
    struct wificfg_file_info info;
    bool safe_path;
    bool usable;

    a90_console_printf("%s.configured=%d\r\n", label, configured ? 1 : 0);
    if (!configured) {
        a90_console_printf("%s.present=0\r\n", label);
        a90_console_printf("%s.path_safe=0\r\n", label);
        a90_console_printf("%s.mode_ok=0\r\n", label);
        return false;
    }

    safe_path = wificfg_secret_path_safe(path);
    a90_console_printf("%s.path_safe=%d\r\n", label, safe_path ? 1 : 0);
    if (!safe_path) {
        a90_console_printf("%s.present=0\r\n", label);
        a90_console_printf("%s.mode_ok=0\r\n", label);
        return false;
    }

    wificfg_stat_path(path, &info);
    usable = info.exists && info.is_regular && !info.is_symlink && info.mode_owner_only;
    a90_console_printf("%s.present=%d\r\n", label, info.exists ? 1 : 0);
    a90_console_printf("%s.path_components_safe=%d\r\n",
                       label,
                       info.path_components_safe ? 1 : 0);
    if (info.exists) {
        a90_console_printf("%s.kind=%s\r\n", label, wificfg_path_kind(&info));
        a90_console_printf("%s.mode=0%03o\r\n", label, (unsigned int)info.mode);
    }
    a90_console_printf("%s.mode_ok=%d\r\n", label, usable ? 1 : 0);
    return usable;
}

static void wificfg_print_profile_fields(const char *label_prefix,
                                         const struct wificfg_profile_config *profile,
                                         const char *profile_path,
                                         bool include_secret_status,
                                         bool *ssid_usable_out,
                                         bool *psk_usable_out) {
    bool ssid_usable = false;
    bool psk_usable = false;

    a90_console_printf("%s_source=%s\r\n", label_prefix, wificfg_profile_source_name(profile));
    a90_console_printf("%s_present=%d\r\n", label_prefix, profile->exists ? 1 : 0);
    a90_console_printf("%s_valid=%d\r\n", label_prefix, profile->exists && profile->parsed ? 1 : 0);
    if (profile->exists) {
        wificfg_print_path_info("profile_file", profile_path, false);
        a90_console_printf("%s_enabled=%d%s\r\n",
                           label_prefix,
                           profile->enabled,
                           profile->enabled_set ? "" : " default");
        a90_console_printf("%s_band=%s%s\r\n",
                           label_prefix,
                           profile->band,
                           profile->band_set ? "" : " default");
        a90_console_printf("%s_priority=%d%s\r\n",
                           label_prefix,
                           profile->priority,
                           profile->priority_set ? "" : " default");
        a90_console_printf("%s_key_mgmt=%s%s\r\n",
                           label_prefix,
                           profile->key_mgmt,
                           profile->key_mgmt_set ? "" : " default");
        a90_console_printf("%s_inline_secret_key_seen=%d\r\n",
                           label_prefix,
                           profile->inline_secret_key_seen ? 1 : 0);
        a90_console_printf("%s_invalid_lines=%d\r\n", label_prefix, profile->invalid_lines);
        a90_console_printf("%s_unknown_keys=%d\r\n", label_prefix, profile->unknown_keys);
        if (include_secret_status) {
            ssid_usable = wificfg_secret_status("ssid_file", profile->ssid_file, profile->ssid_file_set);
            psk_usable = wificfg_secret_status("psk_file", profile->psk_file, profile->psk_file_set);
        }
    } else {
        a90_console_printf("%s_enabled=0\r\n", label_prefix);
        a90_console_printf("%s_inline_secret_key_seen=0\r\n", label_prefix);
        if (include_secret_status) {
            a90_console_printf("ssid_file.configured=0\r\n");
            a90_console_printf("ssid_file.present=0\r\n");
            a90_console_printf("psk_file.configured=0\r\n");
            a90_console_printf("psk_file.present=0\r\n");
        }
    }
    if (ssid_usable_out != NULL) {
        *ssid_usable_out = ssid_usable;
    }
    if (psk_usable_out != NULL) {
        *psk_usable_out = psk_usable;
    }
}

static void wificfg_secure_zero(void *data, size_t data_size) {
    volatile unsigned char *cursor = (volatile unsigned char *)data;

    while (data_size > 0) {
        *cursor++ = 0;
        --data_size;
    }
}

static int wificfg_prepare_dir_owned(const char *path, mode_t mode, uid_t uid, gid_t gid) {
    int fd;
    int rc = 0;

    if (ensure_dir(path, mode) < 0) {
        return negative_errno_or(EIO);
    }
    fd = open(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fchown(fd, uid, gid) < 0) {
        rc = -errno;
    }
    if (rc == 0 && fchmod(fd, mode) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static bool wificfg_hex_string(const char *text) {
    size_t index;

    if (text == NULL || strlen(text) != WIFICFG_PSK_HEX_LEN) {
        return false;
    }
    for (index = 0; text[index] != '\0'; ++index) {
        if (!isxdigit((unsigned char)text[index])) {
            return false;
        }
    }
    return true;
}

static int wificfg_read_secret_value(const char *path, char *out, size_t out_size) {
    struct wificfg_file_info info;

    if (!wificfg_secret_path_safe(path)) {
        return -EINVAL;
    }
    wificfg_stat_path(path, &info);
    if (!info.exists || !info.is_regular || info.is_symlink || !info.mode_owner_only) {
        return -EACCES;
    }
    if (info.size <= 0 || info.size >= (off_t)out_size) {
        return -EFBIG;
    }
    if (wificfg_read_regular_text(path, out, out_size) < 0) {
        return negative_errno_or(EIO);
    }
    trim_newline(out);
    if (out[0] == '\0') {
        return -EINVAL;
    }
    return 0;
}

static bool wificfg_validate_profile_for_prepare(const struct wificfg_profile_config *profile,
                                                 int profile_rc,
                                                 int *reason_errno) {
    if (profile_rc < 0) {
        *reason_errno = -profile_rc;
        return false;
    }
    if (!profile->parsed) {
        *reason_errno = EINVAL;
        return false;
    }
    if (profile->enabled == 0 || profile->inline_secret_key_seen) {
        *reason_errno = EACCES;
        return false;
    }
    if (!profile->ssid_file_set || !profile->psk_file_set) {
        *reason_errno = ENOENT;
        return false;
    }
    if (strcmp(profile->key_mgmt, "WPA-PSK") != 0) {
        *reason_errno = EOPNOTSUPP;
        return false;
    }
    *reason_errno = 0;
    return true;
}

static int wificfg_build_psk_hex(const char *ssid,
                                 const char *psk_text,
                                 char *psk_hex,
                                 size_t psk_hex_size,
                                 const char **format_out) {
    unsigned char derived[32];
    size_t ssid_len = strlen(ssid);
    size_t psk_len = strlen(psk_text);

    if (ssid_len == 0 || ssid_len > 32) {
        return -EINVAL;
    }
    if (wificfg_hex_string(psk_text)) {
        if (!wificfg_copy_value(psk_hex, psk_hex_size, psk_text)) {
            return -ENOSPC;
        }
        *format_out = "psk256-hex";
        return 0;
    }
    if (psk_len < 8 || psk_len > 63) {
        return -EINVAL;
    }
    wificfg_pbkdf2_sha1((const unsigned char *)psk_text,
                        psk_len,
                        (const unsigned char *)ssid,
                        ssid_len,
                        derived);
    wificfg_hex_encode(derived, sizeof(derived), psk_hex, psk_hex_size);
    wificfg_secure_zero(derived, sizeof(derived));
    if (psk_hex[0] == '\0') {
        return -ENOSPC;
    }
    *format_out = "passphrase-pbkdf2-sha1";
    return 0;
}

static bool wificfg_storage_pressure_rc(int rc) {
    return rc == -ENOSPC || rc == -EDQUOT;
}

static int wificfg_write_supplicant_text_inplace(const char *text, size_t text_len) {
    struct stat st;
    int fd;
    int rc = 0;

    fd = open(A90_WIFICFG_SUPPLICANT_CONF, O_WRONLY | O_TRUNC | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return negative_errno_or(EIO);
    }
    if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode)) {
        int saved_errno = errno == 0 ? EACCES : errno;

        close(fd);
        errno = saved_errno;
        return -saved_errno;
    }
    if (fchown(fd, 0, 0) < 0 || fchmod(fd, 0600) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    if (write_all_checked(fd, text, text_len) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    (void)fsync(fd);
    if (close(fd) < 0) {
        rc = negative_errno_or(EIO);
    }
    return rc;
}

static int wificfg_write_supplicant_text_storage_fallback(char *text,
                                                          size_t text_len,
                                                          size_t *bytes_out,
                                                          int original_rc) {
    int rc;

    rc = wificfg_write_supplicant_text_inplace(text, text_len);
    a90_console_printf("wifi_config_cache_fallback=%s original_rc=%d rc=%d\r\n",
                       WIFICFG_ENOSPC_INPLACE_FALLBACK_MARKER,
                       original_rc,
                       rc);
    if (rc == 0 && bytes_out != NULL) {
        *bytes_out = text_len;
    }
    return rc;
}

static int wificfg_write_supplicant_text(const char *ssid_hex,
                                         const char *psk_hex,
                                         const char *key_mgmt,
                                         size_t *bytes_out) {
    char text[1024];
    int text_len;
    int fd;
    int rc;

    rc = wificfg_prepare_dir_owned(WIFICFG_RUNTIME_ROOT, 0755, 0, 0);
    if (rc < 0) {
        return rc;
    }
    rc = wificfg_prepare_dir_owned(WIFICFG_SUPPLICANT_CTRL_DIR,
                                   0770,
                                   WIFICFG_WIFI_UID,
                                   WIFICFG_WIFI_GID);
    if (rc < 0) {
        return rc;
    }

    text_len = snprintf(text,
                        sizeof(text),
                        "ctrl_interface=DIR=%s GROUP=wifi\n"
                        "update_config=0\n"
                        "ap_scan=1\n"
                        "network={\n"
                        "    ssid=%s\n"
                        "    disabled=0\n"
                        "    scan_ssid=1\n"
                        "    key_mgmt=%s\n"
                        "    psk=%s\n"
                        "}\n",
                        WIFICFG_SUPPLICANT_CTRL_DIR,
                        ssid_hex,
                        key_mgmt,
                        psk_hex);
    if (text_len < 0 || (size_t)text_len >= sizeof(text)) {
        return -ENOSPC;
    }

    (void)unlink(WIFICFG_SUPPLICANT_TMP);
    fd = open(WIFICFG_SUPPLICANT_TMP,
              O_WRONLY | O_CREAT | O_EXCL | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        rc = negative_errno_or(EIO);
        if (wificfg_storage_pressure_rc(rc)) {
            rc = wificfg_write_supplicant_text_storage_fallback(text,
                                                                (size_t)text_len,
                                                                bytes_out,
                                                                rc);
        }
        wificfg_secure_zero(text, sizeof(text));
        return rc;
    }
    if (write_all_checked(fd, text, (size_t)text_len) < 0) {
        int saved_errno = errno;

        close(fd);
        (void)unlink(WIFICFG_SUPPLICANT_TMP);
        errno = saved_errno;
        rc = negative_errno_or(EIO);
        if (wificfg_storage_pressure_rc(rc)) {
            rc = wificfg_write_supplicant_text_storage_fallback(text,
                                                                (size_t)text_len,
                                                                bytes_out,
                                                                rc);
        }
        wificfg_secure_zero(text, sizeof(text));
        return rc;
    }
    if (fchown(fd, 0, 0) < 0 ||
        fchmod(fd, 0600) < 0) {
        int saved_errno = errno;

        close(fd);
        (void)unlink(WIFICFG_SUPPLICANT_TMP);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    (void)fsync(fd);
    if (close(fd) < 0) {
        (void)unlink(WIFICFG_SUPPLICANT_TMP);
        rc = negative_errno_or(EIO);
        if (wificfg_storage_pressure_rc(rc)) {
            rc = wificfg_write_supplicant_text_storage_fallback(text,
                                                                (size_t)text_len,
                                                                bytes_out,
                                                                rc);
        }
        wificfg_secure_zero(text, sizeof(text));
        return rc;
    }
    if (rename(WIFICFG_SUPPLICANT_TMP, A90_WIFICFG_SUPPLICANT_CONF) < 0) {
        int saved_errno = errno;

        (void)unlink(WIFICFG_SUPPLICANT_TMP);
        errno = saved_errno;
        rc = negative_errno_or(EIO);
        if (wificfg_storage_pressure_rc(rc)) {
            rc = wificfg_write_supplicant_text_storage_fallback(text,
                                                                (size_t)text_len,
                                                                bytes_out,
                                                                rc);
        }
        wificfg_secure_zero(text, sizeof(text));
        return rc;
    }
    (void)chmod(A90_WIFICFG_SUPPLICANT_CONF, 0600);
    if (bytes_out != NULL) {
        *bytes_out = (size_t)text_len;
    }
    wificfg_secure_zero(text, sizeof(text));
    return 0;
}

int a90_wificfg_prepare_supplicant_config(const char *profile_name,
                                          char *out_path,
                                          size_t out_path_size) {
    struct wificfg_global_config global_config;
    struct wificfg_profile_config profile;
    char profile_path[WIFICFG_MAX_PATH] = "";
    char selected_profile[WIFICFG_MAX_VALUE] = "";
    char ssid[WIFICFG_SECRET_MAX_TEXT];
    char psk_text[WIFICFG_SECRET_MAX_TEXT];
    char ssid_hex[WIFICFG_SECRET_MAX_TEXT * 2];
    char psk_hex[WIFICFG_PSK_HEX_LEN + 1];
    const char *psk_format = "";
    int profile_rc;
    int reason_errno = 0;
    int ssid_rc;
    int psk_rc;
    int psk_build_rc;
    int write_rc;
    size_t generated_bytes = 0;

    memset(ssid, 0, sizeof(ssid));
    memset(psk_text, 0, sizeof(psk_text));
    memset(ssid_hex, 0, sizeof(ssid_hex));
    memset(psk_hex, 0, sizeof(psk_hex));
    (void)wificfg_load_global(&global_config);

    if (profile_name != NULL && profile_name[0] != '\0') {
        if (!wificfg_profile_name_valid(profile_name) ||
            !wificfg_copy_value(selected_profile, sizeof(selected_profile), profile_name)) {
            return -EINVAL;
        }
    } else if (global_config.default_profile_set) {
        if (!wificfg_copy_value(selected_profile, sizeof(selected_profile), global_config.default_profile)) {
            return -EINVAL;
        }
    } else {
        return -ENOENT;
    }

    profile_rc = wificfg_load_profile_by_name(selected_profile, &profile, profile_path, sizeof(profile_path));
    if (!wificfg_validate_profile_for_prepare(&profile, profile_rc, &reason_errno)) {
        return -reason_errno;
    }

    ssid_rc = wificfg_read_secret_value(profile.ssid_file, ssid, sizeof(ssid));
    psk_rc = wificfg_read_secret_value(profile.psk_file, psk_text, sizeof(psk_text));
    if (ssid_rc < 0 || psk_rc < 0) {
        wificfg_secure_zero(ssid, sizeof(ssid));
        wificfg_secure_zero(psk_text, sizeof(psk_text));
        return ssid_rc < 0 ? ssid_rc : psk_rc;
    }

    wificfg_hex_encode((const unsigned char *)ssid, strlen(ssid), ssid_hex, sizeof(ssid_hex));
    if (ssid_hex[0] == '\0') {
        wificfg_secure_zero(ssid, sizeof(ssid));
        wificfg_secure_zero(psk_text, sizeof(psk_text));
        return -EINVAL;
    }
    psk_build_rc = wificfg_build_psk_hex(ssid, psk_text, psk_hex, sizeof(psk_hex), &psk_format);
    if (psk_build_rc < 0) {
        wificfg_secure_zero(ssid, sizeof(ssid));
        wificfg_secure_zero(psk_text, sizeof(psk_text));
        wificfg_secure_zero(psk_hex, sizeof(psk_hex));
        return psk_build_rc;
    }

    write_rc = wificfg_write_supplicant_text(ssid_hex, psk_hex, profile.key_mgmt, &generated_bytes);
    wificfg_secure_zero(ssid, sizeof(ssid));
    wificfg_secure_zero(psk_text, sizeof(psk_text));
    wificfg_secure_zero(psk_hex, sizeof(psk_hex));
    if (write_rc < 0) {
        return write_rc;
    }

    if (out_path != NULL && out_path_size > 0) {
        snprintf(out_path, out_path_size, "%s", A90_WIFICFG_SUPPLICANT_CONF);
    }
    a90_logf("wificfg",
             "prepare profile=%s source=%s bytes=%ld psk_format=%s secret_values_logged=0",
             selected_profile,
             wificfg_profile_source_name(&profile),
             (long)generated_bytes,
             psk_format);
    return 0;
}

static const char *wificfg_decision(const struct wificfg_global_config *config,
                                    const struct wificfg_profile_config *profile,
                                    bool profile_loaded,
                                    bool ssid_usable,
                                    bool psk_usable) {
    if (!config->exists) {
        return "wifi-config-no-autoconnect-config";
    }
    if (!config->parsed) {
        return "wifi-config-invalid-global";
    }
    if (config->autoconnect == 0) {
        return "wifi-config-disabled";
    }
    if (config->external_ping != 0) {
        return "wifi-config-external-ping-blocked";
    }
    if (!config->default_profile_set) {
        return "wifi-config-needs-default-profile";
    }
    if (!profile_loaded) {
        return "wifi-config-missing-profile";
    }
    if (!profile->parsed) {
        return "wifi-config-invalid-profile";
    }
    if (profile->inline_secret_key_seen) {
        return "wifi-config-inline-secret-blocked";
    }
    if (profile->enabled == 0) {
        return "wifi-config-profile-disabled";
    }
    if (!ssid_usable || !psk_usable) {
        return "wifi-config-secret-not-ready";
    }
    return "wifi-config-ready";
}

int a90_wificfg_print_status(void) {
    struct wificfg_global_config config;
    struct wificfg_profile_config profile;
    char profile_path[WIFICFG_MAX_PATH] = "";
    int config_rc;
    int profile_rc;
    bool ssid_usable = false;
    bool psk_usable = false;

    config_rc = wificfg_load_global(&config);
    profile_rc = wificfg_load_profile(&config, &profile, profile_path, sizeof(profile_path));

    a90_console_printf("[wifi config]\r\n");
    wificfg_print_path_info("primary_config_root", WIFICFG_PRIMARY_ROOT, true);
    wificfg_print_path_info("primary_secret_root", WIFICFG_PRIMARY_SECRET_ROOT, true);
    wificfg_print_path_info("cache_config_root", WIFICFG_CACHE_ROOT, true);
    wificfg_print_path_info("runtime_root", WIFICFG_RUNTIME_ROOT, true);
    a90_console_printf("active_config_source=%s\r\n", wificfg_source_name(&config));
    a90_console_printf("autoconnect_config_present=%d\r\n", config.exists ? 1 : 0);
    a90_console_printf("autoconnect_config_valid=%d\r\n", config.exists && config.parsed ? 1 : 0);
    a90_console_printf("autoconnect_config_rc=%d\r\n", config_rc);
    a90_console_printf("version=%d%s\r\n", config.version, config.version_set ? "" : " default");
    a90_console_printf("autoconnect=%d%s\r\n", config.autoconnect, config.autoconnect_set ? "" : " default");
    a90_console_printf("default_profile_set=%d\r\n", config.default_profile_set ? 1 : 0);
    if (config.default_profile_set) {
        a90_console_printf("default_profile=%s\r\n", config.default_profile);
    }
    a90_console_printf("connect_timeout_sec=%d%s\r\n",
                       config.connect_timeout_sec,
                       config.connect_timeout_set ? "" : " default");
    a90_console_printf("dhcp=%d%s\r\n", config.dhcp, config.dhcp_set ? "" : " default");
    a90_console_printf("external_ping=%d%s\r\n",
                       config.external_ping,
                       config.external_ping_set ? "" : " default");
    a90_console_printf("scan_before_connect=%d%s\r\n",
                       config.scan_before_connect,
                       config.scan_before_connect_set ? "" : " default");
    a90_console_printf("retry_count=%d%s\r\n", config.retry_count, config.retry_count_set ? "" : " default");
    a90_console_printf("global_invalid_lines=%d\r\n", config.invalid_lines);
    a90_console_printf("global_unknown_keys=%d\r\n", config.unknown_keys);

    a90_console_printf("profile_source=%s\r\n", wificfg_profile_source_name(&profile));
    a90_console_printf("profile_present=%d\r\n", profile.exists ? 1 : 0);
    a90_console_printf("profile_valid=%d\r\n", profile.exists && profile.parsed ? 1 : 0);
    a90_console_printf("profile_rc=%d\r\n", profile_rc);
    if (profile.exists) {
        wificfg_print_path_info("profile_file", profile_path, false);
        a90_console_printf("profile_enabled=%d%s\r\n", profile.enabled, profile.enabled_set ? "" : " default");
        a90_console_printf("profile_band=%s%s\r\n", profile.band, profile.band_set ? "" : " default");
        a90_console_printf("profile_priority=%d%s\r\n", profile.priority, profile.priority_set ? "" : " default");
        a90_console_printf("profile_key_mgmt=%s%s\r\n", profile.key_mgmt, profile.key_mgmt_set ? "" : " default");
        a90_console_printf("profile_inline_secret_key_seen=%d\r\n", profile.inline_secret_key_seen ? 1 : 0);
        a90_console_printf("profile_invalid_lines=%d\r\n", profile.invalid_lines);
        a90_console_printf("profile_unknown_keys=%d\r\n", profile.unknown_keys);
        ssid_usable = wificfg_secret_status("ssid_file", profile.ssid_file, profile.ssid_file_set);
        psk_usable = wificfg_secret_status("psk_file", profile.psk_file, profile.psk_file_set);
    } else {
        a90_console_printf("profile_enabled=0\r\n");
        a90_console_printf("profile_inline_secret_key_seen=0\r\n");
        a90_console_printf("ssid_file.configured=0\r\n");
        a90_console_printf("ssid_file.present=0\r\n");
        a90_console_printf("psk_file.configured=0\r\n");
        a90_console_printf("psk_file.present=0\r\n");
    }

    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=%s\r\n",
                       wificfg_decision(&config, &profile, profile_rc == 0, ssid_usable, psk_usable));
    a90_logf("wificfg",
             "status source=%s autoconnect=%d profile_present=%d decision=%s",
             wificfg_source_name(&config),
             config.autoconnect,
             profile.exists ? 1 : 0,
             wificfg_decision(&config, &profile, profile_rc == 0, ssid_usable, psk_usable));
    return 0;
}

static const char *wificfg_profile_decision(const struct wificfg_profile_config *profile,
                                            int profile_rc,
                                            bool ssid_usable,
                                            bool psk_usable) {
    if (profile_rc < 0) {
        return "wifi-profile-missing";
    }
    if (!profile->parsed) {
        return "wifi-profile-invalid";
    }
    if (profile->inline_secret_key_seen) {
        return "wifi-profile-inline-secret-blocked";
    }
    if (profile->enabled == 0) {
        return "wifi-profile-disabled";
    }
    if (!ssid_usable || !psk_usable) {
        return "wifi-profile-secret-not-ready";
    }
    if (strcmp(profile->key_mgmt, "WPA-PSK") != 0) {
        return "wifi-profile-key-mgmt-unsupported";
    }
    return "wifi-profile-ready";
}

static bool wificfg_secret_usable_silent(const char *path, bool configured) {
    struct wificfg_file_info info;

    if (!configured || !wificfg_secret_path_safe(path)) {
        return false;
    }
    wificfg_stat_path(path, &info);
    return info.exists && info.is_regular && !info.is_symlink && info.mode_owner_only;
}

static void wificfg_collect_profile_entry(const char *source,
                                          const char *profile_name,
                                          struct a90_wificfg_profile_summary *out) {
    struct wificfg_profile_config profile;
    char profile_path[WIFICFG_MAX_PATH] = "";
    bool ssid_usable = false;
    bool psk_usable = false;
    int profile_rc;
    const char *decision;

    memset(out, 0, sizeof(*out));
    if (!wificfg_copy_value(out->name, sizeof(out->name), profile_name)) {
        snprintf(out->name, sizeof(out->name), "%s", "invalid");
    }
    snprintf(out->source_hint, sizeof(out->source_hint), "%s", source);
    profile_rc = wificfg_load_profile_by_name(profile_name,
                                              &profile,
                                              profile_path,
                                              sizeof(profile_path));
    ssid_usable = wificfg_secret_usable_silent(profile.ssid_file, profile.ssid_file_set);
    psk_usable = wificfg_secret_usable_silent(profile.psk_file, profile.psk_file_set);
    decision = wificfg_profile_decision(&profile, profile_rc, ssid_usable, psk_usable);

    out->exists = profile.exists;
    out->parsed = profile.parsed;
    out->ssid_file_configured = profile.ssid_file_set;
    out->psk_file_configured = profile.psk_file_set;
    out->ssid_usable = ssid_usable;
    out->psk_usable = psk_usable;
    out->load_rc = profile_rc;
    out->enabled = profile.enabled;
    out->priority = profile.priority;
    snprintf(out->source, sizeof(out->source), "%s", wificfg_profile_source_name(&profile));
    snprintf(out->band, sizeof(out->band), "%s", profile.band);
    snprintf(out->key_mgmt, sizeof(out->key_mgmt), "%s", profile.key_mgmt);
    snprintf(out->decision, sizeof(out->decision), "%s", decision);
}

static void wificfg_print_profile_entry(const char *source,
                                        const char *profile_name,
                                        int *index_inout) {
    struct wificfg_profile_config profile;
    char profile_path[WIFICFG_MAX_PATH] = "";
    int profile_rc;

    profile_rc = wificfg_load_profile_by_name(profile_name, &profile, profile_path, sizeof(profile_path));
    a90_console_printf("profile.%d.name=%s\r\n", *index_inout, profile_name);
    a90_console_printf("profile.%d.source_hint=%s\r\n", *index_inout, source);
    a90_console_printf("profile.%d.load_rc=%d\r\n", *index_inout, profile_rc);
    a90_console_printf("profile.%d.source=%s\r\n", *index_inout, wificfg_profile_source_name(&profile));
    a90_console_printf("profile.%d.enabled=%d%s\r\n",
                       *index_inout,
                       profile.enabled,
                       profile.enabled_set ? "" : " default");
    a90_console_printf("profile.%d.band=%s%s\r\n",
                       *index_inout,
                       profile.band,
                       profile.band_set ? "" : " default");
    a90_console_printf("profile.%d.priority=%d%s\r\n",
                       *index_inout,
                       profile.priority,
                       profile.priority_set ? "" : " default");
    a90_console_printf("profile.%d.key_mgmt=%s%s\r\n",
                       *index_inout,
                       profile.key_mgmt,
                       profile.key_mgmt_set ? "" : " default");
    a90_console_printf("profile.%d.ssid_file_configured=%d\r\n",
                       *index_inout,
                       profile.ssid_file_set ? 1 : 0);
    a90_console_printf("profile.%d.psk_file_configured=%d\r\n",
                       *index_inout,
                       profile.psk_file_set ? 1 : 0);
    (*index_inout)++;
}

static bool wificfg_profile_list_record_seen(char seen_names[][WIFICFG_MAX_VALUE],
                                             int *seen_count,
                                             int *duplicate_count,
                                             int *overflow_count,
                                             const char *profile_name);

static void wificfg_collect_profile_dir(const char *source,
                                        const char *dir_path,
                                        struct a90_wificfg_profile_list *out,
                                        char seen_names[][WIFICFG_MAX_VALUE],
                                        int *seen_count) {
    DIR *dir;
    struct dirent *entry;

    if (!wificfg_path_components_safe(dir_path, true)) {
        return;
    }
    dir = opendir(dir_path);
    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        size_t len = strlen(entry->d_name);
        char profile_name[WIFICFG_MAX_VALUE];
        bool recorded;

        if (len <= 5 || strcmp(entry->d_name + len - 5, ".conf") != 0) {
            continue;
        }
        if (len - 5 >= sizeof(profile_name)) {
            continue;
        }
        memcpy(profile_name, entry->d_name, len - 5);
        profile_name[len - 5] = '\0';
        if (!wificfg_profile_name_valid(profile_name)) {
            continue;
        }
        recorded = wificfg_profile_list_record_seen(seen_names,
                                                    seen_count,
                                                    &out->duplicate_count,
                                                    &out->overflow_count,
                                                    profile_name);
        if (!recorded) {
            continue;
        }
        if (out->stored_count < A90_WIFICFG_UI_MAX_PROFILES) {
            wificfg_collect_profile_entry(source,
                                          profile_name,
                                          &out->profiles[out->stored_count]);
            out->stored_count++;
        }
        out->profile_count++;
    }
    closedir(dir);
}

int a90_wificfg_collect_profile_list(struct a90_wificfg_profile_list *out) {
    char seen_names[WIFICFG_PROFILE_LIST_MAX][WIFICFG_MAX_VALUE];
    int seen_count = 0;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    memset(seen_names, 0, sizeof(seen_names));
    (void)a90_wificfg_get_autoconnect(&out->autoconnect, NULL);
    wificfg_collect_profile_dir("primary",
                                WIFICFG_PRIMARY_PROFILES,
                                out,
                                seen_names,
                                &seen_count);
    wificfg_collect_profile_dir("cache",
                                WIFICFG_CACHE_PROFILES,
                                out,
                                seen_names,
                                &seen_count);
    return 0;
}

static bool wificfg_profile_list_record_seen(char seen_names[][WIFICFG_MAX_VALUE],
                                             int *seen_count,
                                             int *duplicate_count,
                                             int *overflow_count,
                                             const char *profile_name) {
    int seen_index;

    for (seen_index = 0; seen_index < *seen_count; seen_index++) {
        if (strcmp(seen_names[seen_index], profile_name) == 0) {
            (*duplicate_count)++;
            return false;
        }
    }
    if (*seen_count >= WIFICFG_PROFILE_LIST_MAX) {
        (*overflow_count)++;
        return false;
    }
    if (!wificfg_copy_value(seen_names[*seen_count], WIFICFG_MAX_VALUE, profile_name)) {
        (*overflow_count)++;
        return false;
    }
    (*seen_count)++;
    return true;
}

static void wificfg_scan_profile_dir(const char *source,
                                     const char *dir_path,
                                     int *index_inout,
                                     char seen_names[][WIFICFG_MAX_VALUE],
                                     int *seen_count,
                                     int *duplicate_count,
                                     int *overflow_count) {
    DIR *dir;
    struct dirent *entry;

    if (!wificfg_path_components_safe(dir_path, true)) {
        return;
    }
    dir = opendir(dir_path);
    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        size_t len = strlen(entry->d_name);
        char profile_name[WIFICFG_MAX_VALUE];

        if (len <= 5 || strcmp(entry->d_name + len - 5, ".conf") != 0) {
            continue;
        }
        if (len - 5 >= sizeof(profile_name)) {
            continue;
        }
        memcpy(profile_name, entry->d_name, len - 5);
        profile_name[len - 5] = '\0';
        if (!wificfg_profile_name_valid(profile_name)) {
            continue;
        }
        if (!wificfg_profile_list_record_seen(seen_names,
                                              seen_count,
                                              duplicate_count,
                                              overflow_count,
                                              profile_name)) {
            continue;
        }
        wificfg_print_profile_entry(source, profile_name, index_inout);
    }
    closedir(dir);
}

int a90_wificfg_print_profile_list(void) {
    char seen_names[WIFICFG_PROFILE_LIST_MAX][WIFICFG_MAX_VALUE];
    int count = 0;
    int seen_count = 0;
    int duplicate_count = 0;
    int overflow_count = 0;

    memset(seen_names, 0, sizeof(seen_names));
    a90_console_printf("[wifi profile list]\r\n");
    a90_console_printf("primary_profiles.path=%s\r\n", WIFICFG_PRIMARY_PROFILES);
    a90_console_printf("cache_profiles.path=%s\r\n", WIFICFG_CACHE_PROFILES);
    a90_console_printf("secret_values_logged=0\r\n");
    wificfg_scan_profile_dir("primary",
                             WIFICFG_PRIMARY_PROFILES,
                             &count,
                             seen_names,
                             &seen_count,
                             &duplicate_count,
                             &overflow_count);
    wificfg_scan_profile_dir("cache",
                             WIFICFG_CACHE_PROFILES,
                             &count,
                             seen_names,
                             &seen_count,
                             &duplicate_count,
                             &overflow_count);
    a90_console_printf("profile_count=%d\r\n", count);
    a90_console_printf("profile_duplicates_skipped=%d\r\n", duplicate_count);
    a90_console_printf("profile_overflow_skipped=%d\r\n", overflow_count);
    a90_console_printf("decision=%s\r\n", count > 0 ? "wifi-profile-list-ready" : "wifi-profile-list-empty");
    return 0;
}

int a90_wificfg_print_profile_status(const char *profile_name) {
    struct wificfg_global_config config;
    struct wificfg_profile_config profile;
    char selected_profile[WIFICFG_MAX_VALUE] = "";
    char profile_path[WIFICFG_MAX_PATH] = "";
    bool ssid_usable = false;
    bool psk_usable = false;
    int profile_rc;

    (void)wificfg_load_global(&config);
    wificfg_profile_defaults(&profile);
    if (profile_name != NULL && profile_name[0] != '\0') {
        if (!wificfg_profile_name_valid(profile_name) ||
            !wificfg_copy_value(selected_profile, sizeof(selected_profile), profile_name)) {
            a90_console_printf("[wifi profile status]\r\n");
            a90_console_printf("profile=invalid\r\n");
            a90_console_printf("secret_values_logged=0\r\n");
            a90_console_printf("decision=wifi-profile-name-invalid\r\n");
            return -EINVAL;
        }
    } else if (config.default_profile_set) {
        if (!wificfg_copy_value(selected_profile, sizeof(selected_profile), config.default_profile)) {
            return -EINVAL;
        }
    } else {
        selected_profile[0] = '\0';
    }

    profile_rc = selected_profile[0] != '\0' ?
        wificfg_load_profile_by_name(selected_profile, &profile, profile_path, sizeof(profile_path)) :
        -ENOENT;

    a90_console_printf("[wifi profile status]\r\n");
    a90_console_printf("profile=%s\r\n", selected_profile[0] != '\0' ? selected_profile : "default");
    a90_console_printf("profile_rc=%d\r\n", profile_rc);
    wificfg_print_profile_fields("profile", &profile, profile_path, true, &ssid_usable, &psk_usable);
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=%s\r\n",
                       wificfg_profile_decision(&profile, profile_rc, ssid_usable, psk_usable));
    return strcmp(wificfg_profile_decision(&profile, profile_rc, ssid_usable, psk_usable),
                  "wifi-profile-ready") == 0 ? 0 : -EINVAL;
}

int a90_wificfg_get_autoconnect(struct a90_wificfg_autoconnect *out,
                                const char *profile_override) {
    struct wificfg_global_config config;
    struct wificfg_profile_config profile;
    char selected_profile[WIFICFG_MAX_VALUE] = "";
    char profile_path[WIFICFG_MAX_PATH] = "";
    bool ssid_usable = false;
    bool psk_usable = false;
    int config_rc;
    int profile_rc = -ENOENT;
    const char *decision;
    bool has_profile_override = profile_override != NULL && profile_override[0] != '\0';

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    wificfg_profile_defaults(&profile);
    config_rc = wificfg_load_global(&config);
    out->config_present = config.exists;
    out->config_valid = config.exists && config.parsed;
    out->enabled = config.autoconnect != 0;
    out->connect_timeout_sec = config.connect_timeout_sec;
    out->dhcp = config.dhcp;
    out->external_ping = config.external_ping;
    out->scan_before_connect = config.scan_before_connect;
    out->retry_count = config.retry_count;
    if (has_profile_override && !config.exists) {
        out->dhcp = 1;
        out->scan_before_connect = 1;
        out->retry_count = 1;
        out->connect_timeout_sec = 35;
    }

    if (has_profile_override) {
        if (!wificfg_profile_name_valid(profile_override) ||
            !wificfg_copy_value(selected_profile, sizeof(selected_profile), profile_override)) {
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-autoconnect-profile-name-invalid");
            return -EINVAL;
        }
    } else if (config.default_profile_set) {
        if (!wificfg_copy_value(selected_profile, sizeof(selected_profile), config.default_profile)) {
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-autoconnect-profile-name-invalid");
            return -EINVAL;
        }
    }

    if (selected_profile[0] != '\0') {
        if (!wificfg_copy_value(out->profile, sizeof(out->profile), selected_profile)) {
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-autoconnect-profile-name-invalid");
            return -EINVAL;
        }
        profile_rc = wificfg_load_profile_by_name(selected_profile, &profile, profile_path, sizeof(profile_path));
        if (profile_rc == 0 && profile.parsed && !profile.inline_secret_key_seen) {
            ssid_usable = wificfg_secret_usable_silent(profile.ssid_file, profile.ssid_file_set);
            psk_usable = wificfg_secret_usable_silent(profile.psk_file, profile.psk_file_set);
        }
    }
    out->profile_valid = profile_rc == 0 &&
        strcmp(wificfg_profile_decision(&profile, profile_rc, ssid_usable, psk_usable),
               "wifi-profile-ready") == 0;

    if ((config_rc < 0 || !config.exists) && !has_profile_override) {
        decision = "wifi-autoconnect-no-config";
    } else if (config.exists && !config.parsed) {
        decision = "wifi-autoconnect-invalid-config";
    } else if (config.autoconnect == 0 && !has_profile_override) {
        decision = "wifi-autoconnect-disabled";
    } else if (config.external_ping != 0) {
        decision = "wifi-autoconnect-external-ping-blocked";
    } else if (selected_profile[0] == '\0') {
        decision = "wifi-autoconnect-no-profile";
    } else if (!out->profile_valid) {
        decision = "wifi-autoconnect-profile-not-ready";
    } else {
        decision = "wifi-autoconnect-ready";
    }
    snprintf(out->decision, sizeof(out->decision), "%s", decision);
    return strcmp(decision, "wifi-autoconnect-ready") == 0 ? 0 : -EINVAL;
}

int a90_wificfg_print_autoconnect_status(void) {
    struct a90_wificfg_autoconnect config;
    (void)a90_wificfg_get_autoconnect(&config, NULL);

    a90_console_printf("[wifi autoconnect status]\r\n");
    a90_console_printf("config_present=%d\r\n", config.config_present ? 1 : 0);
    a90_console_printf("config_valid=%d\r\n", config.config_valid ? 1 : 0);
    a90_console_printf("autoconnect=%d\r\n", config.enabled ? 1 : 0);
    a90_console_printf("default_profile=%s\r\n", config.profile[0] != '\0' ? config.profile : "none");
    a90_console_printf("profile_valid=%d\r\n", config.profile_valid ? 1 : 0);
    a90_console_printf("connect_timeout_sec=%d\r\n", config.connect_timeout_sec);
    a90_console_printf("dhcp=%d\r\n", config.dhcp);
    a90_console_printf("external_ping=%d\r\n", config.external_ping);
    a90_console_printf("scan_before_connect=%d\r\n", config.scan_before_connect);
    a90_console_printf("retry_count=%d\r\n", config.retry_count);
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=%s\r\n", config.decision);
    return 0;
}

static int wificfg_ensure_primary_tree(void) {
    if (ensure_dir(WIFICFG_PRIMARY_A90_ROOT, 0700) < 0 ||
        ensure_dir(WIFICFG_PRIMARY_CONFIG_ROOT, 0700) < 0 ||
        ensure_dir(WIFICFG_PRIMARY_ROOT, 0700) < 0 ||
        ensure_dir(WIFICFG_PRIMARY_PROFILES, 0700) < 0 ||
        ensure_dir(WIFICFG_PRIMARY_SECRET_PARENT, 0700) < 0 ||
        ensure_dir(WIFICFG_PRIMARY_SECRET_ROOT, 0700) < 0) {
        return negative_errno_or(EIO);
    }
    (void)chmod(WIFICFG_PRIMARY_ROOT, 0700);
    (void)chmod(WIFICFG_PRIMARY_PROFILES, 0700);
    (void)chmod(WIFICFG_PRIMARY_SECRET_ROOT, 0700);
    return 0;
}

static int wificfg_write_autoconnect_file(const struct wificfg_global_config *config,
                                          const char *profile_name,
                                          bool enabled) {
    char tmp_path[WIFICFG_MAX_PATH];
    char text[1024];
    int text_len;
    int fd;
    int dhcp_value = config->dhcp_set ? config->dhcp : 1;

    text_len = snprintf(text,
                        sizeof(text),
                        "version=1\n"
                        "autoconnect=%d\n"
                        "%s%s%s"
                        "connect_timeout_sec=%d\n"
                        "dhcp=%d\n"
                        "external_ping=0\n"
                        "scan_before_connect=%d\n"
                        "retry_count=%d\n",
                        enabled ? 1 : 0,
                        profile_name != NULL && profile_name[0] != '\0' ? "default_profile=" : "",
                        profile_name != NULL && profile_name[0] != '\0' ? profile_name : "",
                        profile_name != NULL && profile_name[0] != '\0' ? "\n" : "",
                        config->connect_timeout_sec,
                        dhcp_value,
                        config->scan_before_connect,
                        config->retry_count);
    if (text_len < 0 || (size_t)text_len >= sizeof(text)) {
        return -ENOSPC;
    }

    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", WIFICFG_PRIMARY_AUTOCONNECT);
    (void)unlink(tmp_path);
    fd = open(tmp_path, O_WRONLY | O_CREAT | O_EXCL | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return negative_errno_or(EIO);
    }
    if (write_all_checked(fd, text, (size_t)text_len) < 0 ||
        fchmod(fd, 0600) < 0 ||
        fsync(fd) < 0) {
        int saved_errno = errno;

        close(fd);
        (void)unlink(tmp_path);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    if (close(fd) < 0) {
        (void)unlink(tmp_path);
        return negative_errno_or(EIO);
    }
    if (rename(tmp_path, WIFICFG_PRIMARY_AUTOCONNECT) < 0) {
        (void)unlink(tmp_path);
        return negative_errno_or(EIO);
    }
    (void)chmod(WIFICFG_PRIMARY_AUTOCONNECT, 0600);
    return 0;
}

int a90_wificfg_set_autoconnect(bool enabled, const char *profile_name) {
    struct wificfg_global_config config;
    struct a90_wificfg_autoconnect selected;
    char selected_profile[WIFICFG_MAX_VALUE] = "";
    int tree_rc;
    int write_rc;

    (void)wificfg_load_global(&config);
    if (enabled) {
        if (profile_name != NULL && profile_name[0] != '\0') {
            if (!wificfg_profile_name_valid(profile_name) ||
                !wificfg_copy_value(selected_profile, sizeof(selected_profile), profile_name)) {
                return -EINVAL;
            }
        } else if (config.default_profile_set) {
            if (!wificfg_copy_value(selected_profile, sizeof(selected_profile), config.default_profile)) {
                return -EINVAL;
            }
        } else {
            return -ENOENT;
        }
        if (a90_wificfg_get_autoconnect(&selected, selected_profile) < 0) {
            return -EINVAL;
        }
    } else if (config.default_profile_set) {
        (void)wificfg_copy_value(selected_profile, sizeof(selected_profile), config.default_profile);
    }

    tree_rc = wificfg_ensure_primary_tree();
    if (tree_rc < 0) {
        return tree_rc;
    }
    write_rc = wificfg_write_autoconnect_file(&config, selected_profile, enabled);
    if (write_rc == 0) {
        a90_logf("wificfg",
                 "autoconnect set enabled=%d profile=%s secret_values_logged=0",
                 enabled ? 1 : 0,
                 selected_profile[0] != '\0' ? selected_profile : "none");
    }
    return write_rc;
}

static int a90_wificfg_print_prepare(const char *profile_name) {
    char out_path[WIFICFG_MAX_PATH] = "";
    struct wificfg_file_info info;
    int rc;

    rc = a90_wificfg_prepare_supplicant_config(profile_name, out_path, sizeof(out_path));
    a90_console_printf("[wifi config prepare]\r\n");
    a90_console_printf("profile=%s\r\n",
                       profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default");
    a90_console_printf("supplicant_config.path=%s\r\n", A90_WIFICFG_SUPPLICANT_CONF);
    a90_console_printf("prepare_rc=%d\r\n", rc);
    if (rc == 0) {
        wificfg_stat_path(A90_WIFICFG_SUPPLICANT_CONF, &info);
        a90_console_printf("supplicant_config.present=%d\r\n", info.exists ? 1 : 0);
        if (info.exists) {
            a90_console_printf("supplicant_config.kind=%s\r\n", wificfg_path_kind(&info));
            a90_console_printf("supplicant_config.mode=0%03o\r\n", (unsigned int)info.mode);
            a90_console_printf("supplicant_config.owner_only=%d\r\n", info.mode_owner_only ? 1 : 0);
        }
        a90_console_printf("ctrl_interface.dir=%s\r\n", WIFICFG_SUPPLICANT_CTRL_DIR);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-config-supplicant-prepared\r\n");
        return 0;
    }

    a90_console_printf("supplicant_config.present=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=wifi-config-supplicant-prepare-failed\r\n");
    return rc;
}

int a90_wificfg_cmd(char **argv, int argc) {
    if (argc == 3 &&
        argv != NULL &&
        argv[1] != NULL &&
        argv[2] != NULL &&
        strcmp(argv[1], "config") == 0 &&
        strcmp(argv[2], "status") == 0) {
        return a90_wificfg_print_status();
    }
    if ((argc == 3 || argc == 4) &&
        argv != NULL &&
        argv[1] != NULL &&
        argv[2] != NULL &&
        strcmp(argv[1], "config") == 0 &&
        strcmp(argv[2], "prepare") == 0) {
        return a90_wificfg_print_prepare(argc == 4 ? argv[3] : NULL);
    }

    a90_console_printf("usage: wifi config [status|prepare [profile]]\r\n");
    return -EINVAL;
}
