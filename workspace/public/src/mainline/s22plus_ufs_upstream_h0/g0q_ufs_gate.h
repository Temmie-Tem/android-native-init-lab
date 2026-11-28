/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * S22+ roadmap step 4: deny-by-default write gate for the upstream ufshcd core.
 *
 * The policy half is pure (no kernel dependency) so a host fixture checks every
 * opcode. The kernel half is compiled only into the rendered ufshcd.c, which
 * calls it at the two submission choke points:
 *   - ufshcd_queuecommand(): every SCSI command, including ufshcd's own
 *     REQUEST SENSE / START STOP UNIT and SCSI error-handler commands;
 *   - ufshcd_issue_dev_cmd(): every device-management UPIU (NOP, query, raw
 *     BSG/RPMB UPIU), inspected after composition, just before execution.
 * Phase 4b/4c policy: SCSI reads and status only, START STOP UNIT only to the
 * UFS device W-LU, SYNCHRONIZE CACHE; NOP OUT; query reads and set fDeviceInit.
 */
#ifndef G0Q_UFS_GATE_H
#define G0Q_UFS_GATE_H

#define G0Q_GATE_DEVICE_WLUN	0xd0	/* UFS_UPIU_UFS_DEVICE_WLUN */
#define G0Q_GATE_UPIU_NOP_OUT	0x00
#define G0Q_GATE_UPIU_QUERY_REQ	0x16
#define G0Q_GATE_QUERY_OPCODE	12	/* struct utp_upiu_query after the 12-byte header */
#define G0Q_GATE_QUERY_IDN	13

/* cdb_len >= 1 is guaranteed by the SCSI midlayer; 0x9e also needs byte 1. */
static inline int g0q_gate_scsi_allowed(const unsigned char *cdb, unsigned int cdb_len,
					unsigned char upiu_lun)
{
	switch (cdb[0]) {
	case 0x00:	/* TEST UNIT READY */
	case 0x03:	/* REQUEST SENSE */
	case 0x12:	/* INQUIRY */
	case 0xa0:	/* REPORT LUNS */
	case 0x25:	/* READ CAPACITY(10) */
	case 0x1a:	/* MODE SENSE(6) */
	case 0x5a:	/* MODE SENSE(10) */
	case 0x08:	/* READ(6) */
	case 0x28:	/* READ(10) */
	case 0x88:	/* READ(16) */
	case 0x35:	/* SYNCHRONIZE CACHE(10) */
	case 0x91:	/* SYNCHRONIZE CACHE(16) */
		return 1;
	case 0x9e:	/* SERVICE ACTION IN(16): READ CAPACITY(16) only */
		return cdb_len >= 2 && (cdb[1] & 0x1f) == 0x10;
	case 0x1b:	/* START STOP UNIT: the stock power path, device W-LU only */
		return upiu_lun == G0Q_GATE_DEVICE_WLUN;
	default:
		return 0;
	}
}

static inline int g0q_gate_devman_allowed(const unsigned char *upiu)
{
	if (upiu[0] == G0Q_GATE_UPIU_NOP_OUT)
		return 1;
	if (upiu[0] != G0Q_GATE_UPIU_QUERY_REQ)
		return 0;
	switch (upiu[G0Q_GATE_QUERY_OPCODE]) {
	case 0x01:	/* READ DESCRIPTOR */
	case 0x03:	/* READ ATTRIBUTE */
	case 0x05:	/* READ FLAG */
		return 1;
	case 0x06:	/* SET FLAG: fDeviceInit only */
		return upiu[G0Q_GATE_QUERY_IDN] == 0x01;
	default:
		return 0;
	}
}

#ifdef __KERNEL__
#include <linux/atomic.h>
#include <linux/bitops.h>
#include <linux/moduleparam.h>
#include <linux/spinlock.h>

#define G0Q_GATE_QUERY_LOG 8

/* lock: each refusal's count, bitmap and log change together, and the snapshot sees them together. */
static struct {
	spinlock_t lock;
	atomic_t scsi_allowed, scsi_refused, devman_allowed, devman_refused, query_logged;
	unsigned long refused_ops[BITS_TO_LONGS(256)];
	u16 refused_query[G0Q_GATE_QUERY_LOG];	/* query: opcode<<8 | idn; other UPIU: 0xff00 | type */
	u32 caps_before, caps_after, ahit_disabled, wlun_rpm_kept;
} g0q_gate = { .lock = __SPIN_LOCK_UNLOCKED(g0q_gate.lock) };

static bool g0q_gate_scsi(struct ufs_hba *hba, struct scsi_cmnd *cmd)
{
	u8 lun = ufshcd_scsi_to_upiu_lun(cmd->device->lun);
	unsigned long flags;

	if (g0q_gate_scsi_allowed(cmd->cmnd, cmd->cmd_len, lun)) {
		atomic_inc(&g0q_gate.scsi_allowed);
		return true;
	}
	spin_lock_irqsave(&g0q_gate.lock, flags);
	atomic_inc(&g0q_gate.scsi_refused);
	set_bit(cmd->cmnd[0], g0q_gate.refused_ops);
	spin_unlock_irqrestore(&g0q_gate.lock, flags);
	return false;
}

static bool g0q_gate_devman(const u8 *upiu)
{
	unsigned long flags;
	int slot;

	if (g0q_gate_devman_allowed(upiu)) {
		atomic_inc(&g0q_gate.devman_allowed);
		return true;
	}
	spin_lock_irqsave(&g0q_gate.lock, flags);
	atomic_inc(&g0q_gate.devman_refused);
	slot = atomic_inc_return(&g0q_gate.query_logged) - 1;
	if (slot < G0Q_GATE_QUERY_LOG)
		g0q_gate.refused_query[slot] = upiu[0] == G0Q_GATE_UPIU_QUERY_REQ ?
			(upiu[G0Q_GATE_QUERY_OPCODE] << 8) | upiu[G0Q_GATE_QUERY_IDN] :
			0xff00 | upiu[0];
	spin_unlock_irqrestore(&g0q_gate.lock, flags);
	return false;
}

#define G0Q_GATE_CAPS_CLEARED (UFSHCD_CAP_CLK_GATING | UFSHCD_CAP_HIBERN8_WITH_CLK_GATING | \
	UFSHCD_CAP_CLK_SCALING | UFSHCD_CAP_WB_WITH_CLK_SCALING | UFSHCD_CAP_AUTO_BKOPS_SUSPEND | \
	UFSHCD_CAP_WB_EN | UFSHCD_CAP_AGGR_POWER_COLLAPSE | UFSHCD_CAP_RPM_AUTOSUSPEND | \
	UFSHCD_CAP_CRYPTO | UFSHCD_CAP_TX_EQUALIZATION)

static void g0q_gate_caps(struct ufs_hba *hba)
{
	g0q_gate.caps_before = hba->caps;
	hba->caps &= ~G0Q_GATE_CAPS_CLEARED;
	g0q_gate.caps_after = hba->caps;
}

static int g0q_gate_report(char *buf, const struct kernel_param *kp)
{
	int n = scnprintf(buf, PAGE_SIZE, "g0q-ufs-gate-v1 %d %d %d %d %d %#x %#x %u %u",
			  atomic_read(&g0q_gate.scsi_allowed), atomic_read(&g0q_gate.scsi_refused),
			  atomic_read(&g0q_gate.devman_allowed), atomic_read(&g0q_gate.devman_refused),
			  atomic_read(&g0q_gate.query_logged), g0q_gate.caps_before,
			  g0q_gate.caps_after, g0q_gate.ahit_disabled, g0q_gate.wlun_rpm_kept);

	for (int i = 0; i < 256 / 32; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %08x",
			       (u32)(bitmap_read(g0q_gate.refused_ops, i * 32, 32)));
	for (int i = 0; i < G0Q_GATE_QUERY_LOG; i++)
		n += scnprintf(buf + n, PAGE_SIZE - n, " %04x", g0q_gate.refused_query[i]);
	return n + scnprintf(buf + n, PAGE_SIZE - n, "\n");
}

/* For the composite step-4b module: 5 counters, caps before/after, ahit, W-LU flag,
 * 8 refused-opcode bitmap words, 8 refused-query slots. */
#define G0Q_GATE_SNAPSHOT_WORDS 25
void g0q_gate_snapshot(u32 out[G0Q_GATE_SNAPSHOT_WORDS]);
void g0q_gate_snapshot(u32 out[G0Q_GATE_SNAPSHOT_WORDS])
{
	unsigned long flags;

	spin_lock_irqsave(&g0q_gate.lock, flags);
	out[0] = atomic_read(&g0q_gate.scsi_allowed);
	out[1] = atomic_read(&g0q_gate.scsi_refused);
	out[2] = atomic_read(&g0q_gate.devman_allowed);
	out[3] = atomic_read(&g0q_gate.devman_refused);
	out[4] = atomic_read(&g0q_gate.query_logged);
	out[5] = g0q_gate.caps_before;
	out[6] = g0q_gate.caps_after;
	out[7] = g0q_gate.ahit_disabled;
	out[8] = g0q_gate.wlun_rpm_kept;
	for (int i = 0; i < 8; i++)
		out[9 + i] = (u32)bitmap_read(g0q_gate.refused_ops, i * 32, 32);
	for (int i = 0; i < G0Q_GATE_QUERY_LOG; i++)
		out[17 + i] = g0q_gate.refused_query[i];
	spin_unlock_irqrestore(&g0q_gate.lock, flags);
}

static const struct kernel_param_ops g0q_gate_ops = { .get = g0q_gate_report };
module_param_cb(g0q_gate, &g0q_gate_ops, NULL, 0444);
MODULE_PARM_DESC(g0q_gate, "S22+ step-4 write gate counters (read-only)");
#endif /* __KERNEL__ */
#endif /* G0Q_UFS_GATE_H */
