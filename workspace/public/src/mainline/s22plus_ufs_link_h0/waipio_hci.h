// SPDX-License-Identifier: GPL-2.0-only
#ifndef ML030_WAIPIO_HCI_H
#define ML030_WAIPIO_HCI_H
#include "waipio_phy.h"

/* Report v3 appends two u32 words. The first encodes component:operation
 * (8 bits each); the second holds evaluated bits 0..10 and failed bits 11..21.
 * Bits 22..27 preserve the already masked HCS value (0x39), without a reread.
 * Unset evaluated bits mean unobserved, never a successful condition.
 */
enum g0q_stage2_component {
	G0Q_S2_HCI = 1, G0Q_S2_RESET, G0Q_S2_CORE, G0Q_S2_UNIPRO,
	G0Q_S2_VCC, G0Q_S2_VCCQ, G0Q_S2_REF_PAD, G0Q_S2_PARENT,
};
enum g0q_stage2_operation {
	G0Q_S2_DEADLINE = 1, G0Q_S2_UFS_VERSION, G0Q_S2_HW_VERSION,
	G0Q_S2_QUIESCENT, G0Q_S2_PIN_GUARD, G0Q_S2_SET_RATE,
	G0Q_S2_RATE_READBACK, G0Q_S2_GET_SUPPLY, G0Q_S2_BEFORE_LOAD,
	G0Q_S2_SET_LOAD, G0Q_S2_BEFORE_VOLTAGE, G0Q_S2_SET_VOLTAGE,
	G0Q_S2_BEFORE_ENABLE, G0Q_S2_ENABLE, G0Q_S2_VOLTAGE_READBACK,
	G0Q_S2_SEED_GET, G0Q_S2_SEED_DEADLINE, G0Q_S2_SEED_VOLTAGE,
	G0Q_S2_PARENT_READBACK, G0Q_S2_AFTER_SUPPLY,
};
enum g0q_stage2_check {
	G0Q_S2_HCE, G0Q_S2_HCS, G0Q_S2_TRANSFER_DOORBELL,
	G0Q_S2_TASK_DOORBELL, G0Q_S2_TRANSFER_RUN, G0Q_S2_TASK_RUN,
	G0Q_S2_IRQ_ENABLE, G0Q_S2_IRQ_STATUS, G0Q_S2_AUTO_HIBERNATE,
	G0Q_S2_RESET_OUTPUT, G0Q_S2_RESET_HIGH,
};
struct g0q_stage2_diag {
	u32 site, checks;
};

static inline int g0q_stage2_error(struct g0q_stage2_diag *diag,
				 u32 component, u32 operation, int rc)
{
	if (diag && component && rc)
		diag->site = (component << 8) | operation;
	return rc;
}

static inline bool g0q_stage2_condition(struct g0q_stage2_diag *diag,
				      unsigned int bit, u32 value)
{
	if (diag) {
		diag->checks |= 1U << bit;
		if (value)
			diag->checks |= 1U << (bit + 11);
		if (bit == G0Q_S2_HCS)
			diag->checks |= value << 22;
	}
	return value != 0;
}

struct g0q_link {
	struct g0q_waipio hw;
	u32 version;
	u32 before, interrupt, result, after;
	unsigned int local_commands;
	bool hce_started, link_issued;
};

int g0q_hci_quiescent(struct g0q_link *link);
int g0q_hci_quiescent_observed(struct g0q_link *link, struct g0q_stage2_diag *diag);
int g0q_hci_link_once(struct g0q_link *link, unsigned long core_hz,
		      unsigned long unipro_hz);
#endif
