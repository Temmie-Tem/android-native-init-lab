/* SPDX-License-Identifier: GPL-2.0-only
 * Generated into one private kernel. Finite regular-initcall trace.
 * No header mutation, dynamic cryptography, logger, or device control.
 */
#include <linux/build_bug.h>
#include <linux/compiler.h>
#include <linux/init.h>
#include <linux/types.h>
#include <asm/barrier.h>
#include <asm/early_ioremap.h>
#include <asm/pgtable.h>

#define S22_TRACE_INITCALLS @COUNT@U
#define S22_TRACE_SLOTS (6U + 2U * S22_TRACE_INITCALLS)
#define S22_TRACE_SPAN (128U * S22_TRACE_SLOTS)

static const u8 s22_trace_frames[S22_TRACE_SLOTS][128] __initconst __used = {
@FRAMES@
};
static u32 s22_trace_header[4] __initdata;
static u32 s22_trace_window __initdata;
static u32 s22_trace_span __initdata;
static bool s22_trace_latched __initdata;
static bool s22_trace_disabled __initdata;

void __init s22_retained_trace(u32 event);
noinline void __init s22_retained_trace(u32 event)
{
	u64 el, state;
	u32 before[4], span, cursor;
	volatile u32 *header;
	volatile u8 *slot;
	unsigned long prot;
	unsigned int i;

	BUILD_BUG_ON(S22_TRACE_SLOTS > 4096U);
	BUILD_BUG_ON(sizeof(initcall_entry_t) != 4);
	if (s22_trace_disabled || event >= S22_TRACE_SLOTS)
		return;
	if ((unsigned long)__initcall_end - (unsigned long)__initcall0_start !=
	    4UL * S22_TRACE_INITCALLS) {
		s22_trace_disabled = true;
		return;
	}
	asm volatile("mrs %0, CurrentEL" : "=r" (el));
	if (el == 4)
		asm volatile("mrs %0, sctlr_el1" : "=r" (state));
	else if (el == 8)
		asm volatile("mrs %0, sctlr_el2" : "=r" (state));
	else
		return;
	if ((state & ((1ULL << 25) | 1)) != 1)
		return;
	prot = pgprot_val(pgprot_writecombine(PAGE_KERNEL));
	header = early_memremap_prot(0x800200000ULL, 16, prot);
	if (!header)
		return;
	for (i = 0; i < 4; ++i)
		before[i] = READ_ONCE(header[i]);
	if (!s22_trace_latched) {
		if (before[1] != 0x4d474f4c || before[2] < 128U)
			goto out_header;
		/* Keep available complete slots even when history is short. */
		span = before[2] < S22_TRACE_SPAN ? before[2] : S22_TRACE_SPAN;
		span &= ~127U;
		cursor = before[2] % 0x1ffff0U;
		s22_trace_window = cursor >= span ? cursor - span : 0x1ffff0U - span;
		s22_trace_span = span;
		for (i = 0; i < 4; ++i)
			s22_trace_header[i] = before[i];
		s22_trace_latched = true;
	}
	for (i = 0; i < 4; ++i)
		if (before[i] != s22_trace_header[i] ||
		    READ_ONCE(header[i]) != s22_trace_header[i]) {
			s22_trace_disabled = true;
			goto out_header;
		}
	if ((event + 1U) * 128U > s22_trace_span)
		goto out_header;
	slot = early_memremap_prot(0x800200010ULL + s22_trace_window + event * 128U,
				  128, prot);
	if (!slot)
		goto out_header;
	asm volatile(".global s22_retained_trace_invalidate\n"
		     "s22_retained_trace_invalidate:" ::: "memory");
	for (i = 0; i < 8; ++i)
		WRITE_ONCE(slot[i], 0);
	dsb(sy);
	for (i = 8; i < 128; ++i)
		WRITE_ONCE(slot[i], READ_ONCE(s22_trace_frames[event][i]));
	dsb(sy);
	asm volatile(".global s22_retained_trace_recheck\n"
		     "s22_retained_trace_recheck:" ::: "memory");
	for (i = 0; i < 4; ++i)
		if (READ_ONCE(header[i]) != s22_trace_header[i]) {
			s22_trace_disabled = true;
			goto out_slot;
		}
	for (i = 0; i < 8; ++i)
		WRITE_ONCE(slot[i], READ_ONCE(s22_trace_frames[event][i]));
	dsb(sy);
out_slot:
	early_memunmap((void *)slot, 128);
out_header:
	early_memunmap((void *)header, 16);
}

void __init s22_retained_initcall(initcall_entry_t *entry, u32 phase);
noinline void __init s22_retained_initcall(initcall_entry_t *entry, u32 phase)
{
	unsigned long address = (unsigned long)entry;
	unsigned long first = (unsigned long)__initcall0_start;
	unsigned long end = (unsigned long)__initcall_end;
	u32 ordinal;

	if (end - first != 4UL * S22_TRACE_INITCALLS ||
	    address < first || address >= end || (address - first) % 4 || phase > 1) {
		s22_trace_disabled = true;
		return;
	}
	ordinal = (address - first) / 4;
	s22_retained_trace(6U + 2U * ordinal + phase);
}
