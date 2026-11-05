// SPDX-License-Identifier: GPL-2.0-only
#ifndef ML030_WAIPIO_PHY_H
#define ML030_WAIPIO_PHY_H

#include <linux/types.h>

struct g0q_waipio {
	void __iomem *hci;
	void __iomem *phy;
	u64 deadline_ns;
	bool analog_started;
	bool calibration_started;
	bool pcs_ready;
};

int g0q_phy_analog_on(struct g0q_waipio *ctx);
int g0q_phy_calibrate(struct g0q_waipio *ctx, unsigned int controller_major);

#endif
