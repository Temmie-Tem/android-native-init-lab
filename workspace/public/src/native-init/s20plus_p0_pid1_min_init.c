// SPDX-License-Identifier: MIT
/*
 * S20+ G986N P0 direct-PID1 minimal download-request probe (V4).
 *
 * This is not an ACM candidate and deliberately proves less than one. It
 * answers a single question the three consumed ACM candidates could not:
 * did /init execute at all?
 *
 * Each of those candidates brought up configfs, a USB gadget, a UDC binding
 * and ttyGS0 before it could say anything, then dwelt for a 180-second host
 * observation window. Every link in that chain can fail silently, and the
 * observed outcome - a completed window with no banner - is what the whole
 * chain failing looks like, as is /init never running at all.
 *
 * Here PID1 requests Samsung download mode immediately. The host observes
 * Download-mode enumeration, which is the bootloader's own USB stack and is
 * already proved to work on this exact target. Seeing Download proves PID1
 * executed, with no gadget, no configfs, no UDC, no ttyGS0, no host serial
 * I/O, no dwell and no dependence on any buffer surviving a reboot.
 *
 * A best-effort /dev/kmsg banner runs first so the printk path, and therefore
 * the Samsung sec_log buffer read back through /proc/last_kmsg, may also carry
 * a record. Every step of it ignores its own result: the banner must never be
 * able to prevent the download request, which is the primary evidence.
 */

#include <stddef.h>
#include <stdint.h>

#define AT_FDCWD (-100L)

#define O_WRONLY 00000001
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define NR_MKNODAT 33L
#define NR_MKDIRAT 34L
#define NR_OPENAT 56L
#define NR_CLOSE 57L
#define NR_WRITE 64L
#define NR_EXIT_GROUP 94L
#define NR_NANOSLEEP 101L
#define NR_REBOOT 142L
#define NR_GETPID 172L

#define P0_REBOOT_MAGIC1 0xfee1deadL
#define P0_REBOOT_MAGIC2 0x28121969L
#define P0_REBOOT_CMD_RESTART2 0xa1b2c3d4L
#define P0_REBOOT_ARGUMENT "download"

/* /dev/kmsg is a fixed character device. Unlike ttyGS0 it needs no sysfs
 * lookup, so the banner has no dependency on any driver having bound. */
#define P0_KMSG_PATH "/dev/kmsg"
#define P0_KMSG_MAJOR 1U
#define P0_KMSG_MINOR 11U

#define P0_BANNER "S20PLUS_P0_PID1_MIN_V4;pid=00000001;stage=DOWNLOAD_REQUEST\n"
#define P0_BANNER_SIZE (sizeof(P0_BANNER) - 1U)

struct p0_timespec {
    int64_t tv_sec;
    int64_t tv_nsec;
};

__attribute__((always_inline)) static inline long p0_syscall4(
    long number,
    long a0,
    long a1,
    long a2,
    long a3
) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x8 asm("x8") = number;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x3), "r"(x8)
        : "memory"
    );
    return x0;
}

__attribute__((always_inline)) static inline long p0_syscall3(long number, long a0, long a1, long a2) {
    return p0_syscall4(number, a0, a1, a2, 0);
}

__attribute__((always_inline)) static inline long p0_syscall2(long number, long a0, long a1) {
    return p0_syscall4(number, a0, a1, 0, 0);
}

__attribute__((always_inline)) static inline long p0_syscall1(long number, long a0) {
    return p0_syscall4(number, a0, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p0_syscall0(long number) {
    return p0_syscall4(number, 0, 0, 0, 0);
}

static long p0_getpid(void) {
    return p0_syscall0(NR_GETPID);
}

/* Same encoding the consumed ACM candidate used for /dev/ttyGS0. */
static uint64_t p0_make_dev(unsigned int major_number, unsigned int minor_number) {
    return ((uint64_t)(minor_number & 0xffU)) |
           ((uint64_t)(major_number & 0xfffU) << 8) |
           ((uint64_t)(minor_number & ~0xffU) << 12) |
           ((uint64_t)(major_number & ~0xfffU) << 32);
}

static void p0_sleep_ms(int64_t milliseconds) {
    struct p0_timespec request;
    request.tv_sec = milliseconds / 1000;
    request.tv_nsec = (milliseconds % 1000) * 1000000;
    (void)p0_syscall2(NR_NANOSLEEP, (long)(uintptr_t)&request, 0);
}

__attribute__((noreturn)) static void p0_park(void) {
    for (;;) {
        p0_sleep_ms(60000);
    }
}

/*
 * Best effort in the strict sense: nothing here is checked and nothing here
 * can change what happens next. An existing /dev or /dev/kmsg, a refused
 * mknod, a failed open and a short write are all equally acceptable, because
 * the download request is the evidence and it must not be reachable only on
 * the success path of this function.
 */
static void p0_banner_best_effort(void) {
    long descriptor;
    (void)p0_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t) "/dev", 0755);
    (void)p0_syscall4(
        NR_MKNODAT,
        AT_FDCWD,
        (long)(uintptr_t)P0_KMSG_PATH,
        (long)(S_IFCHR | 0600),
        (long)p0_make_dev(P0_KMSG_MAJOR, P0_KMSG_MINOR)
    );
    descriptor = p0_syscall4(NR_OPENAT, AT_FDCWD, (long)(uintptr_t)P0_KMSG_PATH, O_WRONLY | O_CLOEXEC, 0);
    if (descriptor < 0) {
        return;
    }
    /* One write. /dev/kmsg is record oriented, so a partial write is not
     * retried: a torn record would be worse evidence than none. */
    (void)p0_syscall3(NR_WRITE, descriptor, (long)(uintptr_t)P0_BANNER, (long)P0_BANNER_SIZE);
    (void)p0_syscall1(NR_CLOSE, descriptor);
}

static long p0_request_download(void) {
    return p0_syscall4(
        NR_REBOOT,
        P0_REBOOT_MAGIC1,
        P0_REBOOT_MAGIC2,
        P0_REBOOT_CMD_RESTART2,
        (long)(uintptr_t)P0_REBOOT_ARGUMENT
    );
}

#ifdef S20PLUS_P0_MIN_SELFTEST_ONLY

__attribute__((noreturn)) void _start(void) {
    int ok = 1;
    /* The device encoding must round-trip the two numbers this probe uses and
     * the ones the ACM candidate used, so a regression in it is visible here
     * rather than as a wrong node on the device. */
    ok = ok && p0_make_dev(1U, 11U) == 0x10bULL;
    ok = ok && p0_make_dev(240U, 7U) == 0xf007ULL;
    ok = ok && p0_make_dev(0U, 0U) == 0ULL;
    ok = ok && P0_BANNER_SIZE == sizeof(P0_BANNER) - 1U;
    ok = ok && P0_BANNER[P0_BANNER_SIZE - 1U] == '\n';
    (void)p0_syscall1(NR_EXIT_GROUP, ok ? 0 : 1);
    for (;;) {
    }
}

#else

__attribute__((noreturn)) void _start(void) {
    if (p0_getpid() != 1) {
        /* Never act anywhere but as PID1. */
        p0_park();
    }
    p0_banner_best_effort();
    (void)p0_request_download();
    /* Only reached if the kernel refused the request. Park so the operator's
     * physical Download entry and the authorized rollback remain available. */
    p0_park();
}

#endif
