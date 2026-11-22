#include "layout.h"
ENTRY(y2q_start)
SECTIONS {
    . = 0;
    .start : { KEEP(*(.start)) }
    ASSERT(SIZEOF(.start) == 64, "unexpected arm64 Image header")
    . = 0x200000;
    .stage : { KEEP(*(.stage)) *(.text .text.*) *(.rodata .rodata.*) }
    ASSERT(. <= DATA_OFF, "stage exceeds file budget")
    . = DATA_OFF;
    .board : { KEEP(*(.board)) }
    ASSERT(. <= KERNEL_OFF, "board data exceed file budget")
    . = KERNEL_OFF;
    .kernel : { KEEP(*(.kernel)) }
    ASSERT(. == FILE_END, "wrong stored Image extent")
    .writable : { *(.data .data.* .bss .bss.* .got .got.* COMMON) }
    ASSERT(SIZEOF(.writable) == 0, "writable or absolute table in loader")
    /DISCARD/ : { *(.note.* .comment .eh_frame*) }
}
