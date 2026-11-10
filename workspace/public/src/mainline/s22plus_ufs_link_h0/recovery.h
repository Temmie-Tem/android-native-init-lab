/* V6 only: one independent ordinary Download attempt. This is not a hardware
 * watchdog. A blocked reboot notifier, probe, driver or kernel can defeat it.
 * No device write occurs while arming. The child alone spends the reset slot.
 */
#ifndef G0Q_UFS_RECOVERY_H
#define G0Q_UFS_RECOVERY_H
#include <linux/reboot.h>
#include <sys/syscall.h>

#define G0Q_RECOVERY_TRIGGER_MS 555000U
#define G0Q_RECOVERY_LAST_MS 570000U
#define G0Q_RECOVERY_IPC_MS 1000U
#define G0Q_RECOVERY_FRAME 168U
static int recovery_fd = -1;
static int recovery_started;

static int recovery_property(const char *path, const void *expected, size_t length)
{
    unsigned char data[64]; size_t size = 0;
    return length <= sizeof(data) && !read_small(path, data, sizeof(data), &size) &&
           size == length && !memcmp(data, expected, length);
}

static int recovery_platform_ready(void)
{
    if (!download_ready()) return 0;
#ifndef CANARY_H0_VM
    /* The exact retained DT binds one reboot-mode cell, its offset/bit field,
     * and Download magic. These are OF properties, never NVMEM data reads.
     * The full live DT is separately authenticated before any UFS permit. */
    static const unsigned char cell[] = {0,0,1,12};
    static const unsigned char mode[] = {0,0,0,21};
    static const unsigned char reg[] = {0,0,0,72,0,0,0,1};
    static const unsigned char bits[] = {0,0,0,1,0,0,0,7};
    const char *root = "/sys/firmware/devicetree/base/";
    const struct { const char *path; const void *bytes; size_t size; } rows[] = {
        {"reboot-mode/compatible", "nvmem-reboot-mode", sizeof("nvmem-reboot-mode")},
        {"reboot-mode/nvmem-cell-names", "reboot-mode", sizeof("reboot-mode")},
        {"reboot-mode/nvmem-cells", cell, sizeof(cell)},
        {"reboot-mode/mode-download", mode, sizeof(mode)},
        {"soc@0/spmi@c400000/pmic@0/nvram@7100/reboot-reason@48/phandle", cell, sizeof(cell)},
        {"soc@0/spmi@c400000/pmic@0/nvram@7100/reboot-reason@48/reg", reg, sizeof(reg)},
        {"soc@0/spmi@c400000/pmic@0/nvram@7100/reboot-reason@48/bits", bits, sizeof(bits)},
    };
    for (size_t i = 0; i < sizeof(rows)/sizeof(rows[0]); i++) {
        char path[192];
        int n = snprintf(path, sizeof(path), "%s%s", root, rows[i].path);
        if (n < 0 || (size_t)n >= sizeof(path) ||
            !recovery_property(path, rows[i].bytes, rows[i].size)) return 0;
    }
#endif
    return 1;
}

/* Fixed local datagrams: P/L + fresh base/late challenge, or C + result digest.
 * They never leave the inherited socketpair. No timer renewal command exists.
 * One iteration handles at most one datagram, so a flood cannot defer expiry. */
static _Noreturn void recovery_child(int fd)
{
    int committed = 0, late_seen = 0;
    for (;;) {
        uint64_t now = now_ms();
        if (now >= G0Q_RECOVERY_LAST_MS) _exit(121);
        if (now >= G0Q_RECOVERY_TRIGGER_MS || committed) break;
        struct pollfd p = {fd, POLLIN, 0};
        int timeout = (int)(G0Q_RECOVERY_TRIGGER_MS - now);
        int n = poll(&p, 1, timeout);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 || (n > 0 && !(p.revents & POLLIN) &&
                       (p.revents & (POLLHUP|POLLERR|POLLNVAL)))) {
            if (fd >= 0) close(fd);
            fd = -1;
            continue;
        }
        if (!n || !(p.revents & POLLIN)) continue;
        uint8_t message[34];
        ssize_t got = recv(fd, message, sizeof(message), MSG_DONTWAIT);
        if (got < 0 && (errno == EAGAIN || errno == EINTR)) continue;
        if (got != 33 || (message[0] != 'P' && message[0] != 'L' && message[0] != 'C')) {
            close(fd); fd = -1; continue;
        }
        now = now_ms();
        if (now >= G0Q_RECOVERY_TRIGGER_MS) continue;
        if (message[0] == 'C') {
            if (late_seen && now < 540000U) committed = 1;
            else { close(fd); fd = -1; }
        }
        else {
            if (message[0] == 'L') late_seen = 1;
            message[0] = 'A';
            /* Failed/full IPC never blocks the deadline or causes a retry. */
            (void)send(fd, message, 33, MSG_DONTWAIT|MSG_NOSIGNAL);
        }
    }
    /* ARMED -> COMMITTED -> SYSCALL_SPENT, owned only by this process.
     * No syscall retry, alternative reset or driver/readback step follows. */
    if (fd >= 0) close(fd);
    if (now_ms() >= G0Q_RECOVERY_LAST_MS) _exit(122);
    syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2, "download");
    _exit(123);
}

static int recovery_probe(const uint8_t nonce[32], int late)
{
    if (recovery_fd < 0) return ENODEV;
    uint64_t now = now_ms(), until = now + G0Q_RECOVERY_IPC_MS;
    if (until > deadline) until = deadline;
    if (until > G0Q_RECOVERY_TRIGGER_MS) until = G0Q_RECOVERY_TRIGGER_MS;
    if (now >= until) return ETIMEDOUT;
    uint8_t message[34] = {0}; message[0] = late ? 'L' : 'P'; memcpy(message+1, nonce, 32);
    if (send(recovery_fd, message, 33, MSG_DONTWAIT|MSG_NOSIGNAL) != 33)
        return errno ? errno : EIO;
    for (;;) {
        now = now_ms(); if (now >= until) return ETIMEDOUT;
        struct pollfd p = {recovery_fd, POLLIN, 0};
        int rc = poll(&p, 1, (int)(until-now));
        if (rc < 0 && errno == EINTR) continue;
        if (rc < 0) return errno;
        if (!rc) return ETIMEDOUT;
        ssize_t got = recv(recovery_fd, message, sizeof(message), MSG_DONTWAIT);
        if (got < 0 && (errno == EAGAIN || errno == EINTR)) continue;
        if (now_ms() >= until) return ETIMEDOUT;
        return got == 33 && message[0] == 'A' && g_equal(message+1,nonce,32) ? 0 : EPROTO;
    }
}

static int recovery_begin(void)
{
    if (recovery_started) return EALREADY;
    recovery_started = 1;
    if (now_ms() >= 120000 || !recovery_platform_ready()) return ENODEV;
    int pair[2];
    if (socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC|SOCK_NONBLOCK, 0, pair)) return errno;
    if (now_ms() >= 120000) { close(pair[0]); close(pair[1]); return ETIMEDOUT; }
    pid_t child = fork();
    if (child < 0) { int e=errno; close(pair[0]); close(pair[1]); return e; }
    if (!child) {
        close(pair[0]);
        /* Fork precedes USB/server creation: only stdio and this IPC exist.
         * No parent-death signal, respawn, shell, console or network output. */
        close(0); close(1); close(2);
        recovery_child(pair[1]);
    }
    close(pair[1]); recovery_fd = pair[0];
    const uint8_t initial[32] = {0};
    return recovery_probe(initial, 0);
}

static int recovery_commit(const uint8_t digest[32])
{
    if (recovery_fd < 0 || now_ms() >= deadline || now_ms() >= G0Q_RECOVERY_TRIGGER_MS)
        return ETIMEDOUT;
    uint8_t message[33] = {'C'}; memcpy(message+1, digest, 32);
    int fd = recovery_fd; recovery_fd = -1;
    /* The parent cannot retry this commit even if send returns ambiguously.
     * The already-armed child still has its sole finite fallback slot. */
    ssize_t n = send(fd, message, sizeof(message), MSG_DONTWAIT|MSG_NOSIGNAL);
    int error = n == sizeof(message) ? 0 : (errno ? errno : EIO);
    close(fd);
    return error;
}

static int recovery_frame(int fd, const uint8_t base[G0Q_RESPONSE_SIZE],
                          const uint8_t nonce[32], int late)
{
    int e = recovery_probe(nonce, late); if (e) return e;
    uint8_t frame[G0Q_RECOVERY_FRAME] = {0};
    memcpy(frame, late ? "G040LIV1" : "G040ARM1", 8);
    memcpy(frame+8, canary_id, 32); memcpy(frame+40, base+40, 32);
    memcpy(frame+72, nonce, 32); memcpy(frame+104, base+72, 16);
    g_put64(frame+120, G0Q_RECOVERY_TRIGGER_MS); g_put64(frame+128, G0Q_RECOVERY_LAST_MS);
    g_tag(frame+136, canary_key, canary_id, late ? 22 : 21, frame, 136);
    return transfer(fd, frame, sizeof(frame), 1);
}
#endif
