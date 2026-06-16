/*
 * V2626 ARM32 own-process ACDB AFE-topology GET probe.
 *
 * The paired preload skips common-topology work during acdb_loader_init_v3(),
 * patches the initialized flag, and arms the acdb_ioctl tap only after init
 * returns.  This helper then issues only the AFE topology ID/table GETs needed
 * to identify the missing native cal_type 8/9 payloads.  It does not call the
 * send-audio-cal dispatcher, does not open the native audio calibration device,
 * and does not issue any calibration SET.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long size_t;
typedef unsigned long uintptr_t;

extern int32_t acdb_loader_init_v3(const char *acdb_files_path,
                                   const char *delta_file_path,
                                   uint32_t flags);
extern int32_t acdb_ioctl(uint32_t cmd, const unsigned char *in_buf,
                          uint32_t in_len, unsigned char *out_buf,
                          uint32_t out_len);
extern void a90_arm_capture(void) __attribute__((weak, visibility("default")));

#define A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"
#define A90_DELTA_DIR "/data/local/tmp/a90-acdb-ownget/delta"
#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-v2626-afe-topology-probe-events.jsonl"

#define A90_SPEAKER_ACDB_ID 15U
#define A90_APP_TYPE_MEDIA 0x11135U
#define A90_SAMPLE_RATE_48K 48000U
#define A90_MATRIX_CAPACITY 0x5000U

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_EXIT 1
#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_GETTID 224
#define A90_NR_EXIT_GROUP 248
#define A90_NR_OPENAT 322

static unsigned char a90_out[A90_MATRIX_CAPACITY];
static uint32_t a90_meta_list_head;

static long a90_syscall0(long n)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0");
    __asm__ volatile("svc #0" : "=r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall1(long n, long a0)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a0;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall3(long n, long a0, long a1, long a2)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a0;
    register long r1 __asm__("r1") = a1;
    register long r2 __asm__("r2") = a2;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory");
    return r0;
}

static long a90_syscall4(long n, long a0, long a1, long a2, long a3)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a0;
    register long r1 __asm__("r1") = a1;
    register long r2 __asm__("r2") = a2;
    register long r3 __asm__("r3") = a3;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r7) : "memory");
    return r0;
}

static void a90_exit(int code)
{
    (void)a90_syscall1(A90_NR_EXIT_GROUP, code);
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
    while (s && s[n])
        n++;
    return n;
}

static void a90_write_all(int fd, const char *p, size_t len)
{
    while (len) {
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

static void a90_write_dec(int fd, unsigned int v)
{
    char buf[16];
    char rev[16];
    int n = 0;
    int i;

    if (v == 0) {
        a90_write_str(fd, "0");
        return;
    }
    while (v && n < (int)sizeof(rev)) {
        rev[n++] = (char)('0' + (v % 10));
        v /= 10;
    }
    for (i = 0; i < n; i++)
        buf[i] = rev[n - i - 1];
    a90_write_all(fd, buf, (size_t)n);
}

static void a90_write_hex32(int fd, uint32_t v)
{
    static const char hex[] = "0123456789abcdef";
    char out[10];
    int i;

    out[0] = '0';
    out[1] = 'x';
    for (i = 0; i < 8; i++)
        out[2 + i] = hex[(v >> (28U - ((uint32_t)i * 4U))) & 0xfU];
    a90_write_all(fd, out, sizeof(out));
}

static void a90_write_signed(int fd, int value)
{
    if (value < 0) {
        a90_write_str(fd, "-");
        a90_write_dec(fd, (unsigned int)(-value));
    } else {
        a90_write_dec(fd, (unsigned int)value);
    }
}

static void a90_write_event(const char *stage, int code)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;

    a90_write_str(fd, "{\"event\":\"v2626_afe_topology_probe\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"code\":");
    a90_write_signed(fd, code);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_write_case_event(const char *name, uint32_t cmd, uint32_t step,
                                 int32_t ret, uint32_t out_word)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;

    a90_write_str(fd, "{\"event\":\"v2626_afe_topology_probe\",\"stage\":\"case_return\",\"case\":\"");
    a90_write_str(fd, name);
    a90_write_str(fd, "\",\"cmd\":\"");
    a90_write_hex32(fd, cmd);
    a90_write_str(fd, "\",\"step\":");
    a90_write_dec(fd, step);
    a90_write_str(fd, ",\"ret\":");
    a90_write_signed(fd, ret);
    a90_write_str(fd, ",\"out_word\":\"");
    a90_write_hex32(fd, out_word);
    a90_write_str(fd, "\"}\n");
    a90_close(fd);
}

static void a90_memzero(void *p, uint32_t len)
{
    unsigned char *q = (unsigned char *)p;
    uint32_t i;
    for (i = 0; i < len; i++)
        q[i] = 0;
}

static uint32_t a90_load_le32(const unsigned char *p)
{
    return ((uint32_t)p[0]) | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int32_t a90_call(const char *name, uint32_t cmd, uint32_t *words,
                        uint32_t word_count, uint32_t out_len, uint32_t step)
{
    int32_t ret;
    uint32_t out_word = 0;

    a90_memzero(a90_out, A90_MATRIX_CAPACITY);
    ret = acdb_ioctl(cmd, (const unsigned char *)words, word_count * 4U, a90_out, out_len);
    if (out_len >= 4U)
        out_word = a90_load_le32(a90_out);
    a90_write_case_event(name, cmd, step, ret, out_word);
    return ret;
}

static uint32_t a90_prepare_empty_meta_list(void)
{
    a90_meta_list_head = (uint32_t)(uintptr_t)&a90_meta_list_head;
    return a90_meta_list_head;
}

static void a90_run_afe_topology_probe(void)
{
    uint32_t words[2];
    uint32_t topo_buf_4 = 0;
    uint32_t topo_buf_256[64];
    uint32_t topo_buf_4096[1024];

    words[0] = A90_SPEAKER_ACDB_ID;
    (void)a90_call("afe-topology-id", 0x000130d8U, words, 1U, 4U, 0U);

    a90_memzero(&topo_buf_4, (uint32_t)sizeof(topo_buf_4));
    words[0] = (uint32_t)sizeof(topo_buf_4);
    words[1] = (uint32_t)(uintptr_t)&topo_buf_4;
    (void)a90_call("afe-topology-cap4", 0x00013262U, words, 2U, 4U, 4U);

    a90_memzero(topo_buf_256, (uint32_t)sizeof(topo_buf_256));
    words[0] = (uint32_t)sizeof(topo_buf_256);
    words[1] = (uint32_t)(uintptr_t)topo_buf_256;
    (void)a90_call("afe-topology-cap256", 0x00013262U, words, 2U, 4U, 256U);

    a90_memzero(topo_buf_4096, (uint32_t)sizeof(topo_buf_4096));
    words[0] = (uint32_t)sizeof(topo_buf_4096);
    words[1] = (uint32_t)(uintptr_t)topo_buf_4096;
    (void)a90_call("afe-topology-cap4096", 0x00013262U, words, 2U, 4U, 4096U);
}

void _start(void)
{
    int32_t init_ret;
    uint32_t meta_head;

    meta_head = a90_prepare_empty_meta_list();
    a90_write_event("meta_list_head_ready", meta_head ? 0 : -1);
    a90_write_event("before_init_v3", 0);
    init_ret = acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, meta_head);
    a90_write_event("init_v3_return", init_ret);
    if (init_ret != 0)
        a90_exit(29);

    if (a90_arm_capture) {
        a90_write_event("before_arm_capture", 0);
        a90_arm_capture();
        a90_write_event("arm_capture_return", 0);
    } else {
        a90_write_event("arm_capture_missing", -1);
    }

    a90_write_event("before_afe_topology_probe", 0);
    a90_run_afe_topology_probe();
    a90_write_event("done", 0);
    a90_exit(0);
}
