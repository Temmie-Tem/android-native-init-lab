/* SPDX-License-Identifier: GPL-2.0-only */
#include "uniloader_layout.h"

.section .head.text, "ax"
.balign 8
.global y2q_image
y2q_image:
	b y2q_entry
	.long 0
	.quad Y2Q_TEXT_OFFSET
	.quad Y2Q_WRAPPER_RUNTIME
	.quad 10	/* Little endian, 4 KiB pages, relocatable physical base. */
	.quad 0, 0, 0
	.ascii "ARM\x64"
	.long 0

y2q_entry:
	mov x28, x0
	mrs x9, CurrentEL
	cmp x9, #4
	b.eq 1f
	cmp x9, #8
	b.ne y2q_rejected
	mrs x9, SCTLR_EL2
	b 2f
1:	mrs x9, SCTLR_EL1
2:	tbnz x9, #0, y2q_rejected	/* MMU */
	tbnz x9, #2, y2q_rejected	/* Data cache */
	tbnz x9, #25, y2q_rejected	/* Big endian at this EL */
	mrs x9, DAIF
	and x9, x9, #0x3c0
	cmp x9, #0x3c0
	b.ne y2q_rejected

	adr x1, y2q_image
	sub x9, x1, #Y2Q_TEXT_OFFSET
	tst x9, #(Y2Q_PAYLOAD_OFFSET - 1)
	b.ne y2q_rejected
	bl y2q_guard
	cbz w0, y2q_rejected

	adr x9, y2q_image
	add x10, x9, #Y2Q_STACK_TOP
	mov sp, x10
	mov x0, x28
	add x1, x9, #Y2Q_FDT_OFFSET
	bl y2q_mark_fdt
	cbz x0, y2q_rejected
	adr x4, y2q_image
	add x4, x4, #Y2Q_PAYLOAD_OFFSET
	mov x1, xzr
	mov x2, xzr
	mov x3, xzr
	dsb sy
	isb
	br x4

.global y2q_rejected
y2q_rejected:
	wfe
	b y2q_rejected

.section .note.GNU-stack, "", %progbits
