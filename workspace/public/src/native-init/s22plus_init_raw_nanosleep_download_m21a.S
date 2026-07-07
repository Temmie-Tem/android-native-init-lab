// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ M21A raw timed-download floor discriminator.
 *
 * Raw AArch64 PID1: sleep for a distinctive dwell period using one direct
 * nanosleep(2) syscall, then request Samsung download mode with reboot(2).
 * No C runtime, filesystem setup, marker write, modules, configfs, USB role
 * force, or Android handoff.
 */

    .section .rodata
    .balign 8
    .global s22plus_m21a_static_marker
s22plus_m21a_static_marker:
    .asciz "S22_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD raw-pid1 no-libc nanosleep_sec=90 then-reboot-download then-park"

    .balign 8
download_arg:
    .asciz "download"

    .balign 8
nanosleep_req:
    .xword 90
    .xword 0

    .section .text
    .balign 16
    .global _start
    .type _start, %function
_start:
    // nanosleep({ .tv_sec = 90, .tv_nsec = 0 }, NULL)
    adrp    x0, nanosleep_req
    add     x0, x0, :lo12:nanosleep_req
    mov     x1, xzr
    mov     x8, #101
    svc     #0

    // reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
    //        LINUX_REBOOT_CMD_RESTART2, "download")
    movz    x0, #0xdead
    movk    x0, #0xfee1, lsl #16
    movz    x1, #0x1969
    movk    x1, #0x2812, lsl #16
    movz    x2, #0xc3d4
    movk    x2, #0xa1b2, lsl #16
    adrp    x3, download_arg
    add     x3, x3, :lo12:download_arg
    mov     x8, #142
    svc     #0

1:
    wfe
    b       1b
    .size _start, . - _start
