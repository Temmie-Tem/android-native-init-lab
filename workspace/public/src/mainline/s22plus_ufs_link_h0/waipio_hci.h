// SPDX-License-Identifier: GPL-2.0-only
#ifndef ML030_WAIPIO_HCI_H
#define ML030_WAIPIO_HCI_H
#include "waipio_phy.h"

struct g0q_link {
	struct g0q_waipio hw;
	u32 version;
	u32 before, interrupt, result, after;
	unsigned int local_commands;
	bool hce_started, link_issued;
};

int g0q_hci_quiescent(struct g0q_link *link);
int g0q_hci_link_once(struct g0q_link *link, unsigned long core_hz,
		      unsigned long unipro_hz);
#endif
