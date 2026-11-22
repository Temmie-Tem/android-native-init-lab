/* SPDX-License-Identifier: GPL-2.0-only */
/* Raw VM input. Android packaging and physical loader admission are separate. */
#include "layout.h"
.section .start,"ax"
.global y2q_start
y2q_start:
    b y2q_stage
    .long 0
    .quad 0x80000, FILE_END, 10
    .quad 0, 0, 0
    .ascii "ARM\x64"
    .long 0

.section .stage,"ax"
.global y2q_stage, y2q_first_stack, y2q_before_copy, y2q_before_branch
.global reject_cpu, reject_source, reject_fdt, reject_range, reject_initrd, reject_compose
y2q_stage:
    mov x28, x0
    adr x29, y2q_stage
    sub x29, x29, #512, lsl #12
    mrs x8, CurrentEL
    cmp x8, #4
    b.eq 1f
    cmp x8, #8
    b.ne reject_cpu
    mrs x8, SCTLR_EL2
    b 2f
1:  mrs x8, SCTLR_EL1
2:  tbnz x8,#0,reject_cpu
    tbnz x8,#2,reject_cpu
    tbnz x8,#25,reject_cpu
    mrs x8, daif
    and x8,x8,#0x1c0
    cmp x8,#0x1c0
    b.ne reject_cpu
    /* The IYC2 cleanup masks asynchronous aborts and IRQ/FIQ, but inherits
     * PSTATE.D. Complete the Linux entry mask before accessing the FDT. */
    msr daifset, #8
    isb
    ldr x8,=SRC_MIN
    subs x8,x29,x8
    b.lo reject_source
    tst x8,#0x7fff
    b.ne reject_source
    lsr x8,x8,#15
    cmp x8,#63
    b.hi reject_source
    bl y2q_shape
    cbz x0,reject_fdt
    mov x0,x28
    mov x1,x29
    ldr x2,=FILE_END
    add x2,x1,x2
    bl y2q_interval
    cbz x0,reject_range
    mov x0,x28
    ldr x1,=OUT_KERNEL
    ldr x2,=(OUT_KERNEL+KERNEL_RUNTIME)
    bl y2q_interval
    cbz x0,reject_range
    mov x0,x28
    ldr x1,=OUT_FDT
    ldr x2,=STACK_TOP
    bl y2q_interval
    cbz x0,reject_range
y2q_first_stack:
    ldr x8,=STACK_TOP
    mov sp,x8
    ldr x0,=IN_RD
    adrp x1,initrd_ref
    add x1,x1,:lo12:initrd_ref
    ldr x2,=RD_SIZE
    bl memcmp
    cbnz w0,reject_initrd
    mov x0,x28
    adrp x1,board_blob
    add x1,x1,:lo12:board_blob
    ldr x2,=OUT_FDT
    mov w3,#FDT_CAP
    ldr x4,=FW_LO
    ldr x5,=FW_LEN
    ldr x6,=RD_SIZE
    bl y2q_compose
    cbnz w0,reject_compose
y2q_before_copy:
    ldr x0,=OUT_KERNEL
    adrp x1,kernel_blob
    add x1,x1,:lo12:kernel_blob
    ldr x2,=IMG_SIZE
    bl memcpy
    mrs x5, ctr_el0
    ubfx x5, x5, #16, #4
    mov x6, #4
    lsl x6, x6, x5
    ldr x7, =OUT_KERNEL
    ldr x8, =(OUT_KERNEL+IMG_SIZE)
3:  dc cvac, x7
    add x7, x7, x6
    cmp x7, x8
    b.lo 3b
    dsb sy
    ic iallu
    dsb sy
    isb
    ldr x0,=OUT_FDT
    mov x1,xzr
    mov x2,xzr
    mov x3,xzr
    ldr x4,=OUT_KERNEL
y2q_before_branch:
    br x4
.macro park sym
\sym:
    wfe
    b \sym
.endm
park reject_cpu
park reject_source
park reject_fdt
park reject_range
park reject_initrd
park reject_compose
.ltorg
.section .board,"a"
.global board_blob,initrd_ref
board_blob:
    .incbin "bound-board.dtb"
initrd_ref:
    .incbin "bound-initrd.gz"
.section .kernel,"a"
.global kernel_blob
kernel_blob:
    .incbin "bound-Image"
.section .note.GNU-stack,"",%progbits
