/*
 * V2489 ARM32 own-process ACDB pure-read GET probe.
 *
 * Built as a freestanding 32-bit PIE with a custom _start.  It resolves the
 * Android linker namespace APIs from libdl, loads the stock ACDB libraries from
 * a visible vendor namespace, resolves acdb_loader_init_v3() and acdb_ioctl(),
 * initializes the ACDB database path, then issues a bounded set of read-only GET
 * command candidates from the operator RE update.  It does not touch the native
 * calibration device or calibration SET path.
 *
 * Runtime output directory must already exist:
 *   /data/local/tmp/a90-acdb-ownget
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned char uint8_t;
typedef unsigned long size_t;
typedef unsigned long long uint64_t;

extern void *dlopen(const char *name, int flags);
extern void *dlsym(void *handle, const char *symbol);
extern char *dlerror(void);

#define A90_RTLD_NOW 2
#define A90_ANDROID_DLEXT_USE_NAMESPACE 0x200ULL

#define A90_ACDB_FILES_PATH "/vendor/etc/acdbdata"
#define A90_DELTA_DIR "/data/local/tmp/a90-acdb-ownget/delta"
#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-ownget-events.jsonl"
#define A90_RAW_PREFIX "/data/local/tmp/a90-acdb-ownget/acdb-ownget-"
#define A90_LIBDL "libdl.so"
#define A90_LIBAUDCAL "/vendor/lib/libaudcal.so"
#define A90_LIBACDBLOADER "/vendor/lib/libacdbloader.so"

#define A90_TARGET_OUT_LEN 4916U
#define A90_SIZE_QUERY_OUT_LEN 4U
#define A90_MAX_OUT_LEN 4916U
#define A90_MAX_IN_LEN 32U

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_EXCL 00000200
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_EXIT 1
#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_GETTID 224
#define A90_NR_OPENAT 322

typedef int32_t (*a90_acdb_loader_init_v3_fn)(const char *acdb_files_path,
                                              const char *delta_file_path,
                                              uint32_t meta_info_type);
typedef int32_t (*a90_acdb_ioctl_fn)(uint32_t cmd, const uint8_t *in_buf,
                                     uint32_t in_len, uint8_t *out_buf,
                                     uint32_t out_len);

typedef struct a90_android_namespace a90_android_namespace;

struct a90_android_dlextinfo {
    uint64_t flags;
    void *reserved_addr;
    size_t reserved_size;
    int relro_fd;
    int library_fd;
    uint64_t library_fd_offset;
    a90_android_namespace *library_namespace;
};

typedef a90_android_namespace *(*a90_android_get_exported_namespace_fn)(const char *name);
typedef void *(*a90_android_dlopen_ext_fn)(const char *filename, int flags,
                                           const struct a90_android_dlextinfo *extinfo);
typedef void *(*a90_loader_android_dlopen_ext_fn)(const char *filename, int flags,
                                                  const struct a90_android_dlextinfo *extinfo,
                                                  const void *caller_addr);

struct a90_resolved_dlopen_ext {
    void *fn;
    int is_loader_entry;
    const char *scope;
    const char *symbol;
};

struct a90_sha256 {
    uint32_t h[8];
    uint64_t bits;
    uint8_t block[64];
    uint32_t used;
};

static const uint32_t a90_commands[] = {
    0x00011394U,
    0x00012e01U,
    0x000130daU,
    0x000130dcU,
};

static const uint32_t a90_in_lens[] = {
    0U,
    4U,
    8U,
    16U,
    32U,
};

static const uint32_t a90_out_lens[] = {
    A90_SIZE_QUERY_OUT_LEN,
    A90_TARGET_OUT_LEN,
};

static const char *const a90_namespace_names[] = {
    "sphal",
    "vendor",
    "default",
    "vndk",
};

static uint8_t a90_input[A90_MAX_IN_LEN];
static uint8_t a90_output[A90_MAX_OUT_LEN];
static uint32_t a90_sequence;

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

static void a90_exit(int code)
{
    (void)a90_syscall1(A90_NR_EXIT, code);
    for (;;) {
    }
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

static void a90_write_json_escaped(int fd, const char *s, uint32_t max_len)
{
    uint32_t i;
    if (!s)
        return;
    for (i = 0; s[i] && i < max_len; i++) {
        char c = s[i];
        if (c == '\\' || c == '"') {
            a90_write_all(fd, "\\", 1);
            a90_write_all(fd, &c, 1);
        } else if (c == '\n') {
            a90_write_str(fd, "\\n");
        } else if (c == '\r') {
            a90_write_str(fd, "\\r");
        } else if (c == '\t') {
            a90_write_str(fd, "\\t");
        } else if ((uint8_t)c < 0x20U) {
            a90_write_str(fd, "?");
        } else {
            a90_write_all(fd, &c, 1);
        }
    }
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
    uint32_t used = ctx->used;
    uint64_t bits = ctx->bits;
    ctx->block[used++] = 0x80U;
    if (used > 56U) {
        while (used < 64U)
            ctx->block[used++] = 0;
        a90_sha256_transform(ctx, ctx->block);
        used = 0;
    }
    while (used < 56U)
        ctx->block[used++] = 0;
    for (i = 0; i < 8; i++)
        ctx->block[56U + i] = (uint8_t)(bits >> (56U - (i * 8U)));
    a90_sha256_transform(ctx, ctx->block);
    for (i = 0; i < 8; i++)
        a90_store_be32(out + (i * 4U), ctx->h[i]);
}

static void a90_sha256_bytes(const uint8_t *data, uint32_t len, uint8_t out[32])
{
    struct a90_sha256 ctx;
    a90_sha256_init(&ctx);
    a90_sha256_update(&ctx, data, len);
    a90_sha256_final(&ctx, out);
}

static void a90_write_dec(int fd, uint32_t value)
{
    char tmp[10];
    char out[10];
    uint32_t n = 0;
    uint32_t i = 0;
    if (value == 0) {
        a90_write_str(fd, "0");
        return;
    }
    while (value && n < sizeof(tmp)) {
        tmp[n++] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    while (n)
        out[i++] = tmp[--n];
    a90_write_all(fd, out, i);
}

static void a90_write_sdec(int fd, int32_t value)
{
    uint32_t u;
    if (value < 0) {
        a90_write_str(fd, "-");
        u = (uint32_t)(0U - (uint32_t)value);
    } else {
        u = (uint32_t)value;
    }
    a90_write_dec(fd, u);
}

static void a90_write_hex32(int fd, uint32_t value)
{
    static const char h[] = "0123456789abcdef";
    char out[10];
    uint32_t i;
    out[0] = '0';
    out[1] = 'x';
    for (i = 0; i < 8; i++)
        out[2U + i] = h[(value >> (28U - (i * 4U))) & 0xfU];
    a90_write_all(fd, out, sizeof(out));
}

static size_t a90_append_dec(char *path, size_t n, uint32_t value)
{
    char tmp[10];
    uint32_t t = 0;
    if (value == 0) {
        path[n++] = '0';
        return n;
    }
    while (value && t < sizeof(tmp)) {
        tmp[t++] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    while (t)
        path[n++] = tmp[--t];
    return n;
}

static void a90_write_sha256_hex(int fd, const uint8_t digest[32])
{
    static const char h[] = "0123456789abcdef";
    char out[64];
    uint32_t i;
    for (i = 0; i < 32; i++) {
        out[i * 2U] = h[(digest[i] >> 4) & 0xfU];
        out[(i * 2U) + 1U] = h[digest[i] & 0xfU];
    }
    a90_write_all(fd, out, sizeof(out));
}

static void a90_make_raw_path(char *path, uint32_t seq, uint32_t cmd, uint32_t in_len,
                              uint32_t out_len)
{
    static const char h[] = "0123456789abcdef";
    const char *prefix = A90_RAW_PREFIX;
    size_t n = 0;
    uint32_t i;
    while (prefix[n]) {
        path[n] = prefix[n];
        n++;
    }
    for (i = 0; i < 8; i++)
        path[n++] = h[(seq >> (28U - (i * 4U))) & 0xfU];
    path[n++] = '-';
    for (i = 0; i < 8; i++)
        path[n++] = h[(cmd >> (28U - (i * 4U))) & 0xfU];
    path[n++] = '-';
    path[n++] = 'i';
    path[n++] = 'n';
    n = a90_append_dec(path, n, in_len);
    path[n++] = '-';
    path[n++] = 'o';
    path[n++] = 'u';
    path[n++] = 't';
    n = a90_append_dec(path, n, out_len);
    path[n++] = '.';
    path[n++] = 'b';
    path[n++] = 'i';
    path[n++] = 'n';
    path[n] = 0;
}

static void a90_write_error_event(const char *stage, int32_t code, const char *detail)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"error\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"code\":");
    a90_write_sdec(fd, code);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    if (detail && detail[0]) {
        a90_write_str(fd, ",\"detail\":\"");
        a90_write_json_escaped(fd, detail, 512U);
        a90_write_str(fd, "\"");
    }
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_write_namespace_probe_event(const char *name, int found)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"namespace_probe\",\"name\":\"");
    a90_write_json_escaped(fd, name, 64U);
    a90_write_str(fd, "\",\"found\":");
    a90_write_str(fd, found ? "true" : "false");
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_write_namespace_load_event(const char *name, const char *library,
                                           int ok, const char *detail)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"namespace_load\",\"name\":\"");
    a90_write_json_escaped(fd, name, 64U);
    a90_write_str(fd, "\",\"library\":\"");
    a90_write_json_escaped(fd, library, 160U);
    a90_write_str(fd, "\",\"ok\":");
    a90_write_str(fd, ok ? "true" : "false");
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    if (detail && detail[0]) {
        a90_write_str(fd, ",\"detail\":\"");
        a90_write_json_escaped(fd, detail, 512U);
        a90_write_str(fd, "\"");
    }
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_write_namespace_selected_event(const char *name)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"namespace_selected\",\"name\":\"");
    a90_write_json_escaped(fd, name, 64U);
    a90_write_str(fd, "\",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_write_symbol_probe_event(const char *scope, const char *symbol,
                                         int found, const char *detail)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"symbol_probe\",\"scope\":\"");
    a90_write_json_escaped(fd, scope, 64U);
    a90_write_str(fd, "\",\"symbol\":\"");
    a90_write_json_escaped(fd, symbol, 96U);
    a90_write_str(fd, "\",\"found\":");
    a90_write_str(fd, found ? "true" : "false");
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    if (detail && detail[0]) {
        a90_write_str(fd, ",\"detail\":\"");
        a90_write_json_escaped(fd, detail, 512U);
        a90_write_str(fd, "\"");
    }
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void *a90_probe_symbol(void *handle, const char *scope, const char *symbol)
{
    void *fn;
    (void)dlerror();
    fn = dlsym(handle, symbol);
    if (fn)
        a90_write_symbol_probe_event(scope, symbol, 1, (const char *)0);
    else
        a90_write_symbol_probe_event(scope, symbol, 0, dlerror());
    return fn;
}

static a90_android_get_exported_namespace_fn a90_resolve_get_namespace(void *libdl)
{
    void *fn;
    fn = a90_probe_symbol(libdl, "libdl", "android_get_exported_namespace");
    if (fn)
        return (a90_android_get_exported_namespace_fn)fn;
    fn = a90_probe_symbol((void *)0, "default", "android_get_exported_namespace");
    if (fn)
        return (a90_android_get_exported_namespace_fn)fn;
    fn = a90_probe_symbol((void *)0, "default", "__loader_android_get_exported_namespace");
    if (fn)
        return (a90_android_get_exported_namespace_fn)fn;
    fn = a90_probe_symbol(libdl, "libdl", "__loader_android_get_exported_namespace");
    return (a90_android_get_exported_namespace_fn)fn;
}

static struct a90_resolved_dlopen_ext a90_resolve_dlopen_ext(void *libdl)
{
    struct a90_resolved_dlopen_ext resolved = {0};
    resolved.fn = a90_probe_symbol(libdl, "libdl", "android_dlopen_ext");
    if (resolved.fn) {
        resolved.is_loader_entry = 0;
        resolved.scope = "libdl";
        resolved.symbol = "android_dlopen_ext";
        return resolved;
    }
    resolved.fn = a90_probe_symbol((void *)0, "default", "android_dlopen_ext");
    if (resolved.fn) {
        resolved.is_loader_entry = 0;
        resolved.scope = "default";
        resolved.symbol = "android_dlopen_ext";
        return resolved;
    }
    resolved.fn = a90_probe_symbol((void *)0, "default", "__loader_android_dlopen_ext");
    if (resolved.fn) {
        resolved.is_loader_entry = 1;
        resolved.scope = "default";
        resolved.symbol = "__loader_android_dlopen_ext";
        return resolved;
    }
    resolved.fn = a90_probe_symbol(libdl, "libdl", "__loader_android_dlopen_ext");
    if (resolved.fn) {
        resolved.is_loader_entry = 1;
        resolved.scope = "libdl";
        resolved.symbol = "__loader_android_dlopen_ext";
    }
    return resolved;
}

static void *a90_android_dlopen_in_namespace(const struct a90_resolved_dlopen_ext *dlopen_ext,
                                             const char *library,
                                             a90_android_namespace *namespace_handle)
{
    struct a90_android_dlextinfo extinfo = {0};
    extinfo.flags = A90_ANDROID_DLEXT_USE_NAMESPACE;
    extinfo.library_namespace = namespace_handle;
    (void)dlerror();
    if (dlopen_ext->is_loader_entry) {
        a90_loader_android_dlopen_ext_fn fn =
            (a90_loader_android_dlopen_ext_fn)dlopen_ext->fn;
        return fn(library, A90_RTLD_NOW, &extinfo, __builtin_return_address(0));
    }
    return ((a90_android_dlopen_ext_fn)dlopen_ext->fn)(library, A90_RTLD_NOW, &extinfo);
}

static void a90_write_call_event(uint32_t seq, uint32_t cmd, uint32_t in_len,
                                 uint32_t out_len, int32_t ret,
                                 const uint8_t digest[32], const char *raw_path)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"acdb_ioctl\",\"seq\":");
    a90_write_dec(fd, seq);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, ",\"cmd\":\"");
    a90_write_hex32(fd, cmd);
    a90_write_str(fd, "\",\"in_len\":");
    a90_write_dec(fd, in_len);
    a90_write_str(fd, ",\"out_len\":");
    a90_write_dec(fd, out_len);
    a90_write_str(fd, ",\"ret\":");
    a90_write_sdec(fd, ret);
    a90_write_str(fd, ",\"is_target_4916\":");
    a90_write_str(fd, out_len == A90_TARGET_OUT_LEN ? "true" : "false");
    a90_write_str(fd, ",\"sha256\":\"");
    a90_write_sha256_hex(fd, digest);
    a90_write_str(fd, "\",\"raw_path\":\"");
    a90_write_str(fd, raw_path);
    a90_write_str(fd, "\"}\n");
    a90_close(fd);
}

static void a90_capture_one(a90_acdb_ioctl_fn acdb_ioctl_fn, uint32_t cmd,
                            uint32_t in_len, uint32_t out_len)
{
    uint32_t i;
    int32_t ret;
    uint32_t seq;
    uint8_t digest[32];
    char raw_path[128];
    int raw_fd;

    for (i = 0; i < A90_MAX_OUT_LEN; i++)
        a90_output[i] = 0;
    ret = acdb_ioctl_fn(cmd, in_len == 0 ? (const uint8_t *)0 : a90_input,
                        in_len, a90_output, out_len);
    a90_sha256_bytes(a90_output, out_len, digest);
    seq = ++a90_sequence;
    a90_make_raw_path(raw_path, seq, cmd, in_len, out_len);
    raw_fd = a90_open_new(raw_path);
    if (raw_fd >= 0) {
        a90_write_all(raw_fd, a90_output, out_len);
        a90_close(raw_fd);
    }
    a90_write_call_event(seq, cmd, in_len, out_len, ret, digest, raw_path);
}

void _start(void)
{
    uint32_t i;
    uint32_t j;
    uint32_t k;
    int32_t init_ret;
    int namespace_seen = 0;
    const char *selected_namespace_name = (const char *)0;
    a90_android_namespace *namespace_handle;
    a90_android_namespace *selected_namespace = (a90_android_namespace *)0;
    void *libdl;
    void *audcal;
    void *loader;
    a90_android_get_exported_namespace_fn get_namespace_fn;
    struct a90_resolved_dlopen_ext dlopen_ext;
    a90_acdb_loader_init_v3_fn init_v3;
    a90_acdb_ioctl_fn acdb_ioctl_fn;

    for (i = 0; i < A90_MAX_IN_LEN; i++)
        a90_input[i] = 0;

    (void)dlerror();
    libdl = dlopen(A90_LIBDL, A90_RTLD_NOW);
    if (!libdl) {
        a90_write_error_event("dlopen-libdl", -1, dlerror());
        a90_exit(21);
    }
    get_namespace_fn = a90_resolve_get_namespace(libdl);
    if (!get_namespace_fn) {
        a90_write_error_event("dlsym-android_get_exported_namespace", -2, (const char *)0);
        a90_exit(22);
    }
    dlopen_ext = a90_resolve_dlopen_ext(libdl);
    if (!dlopen_ext.fn) {
        a90_write_error_event("dlsym-android_dlopen_ext", -3, (const char *)0);
        a90_exit(23);
    }

    audcal = (void *)0;
    for (i = 0; i < sizeof(a90_namespace_names) / sizeof(a90_namespace_names[0]); i++) {
        namespace_handle = get_namespace_fn(a90_namespace_names[i]);
        a90_write_namespace_probe_event(a90_namespace_names[i],
                                        namespace_handle != (a90_android_namespace *)0);
        if (!namespace_handle)
            continue;
        namespace_seen = 1;
        audcal = a90_android_dlopen_in_namespace(&dlopen_ext, A90_LIBAUDCAL,
                                                 namespace_handle);
        if (audcal) {
            selected_namespace = namespace_handle;
            selected_namespace_name = a90_namespace_names[i];
            a90_write_namespace_load_event(selected_namespace_name, A90_LIBAUDCAL,
                                           1, (const char *)0);
            a90_write_namespace_selected_event(selected_namespace_name);
            break;
        }
        a90_write_namespace_load_event(a90_namespace_names[i], A90_LIBAUDCAL,
                                       0, dlerror());
    }
    if (!audcal) {
        if (!namespace_seen) {
            a90_write_error_event("namespace-none-visible", -4, (const char *)0);
            a90_exit(24);
        }
        a90_write_error_event("namespace-visible-load-failed-libaudcal", -5,
                              (const char *)0);
        a90_exit(25);
    }

    loader = a90_android_dlopen_in_namespace(&dlopen_ext, A90_LIBACDBLOADER,
                                             selected_namespace);
    if (!loader) {
        a90_write_namespace_load_event(selected_namespace_name, A90_LIBACDBLOADER,
                                       0, dlerror());
        a90_write_error_event("android_dlopen_ext-libacdbloader", -6,
                              (const char *)0);
        a90_exit(26);
    }
    a90_write_namespace_load_event(selected_namespace_name, A90_LIBACDBLOADER,
                                   1, (const char *)0);

    (void)dlerror();
    init_v3 = (a90_acdb_loader_init_v3_fn)dlsym(loader, "acdb_loader_init_v3");
    if (!init_v3) {
        a90_write_error_event("dlsym-acdb_loader_init_v3", -7, dlerror());
        a90_exit(27);
    }
    (void)dlerror();
    acdb_ioctl_fn = (a90_acdb_ioctl_fn)dlsym(audcal, "acdb_ioctl");
    if (!acdb_ioctl_fn) {
        a90_write_error_event("dlsym-acdb_ioctl", -8, dlerror());
        a90_exit(28);
    }
    init_ret = init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U);
    if (init_ret != 0) {
        a90_write_error_event("acdb_loader_init_v3", init_ret, (const char *)0);
        a90_exit(29);
    }

    for (i = 0; i < sizeof(a90_commands) / sizeof(a90_commands[0]); i++) {
        for (j = 0; j < sizeof(a90_in_lens) / sizeof(a90_in_lens[0]); j++) {
            for (k = 0; k < sizeof(a90_out_lens) / sizeof(a90_out_lens[0]); k++) {
                a90_capture_one(acdb_ioctl_fn, a90_commands[i],
                                a90_in_lens[j], a90_out_lens[k]);
            }
        }
    }

    a90_exit(0);
}
