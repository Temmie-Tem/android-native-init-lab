// SPDX-License-Identifier: MIT
/*
 * S22+ M4T2 raw park PID1 probe.
 *
 * This is deliberately smaller than the M4T1 C/glibc reboot-first init:
 * no libc startup, no stack use, no syscalls, no reboot request, no module work,
 * and no Android/Magisk handoff.  If the kernel successfully execs this as
 * PID1, it should not return or exit.  The live discriminator is behavioral:
 * a stable hang/park differs from the fast reboot loop seen with M4T1.
 */

    .section .rodata
    .balign 8
    .global s22plus_m4t2_static_marker
s22plus_m4t2_static_marker:
    .asciz "S22_NATIVE_INIT_PARK_M4T2 raw-pid1 no-libc no-syscall no-reboot infinite-park"

    .section .text
    .balign 16
    .global _start
    .type _start, %function
_start:
1:
    wfe
    b 1b
    .size _start, . - _start
