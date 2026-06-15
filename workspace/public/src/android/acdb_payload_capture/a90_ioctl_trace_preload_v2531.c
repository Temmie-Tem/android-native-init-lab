/*
 * V2531 ARM32 ioctl trace preload for the own-process ACDB init path.
 *
 * This library observes libc ioctl() calls already made by libacdbloader.so.
 * It does not open /dev/msm_audio_cal, does not issue extra ioctls, and does
 * not call AUDIO_SET_CALIBRATION itself.  The wrapper uses a raw ioctl syscall
 * to avoid recursion, then mirrors libc's -1/errno behavior for callers.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long uintptr_t;
typedef unsigned long size_t;

extern int *__errno(void);

#define A90_TRACE_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/ioctl-trace-events.jsonl"

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_IOCTL 54
#define A90_NR_GETTID 224
#define A90_NR_OPENAT 322

#define A90_AUDIO_ALLOCATE_CALIBRATION 0xc00461c8UL
#define A90_AUDIO_DEALLOCATE_CALIBRATION 0xc00461c9UL
#define A90_AUDIO_SET_CALIBRATION 0xc00461cbUL

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

static void a90_write_hex_ptr(int fd, uintptr_t value)
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

static const char *a90_ioctl_name(uint32_t request)
{
    if (request == A90_AUDIO_ALLOCATE_CALIBRATION)
        return "AUDIO_ALLOCATE_CALIBRATION";
    if (request == A90_AUDIO_DEALLOCATE_CALIBRATION)
        return "AUDIO_DEALLOCATE_CALIBRATION";
    if (request == A90_AUDIO_SET_CALIBRATION)
        return "AUDIO_SET_CALIBRATION";
    return "unknown";
}

static void a90_set_errno(int err)
{
    int *slot = __errno();
    if (slot)
        *slot = err;
}

static void a90_write_ioctl_event(int fd, uint32_t request, uintptr_t arg,
                                  int32_t ret, int32_t err)
{
    int out = a90_open_append(A90_TRACE_EVENTS_PATH);
    if (out < 0)
        return;
    a90_write_str(out, "{\"event\":\"ioctl_trace\",\"pid\":");
    a90_write_dec(out, a90_getpid());
    a90_write_str(out, ",\"tid\":");
    a90_write_dec(out, a90_gettid());
    a90_write_str(out, ",\"fd\":");
    a90_write_sdec(out, fd);
    a90_write_str(out, ",\"request\":\"");
    a90_write_hex32(out, request);
    a90_write_str(out, "\",\"name\":\"");
    a90_write_str(out, a90_ioctl_name(request));
    a90_write_str(out, "\",\"arg\":\"");
    a90_write_hex_ptr(out, arg);
    a90_write_str(out, "\",\"ret\":");
    a90_write_sdec(out, ret);
    a90_write_str(out, ",\"errno\":");
    a90_write_sdec(out, err);
    a90_write_str(out, "}\n");
    a90_close(out);
}

__attribute__((visibility("default")))
int ioctl(int fd, unsigned long request, ...)
{
    __builtin_va_list ap;
    uintptr_t arg;
    long rc;
    int err = 0;
    int ret;

    __builtin_va_start(ap, request);
    arg = (uintptr_t)__builtin_va_arg(ap, void *);
    __builtin_va_end(ap);

    rc = a90_syscall3(A90_NR_IOCTL, fd, (long)request, (long)arg);
    if (rc < 0 && rc >= -4095) {
        err = (int)(-rc);
        ret = -1;
        a90_set_errno(err);
    } else {
        ret = (int)rc;
    }

    a90_write_ioctl_event(fd, (uint32_t)request, arg, ret, err);
    return ret;
}
