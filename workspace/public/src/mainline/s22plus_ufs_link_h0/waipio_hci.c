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

#define HCI_CFG1 0xdc
#define HCI_HW_VERSION 0xe4
#define PHY_LINECFG_DISABLE 0xd48
#define UNI_CORE_CLK 0xd002
#define UNI_40NS 0x9007

static int budget(struct g0q_link *link)
{
	return ktime_get_boottime_ns() < link->hw.deadline_ns ? 0 : -ETIMEDOUT;
}

int g0q_hci_quiescent(struct g0q_link *link)
{
	void __iomem *hci = link->hw.hci;
	u32 version;

	if (budget(link))
		return -ETIMEDOUT;
	version = readl(hci + REG_UFS_VERSION);
	/* The fixed legacy request/task lists do not cover UFSHCI 4 MCQ. */
	if (version < 0x200 || version > 0x310)
		return -ENODEV;
	link->version = readl(hci + HCI_HW_VERSION);
	if ((link->version >> 28) != 4)
		return -ENODEV;
	if (readl(hci + REG_CONTROLLER_ENABLE) ||
	    (readl(hci + REG_CONTROLLER_STATUS) &
	     (DEVICE_PRESENT | UIC_COMMAND_READY | HOST_ERROR_INDICATOR | DEVICE_ERROR_INDICATOR)) ||
	    readl(hci + REG_UTP_TRANSFER_REQ_DOOR_BELL) ||
	    readl(hci + REG_UTP_TASK_REQ_DOOR_BELL) ||
	    readl(hci + REG_UTP_TRANSFER_REQ_LIST_RUN_STOP) ||
	    readl(hci + REG_UTP_TASK_REQ_LIST_RUN_STOP) ||
	    readl(hci + REG_INTERRUPT_ENABLE) || readl(hci + REG_INTERRUPT_STATUS) ||
	    readl(hci + REG_AUTO_HIBERNATE_IDLE_TIMER))
		return -EBUSY;
	return 0;
}

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
	    (readl(hci + REG_CONTROLLER_STATUS) & (UIC_COMMAND_READY | DEVICE_PRESENT)))
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
