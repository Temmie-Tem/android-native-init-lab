/*
 * V2475 ARM32 ACDB interposer.
 *
 * Built as a freestanding 32-bit shared object for LD_PRELOAD into the stock
 * Android audio HAL process.  It interposes acdb_ioctl(), calls the real symbol
 * from libaudcal.so (falling back to dlsym(RTLD_NEXT, ...)), and writes bounded
 * metadata/raw output buffers to /data/local/tmp/a90-acdb-tap/.  No libc,
 * liblog, pthread, malloc, or Android headers are required; file writes use raw
 * ARM EABI syscalls.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned char uint8_t;
typedef unsigned long size_t;
typedef unsigned long long uint64_t;

extern void *dlsym(void *handle, const char *symbol);
extern void *dlopen(const char *filename, int flags);

#define A90_RTLD_NEXT ((void *)-1L)
#define A90_RTLD_NOW 2
#define A90_CAPTURE_DIR "/data/local/tmp/a90-acdb-tap"
#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-tap/acdbtap-events.jsonl"
#define A90_RAW_PREFIX "/data/local/tmp/a90-acdb-tap/acdbtap-"
#define A90_TARGET_OUT_LEN 4916U
#define A90_SIZE_QUERY_OUT_LEN 4U
#define A90_CMD_INITIALIZE_V2 0x0001138cU
#define A90_CMD_CUSTOM_TOPO_INFO_V3 0x00013296U
#define A90_MAX_CAPTURE_LEN 65536U
#ifndef A90_ACDBTAP_LOG_ENTER
#define A90_ACDBTAP_LOG_ENTER 0
#endif
#ifndef A90_ACDBTAP_ARMED_CAPTURE
#define A90_ACDBTAP_ARMED_CAPTURE 0
#endif
#ifndef A90_ACDBTAP_EXIT_ON_TARGET
#define A90_ACDBTAP_EXIT_ON_TARGET 1
#endif

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_EXCL 00000200
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_GETTID 224
#define A90_NR_EXIT_GROUP 248
#define A90_NR_OPENAT 322

typedef int32_t (*a90_real_acdb_ioctl_fn)(uint32_t cmd, const uint8_t *in,
                                          uint32_t in_len, uint8_t *out,
                                          uint32_t out_len);

static a90_real_acdb_ioctl_fn a90_real_acdb_ioctl;
static volatile uint32_t a90_sequence;
static volatile int a90_in_hook;
static volatile int a90_armed;

static void a90_resolve_real_acdb_ioctl(void)
{
    void *handle;

    if (a90_real_acdb_ioctl)
        return;

    handle = dlopen("libaudcal.so", A90_RTLD_NOW);
    if (handle)
        a90_real_acdb_ioctl = (a90_real_acdb_ioctl_fn)dlsym(handle, "acdb_ioctl");

    if (!a90_real_acdb_ioctl)
        a90_real_acdb_ioctl = (a90_real_acdb_ioctl_fn)dlsym(A90_RTLD_NEXT, "acdb_ioctl");
}

struct a90_sha256 {
    uint32_t h[8];
    uint64_t bits;
    uint8_t block[64];
    uint32_t used;
};

static long a90_syscall0(long nr)
{
    register long r0 asm("r0");
    register long r7 asm("r7") = nr;
    asm volatile("svc #0" : "=r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall1(long nr, long a0)
{
    register long r0 asm("r0") = a0;
    register long r7 asm("r7") = nr;
    asm volatile("svc #0" : "+r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall3(long nr, long a0, long a1, long a2)
{
    register long r0 asm("r0") = a0;
    register long r1 asm("r1") = a1;
    register long r2 asm("r2") = a2;
    register long r7 asm("r7") = nr;
    asm volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory");
    return r0;
}

static long a90_syscall4(long nr, long a0, long a1, long a2, long a3)
{
    register long r0 asm("r0") = a0;
    register long r1 asm("r1") = a1;
    register long r2 asm("r2") = a2;
    register long r3 asm("r3") = a3;
    register long r7 asm("r7") = nr;
    asm volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r7) : "memory");
    return r0;
}

static int a90_open_append(const char *path)
{
    return (int)a90_syscall4(A90_NR_OPENAT, A90_AT_FDCWD, (long)path,
                             A90_O_WRONLY | A90_O_CREAT | A90_O_APPEND,
                             A90_MODE_0600);
}

static int a90_open_new(const char *path)
{
    return (int)a90_syscall4(A90_NR_OPENAT, A90_AT_FDCWD, (long)path,
                             A90_O_WRONLY | A90_O_CREAT | A90_O_EXCL,
                             A90_MODE_0600);
}

static void a90_close(int fd)
{
    if (fd >= 0)
        (void)a90_syscall1(A90_NR_CLOSE, fd);
}

static void a90_exit_group(int code)
{
    (void)a90_syscall1(A90_NR_EXIT_GROUP, code);
    for (;;) {
    }
}

static uint32_t a90_getpid(void)
{
    return (uint32_t)a90_syscall0(A90_NR_GETPID);
}

static uint32_t a90_gettid(void)
{
    return (uint32_t)a90_syscall0(A90_NR_GETTID);
}

static size_t a90_strlen(const char *s)
{
    size_t n = 0;
    while (s[n])
        n++;
    return n;
}

static void a90_write_all(int fd, const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    while (len > 0) {
        long rc = a90_syscall3(A90_NR_WRITE, fd, (long)p, (long)len);
        if (rc <= 0)
            return;
        p += (size_t)rc;
        len -= (size_t)rc;
    }
}

static void a90_write_str(int fd, const char *s)
{
    a90_write_all(fd, s, a90_strlen(s));
}

static uint32_t a90_rotr(uint32_t x, uint32_t n)
{
    return (x >> n) | (x << (32U - n));
}

static uint32_t a90_load_be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void a90_store_be32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
}

static void a90_sha256_transform(struct a90_sha256 *ctx, const uint8_t *block)
{
    static const uint32_t k[64] = {
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
    uint32_t w[64];
    uint32_t a, b, c, d, e, f, g, h;
    uint32_t i;

    for (i = 0; i < 16; i++)
        w[i] = a90_load_be32(block + (i * 4U));
    for (i = 16; i < 64; i++) {
        uint32_t s0 = a90_rotr(w[i - 15], 7) ^ a90_rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = a90_rotr(w[i - 2], 17) ^ a90_rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }

    a = ctx->h[0];
    b = ctx->h[1];
    c = ctx->h[2];
    d = ctx->h[3];
    e = ctx->h[4];
    f = ctx->h[5];
    g = ctx->h[6];
    h = ctx->h[7];
    for (i = 0; i < 64; i++) {
        uint32_t s1 = a90_rotr(e, 6) ^ a90_rotr(e, 11) ^ a90_rotr(e, 25);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + s1 + ch + k[i] + w[i];
        uint32_t s0 = a90_rotr(a, 2) ^ a90_rotr(a, 13) ^ a90_rotr(a, 22);
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
    ctx->h[0] += a;
    ctx->h[1] += b;
    ctx->h[2] += c;
    ctx->h[3] += d;
    ctx->h[4] += e;
    ctx->h[5] += f;
    ctx->h[6] += g;
    ctx->h[7] += h;
}

static void a90_sha256_init(struct a90_sha256 *ctx)
{
    uint32_t i;
    ctx->h[0] = 0x6a09e667U;
    ctx->h[1] = 0xbb67ae85U;
    ctx->h[2] = 0x3c6ef372U;
    ctx->h[3] = 0xa54ff53aU;
    ctx->h[4] = 0x510e527fU;
    ctx->h[5] = 0x9b05688cU;
    ctx->h[6] = 0x1f83d9abU;
    ctx->h[7] = 0x5be0cd19U;
    ctx->bits = 0;
    ctx->used = 0;
    for (i = 0; i < 64; i++)
        ctx->block[i] = 0;
}

static void a90_sha256_update(struct a90_sha256 *ctx, const uint8_t *data, uint32_t len)
{
    uint32_t i;
    ctx->bits += ((uint64_t)len) << 3;
    for (i = 0; i < len; i++) {
        ctx->block[ctx->used++] = data[i];
        if (ctx->used == 64) {
            a90_sha256_transform(ctx, ctx->block);
            ctx->used = 0;
        }
    }
}

static void a90_sha256_final(struct a90_sha256 *ctx, uint8_t out[32])
{
    uint32_t i;
    uint64_t bits = ctx->bits;
    ctx->block[ctx->used++] = 0x80U;
    if (ctx->used > 56) {
        while (ctx->used < 64)
            ctx->block[ctx->used++] = 0;
        a90_sha256_transform(ctx, ctx->block);
        ctx->used = 0;
    }
    while (ctx->used < 56)
        ctx->block[ctx->used++] = 0;
    for (i = 0; i < 8; i++)
        ctx->block[56 + i] = (uint8_t)(bits >> (56U - (i * 8U)));
    a90_sha256_transform(ctx, ctx->block);
    for (i = 0; i < 8; i++)
        a90_store_be32(out + (i * 4U), ctx->h[i]);
}

static void a90_hex32(char out[8], uint32_t v)
{
    static const char hex[] = "0123456789abcdef";
    int i;
    for (i = 7; i >= 0; i--) {
        out[i] = hex[v & 0xfU];
        v >>= 4;
    }
}

static void a90_sha_hex(char out[64], const uint8_t digest[32])
{
    static const char hex[] = "0123456789abcdef";
    uint32_t i;
    for (i = 0; i < 32; i++) {
        out[i * 2U] = hex[(digest[i] >> 4) & 0xfU];
        out[i * 2U + 1U] = hex[digest[i] & 0xfU];
    }
}

static char *a90_append_str(char *p, const char *s)
{
    while (*s)
        *p++ = *s++;
    return p;
}

static char *a90_append_hex_field(char *p, const char *name, uint32_t value)
{
    char hex[8];
    uint32_t i;
    p = a90_append_str(p, "\"");
    p = a90_append_str(p, name);
    p = a90_append_str(p, "\":\"0x");
    a90_hex32(hex, value);
    for (i = 0; i < 8; i++)
        *p++ = hex[i];
    *p++ = '"';
    return p;
}

static uint32_t a90_load_le32(const uint8_t *p)
{
    return ((uint32_t)p[0]) |
           (((uint32_t)p[1]) << 8) |
           (((uint32_t)p[2]) << 16) |
           (((uint32_t)p[3]) << 24);
}

static void a90_build_raw_path(char *path, uint32_t seq, uint32_t cmd, uint32_t out_len)
{
    char *p = path;
    char hex[8];
    uint32_t i;
    p = a90_append_str(p, A90_RAW_PREFIX);
    a90_hex32(hex, seq);
    for (i = 0; i < 8; i++)
        *p++ = hex[i];
    p = a90_append_str(p, "-cmd-");
    a90_hex32(hex, cmd);
    for (i = 0; i < 8; i++)
        *p++ = hex[i];
    p = a90_append_str(p, "-len-");
    a90_hex32(hex, out_len);
    for (i = 0; i < 8; i++)
        *p++ = hex[i];
    p = a90_append_str(p, ".bin");
    *p = 0;
}

static void a90_log_call_phase(uint32_t seq, uint32_t cmd, const uint8_t *in, uint32_t in_len,
                               const uint8_t *out, uint32_t out_len, const char *phase)
{
    char line[1024];
    char *p;
    int event_fd;
    uint32_t i;
    uint32_t sample_words = in_len / 4U;

    if (sample_words > 4U)
        sample_words = 4U;

    event_fd = a90_open_append(A90_EVENTS_PATH);
    if (event_fd < 0)
        return;

    p = line;
    p = a90_append_str(p, "{\"event\":\"acdb_ioctl_call\",");
    p = a90_append_hex_field(p, "seq", seq);
    *p++ = ',';
    p = a90_append_hex_field(p, "pid", a90_getpid());
    *p++ = ',';
    p = a90_append_hex_field(p, "tid", a90_gettid());
    *p++ = ',';
    p = a90_append_hex_field(p, "cmd", cmd);
    *p++ = ',';
    p = a90_append_hex_field(p, "in_len", in_len);
    *p++ = ',';
    p = a90_append_hex_field(p, "out_len", out_len);
    *p++ = ',';
    p = a90_append_hex_field(p, "in_ptr", (uint32_t)(unsigned long)in);
    *p++ = ',';
    p = a90_append_hex_field(p, "out_ptr", (uint32_t)(unsigned long)out);
    *p++ = ',';
    for (i = 0; in && i < sample_words; i++) {
        char key[] = "in_word0";
        key[7] = (char)('0' + i);
        p = a90_append_hex_field(p, key, a90_load_le32(in + (i * 4U)));
        *p++ = ',';
    }
    p = a90_append_str(p, "\"phase\":\"");
    p = a90_append_str(p, phase);
    *p++ = '\"';
    *p++ = '}';
    *p++ = '\n';

    a90_write_all(event_fd, line, (size_t)(p - line));
    a90_close(event_fd);
}

__attribute__((visibility("default"))) void a90_arm_capture(void)
{
    a90_armed = 1;
    a90_log_call_phase(a90_sequence++, 0, 0, 0, 0, 0, "armed");
}

static int a90_is_all_zero(const uint8_t *buf, uint32_t len)
{
    uint32_t i;
    if (!buf)
        return 1;
    for (i = 0; i < len; i++) {
        if (buf[i] != 0)
            return 0;
    }
    return 1;
}

static int a90_log_capture(uint32_t seq, uint32_t cmd, uint32_t in_len, uint32_t out_len,
                           int32_t ret, const uint8_t *out)
{
    uint8_t digest[32];
    char digest_hex[64];
    char raw_path[160];
    char line[640];
    char *p;
    int event_fd;
    int raw_fd = -1;
    uint32_t i;
    struct a90_sha256 sha;
    int captured_raw = 0;
    int all_zero;

    if (!out || out_len == 0 || out_len > A90_MAX_CAPTURE_LEN)
        return 0;

    all_zero = a90_is_all_zero(out, out_len);
    a90_sha256_init(&sha);
    a90_sha256_update(&sha, out, out_len);
    a90_sha256_final(&sha, digest);
    a90_sha_hex(digest_hex, digest);
    a90_build_raw_path(raw_path, seq, cmd, out_len);

    raw_fd = a90_open_new(raw_path);
    if (raw_fd >= 0) {
        a90_write_all(raw_fd, out, out_len);
        a90_close(raw_fd);
        captured_raw = 1;
    }

    event_fd = a90_open_append(A90_EVENTS_PATH);
    if (event_fd < 0)
        return 0;

    p = line;
    *p++ = '{';
    p = a90_append_hex_field(p, "seq", seq);
    *p++ = ',';
    p = a90_append_hex_field(p, "pid", a90_getpid());
    *p++ = ',';
    p = a90_append_hex_field(p, "tid", a90_gettid());
    *p++ = ',';
    p = a90_append_hex_field(p, "cmd", cmd);
    *p++ = ',';
    p = a90_append_hex_field(p, "in_len", in_len);
    *p++ = ',';
    p = a90_append_hex_field(p, "out_len", out_len);
    *p++ = ',';
    p = a90_append_hex_field(p, "ret", (uint32_t)ret);
    *p++ = ',';
    p = a90_append_str(p, "\"sha256\":\"");
    for (i = 0; i < 64; i++)
        *p++ = digest_hex[i];
    *p++ = '"';
    *p++ = ',';
    p = a90_append_str(p, "\"raw_path\":\"");
    p = a90_append_str(p, raw_path);
    *p++ = '"';
    *p++ = ',';
    p = a90_append_str(p, "\"raw_written\":");
    p = a90_append_str(p, captured_raw ? "true" : "false");
    *p++ = ',';
    p = a90_append_str(p, "\"is_target_4916\":");
    p = a90_append_str(p, out_len == A90_TARGET_OUT_LEN ? "true" : "false");
    *p++ = ',';
    p = a90_append_str(p, "\"is_size_query_4\":");
    p = a90_append_str(p, out_len == A90_SIZE_QUERY_OUT_LEN ? "true" : "false");
    *p++ = ',';
    p = a90_append_str(p, "\"all_zero\":");
    p = a90_append_str(p, all_zero ? "true" : "false");
    *p++ = '}';
    *p++ = '\n';

    a90_write_all(event_fd, line, (size_t)(p - line));
    a90_close(event_fd);
    return ret == 0 && out_len == A90_TARGET_OUT_LEN && !all_zero;
}

__attribute__((visibility("default"))) int32_t
acdb_ioctl(uint32_t cmd, const uint8_t *in, uint32_t in_len, uint8_t *out, uint32_t out_len)
{
    int32_t ret;
    uint32_t seq;

    a90_resolve_real_acdb_ioctl();
    if (!a90_real_acdb_ioctl)
        return -1;

    if (a90_in_hook)
        return a90_real_acdb_ioctl(cmd, in, in_len, out, out_len);

#if A90_ACDBTAP_ARMED_CAPTURE
    if (!a90_armed) {
        ret = a90_real_acdb_ioctl(cmd, in, in_len, out, out_len);
        if (ret == 0 && cmd == A90_CMD_INITIALIZE_V2)
            a90_armed = 1;
        return ret;
    }
#endif

    seq = a90_sequence++;
#if A90_ACDBTAP_LOG_ENTER
    a90_log_call_phase(seq, cmd, in, in_len, out, out_len, "enter");
#endif

    a90_in_hook = 1;
    if (!a90_real_acdb_ioctl) {
#if A90_ACDBTAP_LOG_ENTER
        a90_log_call_phase(seq, cmd, in, in_len, out, out_len, "resolve_failed");
#endif
        a90_in_hook = 0;
        return -1;
    }

#if A90_ACDBTAP_LOG_ENTER
    a90_log_call_phase(seq, cmd, in, in_len, out, out_len, "before_real");
#endif
    ret = a90_real_acdb_ioctl(cmd, in, in_len, out, out_len);
    if (ret == 0 && cmd == A90_CMD_CUSTOM_TOPO_INFO_V3 && in && in_len >= 8U) {
        uint32_t indirect_len = a90_load_le32(in);
        const uint8_t *indirect_out = (const uint8_t *)(unsigned long)a90_load_le32(in + 4U);

        if (indirect_out && indirect_len && indirect_len <= A90_MAX_CAPTURE_LEN) {
#if A90_ACDBTAP_EXIT_ON_TARGET
            if (a90_log_capture(seq, cmd, in_len, indirect_len, ret, indirect_out))
                a90_exit_group(0);
#else
            (void)a90_log_capture(seq, cmd, in_len, indirect_len, ret, indirect_out);
#endif
        }
    }
#if A90_ACDBTAP_EXIT_ON_TARGET
    if (a90_log_capture(seq, cmd, in_len, out_len, ret, out))
        a90_exit_group(0);
#else
    (void)a90_log_capture(seq, cmd, in_len, out_len, ret, out);
#endif
    a90_in_hook = 0;
    return ret;
}
