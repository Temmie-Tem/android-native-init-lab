/* SPDX-License-Identifier: GPL-2.0-only */
/* Included only in the private instrumented y2q Linux 6.18 build. */
#include <linux/io.h>
#include <linux/libfdt.h>
#include <linux/of.h>
#include <asm/early_ioremap.h>
#include "y2q-stage-frames.h"

#define Y2Q_LOG_BASE 0x9f200000ULL
#define Y2Q_LOG_SIZE 0x200000U
#define Y2Q_CAPACITY (Y2Q_LOG_SIZE - 16U)

static u32 y2q_initial_header[4] __initdata;
static bool y2q_first_committed __initdata;

static bool __init y2q_stage_board(const void *fdt)
{
	const fdt32_t *reg;
	int length, chosen, node;

	if (!fdt || fdt_node_check_compatible(fdt, 0, "samsung,y2q"))
		return false;
	chosen = fdt_path_offset(fdt, "/chosen");
	if (chosen < 0 || !fdt_getprop(fdt, chosen, "linux,y2q-log-geometry-v1", &length) || length)
		return false;
	node = fdt_path_offset(fdt, "/reserved-memory/handoff-reserved@9f000000");
	if (node < 0 || !fdt_getprop(fdt, node, "no-map", &length) || length ||
	    fdt_getprop(fdt, node, "status", NULL))
		return false;
	reg = fdt_getprop(fdt, node, "reg", &length);
	return reg && length == 16 && fdt32_to_cpu(reg[0]) == 0 &&
	       fdt32_to_cpu(reg[1]) == 0x9f000000 && fdt32_to_cpu(reg[2]) == 0 &&
	       fdt32_to_cpu(reg[3]) == 0xa00000;
}

static bool __init y2q_header_unchanged(const u32 __iomem *header, const u32 before[4])
{
	unsigned int i;

	for (i = 0; i < 4; i++)
		if (readl_relaxed(&header[i]) != before[i])
			return false;
	return true;
}

static noinline void __init y2q_record_stage(unsigned int stage)
{
	const volatile u8 *encoded;
	u32 __iomem *header;
	u8 __iomem *slot;
	u32 before[4], cursor, offset;
	unsigned int i;

	if (stage >= ARRAY_SIZE(y2q_frames) || (stage && !y2q_first_committed) ||
	    !y2q_stage_board(initial_boot_params))
		return;
	header = early_ioremap(Y2Q_LOG_BASE, 16);
	if (!header)
		return;
	for (i = 0; i < 4; i++)
		before[i] = readl_relaxed(&header[i]);
	if (before[1] != 0x4d474f4c || before[2] < sizeof(y2q_frames) ||
	    (stage && memcmp(before, y2q_initial_header, sizeof(before))))
		goto out_header;

	/* Choose a contiguous pair of slots already visible to the stock
	 * snapshot. When the cursor has wrapped into its first 256 bytes,
	 * the final 256 physical bytes still precede it in that snapshot. */
	cursor = before[2] % Y2Q_CAPACITY;
	offset = (cursor >= sizeof(y2q_frames) ? cursor : Y2Q_CAPACITY) - sizeof(y2q_frames);
	offset += stage * sizeof(y2q_frames[0]);
	slot = early_ioremap(Y2Q_LOG_BASE + 16 + offset, sizeof(y2q_frames[0]));
	if (!slot)
		goto out_header;
	encoded = y2q_frames[stage];
	if (!y2q_header_unchanged(header, before))
		goto out_slot;
	/* Publish the signature after the complete body is visible. The
	 * image carries only encoded frames. No header word is changed. */
	for (i = 0; i < 8; i++)
		writeb_relaxed(0, &slot[i]);
	dsb(sy);
	for (i = 8; i < sizeof(y2q_frames[0]); i++)
		writeb_relaxed(READ_ONCE(encoded[i]) ^ 0xa5, &slot[i]);
	dsb(sy);
	for (i = 8; i < sizeof(y2q_frames[0]); i++)
		if (readb_relaxed(&slot[i]) != (READ_ONCE(encoded[i]) ^ 0xa5))
			goto out_slot;
	if (!y2q_header_unchanged(header, before))
		goto out_slot;
	for (i = 0; i < 8; i++)
		writeb_relaxed(READ_ONCE(encoded[i]) ^ 0xa5, &slot[i]);
	dsb(sy);
	if (!y2q_header_unchanged(header, before))
		goto out_slot;
	for (i = 0; i < 8; i++)
		if (readb_relaxed(&slot[i]) != (READ_ONCE(encoded[i]) ^ 0xa5))
			goto out_slot;
	if (!stage) {
		memcpy(y2q_initial_header, before, sizeof(before));
		y2q_first_committed = true;
	}
out_slot:
	early_iounmap(slot, sizeof(y2q_frames[0]));
out_header:
	early_iounmap(header, 16);
}
