// SPDX-License-Identifier: GPL-2.0-only
/* Compiled only with the private, byte-matched FYG8 PHY tables.
 * Caller owns the powered HCI/PHY windows, global one-shot and board rails.
 * There is no bus registration, module entry point, or device file here.
 */
#include <linux/delay.h>
#include <linux/errno.h>
#include <linux/io.h>
#include <linux/ktime.h>

#include "waipio_phy.h"
#include "phy-qcom-ufs-qmp-v4-waipio.h"

#define G0Q_HCI_CFG1 0xdc
#define G0Q_PHY_RESET BIT(1)

static int budget(const struct g0q_waipio *ctx)
{
	return ktime_get_boottime_ns() < ctx->deadline_ns ? 0 : -ETIMEDOUT;
}

static int set_phy_reset(struct g0q_waipio *ctx, bool asserted)
{
	u32 value;

	if (budget(ctx))
		return -ETIMEDOUT;
	value = readl(ctx->hci + G0Q_HCI_CFG1);
	if (asserted)
		value |= G0Q_PHY_RESET;
	else
		value &= ~G0Q_PHY_RESET;
	writel(value, ctx->hci + G0Q_HCI_CFG1);
	if ((readl(ctx->hci + G0Q_HCI_CFG1) & G0Q_PHY_RESET) != (value & G0Q_PHY_RESET))
		return -EIO;
	usleep_range(1000, 1100);
	return budget(ctx);
}

static int apply_table(struct g0q_waipio *ctx,
		       const struct ufs_qcom_phy_calibration *table, size_t count)
{
	for (size_t i = 0; i < count; i++) {
		if (budget(ctx))
			return -ETIMEDOUT;
		writel_relaxed(table[i].cfg_value, ctx->phy + table[i].reg_offset);
	}
	return 0;
}

int g0q_phy_analog_on(struct g0q_waipio *ctx)
{
	/* Stock order: L5 is held here. L6 and reference clocks come afterwards. */
	const unsigned int offsets[] = { QSERDES_RX0_RX_INTERFACE_MODE, QSERDES_RX1_RX_INTERFACE_MODE };

	if (ctx->analog_started)
		return -EALREADY;
	if (budget(ctx))
		return -ETIMEDOUT;
	ctx->analog_started = true;
	for (size_t i = 0; i < ARRAY_SIZE(offsets); i++) {
		u32 value = readl_relaxed(ctx->phy + offsets[i]);

		writel_relaxed(value & ~QSERDES_RX_INTERFACE_MODE_CLOCK_EDGE_BIT,
			       ctx->phy + offsets[i]);
	}
	mb();
	writel_relaxed(1, ctx->phy + UFS_PHY_POWER_DOWN_CONTROL);
	mb();
	return budget(ctx);
}

int g0q_phy_calibrate(struct g0q_waipio *ctx, unsigned int controller_major)
{
	int err;
	u32 value;
	u64 end;

	if (!ctx->analog_started || ctx->calibration_started)
		return -EPERM;
	/* The retained g0q has two lanes, default Rate B, and no submode override.
	 * Pin the v4 host branch for this first experiment. Other revisions stop.
	 */
	if (controller_major != 4)
		return -ENODEV;
	ctx->calibration_started = true;
	err = set_phy_reset(ctx, true);
	if (err)
		return err;

	writel_relaxed(1, ctx->phy + UFS_PHY_SW_RESET);
	wmb();
	err = apply_table(ctx, phy_cal_table_rate_A, ARRAY_SIZE(phy_cal_table_rate_A));
	if (!err)
		err = apply_table(ctx, phy_cal_table_2nd_lane, ARRAY_SIZE(phy_cal_table_2nd_lane));
	if (!err)
		err = apply_table(ctx, phy_cal_table_rate_B, ARRAY_SIZE(phy_cal_table_rate_B));
	if (err)
		return err;
	writel_relaxed(0, ctx->phy + UFS_PHY_SW_RESET);
	wmb();
	err = set_phy_reset(ctx, false);
	if (err)
		return err;

	value = readl_relaxed(ctx->phy + UFS_PHY_PHY_START);
	writel_relaxed(value | BIT(0), ctx->phy + UFS_PHY_PHY_START);
	mb();
	end = min(ctx->deadline_ns, ktime_get_boottime_ns() + NSEC_PER_SEC);
	while (ktime_get_boottime_ns() < end) {
		value = readl(ctx->phy + UFS_PHY_PCS_READY_STATUS);
		if (value & BIT(0)) {
			err = budget(ctx);
			if (!err)
				ctx->pcs_ready = true;
			return err;
		}
		usleep_range(10, 20);
	}
	return -ETIMEDOUT;
}
