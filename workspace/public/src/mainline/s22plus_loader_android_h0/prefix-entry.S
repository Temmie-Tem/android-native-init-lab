/* SPDX-License-Identifier: GPL-2.0-only */
/* Only the fixed stackless prefix may return through this ABI. */
#include "g0q-android-marker.h"
.text
.balign 16
.global g0q_prefix_enter
.type g0q_prefix_enter, %function
g0q_prefix_enter:
	stp x19, x30, [sp, #-16]!
	mov x19, x0
	mov x0, x1
	mov x1, xzr
	mov x2, xzr
	mov x3, xzr
	ldr x4, =CONFIG_PAYLOAD_ENTRY
	dsb sy
	ic iallu
	dsb sy
	isb
	blr x4
.global g0q_prefix_return
g0q_prefix_return:
	stp x0, x1, [x19]
	stp x2, x3, [x19, #16]
	ldp x19, x30, [sp], #16
	ret
.size g0q_prefix_enter, .-g0q_prefix_enter

#include "g0q-prefix-loader-writer.S"

.section .rodata, "a"
.balign 4096
.global g0q_prefix_image
g0q_prefix_image:
	.incbin "blob/prefix-Image"
.global g0q_prefix_image_end
g0q_prefix_image_end:
