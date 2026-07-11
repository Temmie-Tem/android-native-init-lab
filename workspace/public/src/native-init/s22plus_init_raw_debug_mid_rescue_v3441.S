// SPDX-License-Identifier: MIT
/*
 * S22+ V3441 raw PID1 debug-level MID rescue.
 *
 * First and only intended syscall:
 *   reboot(LINUX_REBOOT_CMD_RESTART2, "debug0x494d")
 *
 * This image is a recovery tool for a future HIGH debug-level experiment.  It
 * performs no filesystem, module, USB, marker, or block-device operation.  If
 * the reboot syscall returns it parks forever.  Repeated boots may therefore
 * repeat the idempotent MID request until the operator enters Download mode
 * and restores the pinned Magisk boot-only AP.
 */

    .section .rodata
    .balign 8
    .global s22plus_v3441_static_marker
s22plus_v3441_static_marker:
    .asciz "S22_V3441_RAW_DEBUG_MID_RESCUE boot-only first-syscall debug0x494d then-park"

    .balign 8
debug_mid_arg:
    .asciz "debug0x494d"

    .section .text
    .balign 16
    .global _start
    .type _start, %function
_start:
    // reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
    //        LINUX_REBOOT_CMD_RESTART2, "debug0x494d")
    movz    x0, #0xdead
    movk    x0, #0xfee1, lsl #16
    movz    x1, #0x1969
    movk    x1, #0x2812, lsl #16
    movz    x2, #0xc3d4
    movk    x2, #0xa1b2, lsl #16
    adrp    x3, debug_mid_arg
    add     x3, x3, :lo12:debug_mid_arg
    mov     x8, #142
    svc     #0

1:
    wfe
    b       1b
    .size _start, . - _start
