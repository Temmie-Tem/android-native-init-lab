/*
 * V2559 ARM32 own-process ACDB per-device manifest caller.
 *
 * V2557 proved the 4916-byte common topology payload and then crashed in the
 * downstream common-topology tail before the per-device fetch could run.  This
 * helper keeps the same ACDB init + dump interposer path, but deliberately skips
 * that common-topology API because the payload is already pinned privately by
 * SHA-256.  It then drives the Android-observed speaker per-device calibration
 * fetch through acdb_loader_send_audio_cal_v5().
 *
 * Safety boundary: this helper itself does not open /dev/msm_audio_cal and does
 * not issue calibration device calls.  Live use must still pair it with the combined preload
 * that fakes AUDIO_ALLOCATE/DEALLOCATE/SET_CALIBRATION, so libacdbloader's SET
 * path is observed but not delivered to the kernel.  Raw acdb_ioctl out buffers
 * are emitted only by the preload into the private capture directory.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long size_t;

extern int32_t acdb_loader_init_v3(const char *acdb_files_path,
                                   const char *delta_file_path,
                                   uint32_t meta_info_type);
extern int32_t acdb_loader_send_audio_cal_v5(int32_t acdb_id,
                                             int32_t path_or_caps,
                                             int32_t app_id,
                                             int32_t sample_rate,
                                             int32_t afe_sample_rate,
                                             int32_t session_type,
                                             int32_t instance_flag);
extern void a90_arm_capture(void) __attribute__((weak, visibility("default")));

#define A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"
#define A90_DELTA_DIR "/data/local/tmp/a90-acdb-ownget/delta"
#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-per-device-manifest-events.jsonl"
#define A90_PINNED_TOPOLOGY_SHA256 "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89"
#define A90_PINNED_TOPOLOGY_LEN 4916

#define A90_SPEAKER_ACDB_ID 15
#define A90_SPEAKER_RX_PATH 0
#define A90_APP_TYPE_MEDIA 0x11135
#define A90_SAMPLE_RATE_48K 48000
#define A90_AFE_SAMPLE_RATE_48K 48000
#define A90_SESSION_TYPE_DEFAULT 0
#define A90_INSTANCE_FLAG_DEFAULT 1

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

static void a90_write_event(const char *event, const char *stage, int32_t code)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"");
    a90_write_str(fd, event);
    a90_write_str(fd, "\",\"stage\":\"");
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

static void a90_write_topology_pinned_event(void)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;
    a90_write_str(fd, "{\"event\":\"per_device_helper\",\"stage\":\"common_topology_skipped_known_payload\",\"code\":0,\"payload_len\":");
    a90_write_dec(fd, A90_PINNED_TOPOLOGY_LEN);
    a90_write_str(fd, ",\"payload_sha256\":\"");
    a90_write_str(fd, A90_PINNED_TOPOLOGY_SHA256);
    a90_write_str(fd, "\",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

void _start(void)
{
    int32_t init_ret;
    int32_t audio_cal_ret;

    init_ret = acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U);
    a90_write_event("per_device_helper", "init_v3_return", init_ret);
    if (init_ret != 0)
        a90_exit(29);

    if (!a90_arm_capture) {
        a90_write_event("per_device_helper", "arm_capture_missing", -1);
        a90_exit(30);
    }

    a90_arm_capture();
    a90_write_event("per_device_helper", "armed_before_send_audio_cal_v5", 0);
    a90_write_topology_pinned_event();

    audio_cal_ret = acdb_loader_send_audio_cal_v5(A90_SPEAKER_ACDB_ID,
                                                  A90_SPEAKER_RX_PATH,
                                                  A90_APP_TYPE_MEDIA,
                                                  A90_SAMPLE_RATE_48K,
                                                  A90_AFE_SAMPLE_RATE_48K,
                                                  A90_SESSION_TYPE_DEFAULT,
                                                  A90_INSTANCE_FLAG_DEFAULT);
    a90_write_event("per_device_helper", "send_audio_cal_v5_return", audio_cal_ret);

    if (audio_cal_ret != 0)
        a90_exit(32);
    a90_exit(0);
}
