// SPDX-License-Identifier: GPL-2.0-only
/*
 * S22+ roadmap step 4b: hand the g0q UFS controller to the upstream drivers, read-only.
 *
 * One composite module (loaded once by the authenticated observer as g0q_ml030.ko) holds the
 * gated ufshcd core, ufshcd-pltfrm, ufs-qcom, the QMP UFS PHY driver with the g0q board values,
 * and this stage. The stage never opens the private RPMh arena: every rail, interconnect and
 * clock request goes through the ordinary frameworks, limited by the overlay's fixed constraints.
 *
 * Order: board/clock admission (pre-effect, may refuse); the module init registers the three
 * drivers (init code runs only in init context); one worker thread applies the overlay
 * (regulators-9, PHY and host "okay"), waits for the bound host and an openable LU 0 disk, and
 * reads LU0 LBAs 1-3 and the fixed test block with direct I/O. The worker starts no new step after
 * the budget ends. The module init waits for it for at most the budget from admission, then
 * freezes the report: a late worker can no longer change it. The write gate in the core refuses
 * every SCSI or device-management write; its counters are in the report. Nothing is ever written.
 */
#include <crypto/sha2.h>
#include <linux/blkdev.h>
#include <linux/completion.h>
#include <linux/delay.h>
#include <linux/fcntl.h>
#include <linux/fs.h>
#include <linux/gfp.h>
#include <linux/kthread.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/uio.h>
#include <linux/unaligned.h>
#include <scsi/scsi_device.h>
#include <scsi/scsi_host.h>
#include <ufs/ufshcd.h>
#include "overlay-data.h"

#define G0Q_HANDOVER_TAG	0xf0300000U	/* report_modes.tag(18) */
#define G0Q_FLOOR_NS		(60ULL * NSEC_PER_SEC)
#define G0Q_CEILING_NS		(525ULL * NSEC_PER_SEC)
#define G0Q_BUDGET_NS		(150ULL * NSEC_PER_SEC)	/* admission to frozen report */
#define G0Q_HOST_PATH		"/soc@0/ufshc@1d84000"
#define G0Q_BLOCK		4096U
#define G0Q_TEST_LBA		62305152ULL
#define G0Q_GATE_WORDS		25	/* g0q_ufs_gate.h G0Q_GATE_SNAPSHOT_WORDS */

extern int g0q_ufshcd_core_init(void);
extern int g0q_qmp_ufs_register(void);
extern int g0q_ufs_qcom_register(void);
extern void g0q_gate_snapshot(u32 out[G0Q_GATE_WORDS]);

enum { STEP_NONE, STEP_ADMITTED, STEP_DRIVERS, STEP_OVERLAY, STEP_HBA, STEP_LU0, STEP_GPT, STEP_DONE };

struct g0q_report {
	int rc, step;
	u32 start_ms, settle_ms;
	int core_rc, phy_rc, qcom_rc, overlay_rc;
	int hba_state;
	u32 evt[4];			/* PA, DL, link-startup failures, host resets */
	struct ufs_pa_layer_attr pwr;
	u32 spec, manufacturer, devices, lu0_block, lu0_blocks;
	int gpt_rc, block_rc;
	u8 gpt[SHA256_DIGEST_SIZE], block[SHA256_DIGEST_SIZE];
};

#define G0Q_REPORT_INIT { .rc = -EINPROGRESS, .hba_state = -1, .gpt_rc = -EINPROGRESS, \
			  .block_rc = -EINPROGRESS }

/* work: the worker's private copy. out: the published report, frozen at the budget. */
static struct g0q_report work = G0Q_REPORT_INIT, out = G0Q_REPORT_INIT;
static DEFINE_MUTEX(out_lock);
static bool frozen;
static DECLARE_COMPLETION(finished);

static void publish(void)
{
	mutex_lock(&out_lock);
	if (!frozen)
		out = work;
	mutex_unlock(&out_lock);
}

static int report(char *buf, const struct kernel_param *kp)
{
	struct g0q_report r;
	u32 gate[G0Q_GATE_WORDS];
	int n, i;

	mutex_lock(&out_lock);
	r = out;
	mutex_unlock(&out_lock);
	g0q_gate_snapshot(gate);	/* fresh, self-consistent counters at every read */
	n = scnprintf(buf, PAGE_SIZE, "%d %d %u %u %u %d %d %d %d %d %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %d",
		      r.rc, r.step, G0Q_HANDOVER_TAG, r.start_ms, r.settle_ms, r.core_rc,
		      r.phy_rc, r.qcom_rc, r.overlay_rc, r.hba_state, r.evt[0], r.evt[1],
		      r.evt[2], r.evt[3], r.pwr.gear_rx, r.pwr.gear_tx, r.pwr.lane_rx,
		      r.pwr.lane_tx, r.pwr.pwr_rx, r.pwr.pwr_tx, r.pwr.hs_rate, r.spec,
		      r.manufacturer, r.devices, r.lu0_block, r.lu0_blocks, r.gpt_rc);
	for (i = 0; i < 8; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %u", get_unaligned_be32(r.gpt + 4 * i));
	n += scnprintf(buf + n, PAGE_SIZE - n, " %d", r.block_rc);
	for (i = 0; i < 8; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %u", get_unaligned_be32(r.block + 4 * i));
	for (i = 0; i < G0Q_GATE_WORDS; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %u", gate[i]);
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

/* The SCSI host's LU 0 disk, with a reference, once sd has registered it with a capacity. */
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

/* One direct read (IOCB_DIRECT: no page cache, no readahead) of whole blocks into aligned memory. */
static int read_digest(struct file *file, u64 lba, size_t bytes, u8 digest[SHA256_DIGEST_SIZE], u64 until)
{
	unsigned int order = get_order(bytes);
	void *buf = (void *)__get_free_pages(GFP_KERNEL, order);
	struct kvec kv = { .iov_base = buf, .iov_len = bytes };
	struct iov_iter iter;
	struct kiocb kiocb;
	ssize_t n;

	if (!buf)
		return -ENOMEM;
	init_sync_kiocb(&kiocb, file);
	kiocb.ki_flags |= IOCB_DIRECT;
	kiocb.ki_pos = lba * G0Q_BLOCK;
	iov_iter_kvec(&iter, ITER_DEST, &kv, 1, bytes);
	/* The budget is checked last, after everything that can sleep, before the read is submitted. */
	if (ktime_get_boottime_ns() >= until) {
		free_pages((unsigned long)buf, order);
		return -ETIMEDOUT;
	}
	n = vfs_iocb_iter_read(file, &kiocb, &iter);
	if (n == bytes)
		sha256(buf, bytes, digest);
	free_pages((unsigned long)buf, order);
	return n == bytes ? 0 : (n < 0 ? (int)n : -EIO);
}

static void sample(struct ufs_hba *hba)
{
	struct scsi_device *sdev;

	work.hba_state = hba->ufshcd_state;
	work.evt[0] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_PA_ERR].cnt);
	work.evt[1] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_DL_ERR].cnt);
	work.evt[2] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_LINK_STARTUP_FAIL].cnt);
	work.evt[3] = clamp_cnt(hba->ufs_stats.event[UFS_EVT_HOST_RESET].cnt);
	work.pwr = hba->pwr_info;
	work.spec = hba->dev_info.wspecversion;
	work.manufacturer = hba->dev_info.wmanufacturerid;
	work.devices = 0;
	shost_for_each_device(sdev, hba->host)
		work.devices++;
}

/* The probed host, pinned by its SCSI host reference, only once probe returned 0. */
static struct ufs_hba *bound_host(struct platform_device *pdev)
{
	struct ufs_hba *hba = NULL;

	device_lock(&pdev->dev);
	if (device_is_bound(&pdev->dev)) {
		hba = platform_get_drvdata(pdev);
		if (hba && !scsi_host_get(hba->host))
			hba = NULL;
	}
	device_unlock(&pdev->dev);
	return hba;
}

static int handover(u64 until)
{
	struct device_node *node;
	struct platform_device *pdev;
	struct ufs_hba *hba = NULL;
	struct gendisk *disk;
	struct device *held;
	struct file *file = NULL;
	u64 applied;
	int id = 0, rc;

	if (ktime_get_boottime_ns() >= until)
		return -ETIMEDOUT;
	rc = of_overlay_fdt_apply(ml030_overlay, sizeof(ml030_overlay), &id, NULL);
	if (rc) {
		work.overlay_rc = rc;
		return rc;
	}
	applied = ktime_get_boottime_ns();
	work.step = STEP_OVERLAY;
	publish();

	node = of_find_node_by_path(G0Q_HOST_PATH);
	pdev = node ? of_find_device_by_node(node) : NULL;
	of_node_put(node);
	if (!pdev)
		return -ENODEV;
	while (ktime_get_boottime_ns() < until) {
		if (!hba)
			hba = bound_host(pdev);
		if (hba && (disk = lu0_disk(hba, &held))) {
			/* device_add() precedes bdev_add(): an early open fails and is retried. */
			file = bdev_file_open_by_dev(disk_devt(disk), BLK_OPEN_READ, NULL, NULL);
			if (!IS_ERR(file)) {
				work.lu0_block = queue_logical_block_size(disk->queue);
				work.lu0_blocks = (u32)min_t(u64, get_capacity(disk) >> 3, U32_MAX);
				put_device(held);
				break;
			}
			file = NULL;
			put_device(held);
		}
		msleep(50);
	}
	put_device(&pdev->dev);
	work.settle_ms = ms(ktime_get_boottime_ns() - applied);
	if (hba) {
		sample(hba);
		work.step = STEP_HBA;
	}
	if (!file) {
		rc = -ETIMEDOUT;
		goto out_host;
	}
	work.step = STEP_LU0;
	publish();

	/* Each read refuses to start after the budget (rc -ETIMEDOUT): no new command after it. */
	work.gpt_rc = read_digest(file, 1, 3 * G0Q_BLOCK, work.gpt, until);
	if (!work.gpt_rc)
		work.step = STEP_GPT;
	publish();
	work.block_rc = read_digest(file, G0Q_TEST_LBA, G0Q_BLOCK, work.block, until);
	rc = work.gpt_rc ? work.gpt_rc : work.block_rc;
	fput(file);
	sample(hba);	/* after the reads: final link, error counts and LU count */
	if (!rc)
		work.step = STEP_DONE;
out_host:
	if (hba)
		scsi_host_put(hba->host);
	return rc;
}

static u64 until_ns;

static int worker(void *unused)
{
	int rc = handover(until_ns);

	work.rc = rc;
	publish();
	complete(&finished);
	return 0;
}

static atomic_t taken = ATOMIC_INIT(0);

static int __init start(void)
{
	u64 now = ktime_get_boottime_ns();
	struct task_struct *task;
	long left;

	/* Pre-effect admission: a refusal unloads the module with nothing registered or applied. */
	if (!of_machine_is_compatible("samsung,g0q"))
		return -ENODEV;
	if (now < G0Q_FLOOR_NS || now + G0Q_BUDGET_NS >= G0Q_CEILING_NS)
		return -ETIMEDOUT;
	if (atomic_cmpxchg(&taken, 0, 1))
		return -EALREADY;
	until_ns = now + G0Q_BUDGET_NS;
	work.start_ms = ms(now);
	work.step = STEP_ADMITTED;
	/* Registration only (no device exists before the overlay); runs here because it is init code. */
	work.core_rc = g0q_ufshcd_core_init();
	work.phy_rc = work.core_rc ? -ECANCELED : g0q_qmp_ufs_register();
	work.qcom_rc = work.phy_rc ? -ECANCELED : g0q_ufs_qcom_register();
	if (work.core_rc || work.phy_rc || work.qcom_rc) {
		work.rc = -ENODEV;
		publish();
		return 0;	/* the report stays readable; nothing was applied */
	}
	work.step = STEP_DRIVERS;
	publish();
	task = kthread_run(worker, NULL, "g0q-handover");
	if (IS_ERR(task)) {
		work.rc = PTR_ERR(task);
		publish();
	} else {
		left = nsecs_to_jiffies(until_ns - min(until_ns, ktime_get_boottime_ns()));
		if (!wait_for_completion_timeout(&finished, max(left, 1L))) {
			mutex_lock(&out_lock);
			frozen = true;
			/* A worker that published its result just now keeps it. */
			if (out.rc == -EINPROGRESS)
				out.rc = -ETIMEDOUT;
			mutex_unlock(&out_lock);
		}
	}
	/*
	 * The upstream core's LU scan runs as async work. Module load would otherwise wait for all
	 * async work before the observer can read this report; the scan continues in the background.
	 */
	THIS_MODULE->async_probe_requested = true;
	/* Returning 0 keeps the drivers, the gate and the read-only report resident until the return. */
	return 0;
}

module_init(start);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("g0q step-4b upstream UFS handover (read-only, write-gated)");
