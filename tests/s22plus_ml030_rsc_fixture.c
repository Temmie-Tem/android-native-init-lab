// SPDX-License-Identifier: GPL-2.0-only
/* H0 register model. Posted writes can be held until after return. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t u32;
typedef uint64_t u64;
#define BIT(i) (1U << (i))
#define TCS_AMC_MODE_TRIGGER BIT(24)
#define TCS_AMC_MODE_ENABLE BIT(16)
#define CMD_MSGID_LEN 8
#define CMD_MSGID_WRITE BIT(16)
#define CMD_MSGID_RESP_REQ BIT(8)
enum { ACTIVE_TCS, RPMH_ACTIVE_ONLY_STATE };
enum { RSC_DRV_CONTROL, RSC_DRV_CMD_ENABLE, RSC_DRV_CMD_ADDR, RSC_DRV_CMD_DATA,
       RSC_DRV_CMD_MSGID, RSC_DRV_IRQ_STATUS, RSC_DRV_IRQ_ENABLE, NREG };
struct tcs_cmd { u32 addr, data; };
struct tcs_request {
	int state, num_cmds;
	bool wait_for_compl;
	struct tcs_cmd *cmds;
};
struct rpmh_request { struct tcs_request msg; };
struct tcs_group { int num_tcs, offset; const struct tcs_request *req[3]; };
struct rsc_drv {
	int id, regs[NREG], tcs_wait, lock;
	unsigned long tcs_in_use[1];
	struct tcs_group tcs[1];
	u32 tcs_base[NREG], slot[3][NREG];
};
static u64 tick = 1;
static const u64 deadline = 1500;
static int writes, triggers, delayed = -1, expire_reg = -1, lock_depth, lock_count;
static u32 held_value;
static int expire_lock;
#define might_sleep() ((void)0)
#define wake_up(wait) ((void)(wait))
#define readl_relaxed(p) (*(p))
#define ktime_get_boottime_ns() tick
#define udelay(t) (tick += (t))
#define set_bit(i,b) (*(b) |= BIT(i))
#define clear_bit(i,b) (*(b) &= ~BIT(i))
#define test_bit(i,b) (!!(*(b) & BIT(i)))

static void lock_test(int *lock)
{
	(void)lock;
	assert(!lock_depth++);
	if (++lock_count == expire_lock)
		tick = deadline;
}
#define spin_lock_irq(lock) lock_test(lock)
#define spin_unlock_irq(lock) do { (void)(lock); assert(lock_depth-- == 1); } while (0)

static int claim_tcs_for_req(struct rsc_drv *drv, struct tcs_group *group,
			     const struct tcs_request *msg)
{
	(void)msg;
	assert(lock_depth == 1);
	for (int i = 0; i < group->num_tcs; i++)
		if (!test_bit(i, drv->tcs_in_use))
			return i;
	return -EBUSY;
}
static u32 read_tcs_reg(struct rsc_drv *drv, int reg, int id)
{
	return drv->slot[id][reg];
}
static void write_tcs_reg(struct rsc_drv *drv, int reg, int id, u32 value)
{
	writes++;
	if (reg == RSC_DRV_CONTROL && (value & TCS_AMC_MODE_TRIGGER)) {
		assert(lock_depth == 1 && tick < deadline);
		triggers++;
	}
	if (reg == delayed) {
		held_value = value;
		if (reg == RSC_DRV_CONTROL && value)
			tick = deadline;
	} else {
		drv->slot[id][reg] = value;
	}
	if (reg == expire_reg)
		tick = deadline;
}
static u32 read_tcs_cmd(struct rsc_drv *drv, int reg, int id, int cmd)
{
	assert(cmd == 0);
	return read_tcs_reg(drv, reg, id);
}
static void write_tcs_cmd(struct rsc_drv *drv, int reg, int id, int cmd, u32 val)
{
	assert(cmd == 0);
	write_tcs_reg(drv, reg, id, val);
}
#include "rsc-send.inc.c"

int main(int argc, char **argv)
{
	assert(argc == 2);
	const char *mode = argv[1];
	struct tcs_cmd cmd = { .addr = 0x40050, .data = 1200 };
	struct rpmh_request req = { .msg = { RPMH_ACTIVE_ONLY_STATE, 1, true, &cmd } };
	struct rsc_drv drv = { .id = 2, .tcs = { { .num_tcs = 3 } } };
	bool claimed = false, triggered = false, reclaimed = false;
	for (int i = 0; i < NREG; i++)
		drv.regs[i] = i;
	drv.tcs_base[RSC_DRV_IRQ_ENABLE] = 7;
	int want_rc = 0;
	bool want_claim = true, want_trigger = false, want_reclaim = false;
	if (!strcmp(mode, "success")) {
		want_trigger = true;
	} else if (!strcmp(mode, "busy") || !strcmp(mode, "expired") ||
		   !strcmp(mode, "old-irq") || !strcmp(mode, "old-enable")) {
		if (!strcmp(mode, "busy"))
			drv.tcs_in_use[0] = 7;
		if (!strcmp(mode, "old-irq"))
			drv.tcs_base[RSC_DRV_IRQ_STATUS] = 1;
		if (!strcmp(mode, "old-enable"))
			drv.slot[0][RSC_DRV_CMD_ENABLE] = 1;
		if (!strcmp(mode, "expired"))
			tick = deadline;
		want_claim = false;
		want_rc = tick == deadline ? -ETIMEDOUT : -EBUSY;
	} else if (!strcmp(mode, "payload-expiry") || !strcmp(mode, "pretrigger-expiry")) {
		if (!strcmp(mode, "payload-expiry"))
			expire_reg = RSC_DRV_CMD_DATA;
		else
			expire_lock = 2;
		want_reclaim = true;
		want_rc = -ETIMEDOUT;
	} else {
		const char *modes[] = { "posted-ctl", "posted-enable", "posted-addr", "posted-data", "posted-msgid" };
		for (int i = 0; i < 5; i++)
			if (!strcmp(mode, modes[i]))
				delayed = i;
		assert(delayed >= 0);
		want_rc = delayed == RSC_DRV_CONTROL ? -ETIMEDOUT : -EIO;
	}
	int rc = g0q_rsc_send(&drv, &req, deadline, &claimed, &triggered, &reclaimed);
	assert(rc == want_rc && claimed == want_claim && triggered == want_trigger && reclaimed == want_reclaim);
	assert(triggers == (int)triggered && !lock_depth);
	if (!claimed)
		assert(!writes);
	if (claimed) {
		assert(test_bit(0, drv.tcs_in_use) == !reclaimed);
		assert((drv.tcs[0].req[0] == &req.msg) == !reclaimed);
		/* An unrelated request gets another slot. Delivering the posted
		 * write now cannot change that other slot's payload or enable. */
		spin_lock_irq(&drv.lock);
		int ordinary = claim_tcs_for_req(&drv, &drv.tcs[0], &req.msg);
		spin_unlock_irq(&drv.lock);
		assert(ordinary == (reclaimed ? 0 : 1));
		if (delayed >= 0) {
			drv.slot[ordinary][delayed] = 0x4321;
			drv.slot[0][delayed] = held_value;
			assert(drv.slot[ordinary][delayed] == 0x4321);
		}
	}
	printf("%s rc=%d claimed=%d triggered=%d reclaimed=%d writes=%d\n",
	       mode, rc, claimed, triggered, reclaimed, writes);
	return 0;
}
