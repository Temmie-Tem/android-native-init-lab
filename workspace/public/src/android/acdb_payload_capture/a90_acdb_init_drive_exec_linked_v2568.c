/*
 * V2568 ARM32 own-process ACDB init driver.
 *
 * This helper only starts acdb_loader_init_v3().  The V2568 preload owns the
 * common-topology hook and exits the process before the known init-tail null
 * dereference can run.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long size_t;

extern int32_t acdb_loader_init_v3(const char *acdb_files_path,
                                   const char *delta_file_path,
                                   uint32_t flags);

#define A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"
#define A90_DELTA_DIR "/data/local/tmp/a90-acdb-ownget/delta"
#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-v2568-init-driver-events.jsonl"

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

static void a90_write_event(const char *stage, int code)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;

    a90_write_str(fd, "{\"event\":\"v2568_init_driver\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"code\":");
    if (code < 0) {
        a90_write_str(fd, "-");
        a90_write_dec(fd, (unsigned int)(-code));
    } else {
        a90_write_dec(fd, (unsigned int)code);
    }
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

    a90_write_event("before_init_v3", 0);
    init_ret = acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U);
    a90_write_event("init_v3_return", init_ret);
    a90_exit(init_ret == 0 ? 0 : 29);
}
