/* SPDX-License-Identifier: GPL-2.0-only */
/* Compiled only into the dedicated y2q RAM-boot candidate. All state is resident. */
#include <crypto/blake2s.h>
#include <linux/file.h>
#include <linux/fs.h>
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
#include <linux/y2q-progress.h>
#include "y2q-trial-data.h"

#define LOG_BASE 0x9f200000ULL
#define LOG_SIZE 0x200000U
#define HEADER_SIZE 16U
#define CAPACITY (LOG_SIZE - HEADER_SIZE)
#define WINDOW 256U
#define WIDTH 80U

/* All call sites belong to global PID 1, including the guarded syscall. */
static bool bound, alternating, anchor_attempted, exec_attempted, armed;
static u32 window_header[4];
static u8 progress_bits[40];
static struct path init_path;

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

static bool bytes_match(const u8 __iomem *slot, const u8 *frame, unsigned int start)
{
	unsigned int i;

	for (i = start; i < WIDTH; ++i)
		if (readb_relaxed(slot + i) != frame[i])
			return false;
	return true;
}

static noinline bool y2q_write_slot(unsigned int offset, const u8 *frame)
{
	u32 __iomem *header;
	u8 __iomem *slot;
	u32 before[4], cursor, start;
	unsigned int i;
	bool ok = false;

	if ((offset != 0 && offset != WIDTH && offset != 2 * WIDTH) ||
	    !allowed_tree() || !nomap_pages(LOG_BASE, HEADER_SIZE))
		return false;
	header = ioremap(LOG_BASE, HEADER_SIZE);
	if (!header)
		return false;
	for (i = 0; i < ARRAY_SIZE(before); ++i)
		before[i] = readl_relaxed(header + i);
	if (before[1] != 0x4d474f4c || before[2] < WINDOW ||
	    !header_matches(header, before) ||
	    (bound && memcmp(before, window_header, sizeof(before))))
		goto out;
	if (!bound) {
		memcpy(window_header, before, sizeof(before));
		bound = true;
	}
	cursor = before[2] % CAPACITY;
	start = (cursor >= WINDOW ? cursor : CAPACITY) - WINDOW + offset;
	if (!nomap_pages(LOG_BASE + HEADER_SIZE + start, WIDTH))
		goto out;
	slot = ioremap(LOG_BASE + HEADER_SIZE + start, WIDTH);
	if (!slot)
		goto out;
	if (!header_matches(header, before))
		goto release;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(0, slot + i);
	dsb(sy);
	for (i = 8; i < WIDTH; ++i)
		writeb_relaxed(frame[i], slot + i);
	dsb(sy);
	if (!bytes_match(slot, frame, 8) || !header_matches(header, before))
		goto release;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(frame[i], slot + i);
	dsb(sy);
	ok = bytes_match(slot, frame, 0) && header_matches(header, before);
release:
	iounmap(slot);
out:
	iounmap(header);
	return ok;
}

void noinline y2q_progress(unsigned int bit)
{
	u8 record[WIDTH];
	unsigned int byte = bit / 8;
	u8 mask = BIT(bit % 8);

	if (bit >= 316 || !global_thread_one() || (progress_bits[byte] & mask))
		return;
	progress_bits[byte] |= mask;
	memcpy(record, "Y2QSURV1", 8);
	memcpy(record + 8, y2q_nonce, 16);
	memcpy(record + 24, progress_bits, sizeof(progress_bits));
	blake2s(record + 64, record, NULL, 16, 64, 0);
	if (y2q_write_slot(alternating ? 2 * WIDTH : WIDTH, record))
		alternating = !alternating;
}

void noinline y2q_basic_anchor(void)
{
	u8 clear[WIDTH];
	unsigned int i;

	if (anchor_attempted || !global_thread_one())
		return;
	anchor_attempted = true;
	for (i = 0; i < WIDTH; ++i)
		clear[i] = READ_ONCE(y2q_anchor[i]) ^ 0xa5;
	y2q_write_slot(0, clear);
	y2q_progress(306);
}

void noinline y2q_trial_exec(void)
{
	struct inode *inode;

	if (!global_thread_one() || exec_attempted)
		return;
	exec_attempted = true;
	if (kern_path("/init", LOOKUP_FOLLOW, &init_path))
		return;
	inode = d_inode(init_path.dentry);
	if (!S_ISREG(inode->i_mode) || i_size_read(inode) != Y2Q_INIT_BYTES) {
		path_put(&init_path);
		return;
	}
	armed = true;
	y2q_progress(314);
}

void noinline y2q_trial_getpid(void)
{
	const struct pt_regs *regs;
	struct file *exe;

	if (!armed || !global_thread_one() || !current->mm)
		return;
	regs = task_pt_regs(current);
	if (!user_mode(regs) || compat_user_mode(regs) || regs->syscallno != __NR_getpid ||
	    regs->regs[8] != __NR_getpid || regs->pc != Y2Q_GETPID_PC || regs->regs[30] != Y2Q_GETPID_LR)
		return;
	exe = get_mm_exe_file(current->mm);
	if (!exe)
		return;
	if (path_equal(&exe->f_path, &init_path)) {
		armed = false;
		y2q_progress(315);
		path_put(&init_path);
	}
	fput(exe);
}
