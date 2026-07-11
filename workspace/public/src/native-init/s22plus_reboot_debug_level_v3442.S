// SPDX-License-Identifier: MIT
/* S22+ V3442 Android-side raw debug-level reboot discriminator. */

    .section .rodata
    .balign 8
    .global s22plus_v3442_static_marker
s22plus_v3442_static_marker:
    .asciz "S22_V3442_RAW_DEBUG_LEVEL_SETTER valid-arg-first-syscall-reboot"

debug_high_arg:
    .asciz "debug0x4948"
debug_mid_arg:
    .asciz "debug0x494d"

    .section .text
    .balign 16
    .global _start
    .type _start, %function
_start:
    ldr     x4, [sp]
    cmp     x4, #2
    b.lt    invalid_arg
    ldr     x4, [sp, #16]
    ldrb    w5, [x4]
    cmp     w5, #'h'
    b.eq    select_high
    cmp     w5, #'H'
    b.eq    select_high
    cmp     w5, #'m'
    b.eq    select_mid
    cmp     w5, #'M'
    b.ne    invalid_arg

select_mid:
    adrp    x3, debug_mid_arg
    add     x3, x3, :lo12:debug_mid_arg
    b       do_reboot

select_high:
    adrp    x3, debug_high_arg
    add     x3, x3, :lo12:debug_high_arg

do_reboot:
    movz    x0, #0xdead
    movk    x0, #0xfee1, lsl #16
    movz    x1, #0x1969
    movk    x1, #0x2812, lsl #16
    movz    x2, #0xc3d4
    movk    x2, #0xa1b2, lsl #16
    mov     x8, #142
    svc     #0

    // A valid reboot request is not expected to return.
    mov     x0, #70
    mov     x8, #93
    svc     #0

invalid_arg:
    mov     x0, #64
    mov     x8, #93
    svc     #0
    .size _start, . - _start
