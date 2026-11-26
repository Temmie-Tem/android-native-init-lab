/* SPDX-License-Identifier: GPL-2.0-only */
/* Built into the private arm64 y2q trial. All callbacks run in process context. */
#include <linux/file.h>
#include <linux/fs.h>
#include <linux/file.h>
#include <linux/io.h>
#include <linux/memblock.h>
#include <linux/mm.h>
#include <linux/namei.h>
#include <linux/of.h>
#include <linux/pid_namespace.h>
#include <linux/sched.h>
#include <linux/sched/mm.h>
#include <linux/sched/task_stack.h>
#include <asm/ptrace.h>
#include <asm/unistd.h>
#include <linux/y2q-pid1-stage.h>
#include "y2q-pid1-frames.h"

#define LOG_BASE 0x9f200000ULL
#define LOG_SIZE 0x200000U
#define HEADER_SIZE 16U
#define CAPACITY (LOG_SIZE - HEADER_SIZE)

/* Only the initial namespace's global thread 1 may access this per-boot state. */
static bool exec_attempted, armed;
static struct path init_path;
static u32 committed_header[4];

static bool global_thread_one(void)
{
	return task_pid_nr(current) == 1 && task_tgid_nr(current) == 1 &&
		task_active_pid_ns(current) == &init_pid_ns;
}

static bool allowed_tree(void)
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

static bool nomap_pages(phys_addr_t base, size_t length)
{
	phys_addr_t page;

	for (page = base & PAGE_MASK; page < base + length; page += PAGE_SIZE) {
		if (!memblock_is_region_memory(page, PAGE_SIZE) || pfn_is_map_memory(PHYS_PFN(page)))
			return false;
	}
	return true;
}

static bool header_matches(const u32 __iomem *header, const u32 before[4])
{
	unsigned int i;

	for (i = 0; i < 4; ++i)
		if (readl_relaxed(&header[i]) != before[i])
			return false;
	return true;
}

static bool bytes_match(const u8 __iomem *slot, const u8 *encoded, unsigned int from, unsigned int end)
{
	unsigned int i;

	for (i = from; i < end; ++i)
		if (readb_relaxed(slot + i) != (READ_ONCE(encoded[i]) ^ 0xa5))
			return false;
	return true;
}

static noinline bool y2q_publish_pid1_stage(unsigned int stage)
{
	u32 __iomem *header;
	u8 __iomem *pair, *slot;
	const u8 *encoded;
	u32 before[4], cursor, offset;
	unsigned int i;
	bool complete = false;

	if (stage >= ARRAY_SIZE(y2q_frames) || !allowed_tree() || !nomap_pages(LOG_BASE, HEADER_SIZE))
		return false;
	header = ioremap(LOG_BASE, HEADER_SIZE);
	if (!header)
		return false;
	for (i = 0; i < 4; ++i)
		before[i] = readl_relaxed(&header[i]);
	if (before[1] != 0x4d474f4c || before[2] < sizeof(y2q_frames) ||
	    (stage && memcmp(before, committed_header, sizeof(before))))
		goto out_header;
	cursor = before[2] % CAPACITY;
	offset = (cursor >= sizeof(y2q_frames) ? cursor : CAPACITY) - sizeof(y2q_frames);
	if (!nomap_pages(LOG_BASE + HEADER_SIZE + offset, sizeof(y2q_frames)))
		goto out_header;
	pair = ioremap(LOG_BASE + HEADER_SIZE + offset, sizeof(y2q_frames));
	if (!pair)
		goto out_header;
	slot = pair + stage * sizeof(y2q_frames[0]);
	encoded = y2q_frames[stage];
	if (!header_matches(header, before) || (stage && !bytes_match(pair, y2q_frames[0], 0, 128)))
		goto out_pair;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(0, slot + i);
	dsb(sy);
	for (i = 8; i < 128; ++i)
		writeb_relaxed(READ_ONCE(encoded[i]) ^ 0xa5, slot + i);
	dsb(sy);
	if (!bytes_match(slot, encoded, 8, 128) || !header_matches(header, before))
		goto out_pair;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(READ_ONCE(encoded[i]) ^ 0xa5, slot + i);
	dsb(sy);
	complete = bytes_match(slot, encoded, 0, 128) && header_matches(header, before);
	if (complete && !stage)
		memcpy(committed_header, before, sizeof(before));
out_pair:
	iounmap(pair);
out_header:
	iounmap(header);
	return complete;
}

void noinline y2q_pid1_exec_attempt(void)
{
	struct inode *inode;

	if (!global_thread_one() || exec_attempted)
		return;
	exec_attempted = true;
	if (!allowed_tree() || kern_path("/init", LOOKUP_FOLLOW, &init_path))
		return;
	inode = d_inode(init_path.dentry);
	if (S_ISREG(inode->i_mode) && i_size_read(inode) == 707960 &&
	    y2q_publish_pid1_stage(0)) {
		armed = true;
		return;
	}
	path_put(&init_path);
}

void noinline y2q_pid1_el0_getpid(void)
{
	const struct pt_regs *regs;
	struct file *exe;

	if (!global_thread_one() || !armed || !current->mm)
		return;
	regs = task_pt_regs(current);
	/* The retained ET_EXEC's main BL, its libc SVC, and the saved next PC. */
	if (!user_mode(regs) || compat_user_mode(regs) || regs->syscallno != __NR_getpid ||
	    regs->regs[8] != __NR_getpid || regs->pc != 0x411c8c || regs->regs[30] != 0x40048c)
		return;
	exe = get_mm_exe_file(current->mm);
	if (!exe)
		return;
	if (path_equal(&exe->f_path, &init_path)) {
		armed = false;
		y2q_publish_pid1_stage(1);
		path_put(&init_path);
	}
	fput(exe);
}
