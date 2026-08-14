// SPDX-License-Identifier: GPL-2.0-only

#include <linux/atomic.h>
#include <linux/compiler.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/string.h>
#include <linux/tracepoint.h>
#include <linux/types.h>

#include "core.h"
#include "trace.h"
#include "s22plus_dwc3_event_decode.h"

#define S22PLUS_DWC3_TARGET_NAME "a600000.dwc3"

struct s22plus_dwc3_latch_state {
	atomic_t gate_claimed;
	atomic_t event_claimed;
	u64 latch_install_ns;
	u64 gadget_exposure_ns;
	u64 first_event_ns;
	u32 first_event_raw;
	u8 first_event_kind;
	int install_ready;
	int gate_ready;
	int event_ready;
};

static struct s22plus_dwc3_latch_state s22plus_latch = {
	.gate_claimed = ATOMIC_INIT(0),
	.event_claimed = ATOMIC_INIT(0),
};

_Static_assert(sizeof(struct dwc3_event_type) == sizeof(u32),
		"DWC3 event type must remain one u32");
_Static_assert(sizeof(struct dwc3_event_devt) == sizeof(u32),
		"DWC3 device event must remain one u32");
_Static_assert(sizeof(struct dwc3_event_depevt) == sizeof(u32),
		"DWC3 endpoint event must remain one u32");
_Static_assert(sizeof(union dwc3_event) == sizeof(u32),
		"DWC3 event union must remain one u32");
_Static_assert(DWC3_EVENT_TYPE_DEV == S22PLUS_DWC3_EVENT_CLASS_DEV,
		"DWC3 device-event class changed");
_Static_assert(DWC3_DEVICE_EVENT_RESET == S22PLUS_DWC3_DEVICE_RESET,
		"DWC3 reset event changed");
_Static_assert(DWC3_DEVICE_EVENT_CONNECT_DONE ==
		S22PLUS_DWC3_DEVICE_CONNECT_DONE,
		"DWC3 connect-done event changed");
_Static_assert(DWC3_DEPEVT_XFERCOMPLETE ==
		S22PLUS_DWC3_ENDPOINT_XFERCOMPLETE,
		"DWC3 endpoint-complete event changed");
_Static_assert(EP0_SETUP_PHASE == S22PLUS_DWC3_EP0_SETUP_PHASE,
		"DWC3 EP0 setup phase changed");

static bool s22plus_dwc3_exact_target(const struct dwc3 *dwc)
{
	return dwc && dwc->dev &&
		strcmp(dev_name(dwc->dev), S22PLUS_DWC3_TARGET_NAME) == 0;
}

static void s22plus_dwc3_event_probe(void *unused, u32 raw, struct dwc3 *dwc)
{
	enum s22plus_dwc3_event_kind kind;
	u32 ep0state;

	(void)unused;
	/* Permanent hot-path rule: a published first event costs one load. */
	if (smp_load_acquire(&s22plus_latch.event_ready))
		return;
	if (!smp_load_acquire(&s22plus_latch.gate_ready))
		return;
	if (!s22plus_dwc3_exact_target(dwc))
		return;

	ep0state = (u32)READ_ONCE(dwc->ep0state);
	kind = s22plus_dwc3_decode_host_event(raw, ep0state);
	if (kind == S22PLUS_DWC3_EVENT_NONE)
		return;
	if (atomic_cmpxchg(&s22plus_latch.event_claimed, 0, 1) != 0)
		return;

	s22plus_latch.first_event_ns = ktime_get_ns();
	s22plus_latch.first_event_raw = raw;
	s22plus_latch.first_event_kind = (u8)kind;
	smp_store_release(&s22plus_latch.event_ready, 1);
}

static bool s22plus_dwc3_exact_one(const char *value)
{
	if (!value || value[0] != '1')
		return false;
	if (value[1] == '\0')
		return true;
	return value[1] == '\n' && value[2] == '\0';
}

static int s22plus_dwc3_expose_gate_set(const char *value,
		const struct kernel_param *parameter)
{
	(void)parameter;
	if (!s22plus_dwc3_exact_one(value))
		return -EINVAL;
	if (!smp_load_acquire(&s22plus_latch.install_ready))
		return -EAGAIN;
	if (atomic_cmpxchg(&s22plus_latch.gate_claimed, 0, 1) != 0)
		return -EBUSY;

	s22plus_latch.gadget_exposure_ns = ktime_get_ns();
	smp_store_release(&s22plus_latch.gate_ready, 1);
	return 0;
}

static int s22plus_dwc3_expose_gate_get(char *buffer,
		const struct kernel_param *parameter)
{
	(void)parameter;
	return scnprintf(buffer, PAGE_SIZE, "%u\n",
			smp_load_acquire(&s22plus_latch.gate_ready) ? 1U : 0U);
}

static const struct kernel_param_ops s22plus_dwc3_expose_gate_ops = {
	.set = s22plus_dwc3_expose_gate_set,
	.get = s22plus_dwc3_expose_gate_get,
};

module_param_cb(expose_gate, &s22plus_dwc3_expose_gate_ops, NULL, 0644);
MODULE_PARM_DESC(expose_gate,
		"write-once pre-UDC exposure gate; reads 0 before and 1 after capture");

static int s22plus_dwc3_snapshot_get(char *buffer,
		const struct kernel_param *parameter)
{
	bool gate_ready;
	bool event_ready;

	(void)parameter;
	if (!smp_load_acquire(&s22plus_latch.install_ready))
		return -EAGAIN;

	gate_ready = smp_load_acquire(&s22plus_latch.gate_ready) != 0;
	event_ready = smp_load_acquire(&s22plus_latch.event_ready) != 0;
	return scnprintf(buffer, PAGE_SIZE,
			"v=1 install_v=1 install_ns=%llu gate_v=%u gate_ns=%llu "
			"event_v=%u event_ns=%llu kind=%u raw=%08x\n",
			(unsigned long long)s22plus_latch.latch_install_ns,
			gate_ready ? 1U : 0U,
			(unsigned long long)(gate_ready ?
				s22plus_latch.gadget_exposure_ns : 0U),
			event_ready ? 1U : 0U,
			(unsigned long long)(event_ready ?
				s22plus_latch.first_event_ns : 0U),
			event_ready ? s22plus_latch.first_event_kind : 0U,
			event_ready ? s22plus_latch.first_event_raw : 0U);
}

static const struct kernel_param_ops s22plus_dwc3_snapshot_ops = {
	.set = NULL,
	.get = s22plus_dwc3_snapshot_get,
};

module_param_cb(snapshot, &s22plus_dwc3_snapshot_ops, NULL, 0444);
MODULE_PARM_DESC(snapshot, "write-once DWC3 event latch snapshot");

static int __init s22plus_dwc3_event_latch_init(void)
{
	int rc;

	rc = register_trace_dwc3_event(s22plus_dwc3_event_probe, NULL);
	if (rc < 0)
		return rc;

	s22plus_latch.latch_install_ns = ktime_get_ns();
	smp_store_release(&s22plus_latch.install_ready, 1);
	return 0;
}

static void __exit s22plus_dwc3_event_latch_exit(void)
{
	unregister_trace_dwc3_event(s22plus_dwc3_event_probe, NULL);
	tracepoint_synchronize_unregister();
}

module_init(s22plus_dwc3_event_latch_init);
module_exit(s22plus_dwc3_event_latch_exit);

MODULE_DESCRIPTION("S22+ FYG8 one-shot DWC3 host-event latch");
MODULE_LICENSE("GPL v2");
