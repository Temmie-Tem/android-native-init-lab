/* No-libc early PID 1 entry. This file is shared with the real ARM64 H0 gate
 * harness. The native observer does not insert any of the measured modules. */
#include "preflight_record.h"
struct bp_kernel_stat {
    unsigned long dev, ino;
    unsigned mode, nlink, uid, gid;
    unsigned long rdev, pad1;
    long size;
    int blksize, pad2;
    long blocks, atime;
    unsigned long atime_ns;
    long mtime;
    unsigned long mtime_ns;
    long ctime;
    unsigned long ctime_ns;
    unsigned unused[2];
};
_Static_assert(sizeof(struct bp_kernel_stat) == 128, "ARM64 kernel stat");
static struct bp_record bp_native_record;
static long bp_sys(long n, long a, long b, long c, long d) {
    register long x8 __asm__("x8") = n;
    register long x0 __asm__("x0") = a;
    register long x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c;
    register long x3 __asm__("x3") = d;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2), "r"(x3) : "memory", "cc");
    return x0;
}
static __attribute__((noreturn)) void bp_native_park(void) {
    /* rt_sigsuspend with the empty mask; PID 1 remains the sole owner. */
    unsigned long mask = 0;
    for (;;) (void)bp_sys(133, (long)&mask, 8, 0, 0);
}
static int bp_stat_ok(const struct bp_kernel_stat *s, unsigned links, long size) {
    return s->mode == 0100400 && !s->uid && !s->gid && s->nlink == links && s->size == size;
}
static void bp_native_enter(const unsigned char run[16], int virt) {
    if (bp_sys(172,0,0,0,0) != 1) bp_native_park();
    long intent = bp_sys(56, -100, (long)"/s22-prehandoff.intent", 524288|32768, 0);
    long descriptor = bp_sys(25, BP_FD, 1, 0, 0); /* F_GETFD */
    if (intent == -2 && descriptor == -9) {
        intent = bp_sys(56, -100, (long)"/s22-prehandoff.intent", 1|64|128|524288|32768, 0400);
        if (intent < 0 || bp_sys(57,intent,0,0,0)) bp_native_park();
        const char *args[] = {"/s22-prehandoff", 0};
        const char *env[] = {"PATH=/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL=C", 0};
        (void)bp_sys(221,(long)args[0],(long)args,(long)env,0);
        bp_native_park();
    }
    struct bp_kernel_stat st;
    if (intent < 0 || descriptor < 0 || bp_sys(80,intent,(long)&st,0,0) ||
        !bp_stat_ok(&st,1,0) || bp_sys(57,intent,0,0,0) ||
        bp_sys(25,BP_FD,1034,0,0) != BP_SEALS ||
        bp_sys(67,BP_FD,(long)&bp_native_record,sizeof(bp_native_record),0) != sizeof(bp_native_record) ||
        !bp_valid(&bp_native_record,run,virt) || bp_sys(80,BP_FD,(long)&st,0,0) ||
        !bp_stat_ok(&st,0,sizeof(bp_native_record)+bp_native_record.log_size) ||
        bp_sys(25,BP_FD,2,1,0)) bp_native_park(); /* F_SETFD CLOEXEC */
}
static long bp_native_boot(void) {
    char boot[38];
    long fd = bp_sys(56,-100,(long)"/proc/sys/kernel/random/boot_id",524288|32768,0);
    if (fd < 0) return fd;
    long n = bp_sys(63,fd,(long)boot,sizeof(boot),0), closed = bp_sys(57,fd,0,0,0);
    if (n != 37 || closed) return -71;
    for (unsigned i = 0; i < 37; ++i) if (boot[i] != bp_native_record.boot_id[i]) return -71;
    return 0;
}
