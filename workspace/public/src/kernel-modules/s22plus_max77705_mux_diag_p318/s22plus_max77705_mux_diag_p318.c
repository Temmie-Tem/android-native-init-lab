// SPDX-License-Identifier: GPL-2.0-only

#include <linux/atomic.h>
#include <linux/bitops.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/of.h>
#include <linux/types.h>

#define S22PLUS_MAX77705_PARENT_COMPATIBLE "maxim,max77705"
#define S22PLUS_MAX77705_PARENT_ADDR 0x66
#define S22PLUS_MAX77705_MUIC_ADDR 0x25

#define S22PLUS_MAX77705_PMIC_ID_REG 0x00
#define S22PLUS_MAX77705_PMIC_REV_REG 0x01
#define S22PLUS_MAX77705_EXPECTED_PMIC_ID 0x15
#define S22PLUS_MAX77705_EXPECTED_PMIC_REV_LOW3 0x02

#define S22PLUS_MAX77705_UIC_INT 0x02
#define S22PLUS_MAX77705_AP_DATAOUT0 0x21
#define S22PLUS_MAX77705_AP_DATAOUT_END 0x41
#define S22PLUS_MAX77705_AP_DATAIN0 0x51
#define S22PLUS_MAX77705_AP_CMD_RESPONSE BIT(7)

#define S22PLUS_MAX77705_CONTROL1_READ 0x05
#define S22PLUS_MAX77705_CONTROL1_WRITE 0x06
#define S22PLUS_MAX77705_COM_USB 0x09

#define S22PLUS_MAX77705_POLL_LIMIT 100U
#define S22PLUS_MAX77705_RETENTION_MS 30000U
#define S22PLUS_MAX77705_COMMAND_COUNT 4U
#define S22PLUS_MAX77705_RESULT_FIXED_MAX 768U

enum s22plus_max77705_command_slot {
	S22PLUS_MAX77705_SLOT_PRE = 0,
	S22PLUS_MAX77705_SLOT_WRITE,
	S22PLUS_MAX77705_SLOT_POST1,
	S22PLUS_MAX77705_SLOT_POST2,
};

enum s22plus_max77705_stage {
	S22PLUS_MAX77705_STAGE_NOT_RUN = 0,
	S22PLUS_MAX77705_STAGE_CLAIMED,
	S22PLUS_MAX77705_STAGE_IDENTITY,
	S22PLUS_MAX77705_STAGE_DUMMY_CLIENT,
	S22PLUS_MAX77705_STAGE_INITIAL_UIC,
	S22PLUS_MAX77705_STAGE_PRE,
	S22PLUS_MAX77705_STAGE_WRITE,
	S22PLUS_MAX77705_STAGE_POST1,
	S22PLUS_MAX77705_STAGE_RETENTION,
	S22PLUS_MAX77705_STAGE_POST2,
	S22PLUS_MAX77705_STAGE_COMPLETE,
};

struct s22plus_max77705_result {
	u32 stage;
	s32 rc;
	u8 pmic_valid_mask;
	u8 pmic_id;
	u8 pmic_rev;
	u8 initial_uic_valid;
	u8 initial_uic;
	u8 command_issued_mask;
	u8 response_seen_mask;
	u8 response_opcode[S22PLUS_MAX77705_COMMAND_COUNT];
	u8 response_value[S22PLUS_MAX77705_COMMAND_COUNT];
	u8 poll_count[S22PLUS_MAX77705_COMMAND_COUNT];
	u8 poll_bytes[S22PLUS_MAX77705_COMMAND_COUNT]
			 [S22PLUS_MAX77705_POLL_LIMIT];
	u8 write_attempted;
	u8 write_ambiguous;
	u8 timing_valid_mask;
	u64 pre_ns;
	u64 write_ns;
	u64 post1_ns;
	u64 post2_ns;
};

static atomic_t s22plus_max77705_claimed = ATOMIC_INIT(0);
static struct s22plus_max77705_result s22plus_max77705_result;
static char cached_result[PAGE_SIZE];
static int cached_result_ready;

_Static_assert(S22PLUS_MAX77705_COMMAND_COUNT == 4U,
		"result encoder assumes four command slots");
_Static_assert(S22PLUS_MAX77705_POLL_LIMIT <= 255U,
		"poll count must fit in one byte");
_Static_assert(S22PLUS_MAX77705_RESULT_FIXED_MAX +
		S22PLUS_MAX77705_COMMAND_COUNT * S22PLUS_MAX77705_POLL_LIMIT * 2U <
		PAGE_SIZE,
		"cached result must fit in one module-parameter page");

static int s22plus_max77705_read_pmic_identity(
		struct i2c_client *parent, struct s22plus_max77705_result *result)
{
	int value;

	value = i2c_smbus_read_byte_data(parent,
			S22PLUS_MAX77705_PMIC_ID_REG);
	if (value < 0)
		return value;
	result->pmic_id = (u8)value;
	result->pmic_valid_mask |= BIT(0);

	value = i2c_smbus_read_byte_data(parent,
			S22PLUS_MAX77705_PMIC_REV_REG);
	if (value < 0)
		return value;
	result->pmic_rev = (u8)value;
	result->pmic_valid_mask |= BIT(1);

	if (result->pmic_id != S22PLUS_MAX77705_EXPECTED_PMIC_ID ||
	    (result->pmic_rev & 0x7U) !=
		    S22PLUS_MAX77705_EXPECTED_PMIC_REV_LOW3)
		return -ENODEV;

	return 0;
}

static int s22plus_max77705_clear_uic_latch_once(
		struct i2c_client *muic, struct s22plus_max77705_result *result)
{
	int status = i2c_smbus_read_byte_data(
			muic, S22PLUS_MAX77705_UIC_INT);

	if (status < 0)
		return status;
	result->initial_uic = (u8)status;
	result->initial_uic_valid = 1U;
	return 0;
}

static int s22plus_max77705_wait_ap_response(
		struct i2c_client *muic, struct s22plus_max77705_result *result,
		u8 slot)
{
	unsigned int attempt;
	int status;

	if (slot >= S22PLUS_MAX77705_COMMAND_COUNT)
		return -EINVAL;

	for (attempt = 0; attempt < S22PLUS_MAX77705_POLL_LIMIT; ++attempt) {
		status = i2c_smbus_read_byte_data(
				muic, S22PLUS_MAX77705_UIC_INT);
		if (status < 0)
			return status;
		result->poll_bytes[slot][attempt] = (u8)status;
		result->poll_count[slot] = (u8)(attempt + 1U);
		if (status & S22PLUS_MAX77705_AP_CMD_RESPONSE)
			return 0;
		usleep_range(1000, 2000);
	}

	return -ETIMEDOUT;
}

static int s22plus_max77705_control1_read_once(
		struct i2c_client *muic, struct s22plus_max77705_result *result,
		u8 slot, u8 *value)
{
	u8 command[1] = { S22PLUS_MAX77705_CONTROL1_READ };
	u8 response[2] = { 0, 0 };
	int rc;

	result->command_issued_mask |= BIT(slot);
	rc = i2c_smbus_write_i2c_block_data(muic,
			S22PLUS_MAX77705_AP_DATAOUT0, 1, command);
	if (rc < 0)
		return rc;
	rc = i2c_smbus_write_byte_data(muic,
			S22PLUS_MAX77705_AP_DATAOUT_END, 0);
	if (rc < 0)
		return rc;
	rc = s22plus_max77705_wait_ap_response(muic, result, slot);
	if (rc < 0)
		return rc;
	rc = i2c_smbus_read_i2c_block_data(muic,
			S22PLUS_MAX77705_AP_DATAIN0, 2, response);
	if (rc < 0)
		return rc;
	if (rc != 2)
		return -EPROTO;

	result->response_opcode[slot] = response[0];
	result->response_value[slot] = response[1];
	result->response_seen_mask |= BIT(slot);
	if (response[0] != S22PLUS_MAX77705_CONTROL1_READ)
		return -EPROTO;

	*value = response[1];
	return 0;
}

static int s22plus_max77705_control1_write_once(
		struct i2c_client *muic, struct s22plus_max77705_result *result,
		u8 value)
{
	u8 command[2] = { S22PLUS_MAX77705_CONTROL1_WRITE, value };
	int response;
	int rc;

	result->write_attempted = 1U;
	result->write_ambiguous = 1U;
	result->command_issued_mask |= BIT(S22PLUS_MAX77705_SLOT_WRITE);
	rc = i2c_smbus_write_i2c_block_data(muic,
			S22PLUS_MAX77705_AP_DATAOUT0, 2, command);
	if (rc < 0)
		return rc;
	rc = i2c_smbus_write_byte_data(muic,
			S22PLUS_MAX77705_AP_DATAOUT_END, 0);
	if (rc < 0)
		return rc;
	rc = s22plus_max77705_wait_ap_response(muic, result,
			S22PLUS_MAX77705_SLOT_WRITE);
	if (rc < 0)
		return rc;
	response = i2c_smbus_read_byte_data(
			muic, S22PLUS_MAX77705_AP_DATAIN0);
	if (response < 0)
		return response;

	result->response_opcode[S22PLUS_MAX77705_SLOT_WRITE] = (u8)response;
	result->response_seen_mask |= BIT(S22PLUS_MAX77705_SLOT_WRITE);
	if (response != S22PLUS_MAX77705_CONTROL1_WRITE)
		return -EPROTO;

	result->write_ambiguous = 0U;
	return 0;
}

static int s22plus_max77705_diag_run(
		struct i2c_client *parent, struct i2c_client *muic,
		struct s22plus_max77705_result *result)
{
	u8 pre;
	u8 post1;
	u8 post2;
	int rc;

	result->stage = S22PLUS_MAX77705_STAGE_IDENTITY;
	rc = s22plus_max77705_read_pmic_identity(parent, result);
	if (rc < 0)
		return rc;

	result->stage = S22PLUS_MAX77705_STAGE_INITIAL_UIC;
	rc = s22plus_max77705_clear_uic_latch_once(muic, result);
	if (rc < 0)
		return rc;

	result->stage = S22PLUS_MAX77705_STAGE_PRE;
	rc = s22plus_max77705_control1_read_once(muic, result,
			S22PLUS_MAX77705_SLOT_PRE, &pre);
	if (rc < 0)
		return rc;
	result->pre_ns = ktime_get_ns();
	result->timing_valid_mask |= BIT(0);

	if (pre != S22PLUS_MAX77705_COM_USB) {
		result->stage = S22PLUS_MAX77705_STAGE_WRITE;
		result->write_ns = ktime_get_ns();
		result->timing_valid_mask |= BIT(1);
		rc = s22plus_max77705_control1_write_once(
				muic, result, S22PLUS_MAX77705_COM_USB);
		if (rc < 0)
			return rc;
	}

	result->stage = S22PLUS_MAX77705_STAGE_POST1;
	rc = s22plus_max77705_control1_read_once(muic, result,
			S22PLUS_MAX77705_SLOT_POST1, &post1);
	if (rc < 0)
		return rc;
	result->post1_ns = ktime_get_ns();
	result->timing_valid_mask |= BIT(2);

	result->stage = S22PLUS_MAX77705_STAGE_RETENTION;
	msleep(S22PLUS_MAX77705_RETENTION_MS);

	result->stage = S22PLUS_MAX77705_STAGE_POST2;
	rc = s22plus_max77705_control1_read_once(muic, result,
			S22PLUS_MAX77705_SLOT_POST2, &post2);
	if (rc < 0)
		return rc;
	result->post2_ns = ktime_get_ns();
	result->timing_valid_mask |= BIT(3);

	result->stage = S22PLUS_MAX77705_STAGE_COMPLETE;
	return 0;
}

static char *s22plus_max77705_append_poll(
		char *cursor, const u8 *bytes, u8 count)
{
	return bin2hex(cursor, bytes, count);
}

static void s22plus_max77705_cache_result(
		const struct s22plus_max77705_result *result)
{
	char *cursor = cached_result;

	cursor += scnprintf(cursor, PAGE_SIZE - (cursor - cached_result),
			"v=2 stage=%u rc=%d pmic_v=%02x pmic_id=%02x "
			"pmic_rev=%02x uic0_v=%u uic0=%02x issued=%02x "
			"seen=%02x wr_attempt=%u wr_amb=%u tm=%02x "
			"tpre=%llu twrite=%llu tpost1=%llu tpost2=%llu "
			"rsp=%02x%02x%02x%02x val=%02x%02x%02x%02x "
			"p0n=%u p0=",
			result->stage, result->rc, result->pmic_valid_mask,
			result->pmic_id, result->pmic_rev,
			result->initial_uic_valid, result->initial_uic,
			result->command_issued_mask, result->response_seen_mask,
			result->write_attempted, result->write_ambiguous,
			result->timing_valid_mask,
			(unsigned long long)result->pre_ns,
			(unsigned long long)result->write_ns,
			(unsigned long long)result->post1_ns,
			(unsigned long long)result->post2_ns,
			result->response_opcode[0], result->response_opcode[1],
			result->response_opcode[2], result->response_opcode[3],
			result->response_value[0], result->response_value[1],
			result->response_value[2], result->response_value[3],
			result->poll_count[0]);
	cursor = s22plus_max77705_append_poll(cursor, result->poll_bytes[0],
			result->poll_count[0]);
	cursor += scnprintf(cursor, PAGE_SIZE - (cursor - cached_result),
			" p1n=%u p1=", result->poll_count[1]);
	cursor = s22plus_max77705_append_poll(cursor, result->poll_bytes[1],
			result->poll_count[1]);
	cursor += scnprintf(cursor, PAGE_SIZE - (cursor - cached_result),
			" p2n=%u p2=", result->poll_count[2]);
	cursor = s22plus_max77705_append_poll(cursor, result->poll_bytes[2],
			result->poll_count[2]);
	cursor += scnprintf(cursor, PAGE_SIZE - (cursor - cached_result),
			" p3n=%u p3=", result->poll_count[3]);
	cursor = s22plus_max77705_append_poll(cursor, result->poll_bytes[3],
			result->poll_count[3]);
	scnprintf(cursor, PAGE_SIZE - (cursor - cached_result), "\n");
	smp_store_release(&cached_result_ready, 1);
}

static int s22plus_max77705_diag_probe(
		struct i2c_client *parent, const struct i2c_device_id *id)
{
	struct i2c_client *muic;
	int rc;

	(void)id;
	if (parent->addr != S22PLUS_MAX77705_PARENT_ADDR)
		return -ENODEV;
	if (atomic_cmpxchg(&s22plus_max77705_claimed, 0, 1) != 0)
		return -EBUSY;

	s22plus_max77705_result.stage = S22PLUS_MAX77705_STAGE_CLAIMED;
	muic = devm_i2c_new_dummy_device(&parent->dev, parent->adapter,
			S22PLUS_MAX77705_MUIC_ADDR);
	if (IS_ERR(muic)) {
		s22plus_max77705_result.stage =
			S22PLUS_MAX77705_STAGE_DUMMY_CLIENT;
		rc = PTR_ERR(muic);
	} else {
		rc = s22plus_max77705_diag_run(parent, muic,
				&s22plus_max77705_result);
	}

	s22plus_max77705_result.rc = rc;
	s22plus_max77705_cache_result(&s22plus_max77705_result);

	/* Keep the one attempted probe bound so the I2C core cannot retry it. */
	return 0;
}

static const struct of_device_id s22plus_max77705_diag_of_match[] = {
	{ .compatible = S22PLUS_MAX77705_PARENT_COMPATIBLE },
	{ }
};

static int s22plus_max77705_result_get(
		char *buffer, const struct kernel_param *parameter)
{
	(void)parameter;
	if (!smp_load_acquire(&cached_result_ready))
		return -EAGAIN;
	return scnprintf(buffer, PAGE_SIZE, "%s", cached_result);
}

static const struct kernel_param_ops s22plus_max77705_result_ops = {
	.set = NULL,
	.get = s22plus_max77705_result_get,
};

module_param_cb(result, &s22plus_max77705_result_ops, NULL, 0444);
MODULE_PARM_DESC(result,
		"cached bounded P3.18 Max77705 MUX diagnostic result");

static struct i2c_driver s22plus_max77705_diag_driver = {
	.driver = {
		.name = "s22plus_max77705_mux_diag_p318",
		.of_match_table = s22plus_max77705_diag_of_match,
		.probe_type = PROBE_FORCE_SYNCHRONOUS,
	},
	.probe = s22plus_max77705_diag_probe,
};

module_i2c_driver(s22plus_max77705_diag_driver);

MODULE_DESCRIPTION("Bounded S22+ P3.18 timed Max77705 CONTROL1 diagnostic");
MODULE_LICENSE("GPL v2");
