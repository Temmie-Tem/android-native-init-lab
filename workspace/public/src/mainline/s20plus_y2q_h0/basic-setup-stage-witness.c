/* SPDX-License-Identifier: GPL-2.0-only */
/* Three boot-only milestones in the original y2q Samsung diagnostic window. */
#include <linux/init.h>
#include <linux/io.h>
#include <linux/memblock.h>
#include <linux/mm.h>
#include <linux/of.h>
#include <asm/early_ioremap.h>
#include <linux/y2q-basic-stage.h>
#include "y2q-basic-frames.h"

#define LOG_BASE 0x9f200000ULL
#define LOG_SIZE 0x200000U
#define HEADER_SIZE 16U
#define CAPACITY (LOG_SIZE - HEADER_SIZE)
#define WINDOW 256U

/* Calls occur once in sequence, on the boot CPU then the init thread. */
static bool attempted[3] __initdata;
static bool window_bound __initdata;
static u32 window_header[4] __initdata;

static bool __init allowed_tree(void)
{
	struct device_node *region;
	const __be32 *reg;
	int len;
	bool ok;

	if (!of_machine_is_compatible("samsung,y2q") || !of_chosen ||
	    !of_find_property(of_chosen, "linux,y2q-log-geometry-v1", &len) || len)
		return false;
	region = of_find_node_by_path("/reserved-memory/handoff-reserved@9f000000");
	if (!region)
		return false;
	reg = of_get_property(region, "reg", &len);
	ok = reg && len == 16 && !be32_to_cpu(reg[0]) &&
		be32_to_cpu(reg[1]) == 0x9f000000 && !be32_to_cpu(reg[2]) &&
		be32_to_cpu(reg[3]) == 0xa00000 && !of_find_property(region, "status", NULL) &&
		of_find_property(region, "no-map", &len) && !len;
	of_node_put(region);
	return ok;
}

static bool __init nomap_pages(phys_addr_t base, size_t length)
{
	phys_addr_t page;

	for (page = base & PAGE_MASK; page < base + length; page += PAGE_SIZE) {
		if (!memblock_is_region_memory(page, PAGE_SIZE) || pfn_is_map_memory(PHYS_PFN(page)))
			return false;
	}
	return true;
}

static bool __init header_matches(const u32 __iomem *header, const u32 before[4])
{
	unsigned int i;

	for (i = 0; i < 4; ++i)
		if (readl_relaxed(&header[i]) != before[i])
			return false;
	return true;
}

static bool __init bytes_match(const u8 __iomem *slot, const u8 *encoded, unsigned int from, unsigned int end)
{
	unsigned int i;

	for (i = from; i < end; ++i)
		if (readb_relaxed(slot + i) != (READ_ONCE(encoded[i]) ^ 0xa5))
			return false;
	return true;
}

static void __iomem * __init map_log(bool early, phys_addr_t base, size_t length)
{
	if (!nomap_pages(base, length))
		return NULL;
	return early ? early_ioremap(base, length) : ioremap(base, length);
}

static void __init unmap_log(bool early, void __iomem *area, size_t length)
{
	if (early)
		early_iounmap(area, length);
	else
		iounmap(area);
}

static noinline void __init y2q_publish_basic_stage(unsigned int stage)
{
	u32 __iomem *header;
	u8 __iomem *slot;
	u32 before[4], cursor, offset;
	const u8 *encoded;
	const unsigned int width = sizeof(y2q_frames[0]);
	unsigned int i;
	bool early = stage == 0;

	BUILD_BUG_ON(sizeof(y2q_frames) > WINDOW);
	if (stage >= ARRAY_SIZE(y2q_frames) || attempted[stage])
		return;
	attempted[stage] = true;
	if (!allowed_tree())
		return;
	header = map_log(early, LOG_BASE, HEADER_SIZE);
	if (!header)
		return;
	for (i = 0; i < ARRAY_SIZE(before); ++i)
		before[i] = readl_relaxed(header + i);
	if (before[1] != 0x4d474f4c || before[2] < WINDOW ||
	    !header_matches(header, before))
		goto out_header;
	/* Once bound, even a failed publication cannot open another window. */
	if (window_bound && memcmp(before, window_header, sizeof(before)))
		goto out_header;
	if (!window_bound) {
		memcpy(window_header, before, sizeof(before));
		window_bound = true;
	}
	cursor = before[2] % CAPACITY;
	offset = (cursor >= WINDOW ? cursor : CAPACITY) - WINDOW + stage * width;
	slot = map_log(early, LOG_BASE + HEADER_SIZE + offset, width);
	if (!slot)
		goto out_header;
	encoded = y2q_frames[stage];
	if (!header_matches(header, before))
		goto out_slot;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(0, slot + i);
	dsb(sy);
	for (i = 8; i < width; ++i)
		writeb_relaxed(READ_ONCE(encoded[i]) ^ 0xa5, slot + i);
	dsb(sy);
	if (!bytes_match(slot, encoded, 8, width) || !header_matches(header, before))
		goto out_slot;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(READ_ONCE(encoded[i]) ^ 0xa5, slot + i);
	dsb(sy);
	if (!bytes_match(slot, encoded, 0, width) || !header_matches(header, before))
		goto out_slot;
out_slot:
	unmap_log(early, slot, width);
out_header:
	unmap_log(early, header, HEADER_SIZE);
}

void noinline __init y2q_dt_ready(void)
{
	y2q_publish_basic_stage(0);
}

void noinline __init y2q_basic_enter(void)
{
	y2q_publish_basic_stage(1);
}

void noinline __init y2q_basic_return(void)
{
	y2q_publish_basic_stage(2);
}
