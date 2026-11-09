// SPDX-License-Identifier: GPL-2.0-only
/* S22+ late cold-link component under H0 development. No physical admission. */
#include <linux/clk.h>
#include <linux/clk-provider.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <linux/reset.h>
#include <soc/qcom/g0q-ml030.h>
#include "waipio_hci.h"
#include "overlay-data.h"
#include "usb-admission.h"

extern int ml030_register_rails(void);
extern void ml030_open_rail_requests(void);

struct board {
	struct g0q_link link;
	void __iomem *reset_io;
	struct clk *core, *unipro, *ref, *aggr, *iface;
	struct regulator *analog, *pll, *vcc, *vccq, *pad, *parent;
	struct reset_control *reset;
	struct device *dev;
};

static struct board board;
static int operation_rc = -EINPROGRESS;
static unsigned int stage;
static atomic_t probe_taken = ATOMIC_INIT(0);
static struct g0q_rpmh_report power;
static bool usb_covered, usb_released;
static u32 usb_reason, usb_detail;

static int remaining(void)
{
	return g0q_rpmh_remaining();
}

static int report(char *buf, const struct kernel_param *kp)
{
	struct g0q_link *link = &board.link;

	return scnprintf(buf, PAGE_SIZE, "%d %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %d %u %u %u %u\n",
			 operation_rc, stage, link->version, link->hw.pcs_ready,
			 link->local_commands, link->link_issued, link->before,
			 link->interrupt, link->result, link->after, link->hce_started,
			 power.records, power.claimed, power.triggered, power.acknowledged,
			 power.reclaimed, power.error, usb_covered, usb_released,
			 usb_reason, usb_detail);
}
static const struct kernel_param_ops report_ops = { .get = report };
module_param_cb(result, &report_ops, NULL, 0444);

static void __iomem *window(struct platform_device *pdev, const char *name,
			    resource_size_t base, resource_size_t size)
{
	struct resource *reg = platform_get_resource_byname(pdev, IORESOURCE_MEM, name);

	if (!reg || reg->start != base || resource_size(reg) != size)
		return ERR_PTR(-ENODEV);
	return devm_ioremap_resource(&pdev->dev, reg);
}

static int clock_on(const char *name, struct clk **held)
{
	struct clk *clk = devm_clk_get(board.dev, name);
	int rc;

	if (IS_ERR_OR_NULL(clk))
		return clk ? PTR_ERR(clk) : -ENODEV;
	if (remaining())
		return -ETIMEDOUT;
	rc = clk_prepare_enable(clk);
	if (!rc && held)
		*held = clk;
	return rc;
}

static int supply(const char *name, int min_uv, int max_uv, int load,
		  struct regulator **held)
{
	struct regulator *reg = devm_regulator_get_optional(board.dev, name);
	int rc;

	if (IS_ERR(reg))
		return PTR_ERR(reg);
	if (remaining())
		return -ETIMEDOUT;
	rc = regulator_set_load(reg, load);
	if (rc)
		return rc;
	if (min_uv) {
		if (remaining())
			return -ETIMEDOUT;
		rc = regulator_set_voltage(reg, min_uv, max_uv);
		if (rc)
			return rc;
	}
	if (remaining())
		return -ETIMEDOUT;
	rc = regulator_enable(reg);
	if (rc)
		return rc;
	*held = reg;
	if (min_uv) {
		rc = regulator_get_voltage(reg);
		if (rc < min_uv || rc > max_uv)
			return -ERANGE;
	}
	return remaining();
}

static int access_power(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	int rc;

	if (remaining())
		return -ETIMEDOUT;
	pm_runtime_enable(dev);
	rc = pm_runtime_resume_and_get(dev);
	if (rc < 0)
		return rc;
	if (remaining())
		return -ETIMEDOUT;
	/* CPU config traffic is already covered by the held apps-usb SH1/CN0
	 * votes. No generic ICC request, batch invalidation or rollback is issued.
	 */
	rc = clock_on("iface_clk", &board.iface);
	if (!rc)
		rc = clock_on("bus_aggr_clk", &board.aggr);
	if (!rc)
		rc = clock_on("core_clk", &board.core);
	if (!rc)
		rc = clock_on("core_clk_unipro", &board.unipro);
	if (!rc)
		rc = clock_on("ref_clk", &board.ref);
	return rc;
}

static int rate(struct clk *clk)
{
	int rc;

	if (remaining())
		return -ETIMEDOUT;
	rc = clk_set_rate(clk, 300000000);
	if (rc)
		return rc;
	return clk_get_rate(clk) == 300000000 ? 0 : -ERANGE;
}

static int host_supplies(void)
{
	int rc = supply("vcc", 2504000, 2504000, 1100000, &board.vcc);

	if (!rc)
		rc = supply("vccq", 1200000, 1200000, 1200000, &board.vccq);
	if (!rc)
		rc = supply("ref-pad", 1200000, 1200000, 100, &board.pad);
	if (!rc) {
		/* The stock provider initial vote is 1.256 V. The separate UFS
		 * parent consumer carries load/enable without a voltage request.
		 */
		struct regulator *seed = devm_regulator_get_optional(board.dev, "parent");

		if (IS_ERR(seed))
			return PTR_ERR(seed);
		if (remaining())
			return -ETIMEDOUT;
		rc = regulator_set_voltage(seed, 1256000, 1256000);
		if (!rc)
			rc = supply("parent", 0, 0, 210000, &board.parent);
		if (!rc && regulator_get_voltage(board.parent) != 1256000)
			rc = -ERANGE;
	}
	return rc;
}

static int reset_host_and_device(void)
{
	u32 pin;
	int rc;

	if (remaining())
		return -ETIMEDOUT;
	/* Claim the dedicated UFS output only. No generic TLMM driver or CTL write. */
	pin = readl(board.reset_io + 4);
	if (!(readl(board.reset_io) & BIT(31)) || !(pin & BIT(0)))
		return -EBUSY;
	rc = reset_control_assert(board.reset);
	if (rc)
		return rc;
	usleep_range(200, 210);
	rc = reset_control_deassert(board.reset);
	if (rc)
		return rc;
	usleep_range(1000, 1100);
	if (remaining())
		return -ETIMEDOUT;
	pin = readl(board.reset_io + 4);
	if (!(readl(board.reset_io) & BIT(31)) || !(pin & BIT(0)))
		return -EBUSY;
	writel(pin & ~BIT(0), board.reset_io + 4);
	/* Always release the single pulse even if its readback fails. */
	rc = (readl(board.reset_io + 4) & BIT(0)) ? -EIO : 0;
	usleep_range(10, 15);
	writel(readl(board.reset_io + 4) | BIT(0), board.reset_io + 4);
	if (!(readl(board.reset_io + 4) & BIT(0)))
		rc = -EIO;
	usleep_range(10, 15);
	return rc ? rc : remaining();
}

static int phy_on(void)
{
	struct regulator *usb = devm_regulator_get_optional(board.dev, "vdda-phy");
	int rc, uv;

	if (IS_ERR(usb))
		return PTR_ERR(usb);
	/* L5 is already held by the proven USB path. Refuse to change its voltage. */
	uv = regulator_get_voltage(usb);
	if (regulator_is_enabled(usb) <= 0 || uv < 880000 || uv > 888000 ||
	    regulator_get_mode(usb) != REGULATOR_MODE_NORMAL)
		return -ERANGE;
	if (remaining())
		return -ETIMEDOUT;
	rc = regulator_set_load(usb, 173000);
	if (!rc && !remaining())
		rc = regulator_enable(usb);
	if (!rc)
		rc = remaining();
	if (!rc && (regulator_get_mode(usb) != REGULATOR_MODE_NORMAL ||
		    regulator_get_voltage(usb) != uv))
		rc = -ERANGE;
	if (!rc)
		board.analog = usb;
	if (!rc)
		rc = g0q_phy_analog_on(&board.link.hw);
	if (!rc)
		rc = supply("vdda-pll", 1200000, 1200000, 24900, &board.pll);
	if (!rc)
		rc = clock_on("phy-qref", NULL);
	if (!rc)
		rc = clock_on("phy-ref", NULL);
	if (!rc)
		rc = clock_on("phy-ref_aux", NULL);
	if (!rc)
		rc = g0q_phy_calibrate(&board.link.hw, board.link.version >> 28);
	return rc;
}

static int symbol_lanes(void)
{
	static const char * const names[] = {"ml030-rx0", "ml030-rx1", "ml030-tx0"};
	static const char * const mux_names[] = {"rx0-mux", "rx1-mux", "tx0-mux"};
	static const char * const lane_names[] = {
		"rx_lane0_sync_clk", "rx_lane1_sync_clk", "tx_lane0_sync_clk"
	};
	struct device_node *node __free(device_node) =
		of_find_node_by_path("/soc@0/phy@1d87000");
	struct clk_hw_onecell_data *symbols;
	int rc;

	if (!node || !of_device_is_available(node) ||
	    !of_device_is_compatible(node, "samsung,g0q-ml030-symbol-clocks"))
		return -ENODEV;
	symbols = devm_kzalloc(board.dev, struct_size(symbols, hws, 3), GFP_KERNEL);
	if (!symbols)
		return -ENOMEM;
	symbols->num = 3;
	for (int i = 0; i < 3; i++) {
		if (remaining())
			return -ETIMEDOUT;
		symbols->hws[i] = devm_clk_hw_register_fixed_rate(board.dev, names[i], NULL, 0, 0);
		if (IS_ERR(symbols->hws[i]))
			return PTR_ERR(symbols->hws[i]);
	}
	rc = of_clk_add_hw_provider(node, of_clk_hw_onecell_get, symbols);
	if (rc)
		return rc;
	for (int i = 0; i < 3; i++) {
		struct clk *mux = devm_clk_get(board.dev, mux_names[i]);
		struct clk *parent = devm_clk_hw_get_clk(board.dev, symbols->hws[i], NULL);

		if (IS_ERR_OR_NULL(mux) || IS_ERR_OR_NULL(parent))
			return -ENODEV;
		if (remaining())
			return -ETIMEDOUT;
		rc = clk_set_parent(mux, parent);
		if (rc || !clk_is_match(clk_get_parent(mux), parent))
			return rc ? rc : -EIO;
	}
	/* FYG8 starts rx0, tx0, then rx1 after all three PHY parents are known. */
	static const unsigned int lane_order[] = { 0, 2, 1 };
	for (int i = 0; i < ARRAY_SIZE(lane_order); i++) {
		rc = clock_on(lane_names[lane_order[i]], NULL);
		if (rc)
			return rc;
	}
	return 0;
}

static int run(struct platform_device *pdev)
{
	int rc;

	stage = 1;
	board.dev = &pdev->dev;
	board.link.hw.hci = window(pdev, "hci", 0x1d84000, 0x1000);
	board.link.hw.phy = window(pdev, "phy", 0x1d87000, 0xe10);
	board.reset_io = window(pdev, "reset-pin", 0x0f1de000, 8);
	if (IS_ERR(board.link.hw.hci) || IS_ERR(board.link.hw.phy) || IS_ERR(board.reset_io))
		return -EBUSY;
	board.reset = devm_reset_control_get_exclusive(board.dev, "rst");
	if (IS_ERR(board.reset))
		return PTR_ERR(board.reset);
	rc = access_power(pdev);
	if (rc)
		return rc;
	stage = 2;
	rc = g0q_hci_quiescent(&board.link);
	if (rc)
		return rc;
	if (!(readl(board.reset_io) & BIT(31)) || !(readl(board.reset_io + 4) & BIT(0)))
		return -EBUSY;
	ml030_open_rail_requests();
	rc = rate(board.core);
	if (!rc)
		rc = rate(board.unipro);
	if (!rc)
		rc = host_supplies();
	if (rc)
		return rc;
	stage = 3;
	rc = reset_host_and_device();
	if (rc)
		return rc;
	stage = 4;
	rc = phy_on();
	if (rc)
		return rc;
	stage = 5;
	rc = symbol_lanes();
	if (rc)
		return rc;
	stage = 6;
	if (remaining())
		return -ETIMEDOUT;
	return g0q_hci_link_once(&board.link, clk_get_rate(board.core), clk_get_rate(board.unipro));
}

static int once_probe(struct platform_device *pdev)
{
	if (atomic_cmpxchg(&probe_taken, 0, 1))
		return -EALREADY;
	operation_rc = run(pdev);
	/* Keep the original references and reached state until the attended return.
	 * The probe core must never unwind or schedule another hardware attempt.
	 */
	return 0;
}

static const struct of_device_id matches[] = {
	{ .compatible = "samsung,g0q-ml030-link" }, {}
};
static struct platform_driver link_driver = {
	.driver = {
		.name = "g0q-ml030-link", .of_match_table = matches,
		.probe_type = PROBE_FORCE_SYNCHRONOUS, .suppress_bind_attrs = true,
	},
};

static bool original_board(void)
{
	struct device_node *host __free(device_node) = of_find_node_by_path("/soc@0/ufshc@1d84000");
	struct device_node *phy __free(device_node) = of_find_node_by_path("/soc@0/phy@1d87000");
	struct device_node *gpio __free(device_node) = of_find_node_by_path("/soc@0/pinctrl@f100000");
	struct device_node *present __free(device_node) =
		of_find_compatible_node(NULL, NULL, "samsung,g0q-ml030-link");
	struct device_node *rails __free(device_node) =
		of_find_compatible_node(NULL, NULL, "samsung,g0q-ml030-ufs-rails");

	return host && phy && gpio && !present && !rails &&
		!of_device_is_available(host) && !of_device_is_available(phy) &&
		!of_device_is_available(gpio) &&
		of_device_is_compatible(host, "qcom,sm8450-ufshc") &&
		of_device_is_compatible(phy, "qcom,sm8450-qmp-ufs-phy");
}

static int __init start(void)
{
	struct device *usb = NULL;
	u64 now = ktime_get_boottime_ns();
	int id = 0, rc;

	if (!of_machine_is_compatible("samsung,g0q") || !original_board())
		return -ENODEV;
	if (now < 300ULL * NSEC_PER_SEC || now + 15ULL * NSEC_PER_SEC >= 540ULL * NSEC_PER_SEC)
		return -ETIMEDOUT;
	board.link.hw.deadline_ns = now + 15ULL * NSEC_PER_SEC;
	rc = g0q_rpmh_begin(board.link.hw.deadline_ns);
	if (rc)
		return rc;
	rc = cover_usb(&usb, &usb_reason, &usb_detail, board.link.hw.deadline_ns);
	usb_covered = !rc;
	if (!rc)
		rc = remaining();
	if (!rc)
		rc = of_overlay_fdt_apply(ml030_overlay, sizeof(ml030_overlay), &id, NULL);
	if (!rc)
		rc = remaining();
	if (!rc)
		rc = ml030_register_rails();
	if (!rc)
		rc = remaining();
	if (!rc)
		rc = platform_driver_probe(&link_driver, once_probe);
	if (operation_rc == -EINPROGRESS)
		operation_rc = rc ? rc : -ETIMEDOUT;
	if (!operation_rc)
		operation_rc = remaining();
	if (usb) {
		pm_runtime_put_noidle(usb);
		put_device(usb);
		usb_released = true;
	}
	g0q_rpmh_status(&power);
	g0q_rpmh_end();
	/* Returning 0 retains the one-shot owner and its read-only terminal report. */
	return 0;
}

module_init(start);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("g0q fixed late UFS link H0 candidate");
