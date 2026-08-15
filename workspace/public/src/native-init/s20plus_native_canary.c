#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif
#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define CANARY_SCHEMA "s20plus_native_canary_n1_result_v1"
#define INTENT_SCHEMA "s20plus_native_canary_n1_intent_v1"
#define BINDING_SCHEMA "s20plus_native_canary_n1_binding_v1"
#define PRODUCTION_STATE_DIR "/data/adb/s20plus-native-init/n1"
#define BINDING_NAME "binding.txt"
#define INTENT_NAME "intent.json"
#define RESULT_NAME "result.json"
#define PENDING_NAME ".result.pending"
#define BINDING_MAX 2048U
#define RESULT_MAX 8192U
#define OBSERVATION_MAX 512U

enum canary_exit {
    CANARY_OK = 0,
    CANARY_ALREADY_CONSUMED = 10,
    CANARY_STATE_REJECTED = 20,
    CANARY_BINDING_REJECTED = 21,
    CANARY_OBSERVATION_FAILED = 22,
    CANARY_PUBLISH_FAILED = 23,
};

struct sha256_ctx {
    uint32_t state[8];
    uint64_t bits;
    unsigned char block[64];
    size_t used;
};

struct n1_binding {
    char module_zip_sha256[65];
    uint64_t module_zip_size;
    char binary_sha256[65];
    uint64_t binary_size;
    char run_nonce[33];
    char pre_boot_id_sha256[65];
};

struct state_nodes {
    int binding;
    int intent;
    int result;
    int other;
};

static uint32_t rotr32(uint32_t value, unsigned int amount) {
    return (value >> amount) | (value << (32U - amount));
}

static void sha256_transform(struct sha256_ctx *ctx,
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
    uint32_t a;
    uint32_t b;
    uint32_t c;
    uint32_t d;
    uint32_t e;
    uint32_t f;
    uint32_t g;
    uint32_t h;
    size_t index;

    for (index = 0; index < 16U; ++index) {
        size_t offset = index * 4U;
        words[index] = ((uint32_t)block[offset] << 24U) |
                       ((uint32_t)block[offset + 1U] << 16U) |
                       ((uint32_t)block[offset + 2U] << 8U) |
                       (uint32_t)block[offset + 3U];
    }
    for (index = 16U; index < 64U; ++index) {
        uint32_t x = words[index - 15U];
        uint32_t y = words[index - 2U];
        uint32_t s0 = rotr32(x, 7U) ^ rotr32(x, 18U) ^ (x >> 3U);
        uint32_t s1 = rotr32(y, 17U) ^ rotr32(y, 19U) ^ (y >> 10U);
        words[index] = words[index - 16U] + s0 + words[index - 7U] + s1;
    }

    a = ctx->state[0];
    b = ctx->state[1];
    c = ctx->state[2];
    d = ctx->state[3];
    e = ctx->state[4];
    f = ctx->state[5];
    g = ctx->state[6];
    h = ctx->state[7];
    for (index = 0; index < 64U; ++index) {
        uint32_t s1 = rotr32(e, 6U) ^ rotr32(e, 11U) ^ rotr32(e, 25U);
        uint32_t choice = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + s1 + choice + constants[index] + words[index];
        uint32_t s0 = rotr32(a, 2U) ^ rotr32(a, 13U) ^ rotr32(a, 22U);
        uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = s0 + majority;
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

static void sha256_init(struct sha256_ctx *ctx) {
    static const uint32_t initial[8] = {
        0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
        0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U,
    };
    memcpy(ctx->state, initial, sizeof(initial));
    ctx->bits = 0U;
    ctx->used = 0U;
}

static void sha256_update(struct sha256_ctx *ctx,
                          const unsigned char *data,
                          size_t size) {
    while (size > 0U) {
        size_t available = 64U - ctx->used;
        size_t amount = size < available ? size : available;
        memcpy(ctx->block + ctx->used, data, amount);
        ctx->used += amount;
        ctx->bits += (uint64_t)amount * 8U;
        data += amount;
        size -= amount;
        if (ctx->used == 64U) {
            sha256_transform(ctx, ctx->block);
            ctx->used = 0U;
        }
    }
}

static void sha256_final(struct sha256_ctx *ctx, unsigned char digest[32]) {
    uint64_t bits = ctx->bits;
    size_t index;

    ctx->block[ctx->used++] = 0x80U;
    if (ctx->used > 56U) {
        memset(ctx->block + ctx->used, 0, 64U - ctx->used);
        sha256_transform(ctx, ctx->block);
        ctx->used = 0U;
    }
    memset(ctx->block + ctx->used, 0, 56U - ctx->used);
    for (index = 0; index < 8U; ++index) {
        ctx->block[63U - index] = (unsigned char)(bits >> (index * 8U));
    }
    sha256_transform(ctx, ctx->block);
    for (index = 0; index < 8U; ++index) {
        digest[index * 4U] = (unsigned char)(ctx->state[index] >> 24U);
        digest[index * 4U + 1U] = (unsigned char)(ctx->state[index] >> 16U);
        digest[index * 4U + 2U] = (unsigned char)(ctx->state[index] >> 8U);
        digest[index * 4U + 3U] = (unsigned char)ctx->state[index];
    }
}

static void digest_hex(const unsigned char digest[32], char out[65]) {
    static const char alphabet[] = "0123456789abcdef";
    size_t index;
    for (index = 0; index < 32U; ++index) {
        out[index * 2U] = alphabet[digest[index] >> 4U];
        out[index * 2U + 1U] = alphabet[digest[index] & 0x0fU];
    }
    out[64] = '\0';
}

static void sha256_bytes(const unsigned char *data, size_t size, char out[65]) {
    struct sha256_ctx ctx;
    unsigned char digest[32];
    sha256_init(&ctx);
    sha256_update(&ctx, data, size);
    sha256_final(&ctx, digest);
    digest_hex(digest, out);
}

static int write_all(int fd, const char *data, size_t size) {
    size_t written = 0U;
    while (written < size) {
        ssize_t amount = write(fd, data + written, size - written);
        if (amount < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (amount == 0) {
            errno = EIO;
            return -1;
        }
        written += (size_t)amount;
    }
    return 0;
}

static int read_all_fd(int fd, char *buffer, size_t capacity, size_t *size_out) {
    size_t used = 0U;
    for (;;) {
        ssize_t amount;
        if (used == capacity) {
            errno = EFBIG;
            return -1;
        }
        amount = read(fd, buffer + used, capacity - used);
        if (amount < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (amount == 0) {
            *size_out = used;
            return 0;
        }
        used += (size_t)amount;
    }
}

static int read_regular_at(int dir_fd,
                           const char *name,
                           uid_t owner,
                           gid_t group,
                           char *buffer,
                           size_t capacity,
                           size_t *size_out) {
    struct stat st;
    int fd = openat(dir_fd, name, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    int rc;
    if (fd < 0) {
        return -1;
    }
    rc = fstat(fd, &st);
    if (rc < 0 || !S_ISREG(st.st_mode) || st.st_nlink != 1 ||
        st.st_uid != owner || st.st_gid != group ||
        (st.st_mode & 0777) != 0600 || st.st_size < 1 ||
        (uint64_t)st.st_size > capacity) {
        (void)close(fd);
        errno = EPERM;
        return -1;
    }
    rc = read_all_fd(fd, buffer, capacity, size_out);
    if (close(fd) < 0 && rc == 0) {
        rc = -1;
    }
    return rc;
}

static int strict_hex(const char *text, size_t length) {
    size_t index;
    if (strlen(text) != length) {
        return 0;
    }
    for (index = 0; index < length; ++index) {
        if (!((text[index] >= '0' && text[index] <= '9') ||
              (text[index] >= 'a' && text[index] <= 'f'))) {
            return 0;
        }
    }
    return 1;
}

static int strict_u64(const char *text, uint64_t maximum, uint64_t *out) {
    uint64_t value = 0U;
    size_t index;
    size_t length = strlen(text);
    if (length == 0U || (length > 1U && text[0] == '0')) {
        return 0;
    }
    for (index = 0; index < length; ++index) {
        unsigned int digit;
        if (text[index] < '0' || text[index] > '9') {
            return 0;
        }
        digit = (unsigned int)(text[index] - '0');
        if (value > (maximum - digit) / 10U) {
            return 0;
        }
        value = value * 10U + digit;
    }
    if (value == 0U || value > maximum) {
        return 0;
    }
    *out = value;
    return 1;
}

static int parse_binding(char *text, struct n1_binding *binding) {
    static const char *keys[] = {
        "schema", "target_model", "target_device", "target_product",
        "target_incremental", "module_zip_sha256", "module_zip_size",
        "binary_sha256", "binary_size", "run_nonce",
        "pre_boot_id_sha256",
    };
    static const char *fixed[] = {
        BINDING_SCHEMA, "SM-G986N", "y2q", "y2qksx", "G986NKSS8IYC2",
    };
    char *save = NULL;
    char *line;
    size_t index = 0U;

    line = strtok_r(text, "\n", &save);
    while (line != NULL) {
        char *separator;
        const char *value;
        if (index >= sizeof(keys) / sizeof(keys[0])) {
            return 0;
        }
        separator = strchr(line, '=');
        if (separator == NULL || separator == line || strchr(separator + 1, '=') != NULL) {
            return 0;
        }
        *separator = '\0';
        value = separator + 1;
        if (strcmp(line, keys[index]) != 0 || value[0] == '\0') {
            return 0;
        }
        if (index < sizeof(fixed) / sizeof(fixed[0]) &&
            strcmp(value, fixed[index]) != 0) {
            return 0;
        }
        switch (index) {
        case 5U:
            if (!strict_hex(value, 64U)) return 0;
            memcpy(binding->module_zip_sha256, value, 65U);
            break;
        case 6U:
            if (!strict_u64(value, 16U * 1024U * 1024U,
                            &binding->module_zip_size)) return 0;
            break;
        case 7U:
            if (!strict_hex(value, 64U)) return 0;
            memcpy(binding->binary_sha256, value, 65U);
            break;
        case 8U:
            if (!strict_u64(value, 8U * 1024U * 1024U,
                            &binding->binary_size)) return 0;
            break;
        case 9U:
            if (!strict_hex(value, 32U)) return 0;
            memcpy(binding->run_nonce, value, 33U);
            break;
        case 10U:
            if (!strict_hex(value, 64U)) return 0;
            memcpy(binding->pre_boot_id_sha256, value, 65U);
            break;
        default:
            break;
        }
        ++index;
        line = strtok_r(NULL, "\n", &save);
    }
    return index == sizeof(keys) / sizeof(keys[0]);
}

static int sha256_self(char out[65], uint64_t *size_out) {
    struct sha256_ctx ctx;
    struct stat st;
    unsigned char digest[32];
    unsigned char buffer[4096];
    int fd = open("/proc/self/exe", O_RDONLY | O_CLOEXEC);
    if (fd < 0 || fstat(fd, &st) < 0 || !S_ISREG(st.st_mode) || st.st_size < 1) {
        if (fd >= 0) (void)close(fd);
        return -1;
    }
    sha256_init(&ctx);
    for (;;) {
        ssize_t amount = read(fd, buffer, sizeof(buffer));
        if (amount < 0) {
            if (errno == EINTR) continue;
            (void)close(fd);
            return -1;
        }
        if (amount == 0) break;
        sha256_update(&ctx, buffer, (size_t)amount);
    }
    if (close(fd) < 0) return -1;
    sha256_final(&ctx, digest);
    digest_hex(digest, out);
    *size_out = (uint64_t)st.st_size;
    return 0;
}

static int read_trimmed(const char *path, char *out, size_t capacity) {
    size_t size = 0U;
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0 || read_all_fd(fd, out, capacity - 1U, &size) < 0) {
        if (fd >= 0) (void)close(fd);
        return -1;
    }
    if (close(fd) < 0) return -1;
    while (size > 0U && (out[size - 1U] == '\n' || out[size - 1U] == '\r' ||
                         out[size - 1U] == '\0')) {
        --size;
    }
    if (size == 0U) {
        errno = EINVAL;
        return -1;
    }
    out[size] = '\0';
    return 0;
}

static int current_boot_hash(char out[65]) {
    char boot_id[64];
    if (read_trimmed("/proc/sys/kernel/random/boot_id", boot_id,
                     sizeof(boot_id)) < 0) {
        return -1;
    }
    sha256_bytes((const unsigned char *)boot_id, strlen(boot_id), out);
    return 0;
}

static int read_namespace(const char *name, char *out, size_t capacity) {
    char path[64];
    ssize_t amount;
    int length = snprintf(path, sizeof(path), "/proc/self/ns/%s", name);
    if (length < 0 || (size_t)length >= sizeof(path)) return -1;
    amount = readlink(path, out, capacity - 1U);
    if (amount <= 0 || (size_t)amount >= capacity) return -1;
    out[amount] = '\0';
    return 0;
}

static int status_value(const char *status,
                        const char *key,
                        char *out,
                        size_t capacity) {
    size_t key_length = strlen(key);
    const char *cursor = status;
    while (*cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        size_t length = end == NULL ? strlen(cursor) : (size_t)(end - cursor);
        if (length > key_length + 1U && memcmp(cursor, key, key_length) == 0 &&
            cursor[key_length] == ':') {
            const char *value = cursor + key_length + 1U;
            size_t value_length;
            while (value < cursor + length && (*value == ' ' || *value == '\t')) ++value;
            value_length = (size_t)((cursor + length) - value);
            if (value_length == 0U || value_length >= capacity) return -1;
            memcpy(out, value, value_length);
            out[value_length] = '\0';
            return 0;
        }
        if (end == NULL) break;
        cursor = end + 1;
    }
    return -1;
}

static int read_status_fields(char cap_eff[32],
                              char cap_prm[32],
                              char cap_bnd[32],
                              char no_new_privs[16]) {
    char status[8192];
    size_t size = 0U;
    int fd = open("/proc/self/status", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0 || read_all_fd(fd, status, sizeof(status) - 1U, &size) < 0) {
        if (fd >= 0) (void)close(fd);
        return -1;
    }
    if (close(fd) < 0) return -1;
    status[size] = '\0';
    if (status_value(status, "CapEff", cap_eff, 32U) < 0 ||
        status_value(status, "CapPrm", cap_prm, 32U) < 0 ||
        status_value(status, "CapBnd", cap_bnd, 32U) < 0 ||
        status_value(status, "NoNewPrivs", no_new_privs, 16U) < 0) {
        return -1;
    }
    return 0;
}

static int json_escape(const char *input, char *out, size_t capacity) {
    size_t used = 0U;
    while (*input != '\0') {
        unsigned char value = (unsigned char)*input++;
        const char *escape = NULL;
        if (value == '"') escape = "\\\"";
        else if (value == '\\') escape = "\\\\";
        else if (value == '\n') escape = "\\n";
        else if (value == '\r') escape = "\\r";
        else if (value == '\t') escape = "\\t";
        if (escape != NULL) {
            size_t amount = strlen(escape);
            if (used + amount >= capacity) return -1;
            memcpy(out + used, escape, amount);
            used += amount;
        } else if (value >= 0x20U && value <= 0x7eU) {
            if (used + 1U >= capacity) return -1;
            out[used++] = (char)value;
        } else {
            if (used + 6U >= capacity) return -1;
            (void)snprintf(out + used, capacity - used, "\\u%04x", value);
            used += 6U;
        }
    }
    if (used >= capacity) return -1;
    out[used] = '\0';
    return 0;
}

static int scan_nodes(int dir_fd,
                      uid_t owner,
                      gid_t group,
                      struct state_nodes *nodes) {
    DIR *directory;
    struct dirent *entry;
    int duplicate = dup(dir_fd);
    if (duplicate < 0) return -1;
    directory = fdopendir(duplicate);
    if (directory == NULL) {
        (void)close(duplicate);
        return -1;
    }
    memset(nodes, 0, sizeof(*nodes));
    errno = 0;
    while ((entry = readdir(directory)) != NULL) {
        struct stat st;
        int *slot = NULL;
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
        if (strcmp(entry->d_name, BINDING_NAME) == 0) slot = &nodes->binding;
        else if (strcmp(entry->d_name, INTENT_NAME) == 0) slot = &nodes->intent;
        else if (strcmp(entry->d_name, RESULT_NAME) == 0) slot = &nodes->result;
        else {
            nodes->other = 1;
            continue;
        }
        if (*slot != 0 || fstatat(dir_fd, entry->d_name, &st,
                                  AT_SYMLINK_NOFOLLOW) < 0 ||
            !S_ISREG(st.st_mode) || st.st_nlink != 1 || st.st_uid != owner ||
            st.st_gid != group || (st.st_mode & 0777) != 0600) {
            nodes->other = 1;
            continue;
        }
        *slot = 1;
    }
    if (errno != 0) {
        (void)closedir(directory);
        return -1;
    }
    if (closedir(directory) < 0) return -1;
    return 0;
}

static int write_new_file_at(int dir_fd,
                             const char *name,
                             uid_t owner,
                             gid_t group,
                             const char *content,
                             size_t size) {
    int fd = openat(dir_fd, name,
                    O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
                    0600);
    int rc = 0;
    if (fd < 0) return -1;
    if (fchown(fd, owner, group) < 0 || fchmod(fd, 0600) < 0 ||
        write_all(fd, content, size) < 0 || fsync(fd) < 0) {
        rc = -1;
    }
    if (close(fd) < 0) rc = -1;
    if (rc < 0) {
        (void)unlinkat(dir_fd, name, 0);
        (void)fsync(dir_fd);
    }
    return rc;
}

static int output_references_binding(int dir_fd,
                                     const char *name,
                                     uid_t owner,
                                     gid_t group,
                                     const char *schema,
                                     const char *binding_sha,
                                     const char *nonce) {
    char content[RESULT_MAX + 1U];
    char binding_token[128];
    char nonce_token[96];
    size_t size = 0U;
    int binding_length;
    int nonce_length;
    if (read_regular_at(dir_fd, name, owner, group, content, RESULT_MAX,
                        &size) < 0) return 0;
    content[size] = '\0';
    binding_length = snprintf(binding_token, sizeof(binding_token),
                              "\"binding_sha256\":\"%s\"", binding_sha);
    nonce_length = snprintf(nonce_token, sizeof(nonce_token),
                            "\"run_nonce\":\"%s\"", nonce);
    if (binding_length < 0 || nonce_length < 0 ||
        (size_t)binding_length >= sizeof(binding_token) ||
        (size_t)nonce_length >= sizeof(nonce_token)) return 0;
    return strstr(content, schema) != NULL &&
           strstr(content, binding_token) != NULL &&
           strstr(content, nonce_token) != NULL &&
           size >= 2U && content[size - 2U] == '}' && content[size - 1U] == '\n';
}

int main(int argc, char **argv) {
    const char *state_path = PRODUCTION_STATE_DIR;
    struct stat state_st;
    struct state_nodes nodes;
    struct n1_binding binding;
    char binding_bytes[BINDING_MAX + 1U];
    char binding_parse[BINDING_MAX + 1U];
    char binding_sha[65];
    char self_sha[65];
    char boot_sha[65];
    char selinux_raw[OBSERVATION_MAX];
    char selinux[OBSERVATION_MAX * 2U];
    char mnt_ns[64];
    char pid_ns[64];
    char uts_ns[64];
    char net_ns[64];
    char cap_eff[32];
    char cap_prm[32];
    char cap_bnd[32];
    char no_new_privs[16];
    char intent[512];
    char result[RESULT_MAX];
    struct timespec monotonic;
    uint64_t self_size = 0U;
    size_t binding_size = 0U;
    uid_t expected_uid = 0;
    gid_t expected_gid = 0;
    int dir_fd;
    int intent_length;
    int result_length;

#ifdef S20PLUS_CANARY_HOST_TEST
    if (argc != 2) return CANARY_STATE_REJECTED;
    state_path = argv[1];
    expected_uid = getuid();
    expected_gid = getgid();
#else
    (void)argv;
    if (argc != 1 || getuid() != 0 || getgid() != 0) return CANARY_STATE_REJECTED;
#endif

    dir_fd = open(state_path, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (dir_fd < 0 || fstat(dir_fd, &state_st) < 0 ||
        !S_ISDIR(state_st.st_mode) || state_st.st_uid != expected_uid ||
        state_st.st_gid != expected_gid || (state_st.st_mode & 0777) != 0700) {
        if (dir_fd >= 0) (void)close(dir_fd);
        return CANARY_STATE_REJECTED;
    }
    if (scan_nodes(dir_fd, expected_uid, expected_gid, &nodes) < 0 ||
        !nodes.binding || nodes.other ||
        !((!nodes.intent && !nodes.result) || (nodes.intent && nodes.result))) {
        (void)close(dir_fd);
        return CANARY_STATE_REJECTED;
    }
    if (read_regular_at(dir_fd, BINDING_NAME, expected_uid, expected_gid,
                        binding_bytes, BINDING_MAX, &binding_size) < 0 ||
        binding_size == 0U || binding_bytes[binding_size - 1U] != '\n' ||
        binding_bytes[0] == '\n' || memchr(binding_bytes, '\0', binding_size) != NULL ||
        memchr(binding_bytes, '\r', binding_size) != NULL) {
        (void)close(dir_fd);
        return CANARY_BINDING_REJECTED;
    }
    sha256_bytes((const unsigned char *)binding_bytes, binding_size, binding_sha);
    memcpy(binding_parse, binding_bytes, binding_size);
    binding_parse[binding_size] = '\0';
    if (strstr(binding_parse, "\n\n") != NULL) {
        (void)close(dir_fd);
        return CANARY_BINDING_REJECTED;
    }
    memset(&binding, 0, sizeof(binding));
    if (!parse_binding(binding_parse, &binding) ||
        sha256_self(self_sha, &self_size) < 0 ||
        self_size != binding.binary_size ||
        strcmp(self_sha, binding.binary_sha256) != 0 ||
        current_boot_hash(boot_sha) < 0 ||
        strcmp(boot_sha, binding.pre_boot_id_sha256) == 0) {
        (void)close(dir_fd);
        return CANARY_BINDING_REJECTED;
    }
    if (nodes.intent && nodes.result) {
        int valid = output_references_binding(
                        dir_fd, INTENT_NAME, expected_uid, expected_gid,
                        INTENT_SCHEMA, binding_sha, binding.run_nonce) &&
                    output_references_binding(
                        dir_fd, RESULT_NAME, expected_uid, expected_gid,
                        CANARY_SCHEMA, binding_sha, binding.run_nonce);
        (void)close(dir_fd);
        return valid ? CANARY_ALREADY_CONSUMED : CANARY_STATE_REJECTED;
    }

    intent_length = snprintf(intent, sizeof(intent),
        "{\"schema\":\"%s\",\"binding_sha256\":\"%s\","
        "\"run_nonce\":\"%s\",\"replay_permitted\":false}\n",
        INTENT_SCHEMA, binding_sha, binding.run_nonce);
    if (intent_length < 0 || (size_t)intent_length >= sizeof(intent) ||
        write_new_file_at(dir_fd, INTENT_NAME, expected_uid, expected_gid,
                          intent, (size_t)intent_length) < 0 || fsync(dir_fd) < 0) {
        (void)close(dir_fd);
        return errno == EEXIST ? CANARY_ALREADY_CONSUMED : CANARY_PUBLISH_FAILED;
    }

    if (read_trimmed("/proc/self/attr/current", selinux_raw,
                     sizeof(selinux_raw)) < 0 ||
        json_escape(selinux_raw, selinux, sizeof(selinux)) < 0 ||
        read_namespace("mnt", mnt_ns, sizeof(mnt_ns)) < 0 ||
        read_namespace("pid", pid_ns, sizeof(pid_ns)) < 0 ||
        read_namespace("uts", uts_ns, sizeof(uts_ns)) < 0 ||
        read_namespace("net", net_ns, sizeof(net_ns)) < 0 ||
        read_status_fields(cap_eff, cap_prm, cap_bnd, no_new_privs) < 0 ||
        clock_gettime(CLOCK_MONOTONIC, &monotonic) < 0) {
        (void)close(dir_fd);
        return CANARY_OBSERVATION_FAILED;
    }

    result_length = snprintf(result, sizeof(result),
        "{\"schema\":\"%s\",\"binding_sha256\":\"%s\","
        "\"run_nonce\":\"%s\",\"target_model\":\"SM-G986N\","
        "\"target_device\":\"y2q\",\"target_product\":\"y2qksx\","
        "\"target_incremental\":\"G986NKSS8IYC2\","
        "\"pid\":%jd,\"ppid\":%jd,\"uid\":%ju,\"gid\":%ju,"
        "\"selinux_context\":\"%s\",\"cap_eff\":\"%s\","
        "\"cap_prm\":\"%s\",\"cap_bnd\":\"%s\","
        "\"no_new_privs\":\"%s\",\"monotonic_sec\":%jd,"
        "\"monotonic_nsec\":%ld,\"self_sha256\":\"%s\","
        "\"self_size\":%" PRIu64 ",\"boot_id_sha256\":\"%s\","
        "\"pre_boot_id_changed\":true,\"mnt_ns\":\"%s\","
        "\"pid_ns\":\"%s\",\"uts_ns\":\"%s\","
        "\"net_ns\":\"%s\",\"replay_permitted\":false}\n",
        CANARY_SCHEMA, binding_sha, binding.run_nonce,
        (intmax_t)getpid(), (intmax_t)getppid(), (uintmax_t)getuid(),
        (uintmax_t)getgid(), selinux, cap_eff, cap_prm, cap_bnd,
        no_new_privs, (intmax_t)monotonic.tv_sec, monotonic.tv_nsec,
        self_sha, self_size, boot_sha, mnt_ns, pid_ns, uts_ns, net_ns);
    if (result_length < 0 || (size_t)result_length >= sizeof(result) ||
        write_new_file_at(dir_fd, PENDING_NAME, expected_uid, expected_gid,
                          result, (size_t)result_length) < 0 ||
        linkat(dir_fd, PENDING_NAME, dir_fd, RESULT_NAME, 0) < 0 ||
        fsync(dir_fd) < 0 || unlinkat(dir_fd, PENDING_NAME, 0) < 0 ||
        fsync(dir_fd) < 0) {
        (void)close(dir_fd);
        return CANARY_PUBLISH_FAILED;
    }
    if (close(dir_fd) < 0) return CANARY_PUBLISH_FAILED;
    return CANARY_OK;
}
