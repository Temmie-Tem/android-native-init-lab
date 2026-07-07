// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M9A C first-action reboot discriminator.
 *
 * M9A keeps the freestanding C build shape used by M5B/M8A but removes every
 * VFS, kmsg, mount, sleep, module, configfs, USB, marker-write, and handoff
 * variable.  The first externally observable action is exactly one arm64
 * reboot(2) syscall requesting Samsung download mode.  If that syscall returns,
 * PID1 parks forever.
 */

#include <stdint.h>

#define NR_REBOOT 142

#define LINUX_REBOOT_MAGIC1 0xfee1deadUL
#define LINUX_REBOOT_MAGIC2 0x28121969UL
#define LINUX_REBOOT_CMD_RESTART2 0xa1b2c3d4UL

static inline long syscall4(long nr, long a0, long a1, long a2, long a3) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x8 asm("x8") = nr;
    asm volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x8) : "memory");
    return x0;
}

__attribute__((noinline)) static long sys_reboot_download(const char *arg) {
    volatile uintptr_t stack_probe[2];
    stack_probe[0] = 0x6d3961353232706cULL;
    stack_probe[1] = (uintptr_t)arg;
    asm volatile("" : : "r"(stack_probe[0]), "r"(stack_probe[1]) : "memory");
    return syscall4(
        NR_REBOOT,
        (long)LINUX_REBOOT_MAGIC1,
        (long)LINUX_REBOOT_MAGIC2,
        (long)LINUX_REBOOT_CMD_RESTART2,
        (long)(uintptr_t)arg);
}

void _start(void) {
    (void)sys_reboot_download("download");
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}
