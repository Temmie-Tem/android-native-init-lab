/*
 * V2719 in-hook route-first common-topology hook.
 *
 * V2718 proved the helper cannot rely on returning from acdb_loader_init_v3:
 * the process can SIGSEGV before post-init helper code runs. This preload moves
 * the route-specific public send_audio_cal_v5() edge and the real common custom
 * topology call into the init-time common-topology hook itself, then exits the
 * process after artifacts are written. The V2630 ioctl shim linked into the same
 * object fake-successes AUDIO_SET_CALIBRATION after dumping SET arg/dma-buf data.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long uintptr_t;
typedef unsigned long size_t;

extern void *dlsym(void *handle, const char *symbol);
extern void a90_arm_capture(void) __attribute__((weak, visibility("default")));

#define A90_RTLD_NEXT ((void *)-1L)
#define A90_RTLD_DEFAULT ((void *)0)

#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-v2719-inhook-route-first-common-events.jsonl"
#define A90_LOADER_IS_INITIALIZED_OFF 0x00008034UL
#define A90_LOADER_INIT_FLAG_OFF 0x00018a9cUL

#define A90_SPEAKER_ACDB_ID 15
#define A90_SPEAKER_RX_CAPMASK 1
#define A90_APP_TYPE_MEDIA 0x11135
#define A90_SAMPLE_RATE_48K 48000
#define A90_AFE_SAMPLE_RATE_INIT 0
#define A90_SESSION_TYPE_48K 48000
#define A90_INSTANCE_FLAG_DEFAULT 1

#define A90_PHASE_INIT_ROUTE 1
#define A90_PHASE_SEND_V5 2
#define A90_PHASE_REAL_COMMON 3

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_GETTID 224
#define A90_NR_EXIT_GROUP 248
#define A90_NR_EXIT 1
#define A90_NR_OPENAT 322

typedef int32_t (*a90_common_topology_fn)(void);
typedef int32_t (*a90_send_audio_cal_v5_fn)(int32_t acdb_id,
                                            int32_t path_or_caps,
                                            int32_t app_id,
                                            int32_t sample_rate,
                                            int32_t afe_sample_rate,
                                            int32_t session_type,
                                            int32_t instance_flag);

static volatile int a90_in_hook;
static volatile int a90_phase;
static volatile uint32_t a90_entry_count;
static volatile uint32_t a90_reentry_count;
static a90_common_topology_fn a90_real_common_topology;
static a90_send_audio_cal_v5_fn a90_real_send_audio_cal_v5;

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

static void a90_exit(int code)
{
    (void)a90_syscall1(A90_NR_EXIT_GROUP, code);
    (void)a90_syscall1(A90_NR_EXIT, code);
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

static void a90_write_dec(int fd, uint32_t value)
{
    char rev[16];
    char out[16];
    int n = 0;
    int i;

    if (value == 0) {
        a90_write_str(fd, "0");
        return;
    }
    while (value && n < (int)sizeof(rev)) {
        rev[n++] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    for (i = 0; i < n; i++)
        out[i] = rev[n - i - 1];
    a90_write_all(fd, out, (size_t)n);
}

static void a90_write_sdec(int fd, int32_t value)
{
    uint32_t u;
    if (value < 0) {
        a90_write_str(fd, "-");
        u = 0U - (uint32_t)value;
    } else {
        u = (uint32_t)value;
    }
    a90_write_dec(fd, u);
}

static void a90_write_hex32(int fd, uint32_t value)
{
    static const char hex[] = "0123456789abcdef";
    char buf[10];
    int i;

    buf[0] = '0';
    buf[1] = 'x';
    for (i = 0; i < 8; i++)
        buf[2 + i] = hex[(value >> ((7 - i) * 4)) & 0xfU];
    a90_write_all(fd, buf, sizeof(buf));
}

static void a90_write_event(const char *stage, int32_t code)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;

    a90_write_str(fd, "{\"event\":\"v2719_inhook_route_first_common\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"code\":");
    a90_write_sdec(fd, code);
    a90_write_str(fd, ",\"phase\":");
    a90_write_dec(fd, (uint32_t)a90_phase);
    a90_write_str(fd, ",\"entry_count\":");
    a90_write_dec(fd, (uint32_t)a90_entry_count);
    a90_write_str(fd, ",\"reentry_count\":");
    a90_write_dec(fd, (uint32_t)a90_reentry_count);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_write_hex_event(const char *stage, uint32_t value)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;

    a90_write_str(fd, "{\"event\":\"v2719_inhook_route_first_common\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"value\":");
    a90_write_hex32(fd, value);
    a90_write_str(fd, ",\"phase\":");
    a90_write_dec(fd, (uint32_t)a90_phase);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static void a90_resolve_symbols(void)
{
    if (!a90_real_common_topology)
        a90_real_common_topology = (a90_common_topology_fn)dlsym(A90_RTLD_NEXT, "acdb_loader_send_common_custom_topology");
    if (!a90_real_send_audio_cal_v5)
        a90_real_send_audio_cal_v5 = (a90_send_audio_cal_v5_fn)dlsym(A90_RTLD_DEFAULT, "acdb_loader_send_audio_cal_v5");
    if (!a90_real_send_audio_cal_v5)
        a90_real_send_audio_cal_v5 = (a90_send_audio_cal_v5_fn)dlsym(A90_RTLD_NEXT, "acdb_loader_send_audio_cal_v5");
}

static int a90_patch_initialized_flag(void)
{
    uintptr_t is_initialized;
    uintptr_t base;
    volatile unsigned char *flag;

    is_initialized = (uintptr_t)dlsym(A90_RTLD_DEFAULT, "acdb_loader_is_initialized");
    if (!is_initialized)
        is_initialized = (uintptr_t)dlsym(A90_RTLD_NEXT, "acdb_loader_is_initialized");
    if (!is_initialized)
        return -1;

    is_initialized &= ~(uintptr_t)1U;
    base = is_initialized - A90_LOADER_IS_INITIALIZED_OFF;
    flag = (volatile unsigned char *)(base + A90_LOADER_INIT_FLAG_OFF);
    *flag = 1U;
    a90_write_hex_event("patched_initialized_flag_addr", (uint32_t)(uintptr_t)flag);
    return 0;
}

__attribute__((visibility("default"))) int32_t acdb_loader_send_common_custom_topology(void)
{
    int32_t audio_cal_ret = -90;
    int32_t common_ret = -91;
    int patch_ret;

    if (a90_in_hook) {
        a90_reentry_count++;
        a90_write_event("common_reentry_neutralized", 0);
        return 0;
    }

    a90_in_hook = 1;
    a90_entry_count++;
    a90_phase = A90_PHASE_INIT_ROUTE;
    a90_write_event("inhook_route_first_enter", 0);
    a90_resolve_symbols();

    patch_ret = a90_patch_initialized_flag();
    a90_write_event("inhook_patch_initialized_flag_return", patch_ret);

    if (a90_arm_capture) {
        a90_arm_capture();
        a90_write_event("inhook_armed_capture", 0);
    } else {
        a90_write_event("inhook_arm_capture_missing", -1);
    }

    a90_phase = A90_PHASE_SEND_V5;
    if (a90_real_send_audio_cal_v5) {
        a90_write_event("inhook_before_send_audio_cal_v5", 0);
        audio_cal_ret = a90_real_send_audio_cal_v5(A90_SPEAKER_ACDB_ID,
                                                   A90_SPEAKER_RX_CAPMASK,
                                                   A90_APP_TYPE_MEDIA,
                                                   A90_SAMPLE_RATE_48K,
                                                   A90_AFE_SAMPLE_RATE_INIT,
                                                   A90_SESSION_TYPE_48K,
                                                   A90_INSTANCE_FLAG_DEFAULT);
        a90_write_event("inhook_send_audio_cal_v5_return", audio_cal_ret);
    } else {
        a90_write_event("inhook_send_audio_cal_v5_missing", -1);
    }

    a90_phase = A90_PHASE_REAL_COMMON;
    if (a90_real_common_topology) {
        a90_write_event("inhook_before_real_common", 0);
        common_ret = a90_real_common_topology();
        a90_write_event("inhook_real_common_return", common_ret);
    } else {
        a90_write_event("inhook_real_common_missing", -1);
    }

    a90_phase = 0;
    a90_write_event("inhook_exit_after_route_first_common", common_ret ? common_ret : audio_cal_ret);
    a90_in_hook = 0;
    a90_exit(0);
    return common_ret;
}
