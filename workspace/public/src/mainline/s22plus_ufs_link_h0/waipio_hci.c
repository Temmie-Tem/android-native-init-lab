// SPDX-License-Identifier: GPL-2.0-only
/* Fixed v4 g0q bootstrap. No SCSI host, IRQ handler, descriptors or data doorbells. */
#include <linux/bitfield.h>
#include <linux/delay.h>
#include <linux/errno.h>
#include <linux/io.h>
#include <linux/ktime.h>
#include <ufs/ufshci.h>
#include <ufs/unipro.h>
#include "waipio_hci.h"
#include "reset-pin.h"

/* UCRDY gates enabled UIC submission; it is not a disabled-state hazard.
 * V8 changes only its membership in the existing disabled-state masks.
 * Exact HCE, device-present/error, list, interrupt and later ready checks stay.
 */
#if defined(G0Q_DISABLED_UCRDY) && !defined(G0Q_RESET_CONFIG)
#error "Disabled UCRDY semantics require the dedicated-reset handoff mode"
#endif
#ifdef G0Q_DISABLED_UCRDY
#define G0Q_DISABLED_UCRDY_MASK 0U
#else
#define G0Q_DISABLED_UCRDY_MASK UIC_COMMAND_READY
#endif

#if defined(G0Q_STALE_UCCS_ACK) && !defined(G0Q_DISABLED_UCRDY)
#error "Initial completion acknowledgement requires the V8 handoff mode"
#endif

#define HCI_CFG1 0xdc
#define HCI_HW_VERSION 0xe4
#define PHY_LINECFG_DISABLE 0xd48
#define UNI_CORE_CLK 0xd002
#define UNI_40NS 0x9007

static int budget(struct g0q_link *link)
{
	return ktime_get_boottime_ns() < link->hw.deadline_ns ? 0 : -ETIMEDOUT;
}

bool g0q_stage2_read_condition(struct g0q_stage2_diag *diag,
		unsigned int bit, void __iomem *reg, u32 mask, u32 expected)
{
	u32 raw = readl(reg);
	u32 failure = expected ? ((raw & mask) != expected) : (raw & mask);

#ifdef G0Q_STALE_UCCS_ACK
	/* Admit only the exact initial completion already seen before a timely
	 * stop. Finish AHIT and both pin predicates before the separate effect.
	 * NULL diagnostics (stage six) and the cold path keep strict IS == 0.
	 */
	if (diag && bit == G0Q_S2_IRQ_STATUS && raw == UIC_COMMAND_COMPL &&
	    diag->handoff_flags == 8191 && diag->pre_is == UIC_COMMAND_COMPL) {
		diag->checks |= G0Q_ACK_PENDING;
		failure = 0;
	}
#endif
#ifdef G0Q_HCE_HANDOFF
	if (diag && failure) {
		diag->refusal_index = bit + 1;
		diag->refusal_raw = raw;
	}
#endif
#ifdef G0Q_DISABLED_UCRDY
	/* Same sample, existing diagnostic slot: readiness is data, not failure. */
	if (diag && bit == G0Q_S2_HCS)
		diag->checks |= (raw & UIC_COMMAND_READY) << 22;
#endif
	return g0q_stage2_condition(diag, bit, failure);
}

#ifdef G0Q_HCE_HANDOFF
static int handoff_failure(struct g0q_stage2_diag *diag, u32 operation,
		int rc, u32 index, u32 value)
{
	diag->refusal_index = index;
	diag->refusal_raw = value;
	return g0q_stage2_error(diag, G0Q_S2_HCI, operation, rc);
}

static int handoff_sample(struct g0q_link *link, struct g0q_stage2_diag *diag,
		void __iomem *reg, u32 flag, u32 *value)
{
	if (budget(link))
		return handoff_failure(diag, G0Q_S2_HANDOFF_DEADLINE, -ETIMEDOUT, 0, 0);
	*value = readl(reg);
	diag->handoff_flags |= flag;
	return 0;
}

static u64 handoff_time(struct g0q_stage2_diag *diag, u64 start)
{
	u64 now = ktime_get_boottime_ns();
	diag->handoff_elapsed_us = min((now - start) / 1000, 4095ULL);
	return now;
}

/* Separate admission for a known enabled controller. No list, interrupt,
 * AHIT or status write; a timeout never retries or re-enables the controller.
 * Only stage two with a real diagnostic record can call this function.
 */
static int hce_handoff(struct g0q_link *link, struct g0q_stage2_diag *diag, u32 *hce)
{
	void __iomem *hci = link->hw.hci;
	u64 now, until;
	u32 value;
	int rc;

	if (link->handoff_taken)
		return handoff_failure(diag, G0Q_S2_HANDOFF_STATE, -EALREADY, 0, 0);
	rc = handoff_sample(link, diag, hci + REG_CONTROLLER_ENABLE, G0Q_HO_HCE, &value);
	if (rc)
		return rc;
	diag->pre_hce = value;
	if (!value) {
		*hce = value;
		return 0;
	}
	if (value != CONTROLLER_ENABLE)
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 1, value);
	rc = handoff_sample(link, diag, hci + REG_CONTROLLER_STATUS, G0Q_HO_HCS, &value);
	if (rc)
		return rc;
	diag->pre_hcs = value;
	if (!(value & UIC_COMMAND_READY) || value & (HOST_ERROR_INDICATOR | DEVICE_ERROR_INDICATOR))
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 2, value);
	rc = handoff_sample(link, diag, hci + REG_UTP_TRANSFER_REQ_DOOR_BELL, G0Q_HO_TRANSFER, &value);
	if (rc)
		return rc;
	if (value)
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 3, value);
	rc = handoff_sample(link, diag, hci + REG_UTP_TASK_REQ_DOOR_BELL, G0Q_HO_TASK, &value);
	if (rc)
		return rc;
	if (value)
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 4, value);
	rc = handoff_sample(link, diag, hci + REG_INTERRUPT_ENABLE, G0Q_HO_IE, &value);
	if (rc)
		return rc;
	if (value)
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 7, value);
	rc = handoff_sample(link, diag, hci + REG_INTERRUPT_STATUS, G0Q_HO_IS, &value);
	if (rc)
		return rc;
	diag->pre_is = value;
	if (value & ~UIC_COMMAND_COMPL)
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 8, value);
	rc = handoff_sample(link, diag, link->reset_io, G0Q_HO_PIN_OUTPUT, &value);
	if (rc)
		return rc;
	if (!g0q_reset_ctl_admitted(value))
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 10, value);
	rc = handoff_sample(link, diag, link->reset_io + 4, G0Q_HO_PIN_HIGH, &value);
	if (rc)
		return rc;
	if (!(value & BIT(0)))
		return handoff_failure(diag, G0Q_S2_HANDOFF_ADMISSION, -EBUSY, 11, value);
	rc = handoff_sample(link, diag, hci + REG_CONTROLLER_ENABLE, G0Q_HO_FINAL_HCE, &value);
	if (rc)
		return rc;
	diag->last_hce = value;
	if (value != CONTROLLER_ENABLE)
		return handoff_failure(diag, G0Q_S2_HANDOFF_DRIFT, -EBUSY, 1, value);
	now = ktime_get_boottime_ns();
	if (now >= link->hw.deadline_ns)
		return handoff_failure(diag, G0Q_S2_HANDOFF_DEADLINE, -ETIMEDOUT, 0, 0);
	/* Retained ufshcd_hba_stop uses a 10-us interval and a 1-ms limit.
	 * This owner rejects late completion and never repeats its single write.
	 */
	until = min(link->hw.deadline_ns, now + NSEC_PER_MSEC);
	link->handoff_taken = true;
	diag->handoff_flags |= G0Q_HO_ISSUED;
	writel(0, hci + REG_CONTROLLER_ENABLE);
	for (;;) {
		if (handoff_time(diag, now) >= until)
			return handoff_failure(diag, G0Q_S2_HANDOFF_TIMEOUT, -ETIMEDOUT, 0, 0);
		value = readl(hci + REG_CONTROLLER_ENABLE);
		diag->handoff_polls++;
		diag->last_hce = value;
		diag->handoff_flags |= G0Q_HO_READBACK;
		if (!value)
			diag->handoff_flags |= G0Q_HO_ZERO;
		if (handoff_time(diag, now) >= until)
			return handoff_failure(diag, G0Q_S2_HANDOFF_TIMEOUT, -ETIMEDOUT, 0, 0);
		if (!value) {
			diag->handoff_flags |= G0Q_HO_TIMELY;
			*hce = value;
			return 0;
		}
		if (value != CONTROLLER_ENABLE)
			return handoff_failure(diag, G0Q_S2_HANDOFF_STATE, -EIO, 1, value);
		usleep_range(10, 20);
	}
}
#endif

static u32 observed_hce(struct g0q_link *link, struct g0q_stage2_diag *diag)
{
	u32 value = readl(link->hw.hci + REG_CONTROLLER_ENABLE);
	(void)diag; /* Used only by the separately compiled V5 snapshot branch. */

#ifdef G0Q_HCI_SNAPSHOT
	if (diag) {
		static const u32 offsets[] = {
			REG_CONTROLLER_STATUS, REG_UTP_TRANSFER_REQ_DOOR_BELL,
			REG_UTP_TASK_REQ_DOOR_BELL, REG_INTERRUPT_ENABLE,
			REG_INTERRUPT_STATUS,
		};
		diag->raw[0] = value;
		diag->captured = 1;
		/* This branch still refuses HCE != 0. Only defined HCE states
		 * admit the five fixed reads; each consumes the original budget.
		 * No UIC error (read-clear), PHY, list pointer or reset-pin read.
		 * No write, retry, return eligibility or predicate is added.
		 */
		if (value && !(value & ~3U)) {
			for (unsigned int i = 0; i < 5; i++) {
				if (budget(link))
					break;
				diag->raw[i + 1] = readl(link->hw.hci + offsets[i]);
				diag->captured |= 1U << (i + 1);
			}
		}
	}
#endif
	return value;
}

int g0q_hci_quiescent_observed(struct g0q_link *link, struct g0q_stage2_diag *diag)
{
	void __iomem *hci = link->hw.hci;
	u32 version, hce;

	if (budget(link))
		return g0q_stage2_error(diag, G0Q_S2_HCI, G0Q_S2_DEADLINE, -ETIMEDOUT);
	version = readl(hci + REG_UFS_VERSION);
	/* The fixed legacy request/task lists do not cover UFSHCI 4 MCQ. */
	if (version < 0x200 || version > 0x310)
		return g0q_stage2_error(diag, G0Q_S2_HCI, G0Q_S2_UFS_VERSION, -ENODEV);
	link->version = readl(hci + HCI_HW_VERSION);
	if ((link->version >> 28) != 4)
		return g0q_stage2_error(diag, G0Q_S2_HCI, G0Q_S2_HW_VERSION, -ENODEV);
#ifdef G0Q_HCE_HANDOFF
	if (diag) {
		int rc = hce_handoff(link, diag, &hce);
		if (rc)
			return rc;
	} else
#endif
		hce = observed_hce(link, diag);
	/* Preserve short-circuit evaluation and the original read order. */
	if (g0q_stage2_condition(diag, G0Q_S2_HCE, hce) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_HCS, hci + REG_CONTROLLER_STATUS,
	     DEVICE_PRESENT | G0Q_DISABLED_UCRDY_MASK | HOST_ERROR_INDICATOR | DEVICE_ERROR_INDICATOR, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_TRANSFER_DOORBELL, hci + REG_UTP_TRANSFER_REQ_DOOR_BELL, ~0U, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_TASK_DOORBELL, hci + REG_UTP_TASK_REQ_DOOR_BELL, ~0U, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_TRANSFER_RUN, hci + REG_UTP_TRANSFER_REQ_LIST_RUN_STOP, ~0U, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_TASK_RUN, hci + REG_UTP_TASK_REQ_LIST_RUN_STOP, ~0U, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_IRQ_ENABLE, hci + REG_INTERRUPT_ENABLE, ~0U, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_IRQ_STATUS, hci + REG_INTERRUPT_STATUS, ~0U, 0) ||
	    g0q_stage2_read_condition(diag, G0Q_S2_AUTO_HIBERNATE, hci + REG_AUTO_HIBERNATE_IDLE_TIMER, ~0U, 0))
		return g0q_stage2_error(diag, G0Q_S2_HCI, G0Q_S2_QUIESCENT, -EBUSY);
	return 0;
}

int g0q_hci_quiescent(struct g0q_link *link)
{
	/* The later pre-link check must not overwrite stage-two evidence. */
	return g0q_hci_quiescent_observed(link, NULL);
}

#ifdef G0Q_STALE_UCCS_ACK
int g0q_hci_ack_initial(struct g0q_link *link, struct g0q_stage2_diag *diag)
{
	void __iomem *hci = link->hw.hci;
	u32 value;

	/* The board owns this latch for the module lifetime. Reload/reboot is
	 * bounded separately by the one-permit owner, never by this RAM latch.
	 */
	if (link->initial_ack_taken)
		return -EALREADY;
	if (!diag)
		return -EPERM;
	if (!(diag->checks & G0Q_ACK_PENDING))
		return 0;
	if ((diag->checks & ~(UIC_COMMAND_READY << 22)) != (G0Q_ACK_PENDING | 0x7ff) ||
	    diag->site || diag->handoff_flags != 8191 || diag->pre_is != UIC_COMMAND_COMPL)
		return -EPERM;
	if (budget(link))
		return handoff_failure(diag, G0Q_S2_ACK_DEADLINE, -ETIMEDOUT, 0, 0);
	value = readl(hci + REG_CONTROLLER_ENABLE);
	if (value)
		return handoff_failure(diag, G0Q_S2_ACK_DRIFT, -EBUSY, 1, value);
	if (budget(link))
		return handoff_failure(diag, G0Q_S2_ACK_DEADLINE, -ETIMEDOUT, 0, 0);
	value = readl(hci + REG_INTERRUPT_STATUS);
	if (value != UIC_COMMAND_COMPL)
		return handoff_failure(diag, G0Q_S2_ACK_DRIFT, -EBUSY, 8, value);
	if (budget(link))
		return handoff_failure(diag, G0Q_S2_ACK_DEADLINE, -ETIMEDOUT, 0, 0);
	/* These nearby reads are not an atomic hardware snapshot. No locking,
	 * polling, RMW, fault-bit clearing or second store is introduced.
	 */
	link->initial_ack_taken = true;
	diag->checks |= G0Q_ACK_ISSUED;
	writel(UIC_COMMAND_COMPL, hci + REG_INTERRUPT_STATUS);
	if (budget(link))
		return handoff_failure(diag, G0Q_S2_ACK_DEADLINE, -ETIMEDOUT, 0, 0);
	value = readl(hci + REG_INTERRUPT_STATUS);
	diag->checks |= G0Q_ACK_READBACK;
	if (!value)
		diag->checks |= G0Q_ACK_ZERO;
	if (budget(link))
		return handoff_failure(diag, G0Q_S2_ACK_DEADLINE, -ETIMEDOUT, 8, value);
	if (value)
		return handoff_failure(diag, G0Q_S2_ACK_READBACK, -EIO, 8, value);
	return 0;
}
#endif

static int command(struct g0q_link *link, u32 opcode, u32 attribute, u32 argument,
		   u32 *response)
{
	void __iomem *hci = link->hw.hci;
	u32 before, status, code, after;
	u64 until;

	if (budget(link))
		return -ETIMEDOUT;
	before = readl(hci + REG_CONTROLLER_STATUS);
	if ((before & (DEVICE_PRESENT | UIC_COMMAND_READY | HOST_ERROR_INDICATOR |
		       DEVICE_ERROR_INDICATOR)) != UIC_COMMAND_READY ||
	    readl(hci + REG_INTERRUPT_STATUS) || readl(hci + REG_INTERRUPT_ENABLE))
		return -EBUSY;
	if (link->link_issued)
		return -EALREADY;
	writel(attribute << 16, hci + REG_UIC_COMMAND_ARG_1);
	writel(0, hci + REG_UIC_COMMAND_ARG_2);
	writel(argument, hci + REG_UIC_COMMAND_ARG_3);
	if (budget(link))
		return -ETIMEDOUT;
	if (opcode == UIC_CMD_DME_LINK_STARTUP) {
		link->before = before;
		link->link_issued = true;
	} else {
		link->local_commands++;
	}
	writel(opcode, hci + REG_UIC_COMMAND);

	until = min(link->hw.deadline_ns, ktime_get_boottime_ns() + 500 * NSEC_PER_MSEC);
	while (ktime_get_boottime_ns() < until) {
		status = readl(hci + REG_INTERRUPT_STATUS);
		if (status & ~(UIC_COMMAND_COMPL |
			       (link->link_issued ? UIC_LINK_STARTUP : 0)))
			return -EIO;
		if (status & UIC_COMMAND_COMPL) {
			code = readl(hci + REG_UIC_COMMAND_ARG_2) & 0xff;
			after = readl(hci + REG_CONTROLLER_STATUS);
			if (link->link_issued) {
				link->interrupt = status;
				link->result = code;
				link->after = after;
			}
			if (code || (after & (HOST_ERROR_INDICATOR | DEVICE_ERROR_INDICATOR)) ||
			    !!(after & DEVICE_PRESENT) != link->link_issued)
				return -EIO;
			if (response)
				*response = readl(hci + REG_UIC_COMMAND_ARG_3);
			/* Only consume our own local completion. Preserve terminal link status. */
			if (!link->link_issued) {
				writel(UIC_COMMAND_COMPL, hci + REG_INTERRUPT_STATUS);
				if (readl(hci + REG_INTERRUPT_STATUS))
					return -EBUSY;
			}
			return budget(link);
		}
		usleep_range(20, 40);
	}
	return -ETIMEDOUT;
}

static int set_timers(struct g0q_link *link)
{
	u32 value, stock, upstream;
	int err = command(link, UIC_CMD_DME_GET, UNI_CORE_CLK, 0, &value);

	if (err)
		return err;
	/* FYG8 shifts the whole intermediate register. Upstream updates the v4
	 * field in place. Proceed only when the actual register agrees on the write.
	 */
	stock = (((value & ~0xfffU) | 300U) << 16) & ~BIT(8);
	upstream = (value & ~(GENMASK(27, 16) | BIT(8))) | (300U << 16);
	if (stock != upstream)
		return -EOPNOTSUPP;
	err = command(link, UIC_CMD_DME_SET, UNI_CORE_CLK, stock, NULL);
	if (err)
		return err;
	err = command(link, UIC_CMD_DME_GET, UNI_40NS, 0, &value);
	if (err)
		return err;
	stock = (value & ~0xfU) | 12U;
	if (stock != ((value & ~0x7fU) | 12U))
		return -EOPNOTSUPP;
	return command(link, UIC_CMD_DME_SET, UNI_40NS, stock, NULL);
}

int g0q_hci_link_once(struct g0q_link *link, unsigned long core_hz,
		      unsigned long unipro_hz)
{
	void __iomem *hci = link->hw.hci;
	u32 value;
	u64 until;
	int err;

	if (link->hce_started || !link->hw.pcs_ready)
		return -EPERM;
	if (core_hz != 300000000 || unipro_hz != 300000000)
		return -ERANGE;
	err = g0q_hci_quiescent(link);
	if (err)
		return err;
	if (!(readl(link->hw.phy + 0xd80) & BIT(0)) || readl(hci + REG_CONTROLLER_ENABLE) ||
	    (readl(hci + REG_CONTROLLER_STATUS) & (G0Q_DISABLED_UCRDY_MASK | DEVICE_PRESENT)))
		return -EBUSY;
	link->hce_started = true;
	writel(readl(hci + HCI_CFG1) | BIT(0), hci + HCI_CFG1);
	if (!(readl(hci + HCI_CFG1) & BIT(0)) || budget(link))
		return -EIO;
	writel(CONTROLLER_ENABLE, hci + REG_CONTROLLER_ENABLE);
	until = min(link->hw.deadline_ns, ktime_get_boottime_ns() + 50 * NSEC_PER_MSEC);
	/* FYG8 and mainline wait 1 ms before polling the 1 -> 0 -> 1 HCE transition. */
	usleep_range(1000, 1100);
	do {
		if (ktime_get_boottime_ns() >= until)
			return -ETIMEDOUT;
		if (readl(hci + REG_CONTROLLER_ENABLE) == CONTROLLER_ENABLE &&
		    (readl(hci + REG_CONTROLLER_STATUS) & UIC_COMMAND_READY))
			break;
		usleep_range(100, 200);
	} while (true);

	err = command(link, UIC_CMD_DME_GET, 0x41, 0, &value);
	if (err || value != 1)
		return err ? err : -EAGAIN;
	writel(300, hci + 0xc0);
	if (readl(hci + 0xc0) != 300)
		return -EIO;
	value = readl(link->hw.phy + PHY_LINECFG_DISABLE);
	writel(value & ~BIT(1), link->hw.phy + PHY_LINECFG_DISABLE);
	err = set_timers(link);
	if (err)
		return err;
	/* The Waipio boot driver disables the UTP ICE config check for non-SCSI
	 * commands. No ICE aperture, key, crypto-enable bit or data path is used.
	 */
	writel(readl(hci + HCI_CFG1) | BIT(31), hci + HCI_CFG1);
	if (!(readl(hci + HCI_CFG1) & BIT(31)))
		return -EIO;
	err = command(link, UIC_CMD_DME_SET, PA_LOCAL_TX_LCC_ENABLE, 0, NULL);
	if (err)
		return err;
	return command(link, UIC_CMD_DME_LINK_STARTUP, 0, 0, NULL);
}
