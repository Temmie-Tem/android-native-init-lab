// SPDX-License-Identifier: GPL-2.0-only
/* Private addition to rpmh-rsc.c. No legacy IRQ, cache, queue or recovery
 * caller enters this function. At most one dedicated active slot can remain
 * owned after uncertainty; the operation stops and does not borrow a wake TCS.
 */
#include <linux/ktime.h>
#include <soc/qcom/g0q-ml030.h>

static int g0q_control(struct rsc_drv *drv, int id, u32 value, u64 deadline, bool *uncertain)
{
	u32 reg = drv->regs[RSC_DRV_CONTROL];

	if (ktime_get_boottime_ns() >= deadline)
		return -ETIMEDOUT;
	*uncertain = true;
	write_tcs_reg(drv, reg, id, value);
	while (ktime_get_boottime_ns() < deadline) {
		if (read_tcs_reg(drv, reg, id) == value) {
			*uncertain = false;
			return 0;
		}
		udelay(1);
	}
	return -ETIMEDOUT;
}

static bool g0q_unclaim(struct rsc_drv *drv, struct tcs_group *tcs, int id,
			const struct tcs_request *msg)
{
	u32 ctl, enable;
	bool released = false;

	/* Only undo an untriggered preparation. The two optional clearing
	 * writes are paired cleanup for this slot; they cannot launch a vote.
	 * Any ambiguous readback retains the slot for attended recovery.
	 */
	spin_lock_irq(&drv->lock);
	ctl = read_tcs_reg(drv, drv->regs[RSC_DRV_CONTROL], id);
	enable = read_tcs_reg(drv, drv->regs[RSC_DRV_CMD_ENABLE], id);
	if (!test_bit(id, drv->tcs_in_use) || tcs->req[id - tcs->offset] != msg ||
	    ctl & TCS_AMC_MODE_TRIGGER ||
	    readl_relaxed(drv->tcs_base + drv->regs[RSC_DRV_IRQ_STATUS]) & BIT(id) ||
	    enable & ~BIT(0) || (enable && read_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_ADDR],
							 id, 0) != msg->cmds[0].addr))
		goto out;
	if (ctl & TCS_AMC_MODE_ENABLE) {
		write_tcs_reg(drv, drv->regs[RSC_DRV_CONTROL], id, ctl & ~TCS_AMC_MODE_ENABLE);
		if (read_tcs_reg(drv, drv->regs[RSC_DRV_CONTROL], id) != (ctl & ~TCS_AMC_MODE_ENABLE))
			goto out;
	}
	if (enable) {
		write_tcs_reg(drv, drv->regs[RSC_DRV_CMD_ENABLE], id, 0);
		if (read_tcs_reg(drv, drv->regs[RSC_DRV_CMD_ENABLE], id))
			goto out;
	}
	tcs->req[id - tcs->offset] = NULL;
	clear_bit(id, drv->tcs_in_use);
	released = true;
out:
	spin_unlock_irq(&drv->lock);
	if (released)
		wake_up(&drv->tcs_wait);
	return released;
}

int g0q_rsc_send(struct rsc_drv *drv, struct rpmh_request *request, u64 deadline,
		 bool *claimed, bool *triggered, bool *reclaimed)
{
	struct tcs_group *tcs = &drv->tcs[ACTIVE_TCS];
	const struct tcs_request *msg = &request->msg;
	u32 val, ctrl, msgid = CMD_MSGID_LEN | CMD_MSGID_WRITE | CMD_MSGID_RESP_REQ;
	bool uncertain = false;
	int id, rc;

	if (drv->id != 2 || tcs->num_tcs != 3 || msg->num_cmds != 1 ||
	    msg->state != RPMH_ACTIVE_ONLY_STATE || !msg->wait_for_compl)
		return -ENODEV;
	might_sleep();
	spin_lock_irq(&drv->lock);
	rc = -ETIMEDOUT;
	if (ktime_get_boottime_ns() >= deadline)
		goto unlock;
	/* One try only, with the original conflict detection and slot lock. */
	id = claim_tcs_for_req(drv, tcs, msg);
	rc = id;
	if (id < 0)
		goto unlock;
	rc = -EBUSY;
	ctrl = read_tcs_reg(drv, drv->regs[RSC_DRV_CONTROL], id);
	if (ctrl & (TCS_AMC_MODE_ENABLE | TCS_AMC_MODE_TRIGGER) ||
	    read_tcs_reg(drv, drv->regs[RSC_DRV_CMD_ENABLE], id) ||
	    readl_relaxed(drv->tcs_base + drv->regs[RSC_DRV_IRQ_STATUS]) & BIT(id) ||
	    !(readl_relaxed(drv->tcs_base + drv->regs[RSC_DRV_IRQ_ENABLE]) & BIT(id)))
		goto unlock;
	tcs->req[id - tcs->offset] = msg;
	set_bit(id, drv->tcs_in_use);
	*claimed = true;
	spin_unlock_irq(&drv->lock);

	/* Reclaim only a proved untriggered slot on failure. Never enable a
	 * slot containing an unverified address. */
	rc = -ETIMEDOUT;
	if (ktime_get_boottime_ns() >= deadline)
		goto abort;
	write_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_MSGID], id, 0, msgid);
	write_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_ADDR], id, 0, msg->cmds[0].addr);
	write_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_DATA], id, 0, msg->cmds[0].data);
	if (read_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_MSGID], id, 0) != msgid ||
	    read_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_ADDR], id, 0) != msg->cmds[0].addr ||
	    read_tcs_cmd(drv, drv->regs[RSC_DRV_CMD_DATA], id, 0) != msg->cmds[0].data) {
		/* A posted payload can still reach this slot after a failed
		 * readback. Keep it claimed even though CMD_ENABLE is zero.
		 */
		return -EIO;
	}
	if (ktime_get_boottime_ns() >= deadline)
		goto abort;
	write_tcs_reg(drv, drv->regs[RSC_DRV_CMD_ENABLE], id, BIT(0));
	if (read_tcs_reg(drv, drv->regs[RSC_DRV_CMD_ENABLE], id) != BIT(0)) {
		return -EIO; /* A late posted enable must not reach a reused slot. */
	}
	rc = g0q_control(drv, id, ctrl & ~TCS_AMC_MODE_TRIGGER, deadline, &uncertain);
	if (!rc)
		rc = g0q_control(drv, id, ctrl & ~(TCS_AMC_MODE_TRIGGER | TCS_AMC_MODE_ENABLE), deadline, &uncertain);
	if (!rc)
		rc = g0q_control(drv, id, TCS_AMC_MODE_ENABLE, deadline, &uncertain);
	if (uncertain)
		return rc;
	if (rc)
		goto abort;
	/* Nothing can schedule between the last absolute check and the physical
	 * trigger write. The original IRQ completes the persistent request.
	 */
	spin_lock_irq(&drv->lock);
	rc = -ETIMEDOUT;
	if (ktime_get_boottime_ns() < deadline) {
		val = TCS_AMC_MODE_ENABLE | TCS_AMC_MODE_TRIGGER;
		write_tcs_reg(drv, drv->regs[RSC_DRV_CONTROL], id, val);
		*triggered = true;
		spin_unlock_irq(&drv->lock);
		return 0;
	}
	spin_unlock_irq(&drv->lock);
abort:
	*reclaimed = g0q_unclaim(drv, tcs, id, msg);
	return rc;
unlock:
	spin_unlock_irq(&drv->lock);
	return rc;
}
