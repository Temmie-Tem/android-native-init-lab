#define _GNU_SOURCE

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define PROBE_VERSION "a90_xbl_context_probe v1653"
#define MAX_STORED_STRING 65536U
#define DEFAULT_MIN_LEN 4U
#define DEFAULT_MAX_RECORDS 256U

struct sha256_ctx {
    uint8_t data[64];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
};

struct range_spec {
    uint64_t start;
    uint64_t end;
};

struct options {
    const char *path;
    const char *artifact;
    struct range_spec ranges[16];
    size_t range_count;
    unsigned int min_len;
    unsigned int max_records;
    int selftest;
};

struct string_state {
    uint64_t offset;
    uint64_t length;
    int active;
    int truncated;
    uint8_t *stored;
    size_t stored_len;
    size_t stored_cap;
    struct sha256_ctx sha;
};

static const uint32_t k256[64] = {
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
    0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
    0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU, 0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
    0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
    0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
    0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
    0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
};

static uint32_t rotr32(uint32_t value, uint32_t bits) {
    return (value >> bits) | (value << (32U - bits));
}

static void sha256_transform(struct sha256_ctx *ctx, const uint8_t data[64]) {
    uint32_t a, b, c, d, e, f, g, h;
    uint32_t m[64];

    for (uint32_t i = 0, j = 0; i < 16; i++, j += 4) {
        m[i] = ((uint32_t)data[j] << 24) | ((uint32_t)data[j + 1] << 16) | ((uint32_t)data[j + 2] << 8) | data[j + 3];
    }
    for (uint32_t i = 16; i < 64; i++) {
        uint32_t s0 = rotr32(m[i - 15], 7) ^ rotr32(m[i - 15], 18) ^ (m[i - 15] >> 3);
        uint32_t s1 = rotr32(m[i - 2], 17) ^ rotr32(m[i - 2], 19) ^ (m[i - 2] >> 10);
        m[i] = m[i - 16] + s0 + m[i - 7] + s1;
    }

    a = ctx->state[0];
    b = ctx->state[1];
    c = ctx->state[2];
    d = ctx->state[3];
    e = ctx->state[4];
    f = ctx->state[5];
    g = ctx->state[6];
    h = ctx->state[7];

    for (uint32_t i = 0; i < 64; i++) {
        uint32_t s1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t temp1 = h + s1 + ch + k256[i] + m[i];
        uint32_t s0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = s0 + maj;
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
    ctx->datalen = 0;
    ctx->bitlen = 0;
    ctx->state[0] = 0x6a09e667U;
    ctx->state[1] = 0xbb67ae85U;
    ctx->state[2] = 0x3c6ef372U;
    ctx->state[3] = 0xa54ff53aU;
    ctx->state[4] = 0x510e527fU;
    ctx->state[5] = 0x9b05688cU;
    ctx->state[6] = 0x1f83d9abU;
    ctx->state[7] = 0x5be0cd19U;
}

static void sha256_update(struct sha256_ctx *ctx, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        ctx->data[ctx->datalen++] = data[i];
        if (ctx->datalen == 64) {
            sha256_transform(ctx, ctx->data);
            ctx->bitlen += 512;
            ctx->datalen = 0;
        }
    }
}

static void sha256_final(struct sha256_ctx *ctx, uint8_t hash[32]) {
    uint32_t i = ctx->datalen;

    if (ctx->datalen < 56) {
        ctx->data[i++] = 0x80;
        while (i < 56) {
            ctx->data[i++] = 0x00;
        }
    } else {
        ctx->data[i++] = 0x80;
        while (i < 64) {
            ctx->data[i++] = 0x00;
        }
        sha256_transform(ctx, ctx->data);
        memset(ctx->data, 0, 56);
    }

    ctx->bitlen += (uint64_t)ctx->datalen * 8U;
    ctx->data[63] = (uint8_t)(ctx->bitlen);
    ctx->data[62] = (uint8_t)(ctx->bitlen >> 8);
    ctx->data[61] = (uint8_t)(ctx->bitlen >> 16);
    ctx->data[60] = (uint8_t)(ctx->bitlen >> 24);
    ctx->data[59] = (uint8_t)(ctx->bitlen >> 32);
    ctx->data[58] = (uint8_t)(ctx->bitlen >> 40);
    ctx->data[57] = (uint8_t)(ctx->bitlen >> 48);
    ctx->data[56] = (uint8_t)(ctx->bitlen >> 56);
    sha256_transform(ctx, ctx->data);

    for (i = 0; i < 4; i++) {
        hash[i] = (uint8_t)((ctx->state[0] >> (24 - i * 8)) & 0xff);
        hash[i + 4] = (uint8_t)((ctx->state[1] >> (24 - i * 8)) & 0xff);
        hash[i + 8] = (uint8_t)((ctx->state[2] >> (24 - i * 8)) & 0xff);
        hash[i + 12] = (uint8_t)((ctx->state[3] >> (24 - i * 8)) & 0xff);
        hash[i + 16] = (uint8_t)((ctx->state[4] >> (24 - i * 8)) & 0xff);
        hash[i + 20] = (uint8_t)((ctx->state[5] >> (24 - i * 8)) & 0xff);
        hash[i + 24] = (uint8_t)((ctx->state[6] >> (24 - i * 8)) & 0xff);
        hash[i + 28] = (uint8_t)((ctx->state[7] >> (24 - i * 8)) & 0xff);
    }
}

static int is_printable_byte(uint8_t value) {
    return value >= 0x20 && value <= 0x7e;
}

static int append_stored(struct string_state *state, uint8_t value) {
    if (state->stored_len >= MAX_STORED_STRING) {
        state->truncated = 1;
        return 0;
    }
    if (state->stored_len == state->stored_cap) {
        size_t next_cap = state->stored_cap ? state->stored_cap * 2U : 128U;
        if (next_cap > MAX_STORED_STRING) {
            next_cap = MAX_STORED_STRING;
        }
        uint8_t *next = realloc(state->stored, next_cap);
        if (!next) {
            return -1;
        }
        state->stored = next;
        state->stored_cap = next_cap;
    }
    state->stored[state->stored_len++] = value;
    return 0;
}

static void reset_string_state(struct string_state *state) {
    state->active = 0;
    state->truncated = 0;
    state->offset = 0;
    state->length = 0;
    state->stored_len = 0;
    sha256_init(&state->sha);
}

static int contains_token(const uint8_t *data, size_t len, const char *token) {
    size_t token_len = strlen(token);
    if (token_len == 0 || token_len > len) {
        return 0;
    }
    for (size_t i = 0; i + token_len <= len; i++) {
        size_t j = 0;
        for (; j < token_len; j++) {
            if (tolower((unsigned char)data[i + j]) != tolower((unsigned char)token[j])) {
                break;
            }
        }
        if (j == token_len) {
            return 1;
        }
    }
    return 0;
}

static const char *class_for_tokens(int has_pon, int has_ps_hold, int has_pmic, int has_vdd, int has_rpmh, int has_aop, int has_sdx, int has_mdm, int has_pcie) {
    if (has_pon && has_ps_hold && has_pmic) {
        return "pon-pshold-pmic-context";
    }
    if (has_rpmh && (has_aop || has_pmic)) {
        return "rpmh-aop-pmic-context";
    }
    if (has_sdx || has_mdm) {
        return "sdx-mdm-context";
    }
    if (has_pcie) {
        return "pcie-context";
    }
    if (has_pmic || has_vdd || has_pon || has_aop) {
        return "generic-power-token-context";
    }
    return "no-token-context";
}

static void hex_digest(const uint8_t hash[32], char out[65]) {
    static const char hexdigits[] = "0123456789abcdef";
    for (int i = 0; i < 32; i++) {
        out[i * 2] = hexdigits[(hash[i] >> 4) & 0xf];
        out[i * 2 + 1] = hexdigits[hash[i] & 0xf];
    }
    out[64] = '\0';
}

static int finalize_string(const struct options *opts, const struct range_spec *range, struct string_state *state, unsigned int *records) {
    if (!state->active) {
        return 0;
    }
    if (state->length < opts->min_len) {
        reset_string_state(state);
        return 0;
    }

    int has_aop = contains_token(state->stored, state->stored_len, "aop");
    int has_gpio = contains_token(state->stored, state->stored_len, "gpio");
    int has_mdm = contains_token(state->stored, state->stored_len, "mdm") || contains_token(state->stored, state->stored_len, "mdm2ap") || contains_token(state->stored, state->stored_len, "ap2mdm");
    int has_mhi = contains_token(state->stored, state->stored_len, "mhi");
    int has_pcie = contains_token(state->stored, state->stored_len, "pcie");
    int has_pmic = contains_token(state->stored, state->stored_len, "pmic") || contains_token(state->stored, state->stored_len, "pm8150") || contains_token(state->stored, state->stored_len, "pm8150l") || contains_token(state->stored, state->stored_len, "pmxprairie");
    int has_pon = contains_token(state->stored, state->stored_len, "pon");
    int has_ps_hold = contains_token(state->stored, state->stored_len, "ps_hold");
    int has_rpmh = contains_token(state->stored, state->stored_len, "rpmh");
    int has_sdx = contains_token(state->stored, state->stored_len, "sdx") || contains_token(state->stored, state->stored_len, "sdx50") || contains_token(state->stored, state->stored_len, "sdxprairie");
    int has_vdd = contains_token(state->stored, state->stored_len, "vdd");

    if (!(has_aop || has_gpio || has_mdm || has_mhi || has_pcie || has_pmic || has_pon || has_ps_hold || has_rpmh || has_sdx || has_vdd)) {
        reset_string_state(state);
        return 0;
    }
    if (*records >= opts->max_records) {
        reset_string_state(state);
        return 0;
    }

    uint8_t digest[32];
    char digest_hex[65];
    struct sha256_ctx copy = state->sha;
    sha256_final(&copy, digest);
    hex_digest(digest, digest_hex);
    const char *class_name = class_for_tokens(has_pon, has_ps_hold, has_pmic, has_vdd, has_rpmh, has_aop, has_sdx, has_mdm, has_pcie);

    printf("record artifact=%s range_start=%" PRIu64 " range_end=%" PRIu64 " offset=%" PRIu64 " length=%" PRIu64 " truncated=%d string_sha256=%s tokens=",
           opts->artifact, range->start, range->end, state->offset, state->length, state->truncated, digest_hex);
    int first = 1;
#define PRINT_TOKEN(flag, name) do { if (flag) { printf("%s%s", first ? "" : ",", name); first = 0; } } while (0)
    PRINT_TOKEN(has_aop, "aop");
    PRINT_TOKEN(has_gpio, "gpio");
    PRINT_TOKEN(has_mdm, "mdm");
    PRINT_TOKEN(has_mhi, "mhi");
    PRINT_TOKEN(has_pcie, "pcie");
    PRINT_TOKEN(has_pmic, "pmic");
    PRINT_TOKEN(has_pon, "pon");
    PRINT_TOKEN(has_ps_hold, "ps_hold");
    PRINT_TOKEN(has_rpmh, "rpmh");
    PRINT_TOKEN(has_sdx, "sdx");
    PRINT_TOKEN(has_vdd, "vdd");
#undef PRINT_TOKEN
    printf(" class=%s\n", class_name);
    (*records)++;
    reset_string_state(state);
    return 0;
}

static int parse_u64(const char *text, uint64_t *out) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 0);
    if (errno != 0 || end == text || *end != '\0') {
        return -1;
    }
    *out = (uint64_t)value;
    return 0;
}

static int parse_range(const char *text, struct range_spec *range) {
    const char *sep = strchr(text, ':');
    if (!sep) {
        sep = strstr(text, "..");
    }
    if (!sep) {
        return -1;
    }
    size_t left_len = (size_t)(sep - text);
    size_t sep_len = sep[0] == ':' ? 1U : 2U;
    char left[64];
    char right[64];
    if (left_len == 0 || left_len >= sizeof(left) || strlen(sep + sep_len) >= sizeof(right)) {
        return -1;
    }
    memcpy(left, text, left_len);
    left[left_len] = '\0';
    strcpy(right, sep + sep_len);
    if (parse_u64(left, &range->start) != 0 || parse_u64(right, &range->end) != 0 || range->end < range->start) {
        return -1;
    }
    return 0;
}

static int scan_range(int fd, const struct options *opts, const struct range_spec *range) {
    uint8_t buffer[4096];
    uint64_t pos = range->start;
    uint64_t remaining = range->end - range->start + 1U;
    struct string_state state;
    unsigned int records = 0;
    memset(&state, 0, sizeof(state));
    sha256_init(&state.sha);
    printf("range artifact=%s start=%" PRIu64 " end=%" PRIu64 "\n", opts->artifact, range->start, range->end);

    while (remaining > 0) {
        size_t want = remaining > sizeof(buffer) ? sizeof(buffer) : (size_t)remaining;
        ssize_t got = pread(fd, buffer, want, (off_t)pos);
        if (got < 0) {
            perror("pread");
            free(state.stored);
            return -1;
        }
        if (got == 0) {
            break;
        }
        for (ssize_t i = 0; i < got; i++) {
            uint8_t value = buffer[i];
            uint64_t absolute = pos + (uint64_t)i;
            if (is_printable_byte(value)) {
                if (!state.active) {
                    reset_string_state(&state);
                    state.active = 1;
                    state.offset = absolute;
                }
                sha256_update(&state.sha, &value, 1);
                state.length++;
                if (append_stored(&state, value) != 0) {
                    perror("realloc");
                    free(state.stored);
                    return -1;
                }
            } else if (state.active) {
                finalize_string(opts, range, &state, &records);
            }
        }
        pos += (uint64_t)got;
        remaining -= (uint64_t)got;
    }
    if (state.active) {
        finalize_string(opts, range, &state, &records);
    }
    printf("summary artifact=%s range_start=%" PRIu64 " range_end=%" PRIu64 " records=%u\n", opts->artifact, range->start, range->end, records);
    free(state.stored);
    return 0;
}

static int run_selftest(void) {
    struct sha256_ctx ctx;
    uint8_t hash[32];
    char hex[65];
    const uint8_t abc[] = {'a', 'b', 'c'};
    sha256_init(&ctx);
    sha256_update(&ctx, abc, sizeof(abc));
    sha256_final(&ctx, hash);
    hex_digest(hash, hex);
    printf("%s\n", PROBE_VERSION);
    printf("selftest.sha256_abc=%s\n", hex);
    printf("selftest.sha256_ok=%d\n", strcmp(hex, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);
    printf("selftest.token_ok=%d\n", contains_token((const uint8_t *)"PMIC PS_HOLD SDX", 16, "ps_hold"));
    return strcmp(hex, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0 ? 0 : 1;
}

static void usage(FILE *out) {
    fprintf(out,
            "%s\n"
            "usage:\n"
            "  a90_xbl_context_probe --selftest\n"
            "  a90_xbl_context_probe --path PATH --artifact LABEL --range START:END [--range START:END] [--min-len N] [--max-records N]\n"
            "safety: read-only bounded ranges; tracked output has no raw string text\n",
            PROBE_VERSION);
}

static int parse_args(int argc, char **argv, struct options *opts) {
    memset(opts, 0, sizeof(*opts));
    opts->artifact = "unknown";
    opts->min_len = DEFAULT_MIN_LEN;
    opts->max_records = DEFAULT_MAX_RECORDS;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--selftest") == 0) {
            opts->selftest = 1;
        } else if (strcmp(argv[i], "--path") == 0 && i + 1 < argc) {
            opts->path = argv[++i];
        } else if (strcmp(argv[i], "--artifact") == 0 && i + 1 < argc) {
            opts->artifact = argv[++i];
        } else if (strcmp(argv[i], "--range") == 0 && i + 1 < argc) {
            if (opts->range_count >= sizeof(opts->ranges) / sizeof(opts->ranges[0])) {
                fprintf(stderr, "too many ranges\n");
                return -1;
            }
            if (parse_range(argv[++i], &opts->ranges[opts->range_count]) != 0) {
                fprintf(stderr, "invalid range: %s\n", argv[i]);
                return -1;
            }
            opts->range_count++;
        } else if (strcmp(argv[i], "--min-len") == 0 && i + 1 < argc) {
            uint64_t value = 0;
            if (parse_u64(argv[++i], &value) != 0 || value == 0 || value > 1024) {
                fprintf(stderr, "invalid min-len\n");
                return -1;
            }
            opts->min_len = (unsigned int)value;
        } else if (strcmp(argv[i], "--max-records") == 0 && i + 1 < argc) {
            uint64_t value = 0;
            if (parse_u64(argv[++i], &value) != 0 || value > 10000) {
                fprintf(stderr, "invalid max-records\n");
                return -1;
            }
            opts->max_records = (unsigned int)value;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            usage(stdout);
            exit(0);
        } else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            return -1;
        }
    }
    if (!opts->selftest && (!opts->path || opts->range_count == 0)) {
        usage(stderr);
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    struct options opts;
    if (parse_args(argc, argv, &opts) != 0) {
        return 2;
    }
    if (opts.selftest) {
        return run_selftest();
    }
    int fd = open(opts.path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open");
        return 1;
    }
    printf("%s\n", PROBE_VERSION);
    printf("mode=redacted-context\n");
    printf("raw_string_output=0\n");
    printf("path=%s\n", opts.path);
    printf("artifact=%s\n", opts.artifact);
    printf("min_len=%u\n", opts.min_len);
    printf("max_records=%u\n", opts.max_records);
    int rc = 0;
    for (size_t i = 0; i < opts.range_count; i++) {
        if (scan_range(fd, &opts, &opts.ranges[i]) != 0) {
            rc = 1;
            break;
        }
    }
    close(fd);
    return rc;
}
