/* SPDX-License-Identifier: GPL-2.0-only
 * Generated only into a private kernel. Fixed early-C retained marker V2.
 * Called after early_ioremap_init and before setup_machine_fdt.
 */
#include <linux/compiler.h>
#include <linux/init.h>
#include <linux/types.h>
#include <asm/barrier.h>
#include <asm/early_ioremap.h>
#include <asm/pgtable.h>

static const u8 s22_retained_early_c_frame[128] __initconst __used = {
@FRAME@
};

void __init s22_retained_early_c(void);
noinline void __init s22_retained_early_c(void)
{
	u64 el, state;
	u32 before[4], idx, cursor, position;
	volatile u32 *header;
	volatile u8 *slot;
	unsigned long prot;
	unsigned int i;

	asm volatile("mrs %0, CurrentEL" : "=r" (el));
	if (el == 4)
		asm volatile("mrs %0, sctlr_el1" : "=r" (state));
	else if (el == 8)
		asm volatile("mrs %0, sctlr_el2" : "=r" (state));
	else
		return;
	/* Mapping is usable only with the current EL's MMU on, little endian. */
	if ((state & ((1ULL << 25) | 1)) != 1)
		return;
	prot = pgprot_val(pgprot_writecombine(PAGE_KERNEL));
	header = early_memremap_prot(0x800200000ULL, 16, prot);
	if (!header)
		return;
	for (i = 0; i < 4; ++i)
		before[i] = READ_ONCE(header[i]);
	idx = before[2];
	if (before[1] != 0x4d474f4c || idx < 256)
		goto out_header;
	cursor = idx % 0x1ffff0U;
	position = (cursor >= 256 ? cursor - 256 : 0x1ffff0U - 256) + 128;
	slot = early_memremap_prot(0x800200010ULL + position, 128, prot);
	if (!slot)
		goto out_header;
	asm volatile(".global s22_retained_early_c_invalidate\n"
		     "s22_retained_early_c_invalidate:" ::: "memory");
	for (i = 0; i < 8; ++i)
		WRITE_ONCE(slot[i], 0);
	dsb(sy);
	for (i = 8; i < 128; ++i)
		WRITE_ONCE(slot[i], READ_ONCE(s22_retained_early_c_frame[i]));
	dsb(sy);
	asm volatile(".global s22_retained_early_c_recheck\n"
		     "s22_retained_early_c_recheck:" ::: "memory");
	for (i = 0; i < 4; ++i)
		if (READ_ONCE(header[i]) != before[i])
			goto out_slot;
	for (i = 0; i < 8; ++i)
		WRITE_ONCE(slot[i], READ_ONCE(s22_retained_early_c_frame[i]));
	dsb(sy);
out_slot:
	early_memunmap((void *)slot, 128);
out_header:
	early_memunmap((void *)header, 16);
}
