/* The fixed module is a regular member of the initial RAM root. The caller
 * reaches this function only after authenticating both same-boot witnesses
 * and the separate late permit on its original connected descriptor.
 */
#include <sys/syscall.h>
#ifdef G0Q_PRE_EFFECT_RETURN
#include "link-report.h"
#endif

#define ML030_MODULE_PATH "/usr/lib/g0q_ml030.ko"
#define ML030_RESULT_PATH "/sys/module/g0q_ml030/parameters/result"
#define ML030_REPORT_MAX 256U
static uint8_t ml030_result_digest[32];

static int ml030_read_result(uint8_t *out, size_t *size)
{
    int fd = open(ML030_RESULT_PATH, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return errno;
    int error = 0;
    *size = 0;
    while (*size < ML030_REPORT_MAX) {
        ssize_t n = read(fd, out + *size, ML030_REPORT_MAX - *size);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) {
            error = n < 0 ? errno : 0;
            break;
        }
        *size += (size_t)n;
    }
    if (*size == ML030_REPORT_MAX) {
        uint8_t extra;
        ssize_t n;
        do { n = read(fd, &extra, 1); } while (n < 0 && errno == EINTR);
        error = n < 0 ? errno : (n ? EOVERFLOW : 0);
    }
    if (close(fd) && !error) error = errno;
    return error;
}

static int ml030_load_once(void)
{
    int fd = open(ML030_MODULE_PATH, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return errno;
    struct stat st;
    int error = 0;
    if (fstat(fd, &st)) error = errno;
    else if (st.st_mode != (S_IFREG | 0400) || st.st_uid || st.st_gid ||
             st.st_nlink != 1 || st.st_size != ML030_MODULE_SIZE ||
             st.st_size <= 0 || st.st_size > 4*1024*1024) error = EINVAL;
    struct s22plus_max77705_runtime_sha256 hash;
    s22plus_max77705_runtime_sha256_init(&hash);
    uint8_t buf[4096], digest[32];
    off_t offset = 0;
    while (!error && offset < st.st_size) {
        ssize_t n = pread(fd, buf, sizeof(buf), offset);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) error = n < 0 ? errno : EIO;
        else {
            offset += n;
            s22plus_max77705_runtime_sha256_update(&hash, buf, (size_t)n);
        }
    }
    if (!error) {
        s22plus_max77705_runtime_sha256_final(&hash, digest);
        if (offset != st.st_size || !g_equal(digest, ml030_module_sha256, sizeof(digest)))
            error = EBADMSG;
    }
    if (!error && now_ms() >= deadline - 15000U) error = ETIMEDOUT;
    if (!error && syscall(SYS_finit_module, fd, "", 0)) error = errno;
    if (close(fd) && !error) error = errno;
    return error;
}

/* Seal the syscall error and bounded sysfs bytes even on failure. A failed
 * load or read parks the guest after the result. A verified result still
 * requires a separate authenticated Download request from the same peer.
 */
static int ml030_module_result(int fd, const uint8_t witness[ML030_FRAME])
{
    uint8_t record[ML030_BODY + 12 + ML030_REPORT_MAX + 32] = {0};
    size_t size = 0;
    int load_error = ml030_load_once();
    int read_error = 0;
    if (!load_error)
        read_error = ml030_read_result(record + ML030_BODY + 12, &size);
    memcpy(record, witness, ML030_BODY);
    memcpy(record, "G030RES1", 8);
    g_put32(record + ML030_BODY, (uint32_t)load_error);
    g_put32(record + ML030_BODY + 4, (uint32_t)read_error);
    g_put32(record + ML030_BODY + 8, (uint32_t)size);
    g_tag(record + sizeof(record)-32, canary_key, canary_id, 20, record, sizeof(record)-32);
    int rc = transfer(fd, record, sizeof(record), 1);
    if (rc || load_error || read_error)
        return rc ? rc : (load_error ? load_error : read_error);
    /* Only run() success on this one-shot module yields an operation_rc of 0.
     * The host also verifies every field before signing a return command.
     */
#ifdef G0Q_PRE_EFFECT_RETURN
    long long values[G0Q_REPORT_FIELDS];
    if (g0q_report_parse(record + ML030_BODY + 12, (unsigned int)size, values) ||
        (values[21] & ~0x1ffffLL) != G0Q_REPORT_V4_TAG ||
        (values[0] == 0 && (values[21] & G0Q_PRE_EFFECT_CERT)) ||
        (values[0] != 0 && !g0q_pre_effect_fields(values))) return EPROTO;
#else
    if (size < 2 || memcmp(record + ML030_BODY + 12, "0 ", 2)) return EPROTO;
#endif
    g_hash(record, sizeof(record), ml030_result_digest);
    return 0;
}
