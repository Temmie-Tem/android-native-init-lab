/* SPDX-License-Identifier: GPL-2.0-only */
/* Compiled only into the dedicated y2q RAM-boot candidate. All state is resident. */
#include <crypto/blake2s.h>
#include <linux/device.h>
#include <linux/timekeeping.h>
#include <linux/random.h>
#include <linux/interrupt.h>
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

/* PID 1 initializes this window before enabling the single deferred work item. */
static bool bound, anchor_attempted, exec_attempted, armed;
static u32 window_header[4];
struct lane {
	u32 seq, one, two;
};
static struct lane init_lane, retry_lane;
static bool recording;
static u8 instance[16];
static atomic_t provider_mask = ATOMIC_INIT(0);
static atomic_t db_result = ATOMIC_INIT(-32768);
static u32 init_steps, retry_step;
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

static bool bytes_match(const u8 __iomem *slot, const u8 *frame, unsigned int start, unsigned int width)
{
	unsigned int i;

	for (i = start; i < width; ++i)
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

	unsigned int width = offset ? 40 : WIDTH;
	if ((offset && (offset < 80 || offset > 200 || offset % 40)) ||
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
	if (!nomap_pages(LOG_BASE + HEADER_SIZE + start, width))
		goto out;
	slot = ioremap(LOG_BASE + HEADER_SIZE + start, width);
	if (!slot)
		goto out;
	if (!header_matches(header, before))
		goto release;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(0, slot + i);
	dsb(sy);
	for (i = 8; i < width; ++i)
		writeb_relaxed(frame[i], slot + i);
	dsb(sy);
	if (!bytes_match(slot, frame, 8, width) || !header_matches(header, before))
		goto release;
	for (i = 0; i < 8; ++i)
		writeb_relaxed(frame[i], slot + i);
	dsb(sy);
	ok = bytes_match(slot, frame, 0, width) && header_matches(header, before);
release:
	iounmap(slot);
out:
	iounmap(header);
	return ok;
}

static noinline void emit_progress(struct lane *lane, bool worker)
{
	u32 frame[10] = {};
	u32 rc = (u16)atomic_read(&db_result);
	u32 state = worker ? retry_step : init_steps;
	unsigned int base = worker ? 160 : 80;

	if (!smp_load_acquire(&recording) || lane->seq >= (worker ? 128 : 328))
		return;
	frame[0] = worker ? 0x32574c48 : 0x32504c48;
	frame[1] = ++lane->seq;
	frame[2] = lane->one;
	frame[3] = lane->two;
	frame[4] = ((state & 1023) << 21) |
		   ((atomic_read(&provider_mask) & 31) << 16) | rc;
	frame[5] = min_t(u64, div_u64(ktime_get_boottime_ns(), 1000000), U32_MAX);
	blake2s((u8 *)frame + 24, (const u8 *)frame, instance, 16, 24, 16);
	y2q_write_slot(base + 40 * ((lane->seq - 1) & 1), (u8 *)frame);
}

void noinline y2q_deferred_worker(struct device *dev, unsigned int phase)
{
	const char *name;
	u32 id = 2166136261U;

	if (!smp_load_acquire(&recording) || retry_lane.seq >= 128 ||
	    in_interrupt() || !(current->flags & PF_WQ_WORKER))
		return;
	name = dev_name(dev);
	if (!name)
		return;
	while (*name) {
		id ^= (u8)*name++;
		id *= 16777619U;
	}
	retry_lane.one = id;
	if (phase == 2)
		retry_lane.two = id;
	retry_step = phase;
	emit_progress(&retry_lane, true);
}

void noinline y2q_provider_progress(unsigned int phase, int rc)
{
	if (phase == 2)
		atomic_set(&db_result, rc);
	atomic_or(BIT(phase), &provider_mask);
}

void noinline y2q_progress(unsigned int bit)
{
	if (!global_thread_one())
		return;
	if (bit >= 1024) {
		unsigned int next = (bit - 1024) / 2 + 1;

		if (bit & 1)
			init_lane.two = next;
		else
			init_lane.one = next;
	} else if (bit >= 306 && bit < 316) {
		init_steps |= BIT(bit - 306);
	}
	emit_progress(&init_lane, false);
}

void noinline y2q_basic_anchor(void)
{
	u8 frame[WIDTH] = {};

	if (anchor_attempted || !global_thread_one())
		return;
	anchor_attempted = true;
	memcpy(frame + 8, y2q_nonce, 16);
	if (rng_is_initialized()) {
		memcpy(frame, "H0EPOCH3", 8);
		get_random_bytes(frame + 24, 16);
	} else {
		memcpy(frame, "H0UNATR3", 8);
		memcpy(frame + 24, "RUN-LEVEL-ONLY!!", 16);
	}
	blake2s(instance, frame + 24, y2q_nonce, 16, 16, 16);
	blake2s(frame + 64, frame, y2q_nonce, 16, 64, 16);
	if (y2q_write_slot(0, frame))
		smp_store_release(&recording, true);
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
