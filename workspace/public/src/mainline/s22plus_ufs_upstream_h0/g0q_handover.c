// SPDX-License-Identifier: GPL-2.0-only
/*
 * S22+ roadmap step 4b: hand the g0q UFS controller to the upstream drivers, read-only.
 *
 * One composite module (loaded once by the authenticated observer as g0q_ml030.ko) holds the
 * gated ufshcd core, ufshcd-pltfrm, ufs-qcom, the QMP UFS PHY driver with the g0q board values,
 * and this stage. The stage never opens the private RPMh arena: every rail, interconnect and
 * clock request goes through the ordinary frameworks, limited by the overlay's fixed constraints.
 *
 * Order: board/clock admission (pre-effect, may refuse), register the three drivers, apply the
 * overlay (regulators-9, PHY and host "okay"), wait for probe and the LU scan, read LU0 LBAs 1-3
 * and the fixed test block through the block layer, publish the V18 report and stay resident.
 * The write gate in the core refuses every SCSI or device-management write; its counters are in
 * the report. Nothing is ever written by this stage.
 */
#include <crypto/sha2.h>
#include <linux/blkdev.h>
#include <linux/delay.h>
#include <linux/fs.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/slab.h>
#include <linux/unaligned.h>
#include <scsi/scsi_device.h>
#include <scsi/scsi_host.h>
#include <ufs/ufshcd.h>
#include "overlay-data.h"

#define G0Q_HANDOVER_TAG	0xf0300000U	/* report_modes.tag(18) */
#define G0Q_FLOOR_NS		(60ULL * NSEC_PER_SEC)
#define G0Q_CEILING_NS		(525ULL * NSEC_PER_SEC)
#define G0Q_SETTLE_NS		(120ULL * NSEC_PER_SEC)
#define G0Q_HOST_PATH		"/soc@0/ufshc@1d84000"
#define G0Q_BLOCK		4096U
#define G0Q_TEST_LBA		62305152ULL
#define G0Q_GATE_WORDS		25	/* g0q_ufs_gate.h G0Q_GATE_SNAPSHOT_WORDS */

extern int g0q_ufshcd_core_init(void);
extern int g0q_qmp_ufs_register(void);
extern int g0q_ufs_qcom_register(void);
extern void g0q_gate_snapshot(u32 out[G0Q_GATE_WORDS]);

enum { STEP_NONE, STEP_ADMITTED, STEP_DRIVERS, STEP_OVERLAY, STEP_HBA, STEP_LU0, STEP_GPT, STEP_BLOCK,
       STEP_DONE };

static struct {
	int rc, step;
	u32 start_ms, settle_ms;
	int core_rc, phy_rc, qcom_rc, overlay_rc;
	int hba_state;
	u32 evt[4];			/* PA, DL, link-startup failures, host resets */
	struct ufs_pa_layer_attr pwr;
	u32 spec, manufacturer, devices, lu0_block, lu0_blocks;
	int gpt_rc, block_rc;
	u8 gpt[SHA256_DIGEST_SIZE], block[SHA256_DIGEST_SIZE];
	u32 gate[G0Q_GATE_WORDS];
} out = { .rc = -EINPROGRESS, .hba_state = -1, .gpt_rc = -EINPROGRESS, .block_rc = -EINPROGRESS };

static int report(char *buf, const struct kernel_param *kp)
{
	int n, i;

	g0q_gate_snapshot(out.gate);	/* fresh counters at every read */
	n = scnprintf(buf, PAGE_SIZE, "%d %d %u %u %u %d %d %d %d %d %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %d",
		      out.rc, out.step, G0Q_HANDOVER_TAG, out.start_ms, out.settle_ms, out.core_rc,
		      out.phy_rc, out.qcom_rc, out.overlay_rc, out.hba_state, out.evt[0], out.evt[1],
		      out.evt[2], out.evt[3], out.pwr.gear_rx, out.pwr.gear_tx, out.pwr.lane_rx,
		      out.pwr.lane_tx, out.pwr.pwr_rx, out.pwr.pwr_tx, out.pwr.hs_rate, out.spec,
		      out.manufacturer, out.devices, out.lu0_block, out.lu0_blocks, out.gpt_rc);
	for (i = 0; i < 8; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %u", get_unaligned_be32(out.gpt + 4 * i));
	n += scnprintf(buf + n, PAGE_SIZE - n, " %d", out.block_rc);
	for (i = 0; i < 8; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %u", get_unaligned_be32(out.block + 4 * i));
	for (i = 0; i < G0Q_GATE_WORDS; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %u", out.gate[i]);
	return n + scnprintf(buf + n, PAGE_SIZE - n, "\n");
}

static const struct kernel_param_ops report_ops = { .get = report };
module_param_cb(result, &report_ops, NULL, 0444);

static u32 ms(u64 ns)
{
	return (u32)div_u64(ns, NSEC_PER_MSEC);
}

static u32 clamp_cnt(unsigned long long cnt)
{
	return cnt > U32_MAX ? U32_MAX : (u32)cnt;
}

static int is_disk(struct device *dev, const void *unused)
{
	return dev->class && !strcmp(dev->class->name, "block") && dev->type &&
	       dev->type->name && !strcmp(dev->type->name, "disk");
}

/* The SCSI host's LU 0 disk, with a reference, once sd has registered it. */
static struct gendisk *lu0_disk(struct ufs_hba *hba, struct device **held)
{
	struct scsi_device *sdev = scsi_device_lookup(hba->host, 0, 0, 0);
	struct device *dev;

	*held = NULL;
	if (!sdev)
		return NULL;
	dev = device_find_child(&sdev->sdev_gendev, NULL, is_disk);
	scsi_device_put(sdev);
	if (!dev)
		return NULL;
	if (!get_capacity(dev_to_disk(dev))) {
		put_device(dev);
		return NULL;
	}
	*held = dev;
	return dev_to_disk(dev);
}

static int read_digest(struct file *file, u64 lba, size_t bytes, u8 digest[SHA256_DIGEST_SIZE])
{
	void *buf = kmalloc(bytes, GFP_KERNEL);
	loff_t pos = lba * G0Q_BLOCK;
	ssize_t n;

	if (!buf)
		return -ENOMEM;
	n = kernel_read(file, buf, bytes, &pos);
	if (n == bytes)
		sha256(buf, bytes, digest);
	kfree(buf);
	return n == bytes ? 0 : (n < 0 ? (int)n : -EIO);
}

static void sample(struct ufs_hba *hba)
{
	struct scsi_device *sdev;

	out.hba_state = hba->ufshcd_state;
	out.evt[0] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_PA_ERR].cnt);
	out.evt[1] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_DL_ERR].cnt);
	out.evt[2] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_LINK_STARTUP_FAIL].cnt);
	out.evt[3] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_HOST_RESET].cnt);
	out.pwr = hba->pwr_info;
	out.spec = hba->dev_info.wspecversion;
	out.manufacturer = hba->dev_info.wmanufacturerid;
	out.devices = 0;
	if (hba->host)
		shost_for_each_device(sdev, hba->host)
			out.devices++;
}

static int handover(void)
{
	struct device_node *node;
	struct platform_device *pdev;
	struct ufs_hba *hba = NULL;
	struct gendisk *disk = NULL;
	struct device *held = NULL;
	struct file *file;
	u64 applied, until;
	int id = 0;

	out.core_rc = g0q_ufshcd_core_init();
	out.phy_rc = out.core_rc ? -ECANCELED : g0q_qmp_ufs_register();
	out.qcom_rc = out.phy_rc ? -ECANCELED : g0q_ufs_qcom_register();
	if (out.core_rc || out.phy_rc || out.qcom_rc)
		return -ENODEV;
	out.step = STEP_DRIVERS;

	out.overlay_rc = of_overlay_fdt_apply(ml030_overlay, sizeof(ml030_overlay), &id, NULL);
	if (out.overlay_rc)
		return out.overlay_rc;
	out.step = STEP_OVERLAY;
	applied = ktime_get_boottime_ns();
	until = applied + G0Q_SETTLE_NS;

	node = of_find_node_by_path(G0Q_HOST_PATH);
	pdev = node ? of_find_device_by_node(node) : NULL;
	of_node_put(node);
	if (!pdev)
		return -ENODEV;
	while (ktime_get_boottime_ns() < until) {
		if (!hba && pdev->dev.driver)
			hba = platform_get_drvdata(pdev);
		if (hba && hba->host && (disk = lu0_disk(hba, &held)))
			break;
		msleep(50);
	}
	out.settle_ms = ms(ktime_get_boottime_ns() - applied);
	if (hba) {
		out.step = STEP_HBA;
		sample(hba);
	}
	if (!disk) {
		put_device(&pdev->dev);
		return -ETIMEDOUT;
	}
	out.step = STEP_LU0;
	out.lu0_block = queue_logical_block_size(disk->queue);
	out.lu0_blocks = (u32)min_t(u64, get_capacity(disk) >> 3, U32_MAX);
	file = bdev_file_open_by_dev(disk_devt(disk), BLK_OPEN_READ, NULL, NULL);
	put_device(held);
	put_device(&pdev->dev);
	if (IS_ERR(file))
		return PTR_ERR(file);
	out.gpt_rc = read_digest(file, 1, 3 * G0Q_BLOCK, out.gpt);
	if (!out.gpt_rc)
		out.step = STEP_GPT;
	out.block_rc = read_digest(file, G0Q_TEST_LBA, G0Q_BLOCK, out.block);
	if (!out.gpt_rc && !out.block_rc)
		out.step = STEP_BLOCK;
	fput(file);
	sample(hba);	/* after the reads: final link, error counts and LU count */
	if (out.gpt_rc)
		return out.gpt_rc;
	if (out.block_rc)
		return out.block_rc;
	out.step = STEP_DONE;
	return 0;
}

static atomic_t taken = ATOMIC_INIT(0);

static int __init start(void)
{
	u64 now = ktime_get_boottime_ns();

	/* Pre-effect admission: a refusal unloads the module with nothing registered or applied. */
	if (!of_machine_is_compatible("samsung,g0q"))
		return -ENODEV;
	if (now < G0Q_FLOOR_NS || now + G0Q_SETTLE_NS >= G0Q_CEILING_NS)
		return -ETIMEDOUT;
	if (atomic_cmpxchg(&taken, 0, 1))
		return -EALREADY;
	out.start_ms = ms(now);
	out.step = STEP_ADMITTED;
	out.rc = handover();
	/* Returning 0 keeps the drivers, the gate and the read-only report resident until the return. */
	return 0;
}

module_init(start);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("g0q step-4b upstream UFS handover (read-only, write-gated)");
