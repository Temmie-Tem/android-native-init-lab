// SPDX-License-Identifier: MIT
/*
 * S22+ M4T3 raw reboot-download PID1 probe.
 *
 * M4T2 proved that a raw no-syscall /init can execute and park as PID1.
 * M4T3 adds exactly one primitive on top of that floor: a direct arm64
 * reboot(2) syscall requesting "download", with no libc, no stack use, no
 * marker writes, no module/configfs work, and no Android/Magisk handoff.
 *
 * Live discriminator for a future attended run:
 *   - self-enters download mode: raw reboot syscall path works;
 *   - parks without looping: raw PID1 survived, syscall returned/failed;
 *   - fast loop: reboot syscall path or immediate PID1 action is unstable.
 */

    .section .rodata
    .balign 8
    .global s22plus_m4t3_static_marker
s22plus_m4t3_static_marker:
    .asciz "S22_NATIVE_INIT_RAW_REBOOT_M4T3 raw-pid1 no-libc one-raw-syscall reboot-download then-park"

    .balign 8
download_arg:
    .asciz "download"

    .section .text
    .balign 16
    .global _start
    .type _start, %function
_start:
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
