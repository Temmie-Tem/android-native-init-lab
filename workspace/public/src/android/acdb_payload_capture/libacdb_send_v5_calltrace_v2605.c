/*
 * V2605 send_audio_cal_v5 imported-call tracer.
 *
 * This interposer is measurement-only.  It does not issue ACDB commands,
 * does not open audio-calibration device nodes, and does not touch audio routes.  It logs
 * only metadata for imported calls reached from libacdbloader's
 * acdb_loader_send_audio_cal_v5() range so a future live run can distinguish
 * a mutex wait from progress into the pre-GET setup path.
 */

#include <stdarg.h>

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long uintptr_t;
typedef unsigned long size_t;

extern void *dlsym(void *handle, const char *symbol);

#define A90_RTLD_NEXT ((void *)-1L)
#define A90_RTLD_DEFAULT ((void *)0)

#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-v2605-send-v5-calltrace-events.jsonl"
#define A90_SEND_AUDIO_CAL_V5_OFF 0x00009d31UL
#define A90_SEND_AUDIO_CAL_V5_RANGE_START 0x00009d30UL
#define A90_SEND_AUDIO_CAL_V5_RANGE_STOP  0x0000a100UL

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_GETTID 224
#define A90_NR_OPENAT 322

typedef int (*a90_pthread_mutex_lock_fn)(void *mutex);
typedef int (*a90_pthread_mutex_unlock_fn)(void *mutex);
typedef int (*a90_android_log_vprint_fn)(int prio, const char *tag, const char *fmt, va_list ap);
typedef int (*a90_android_log_print_fn)(int prio, const char *tag, const char *fmt, ...);

typedef int32_t (*a90_send_audio_cal_v5_fn)(int32_t acdb_id,
                                            int32_t path,
                                            int32_t app_id,
                                            int32_t sample_rate,
                                            int32_t stack_arg5,
                                            int32_t stack_arg6,
                                            int32_t instance);

static volatile int a90_in_hook;
static a90_pthread_mutex_lock_fn a90_real_pthread_mutex_lock;
static a90_pthread_mutex_unlock_fn a90_real_pthread_mutex_unlock;
static a90_android_log_vprint_fn a90_real_android_log_vprint;
static a90_android_log_print_fn a90_real_android_log_print;
static a90_send_audio_cal_v5_fn a90_real_send_audio_cal_v5;
static uintptr_t a90_loader_base;

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
    for (i = n - 1; i >= 0; i--)
        a90_write_all(fd, &rev[i], 1);
}

static void a90_write_sdec(int fd, int value)
{
    if (value < 0) {
        a90_write_str(fd, "-");
        a90_write_dec(fd, (unsigned int)(0U - (uint32_t)value));
    } else {
        a90_write_dec(fd, (unsigned int)value);
    }
}

static void a90_write_hex32(int fd, uint32_t v)
{
    static const char hex[] = "0123456789abcdef";
    char buf[10];
    int i;
    buf[0] = '0';
    buf[1] = 'x';
    for (i = 0; i < 8; i++)
        buf[2 + i] = hex[(v >> ((7 - i) * 4)) & 0xf];
    a90_write_all(fd, buf, sizeof(buf));
}

static uintptr_t a90_ptr_value(void *p)
{
    return ((uintptr_t)p) & ~(uintptr_t)1U;
}

static void a90_resolve(void)
{
    if (!a90_real_pthread_mutex_lock)
        a90_real_pthread_mutex_lock = (a90_pthread_mutex_lock_fn)dlsym(A90_RTLD_NEXT, "pthread_mutex_lock");
    if (!a90_real_pthread_mutex_unlock)
        a90_real_pthread_mutex_unlock = (a90_pthread_mutex_unlock_fn)dlsym(A90_RTLD_NEXT, "pthread_mutex_unlock");
    if (!a90_real_android_log_vprint)
        a90_real_android_log_vprint = (a90_android_log_vprint_fn)dlsym(A90_RTLD_NEXT, "__android_log_vprint");
    if (!a90_real_android_log_print)
        a90_real_android_log_print = (a90_android_log_print_fn)dlsym(A90_RTLD_NEXT, "__android_log_print");
    if (!a90_real_send_audio_cal_v5) {
        a90_real_send_audio_cal_v5 = (a90_send_audio_cal_v5_fn)dlsym(A90_RTLD_NEXT, "acdb_loader_send_audio_cal_v5");
        if (!a90_real_send_audio_cal_v5)
            a90_real_send_audio_cal_v5 = (a90_send_audio_cal_v5_fn)dlsym(A90_RTLD_DEFAULT, "acdb_loader_send_audio_cal_v5");
        if (a90_real_send_audio_cal_v5)
            a90_loader_base = a90_ptr_value((void *)a90_real_send_audio_cal_v5) - A90_SEND_AUDIO_CAL_V5_OFF;
    }
}

static uint32_t a90_caller_offset(uintptr_t caller)
{
    if (!a90_loader_base || caller < a90_loader_base)
        return 0;
    return (uint32_t)(caller - a90_loader_base);
}

static int a90_is_send_v5_offset(uint32_t offset)
{
    return offset >= A90_SEND_AUDIO_CAL_V5_RANGE_START && offset < A90_SEND_AUDIO_CAL_V5_RANGE_STOP;
}

static void a90_log_event(const char *hook, const char *phase, uintptr_t caller, void *arg0, int ret)
{
    uint32_t offset;
    int fd;

    if (a90_in_hook)
        return;
    a90_in_hook = 1;
    a90_resolve();
    offset = a90_caller_offset(caller);
    if (!a90_is_send_v5_offset(offset)) {
        a90_in_hook = 0;
        return;
    }

    fd = a90_open_append(A90_EVENTS_PATH);
    if (fd >= 0) {
        a90_write_str(fd, "{\"event\":\"v2605_send_v5_calltrace\",\"hook\":\"");
        a90_write_str(fd, hook);
        a90_write_str(fd, "\",\"phase\":\"");
        a90_write_str(fd, phase);
        a90_write_str(fd, "\",\"pid\":");
        a90_write_dec(fd, a90_getpid());
        a90_write_str(fd, ",\"tid\":");
        a90_write_dec(fd, a90_gettid());
        a90_write_str(fd, ",\"caller\":\"");
        a90_write_hex32(fd, (uint32_t)caller);
        a90_write_str(fd, "\",\"caller_offset\":\"");
        a90_write_hex32(fd, offset);
        a90_write_str(fd, "\",\"arg0\":\"");
        a90_write_hex32(fd, (uint32_t)(uintptr_t)arg0);
        a90_write_str(fd, "\",\"ret\":");
        a90_write_sdec(fd, ret);
        a90_write_str(fd, "}\n");
        a90_close(fd);
    }
    a90_in_hook = 0;
}

__attribute__((visibility("default"))) int pthread_mutex_lock(void *mutex)
{
    uintptr_t caller = (uintptr_t)__builtin_return_address(0);
    int ret = -1;

    if (!a90_in_hook) {
        a90_in_hook = 1;
        a90_resolve();
        a90_in_hook = 0;
        a90_log_event("pthread_mutex_lock", "enter", caller, mutex, 0);
    }
    if (a90_real_pthread_mutex_lock)
        ret = a90_real_pthread_mutex_lock(mutex);
    a90_log_event("pthread_mutex_lock", "return", caller, mutex, ret);
    return ret;
}

__attribute__((visibility("default"))) int pthread_mutex_unlock(void *mutex)
{
    uintptr_t caller = (uintptr_t)__builtin_return_address(0);
    int ret = -1;

    if (!a90_in_hook) {
        a90_in_hook = 1;
        a90_resolve();
        a90_in_hook = 0;
        a90_log_event("pthread_mutex_unlock", "enter", caller, mutex, 0);
    }
    if (a90_real_pthread_mutex_unlock)
        ret = a90_real_pthread_mutex_unlock(mutex);
    a90_log_event("pthread_mutex_unlock", "return", caller, mutex, ret);
    return ret;
}

__attribute__((visibility("default"))) int __android_log_print(int prio, const char *tag, const char *fmt, ...)
{
    uintptr_t caller = (uintptr_t)__builtin_return_address(0);
    int ret = 0;
    va_list ap;

    a90_log_event("__android_log_print", "enter", caller, (void *)fmt, prio);
    if (!a90_in_hook) {
        a90_in_hook = 1;
        a90_resolve();
        a90_in_hook = 0;
    }
    va_start(ap, fmt);
    if (a90_real_android_log_vprint)
        ret = a90_real_android_log_vprint(prio, tag, fmt, ap);
    else if (a90_real_android_log_print)
        ret = 0;
    va_end(ap);
    a90_log_event("__android_log_print", "return", caller, (void *)fmt, ret);
    return ret;
}
