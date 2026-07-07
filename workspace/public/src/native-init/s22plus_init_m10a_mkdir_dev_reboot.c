// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M10A mkdir-dev reboot discriminator.
 *
 * M10A starts from the M9A freestanding C first-reboot proof and adds exactly
 * one M8A-style runtime side effect before reboot: mkdirat("/dev", 0755).
 * It intentionally does not mount, create device nodes, open/write kmsg, sleep,
 * insert modules, configure USB, or hand off to Android/Magisk.
 */

#include <stdint.h>

#define AT_FDCWD (-100)

#define NR_MKDIRAT 34
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

static inline long syscall3(long nr, long a0, long a1, long a2) {
    return syscall4(nr, a0, a1, a2, 0);
}

__attribute__((noinline)) static long sys_mkdir_dev(const char *path) {
    volatile uintptr_t stack_probe[2];
    stack_probe[0] = 0x6130316d3232706cULL;
    stack_probe[1] = (uintptr_t)path;
    asm volatile("" : : "r"(stack_probe[0]), "r"(stack_probe[1]) : "memory");
    return syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, 0755);
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
    (void)sys_mkdir_dev("/dev");
    (void)sys_reboot_download("download");
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}
