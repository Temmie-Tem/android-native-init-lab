/* SPDX-License-Identifier: GPL-2.0-only */
ENTRY(y2q_image)

SECTIONS
{
	. = 0;
	.prefix : {
		KEEP(*(.head.text))
		*(.text .text.*)
		*(.rodata .rodata.*)
	}
	ASSERT(SIZEOF(.prefix) <= 0x20000, "loader code overlaps private stack")
	.writable : { *(.data .data.* .bss .bss.* COMMON .got .got.*) }
	ASSERT(SIZEOF(.writable) == 0, "unexpected writable loader state")
	/DISCARD/ : { *(.note.* .comment .eh_frame*) }
}
