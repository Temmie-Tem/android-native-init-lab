/* SPDX-License-Identifier: GPL-2.0-only
 * Fixed g0q early marker template. Generated only into a private artifact.
 * No stack, calls, header writes, MMU changes or peripheral access.
 * x0-x8, x18-x30 and SP are preserved. x9-x17 and NZCV are scratch.
 */
.balign 16
.global @NAME@
.type @NAME@, %function
@NAME@:
	mrs x9, CurrentEL
@NAME@_check_el:
	cmp x9, #4
	b.eq @NAME@_el1
	cmp x9, #8
	b.ne @NAME@_skip
@NAME@_read_el2:
	mrs x10, sctlr_el2
	b @NAME@_check_state
@NAME@_el1:
	mrs x10, sctlr_el1
@NAME@_check_state:
	mov x9, #5
	movk x9, #0x200, lsl #16
	tst x10, x9
	b.ne @NAME@_skip
	movz x9, #0
	movk x9, #0x20, lsl #16
	movk x9, #8, lsl #32  /* exact LOGM slice: 0x800200000 */
	ldr w10, [x9, #4]
	movz w14, #0x4f4c
	movk w14, #0x4d47, lsl #16
	cmp w10, w14
	b.ne @NAME@_skip
	ldr w11, [x9, #8]
	cmp w11, #256
	b.lo @NAME@_skip
	ldr w12, [x9]
	ldr w13, [x9, #12]
	movz x14, #0xfff0
	movk x14, #0x1f, lsl #16 /* 2 MiB minus header */
	udiv x15, x11, x14
	msub x15, x15, x14, x11
	sub x16, x15, #256
	sub x14, x14, #256
	cmp x15, #256
	csel x15, x16, x14, hs
	add x15, x15, #@SLOT@
	add x15, x15, #16
	add x15, x9, x15
	/* Invalidate the entire commit prefix before changing the body. */
	mov x16, #0
@NAME@_invalidate:
	strb wzr, [x15, x16]
	add x16, x16, #1
	cmp x16, #8
	b.lo @NAME@_invalidate
	dsb sy
	adr x14, @NAME@_frame
@NAME@_body:
	ldrb w17, [x14, x16]
	strb w17, [x15, x16]
	add x16, x16, #1
	cmp x16, #128
	b.lo @NAME@_body
	dsb sy
@NAME@_recheck:
	ldr w16, [x9, #4]
	cmp w16, w10
	b.ne @NAME@_skip
	ldr w16, [x9, #8]
	cmp w16, w11
	b.ne @NAME@_skip
	ldr w16, [x9]
	cmp w16, w12
	b.ne @NAME@_skip
	ldr w16, [x9, #12]
	cmp w16, w13
	b.ne @NAME@_skip
	mov x16, #0
@NAME@_commit:
	ldrb w17, [x14, x16]
	strb w17, [x15, x16]
	add x16, x16, #1
	cmp x16, #8
	b.lo @NAME@_commit
	dsb sy
@NAME@_skip:
	ret
.size @NAME@, .-@NAME@
.balign 16
.global @NAME@_frame
@NAME@_frame:
@FRAME@
.global @NAME@_end
@NAME@_end:
