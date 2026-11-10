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
	G0Q_S2_HANDOFF_ADMISSION, G0Q_S2_HANDOFF_DEADLINE,
	G0Q_S2_HANDOFF_DRIFT, G0Q_S2_HANDOFF_TIMEOUT, G0Q_S2_HANDOFF_STATE,
};
enum g0q_stage2_check {
	G0Q_S2_HCE, G0Q_S2_HCS, G0Q_S2_TRANSFER_DOORBELL,
	G0Q_S2_TASK_DOORBELL, G0Q_S2_TRANSFER_RUN, G0Q_S2_TASK_RUN,
	G0Q_S2_IRQ_ENABLE, G0Q_S2_IRQ_STATUS, G0Q_S2_AUTO_HIBERNATE,
	G0Q_S2_RESET_OUTPUT, G0Q_S2_RESET_HIGH,
};
struct g0q_stage2_diag {
	u32 site, checks;
	/* V5 raw captures are separate from the unchanged predicate history.
	 * Order: HCE, HCS, transfer doorbell, task doorbell, IE, IS.
	 */
	u32 captured, raw[6];
	/* V6 is a separate pre-handoff admission, not a failed predicate
	 * overwritten after an effect. checks describes only the actual
	 * post-handoff/cold-path evaluation. Every valid prefix is explicit.
	 * V8 also retains the same-read UCRDY sample in checks bit 25,
	 * independently of its HCS failure bit; older modes keep their meaning.
	 */
	u32 handoff_flags, pre_hce, pre_hcs, pre_is, last_hce;
	u32 refusal_index, refusal_raw;
	u32 handoff_polls, handoff_elapsed_us;
};

static inline u32 g0q_handoff_word(const struct g0q_stage2_diag *diag)
{
	/* The upper fields are diagnostic, saturating lower bounds. They never
	 * drive deadlines or authorize a transition. The live clocks do that.
	 */
	u32 polls = diag->handoff_polls > 127 ? 127 : diag->handoff_polls;
	u32 elapsed = diag->handoff_elapsed_us > 4095 ? 4095 : diag->handoff_elapsed_us;
	return diag->handoff_flags | (polls << 13) | (elapsed << 20);
}

enum g0q_handoff_flag {
	G0Q_HO_HCE = 1U << 0, G0Q_HO_HCS = 1U << 1,
	G0Q_HO_TRANSFER = 1U << 2, G0Q_HO_TASK = 1U << 3,
	G0Q_HO_IE = 1U << 4, G0Q_HO_IS = 1U << 5,
	G0Q_HO_PIN_OUTPUT = 1U << 6, G0Q_HO_PIN_HIGH = 1U << 7,
	G0Q_HO_FINAL_HCE = 1U << 8, G0Q_HO_ISSUED = 1U << 9,
	G0Q_HO_READBACK = 1U << 10, G0Q_HO_ZERO = 1U << 11,
	G0Q_HO_TIMELY = 1U << 12,
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
	void __iomem *reset_io;
	u32 version;
	u32 before, interrupt, result, after;
	unsigned int local_commands;
	bool hce_started, link_issued;
	bool handoff_taken;
};

bool g0q_stage2_read_condition(struct g0q_stage2_diag *diag,
		unsigned int bit, void __iomem *reg, u32 mask, u32 expected);

int g0q_hci_quiescent(struct g0q_link *link);
int g0q_hci_quiescent_observed(struct g0q_link *link, struct g0q_stage2_diag *diag);
int g0q_hci_link_once(struct g0q_link *link, unsigned long core_hz,
		      unsigned long unipro_hz);
#endif
