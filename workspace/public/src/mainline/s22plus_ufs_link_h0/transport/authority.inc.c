// SPDX-License-Identifier: GPL-2.0-only
/* Private addition to rpmh.c. Ordinary RPMh requests never use this arena. */
#include <linux/ktime.h>
#include <linux/of.h>
#include <linux/sched.h>
#include <soc/qcom/cmd-db.h>
#include <soc/qcom/g0q-ml030.h>

#define G0Q_MAX_COMMANDS 32
static const struct {
	const char *name;
	unsigned int mv;
} rails[] = {
	{ "ldob6", 1200 }, { "ldob7", 2504 }, { "ldob9", 1200 }, { "smpb12", 1256 }
};
static struct {
	int consumed;
	struct task_struct *issuer;
	u64 deadline;
	int failure;
	unsigned int used;
	u32 base[ARRAY_SIZE(rails)];
	u32 claimed, triggered, acknowledged, reclaimed;
	struct {
		struct rpmh_request req;
		struct completion ack;
	} records[G0Q_MAX_COMMANDS];
} g0q_run;

static bool g0q_issuer(void)
{
	return in_task() && READ_ONCE(g0q_run.issuer) == current;
}

int g0q_rpmh_begin(u64 deadline)
{
	u64 now = ktime_get_boottime_ns();

	if (!of_machine_is_compatible("samsung,g0q") || !in_task() ||
	    now < 300ULL * NSEC_PER_SEC || now >= deadline ||
	    deadline - now > 15ULL * NSEC_PER_SEC || deadline > 540ULL * NSEC_PER_SEC)
		return -EPERM;
	if (cmpxchg(&g0q_run.consumed, 0, 1))
		return -EALREADY;
	for (unsigned int i = 0; i < ARRAY_SIZE(rails); i++) {
		int rc = g0q_unique_vrm(rails[i].name, &g0q_run.base[i]);

		if (rc)
			return rc;
	}
	g0q_run.deadline = deadline;
	WRITE_ONCE(g0q_run.issuer, current);
	return 0;
}
EXPORT_SYMBOL_GPL(g0q_rpmh_begin);

void g0q_rpmh_end(void)
{
	/* The issuing task executes the module synchronously. After it returns,
	 * its ordinary Download path has no experimental transport context.
	 */
	if (g0q_issuer())
		WRITE_ONCE(g0q_run.issuer, NULL);
}
EXPORT_SYMBOL_GPL(g0q_rpmh_end);

void g0q_rpmh_status(struct g0q_rpmh_report *report)
{
	*report = (struct g0q_rpmh_report) { .records = g0q_run.used,
		.claimed = g0q_run.claimed, .triggered = g0q_run.triggered,
		.acknowledged = g0q_run.acknowledged, .reclaimed = g0q_run.reclaimed,
		.error = g0q_run.failure };
}
EXPORT_SYMBOL_GPL(g0q_rpmh_status);

int g0q_rpmh_remaining(void)
{
	if (!g0q_issuer())
		return -EPERM;
	if (!g0q_run.failure && ktime_get_boottime_ns() >= g0q_run.deadline)
		g0q_run.failure = -ETIMEDOUT;
	return g0q_run.failure;
}
EXPORT_SYMBOL_GPL(g0q_rpmh_remaining);

bool g0q_rpmh_deny_ordinary(void)
{
	if (!g0q_issuer())
		return false;
	if (!g0q_run.failure)
		g0q_run.failure = -EPERM;
	return true;
}
EXPORT_SYMBOL_GPL(g0q_rpmh_deny_ordinary);

static int g0q_resource(u32 address, u32 data)
{
	for (unsigned int i = 0; i < ARRAY_SIZE(rails); i++) {
		u32 base = g0q_run.base[i];

		if (address == base)
			return data == rails[i].mv ? 0 : -ERANGE;
		if (address == base + 4)
			return data == 1 ? 0 : -EPERM;
		if (address == base + 8)
			return i < 3 && (data == 4 || data == 7) ? 0 : -EPERM;
	}
	return -EPERM;
}

static bool g0q_cache_conflict(struct rpmh_ctrlr *ctrlr, u32 addr)
{
	struct cache_req *item;
	struct batch_cache_req *batch;
	unsigned long flags;
	bool found = false;

	spin_lock_irqsave(&ctrlr->cache_lock, flags);
	list_for_each_entry(item, &ctrlr->cache, list) {
		if (cmd_db_match_resource_addr(item->addr, addr)) {
			found = true;
			goto out;
		}
	}
	list_for_each_entry(batch, &ctrlr->batch_cache, list) {
		for (int i = 0; i < batch->count; i++) {
			struct tcs_request *msg = &batch->rpm_msgs[i].msg;
			for (unsigned int j = 0; j < msg->num_cmds; j++)
				if (cmd_db_match_resource_addr(msg->cmds[j].addr, addr)) {
					found = true;
					goto out;
				}
		}
	}
out:
	spin_unlock_irqrestore(&ctrlr->cache_lock, flags);
	return found;
}

int g0q_rpmh_vrm(const struct device *dev, u32 address, u32 data)
{
	struct device_node *parent __free(device_node) = of_find_node_by_path("/soc@0/rsc@17a00000");
	struct rpmh_ctrlr *ctrlr;
	struct rpmh_request *req;
	struct completion *ack;
	bool claimed = false, triggered = false, reclaimed = false;
	u32 bit;
	u64 now;
	unsigned long timeout;
	int rc = g0q_rpmh_remaining();

	if (rc)
		return rc;
	if (!dev || !dev->parent || !dev->of_node || !dev->parent->of_node ||
	    !of_node_name_eq(dev->of_node, "ml030-ufs-rails") ||
	    !of_device_is_compatible(dev->of_node, "samsung,g0q-ml030-ufs-rails") ||
	    !parent || dev->parent->of_node != parent) {
		rc = -ENODEV;
		goto stop;
	}
	ctrlr = get_rpmh_ctrlr(dev);
	rc = g0q_resource(address, data);
	if (rc)
		goto stop;
	if (g0q_cache_conflict(ctrlr, address)) {
		rc = -EBUSY;
		goto stop;
	}
	if (g0q_run.used == ARRAY_SIZE(g0q_run.records)) {
		rc = -E2BIG;
		goto stop;
	}
	/* Each record is persistent until reboot, including after a timeout. The
	 * stock tcs_tx_done/rpmh_tx_done pair can signal any late real IRQ safely.
	 * No record, completion or command storage is ever recycled.
	 */
	bit = BIT(g0q_run.used);
	req = &g0q_run.records[g0q_run.used].req;
	ack = &g0q_run.records[g0q_run.used++].ack;
	init_completion(ack);
	req->cmd[0] = (struct tcs_cmd) { .addr = address, .data = data, .wait = true };
	req->msg = (struct tcs_request) { .state = RPMH_ACTIVE_ONLY_STATE, .cmds = req->cmd,
					 .num_cmds = 1, .wait_for_compl = true };
	req->dev = dev;
	req->completion = ack;
	req->needs_free = false;

	rc = g0q_rsc_send(ctrlr_to_drv(ctrlr), req, g0q_run.deadline,
			  &claimed, &triggered, &reclaimed);
	if (claimed)
		g0q_run.claimed |= bit;
	if (triggered)
		g0q_run.triggered |= bit;
	if (reclaimed)
		g0q_run.reclaimed |= bit;
	if (rc)
		goto stop;
	now = ktime_get_boottime_ns();
	if (now >= g0q_run.deadline) {
		rc = -ETIMEDOUT;
		goto stop;
	}
	timeout = max_t(unsigned long, 1, nsecs_to_jiffies(g0q_run.deadline - now));
	if (!wait_for_completion_timeout(ack, timeout) || ktime_get_boottime_ns() >= g0q_run.deadline) {
		rc = -ETIMEDOUT;
		goto stop;
	}
	g0q_run.acknowledged |= bit;
	return 0;
stop:
	g0q_run.failure = rc;
	pr_info("g0q ML030 resource stop rc=%d claimed=%d triggered=%d\n", rc, claimed, triggered);
	return rc;
}
EXPORT_SYMBOL_GPL(g0q_rpmh_vrm);
