/* SPDX-License-Identifier: GPL-2.0-only
 * V10 generated once into drivers/base/dd.c. Fixed observations, no control.
 * Persistent hooks reach init memory only through the protected live pointer.
 */
#include <linux/bitmap.h>
#include <linux/build_bug.h>
#include <linux/cpu.h>
#include <linux/init.h>
#include <linux/of.h>
#include <linux/pid_namespace.h>
#include <linux/preempt.h>
#include <linux/sched.h>
#include <asm/barrier.h>
#include <asm/early_ioremap.h>
#include <asm/pgtable.h>

#define S22_PROBE_INITCALLS @COUNT@U
#define S22_PROBE_SLOTS @SLOTS@U
#define S22_PROBE_NODES @NODES_COUNT@U
#define S22_PROBE_ORDINALS @ORDINAL_COUNT@U
#define S22_PROBE_TLMM_NODE @TLMM_NODE@U
#define S22_PROBE_TLMM_BASE @FIXED_COUNT@U
#define S22_PROBE_TLMM_POINTS @TLMM_POINTS@U
#define S22_PROBE_TLMM_GROUPS @TLMM_GROUPS@U
#define S22_PROBE_SPARSE_BASE (S22_PROBE_TLMM_BASE + S22_PROBE_TLMM_POINTS * S22_PROBE_TLMM_GROUPS)
#define S22_PROBE_DEVICE_BASE (S22_PROBE_SPARSE_BASE + 2U * S22_PROBE_ORDINALS)
#define S22_PROBE_BUCKETS (S22_PROBE_NODES + 2U)
#define S22_PROBE_SPAN (128U * S22_PROBE_SLOTS)

@EVENT_CONSTANTS@
@TLMM_CONSTANTS@

enum s22_probe_op {
	S22_ARM, S22_FIXED, S22_PHASE_TWO, S22_DISARM,
	S22_WORK_ENTER, S22_WORK_RETURN, S22_DEVICE, S22_RETURN,
	S22_TLMM_ENTER, S22_TLMM_POINT
};
typedef u32 (*s22_probe_dispatch_t)(u32, struct device *, u32);
static s22_probe_dispatch_t s22_probe_dispatch;

static const u8 s22_probe_frames[S22_PROBE_SLOTS][128] __initconst __used = {
@FRAMES@
};
static const char * const s22_probe_paths[S22_PROBE_NODES] __initconst = {
@PATHS@
};
static const u32 s22_probe_ordinals[S22_PROBE_ORDINALS] __initconst = {@ORDINALS@};
static struct device_node *s22_probe_nodes[S22_PROBE_NODES] __initdata;
static DECLARE_BITMAP(s22_probe_seen, S22_PROBE_SLOTS) __initdata;
static struct task_struct *s22_probe_owner __initdata;
static u32 s22_probe_header[4] __initdata;
static u32 s22_probe_window __initdata;
static u32 s22_probe_span __initdata;
static u32 s22_probe_phase __initdata;
static bool s22_probe_latched __initdata;
static bool s22_probe_disabled __initdata;
static bool s22_probe_armed __initdata;
static bool s22_probe_prepared __initdata;
static struct task_struct *s22_probe_tlmm_owner[S22_PROBE_TLMM_GROUPS] __initdata;
static bool s22_probe_tlmm_active[S22_PROBE_TLMM_GROUPS] __initdata;
extern initcall_entry_t __initcall0_start[], __initcall_end[];

/* Called with preemption disabled on the sole online boot CPU. No sleeper,
 * IRQ client, runtime mapping or mapping held across a callback is added.
 */
void __init s22_retained_probe_write(u32 event);
noinline void __init s22_retained_probe_write(u32 event)
{
	u64 el, state;
	u32 before[4], span, cursor;
	volatile u32 *header;
	volatile u8 *slot;
	unsigned long prot;
	unsigned int i;

	BUILD_BUG_ON(S22_PROBE_SLOTS > 4096U);
	BUILD_BUG_ON(sizeof(initcall_entry_t) != 4);
	BUILD_BUG_ON(S22_PROBE_DEVICE_BASE + 10U * S22_PROBE_BUCKETS != S22_PROBE_SLOTS);
	BUILD_BUG_ON(S22_PROBE_TLMM_NODE >= S22_PROBE_NODES);
	if (s22_probe_disabled || event >= S22_PROBE_SLOTS)
		return;
	if (test_bit(event, s22_probe_seen))
		return;
	__set_bit(event, s22_probe_seen);
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
	if (!s22_probe_latched) {
		if (before[1] != 0x4d474f4c || before[2] < 128U)
			goto out_header;
		span = before[2] < S22_PROBE_SPAN ? before[2] : S22_PROBE_SPAN;
		span &= ~127U;
		cursor = before[2] % 0x1ffff0U;
		s22_probe_window = cursor >= span ? cursor - span : 0x1ffff0U - span;
		s22_probe_span = span;
		for (i = 0; i < 4; ++i)
			s22_probe_header[i] = before[i];
		s22_probe_latched = true;
	}
	for (i = 0; i < 4; ++i)
		if (before[i] != s22_probe_header[i] ||
		    READ_ONCE(header[i]) != s22_probe_header[i]) {
			s22_probe_disabled = true;
			goto out_header;
		}
	if ((event + 1U) * 128U > s22_probe_span)
		goto out_header;
	slot = early_memremap_prot(0x800200010ULL + s22_probe_window +
				  s22_probe_span - (event + 1U) * 128U,
				  128, prot);
	if (!slot)
		goto out_header;
	asm volatile(".global s22_retained_probe_invalidate\n"
		     "s22_retained_probe_invalidate:" ::: "memory");
	for (i = 0; i < 8; ++i)
		WRITE_ONCE(slot[i], 0);
	dsb(sy);
	for (i = 8; i < 128; ++i)
		WRITE_ONCE(slot[i], READ_ONCE(s22_probe_frames[event][i]));
	dsb(sy);
	asm volatile(".global s22_retained_probe_recheck\n"
		     "s22_retained_probe_recheck:" ::: "memory");
	for (i = 0; i < 4; ++i)
		if (READ_ONCE(header[i]) != s22_probe_header[i]) {
			s22_probe_disabled = true;
			goto out_slot;
		}
	for (i = 0; i < 8; ++i)
		WRITE_ONCE(slot[i], READ_ONCE(s22_probe_frames[event][i]));
	dsb(sy);
out_slot:
	early_memunmap((void *)slot, 128);
out_header:
	early_memunmap((void *)header, 16);
}

static bool __init s22_probe_context(void)
{
	if (num_online_cpus() != 1 || smp_processor_id() != 0 ||
	    system_state >= SYSTEM_FREEING_INITMEM ||
	    (unsigned long)__initcall_end - (unsigned long)__initcall0_start !=
	    4UL * S22_PROBE_INITCALLS) {
		s22_probe_disabled = true;
		WRITE_ONCE(s22_probe_dispatch, NULL);
		return false;
	}
	return !s22_probe_disabled;
}

void __init s22_retained_probe_mark(u32 event);
noinline void __init s22_retained_probe_mark(u32 event)
{
	preempt_disable();
	if (s22_probe_context())
		s22_retained_probe_write(event);
	preempt_enable();
}

static u32 __init s22_probe_handle(u32 op, struct device *dev, u32 value)
{
	u32 event, node, point, token, group;

	/* A recording failure must not prevent lifetime closure. */
	if (op == S22_DISARM && current == s22_probe_owner) {
		if (s22_probe_context() && s22_probe_armed)
			s22_retained_probe_write(S22_EV_DEFERRED_PRE_EXIT);
		s22_probe_armed = false;
		WRITE_ONCE(s22_probe_dispatch, NULL);
		return 0;
	}
	if (!s22_probe_context())
		return 0;
	/* Group zero is the first prepared invocation before deferred arming.
	 * The local token keeps subsequent points in their entry-observed group,
	 * including a return after the global phase has advanced. A repeated or
	 * nested entry in that group gets no token, even after a failed mapping.
	 */
	if (op == S22_TLMM_ENTER) {
		if (!dev || !dev->of_node || s22_probe_phase >= S22_PROBE_TLMM_GROUPS ||
		    s22_probe_armed != (s22_probe_phase != 0) ||
		    !s22_probe_nodes[S22_PROBE_TLMM_NODE] ||
		    dev->of_node != s22_probe_nodes[S22_PROBE_TLMM_NODE])
			return 0;
		event = S22_PROBE_TLMM_BASE + s22_probe_phase * S22_PROBE_TLMM_POINTS;
		if (test_bit(event, s22_probe_seen))
			return 0;
		s22_probe_tlmm_owner[s22_probe_phase] = current;
		s22_probe_tlmm_active[s22_probe_phase] = true;
		s22_retained_probe_write(event);
		return event + 1;
	}
	if (op == S22_TLMM_POINT) {
		token = value >> 8;
		point = value & 255U;
		if (token < S22_PROBE_TLMM_BASE + 1U ||
		    token > S22_PROBE_TLMM_BASE + 1U +
			    (S22_PROBE_TLMM_GROUPS - 1U) * S22_PROBE_TLMM_POINTS ||
		    (token - 1U - S22_PROBE_TLMM_BASE) % S22_PROBE_TLMM_POINTS ||
		    point == 0 || point >= S22_PROBE_TLMM_POINTS)
			return 0;
		group = (token - 1U - S22_PROBE_TLMM_BASE) / S22_PROBE_TLMM_POINTS;
		if (!s22_probe_tlmm_active[group] || s22_probe_tlmm_owner[group] != current)
			return 0;
		s22_retained_probe_write(token - 1U + point);
		if (point >= S22_TLMM_PROBE_RETURN_ZERO)
			s22_probe_tlmm_active[group] = false;
		return 0;
	}
	if (op == S22_ARM) {
		if (current != s22_probe_owner || s22_probe_armed || s22_probe_phase)
			return 0;
		s22_probe_armed = true;
		s22_probe_phase = 1;
		s22_retained_probe_write(S22_EV_DEFERRED_BODY_ENTER);
		return 0;
	}
	if (!s22_probe_armed)
		return 0;
	if (op == S22_FIXED || op == S22_PHASE_TWO) {
		if (current != s22_probe_owner)
			return 0;
		if (op == S22_PHASE_TWO) {
			s22_probe_phase = 2;
			s22_retained_probe_write(S22_EV_PRE_SECOND_TRIGGER);
		} else if (value >= S22_EV_POST_DEFERRED_DEBUGFS &&
			   value <= S22_EV_POST_TIMEOUT_SCHEDULE_CALL &&
			   value != S22_EV_PRE_SECOND_TRIGGER) {
			s22_retained_probe_write(value);
		}
		return 0;
	}
	if (op == S22_WORK_ENTER) {
		event = S22_EV_PHASE_1_WORKER_ENTER + 2 * (s22_probe_phase - 1);
		if (test_bit(event, s22_probe_seen))
			return 0;
		s22_retained_probe_write(event);
		return event + 1;
	}
	if (op == S22_WORK_RETURN) {
		if (value == S22_EV_PHASE_1_WORKER_RETURN || value == S22_EV_PHASE_2_WORKER_RETURN)
			s22_retained_probe_write(value);
		return 0;
	}
	if (op == S22_RETURN) {
		if (value <= S22_PROBE_DEVICE_BASE || value >= S22_PROBE_SLOTS)
			return 0;
		point = (value - 1 - S22_PROBE_DEVICE_BASE) % 5;
		if (point == 0 || point == 3)
			s22_retained_probe_write(value);
		return 0;
	}
	if (op != S22_DEVICE || !dev || (value != 0 && value != 2 && value != 3))
		return 0;
	if (!dev->of_node) {
		node = S22_PROBE_NODES;
	} else {
		for (node = 0; node < S22_PROBE_NODES; ++node)
			if (s22_probe_nodes[node] && s22_probe_nodes[node] == dev->of_node)
				break;
		if (node == S22_PROBE_NODES)
			++node;
	}
	event = S22_PROBE_DEVICE_BASE +
		5 * ((s22_probe_phase - 1) * S22_PROBE_BUCKETS + node) + value;
	if (test_bit(event, s22_probe_seen))
		return 0;
	s22_retained_probe_write(event);
	return value == 2 ? 0 : event + 1;
}

/* The only persistent path to init code. The pointer read and complete call
 * share preemption exclusion with disarm on the qualified sole online CPU.
 * It is NULL before preparation and from deferred-initcall exit onward.
 */
static noinline u32 s22_probe_hook(u32 op, struct device *dev, u32 value)
{
	s22_probe_dispatch_t handler;
	u32 token = 0;

	if (!in_task())
		return 0;
	preempt_disable();
	handler = num_online_cpus() == 1 && smp_processor_id() == 0 ?
		READ_ONCE(s22_probe_dispatch) : NULL;
	if (handler)
		token = handler(op, dev, value);
	preempt_enable();
	return token;
}

u32 s22_retained_probe_tlmm_begin(struct device *dev);
noinline u32 s22_retained_probe_tlmm_begin(struct device *dev)
{
	return s22_probe_hook(S22_TLMM_ENTER, dev, 0);
}

void s22_retained_probe_tlmm_point(u32 token, u32 point);
noinline void s22_retained_probe_tlmm_point(u32 token, u32 point)
{
	if (token <= S22_PROBE_TLMM_BASE + 1U +
		     (S22_PROBE_TLMM_GROUPS - 1U) * S22_PROBE_TLMM_POINTS &&
	    point < S22_PROBE_TLMM_POINTS)
		s22_probe_hook(S22_TLMM_POINT, NULL, (token << 8) | point);
}

void __init s22_retained_probe_prepare(void);
noinline void __init s22_retained_probe_prepare(void)
{
	u32 i;

	if (s22_probe_prepared || current != init_pid_ns.child_reaper || task_pid_nr(current) != 1)
		return;
	s22_probe_prepared = true;
	if ((unsigned long)__initcall_end - (unsigned long)__initcall0_start !=
	    4UL * S22_PROBE_INITCALLS) {
		s22_probe_disabled = true;
		return;
	}
	for (i = 0; i < S22_PROBE_NODES; ++i)
		s22_probe_nodes[i] = of_find_node_by_path(s22_probe_paths[i]);
	preempt_disable();
	if (s22_probe_context()) {
		s22_probe_owner = current;
		WRITE_ONCE(s22_probe_dispatch, s22_probe_handle);
	}
	preempt_enable();
}

void __init s22_retained_probe_finish(void);
noinline void __init s22_retained_probe_finish(void)
{
	u32 i;

	preempt_disable();
	WRITE_ONCE(s22_probe_dispatch, NULL);
	s22_probe_armed = false;
	preempt_enable();
	for (i = 0; i < S22_PROBE_NODES; ++i) {
		of_node_put(s22_probe_nodes[i]);
		s22_probe_nodes[i] = NULL;
	}
}

void __init s22_retained_probe_initcall(initcall_entry_t *entry, u32 phase);
noinline void __init s22_retained_probe_initcall(initcall_entry_t *entry, u32 phase)
{
	unsigned long address = (unsigned long)entry;
	unsigned long first = (unsigned long)__initcall0_start;
	unsigned long end = (unsigned long)__initcall_end;
	u32 ordinal, i;

	if (end - first != 4UL * S22_PROBE_INITCALLS || address < first ||
	    address >= end || (address - first) % 4 || phase > 1) {
		s22_probe_disabled = true;
		return;
	}
	ordinal = (address - first) / 4;
	for (i = 0; i < S22_PROBE_ORDINALS; ++i)
		if (s22_probe_ordinals[i] == ordinal) {
			s22_retained_probe_mark(S22_PROBE_SPARSE_BASE + 2 * i + phase);
			return;
		}
}
