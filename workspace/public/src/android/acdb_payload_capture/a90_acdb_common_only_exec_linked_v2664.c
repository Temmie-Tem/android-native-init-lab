/*
 * V2664 ARM32 own-process ACDB common-custom-topology caller.
 *
 * This helper initializes the stock ACDB loader, arms the SET-calibration
 * capture interposer, then calls only acdb_loader_send_common_custom_topology().
 * It intentionally does not call send_audio_cal_v5: V2663 proved the exported
 * common function already contains the missing 10/14/24 custom-topology SET
 * paths, and V2660's full-manifest route crashed before its post-init common
 * call.  Live use must pair this helper with the V2659 phase-common preload and
 * the V2630 ioctl shim that fake-successes AUDIO_SET_CALIBRATION after dumping
 * the exact arg/dma-buf bytes.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long size_t;

extern int32_t acdb_loader_init_v3(const char *acdb_files_path,
                                   const char *delta_file_path,
                                   uint32_t meta_info_type);
extern int32_t acdb_loader_send_common_custom_topology(void);
extern void a90_arm_capture(void) __attribute__((weak, visibility("default")));

#define A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"
#define A90_DELTA_DIR "/data/local/tmp/a90-acdb-ownget/delta"
#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-common-only-events.jsonl"

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
    while (s[n])
        n++;
    return n;
}

static void a90_write_all(int fd, const void *buf, size_t len)
{
    const char *p = (const char *)buf;
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

static void a90_write_event(const char *stage, int32_t code)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"common_only_helper\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"code\":");
    a90_write_sdec(fd, code);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

void _start(void)
{
    int32_t init_ret;
    int32_t topology_ret;

    init_ret = acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U);
    a90_write_event("init_v3_return", init_ret);
    if (init_ret != 0)
        a90_exit(29);

    if (!a90_arm_capture) {
        a90_write_event("arm_capture_missing", -1);
        a90_exit(30);
    }

    a90_arm_capture();
    a90_write_event("armed_before_common_topology", 0);
    a90_write_event("before_send_common_custom_topology", 0);

    topology_ret = acdb_loader_send_common_custom_topology();
    a90_write_event("send_common_custom_topology_return", topology_ret);

    /* Non-zero common return is still useful if SET rows were dumped. */
    a90_exit(0);
}
