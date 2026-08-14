/*
 * Strict, allocation-free parser for the read-only P3.18 timed Max77705 diagnostic
 * module-parameter result.  This file is intended to be included by the S22+
 * native PID1 runtime after <stddef.h> and <stdint.h> are available.
 *
 * It performs no I/O and names no sysfs path.  A future target-specific
 * transform may call it only after a fresh D0 fixes the exact device paths and
 * binding state.  The SHA-256 implementation is adapted from the existing S22
 * native-init implementation in s22plus_init_v3429_phase_observer.c; its
 * output is cross-checked against the Python telemetry authority by the host
 * fixture.
 */

#define S22PLUS_MAX77705_RUNTIME_COMMANDS 4U
#define S22PLUS_MAX77705_RUNTIME_POLL_LIMIT 100U
#define S22PLUS_MAX77705_RUNTIME_APCMDRES 0x80U
#define S22PLUS_MAX77705_RUNTIME_STAGE_PRE 5U
#define S22PLUS_MAX77705_RUNTIME_STAGE_WRITE 6U
#define S22PLUS_MAX77705_RUNTIME_STAGE_POST1 7U
#define S22PLUS_MAX77705_RUNTIME_STAGE_POST2 9U
#define S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE 10U
#define S22PLUS_MAX77705_RUNTIME_ETIMEDOUT (-110)
#define S22PLUS_MAX77705_RUNTIME_RETENTION_NS 30000000000ULL

enum s22plus_max77705_runtime_parse_status {
	S22PLUS_MAX77705_RUNTIME_PARSE_OK = 0,
	S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX = -1,
	S22PLUS_MAX77705_RUNTIME_PARSE_RANGE = -2,
	S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC = -3,
};

struct s22plus_max77705_runtime_result {
	uint8_t stage;
	int32_t rc;
	uint8_t pmic_valid_mask;
	uint8_t pmic_id;
	uint8_t pmic_rev;
	uint8_t initial_uic_valid;
	uint8_t initial_uic;
	uint8_t command_issued_mask;
	uint8_t response_seen_mask;
	uint8_t write_attempted;
	uint8_t write_ambiguous;
	uint8_t response_opcode[S22PLUS_MAX77705_RUNTIME_COMMANDS];
	uint8_t response_value[S22PLUS_MAX77705_RUNTIME_COMMANDS];
	uint8_t poll_count[S22PLUS_MAX77705_RUNTIME_COMMANDS];
	uint8_t poll_bytes[S22PLUS_MAX77705_RUNTIME_COMMANDS]
		[S22PLUS_MAX77705_RUNTIME_POLL_LIMIT];
	uint8_t timing_valid_mask;
	uint64_t pre_ns;
	uint64_t write_ns;
	uint64_t post1_ns;
	uint64_t post2_ns;
};

struct s22plus_max77705_runtime_poll_summary {
	uint8_t sha256[32];
	uint8_t or_mask[S22PLUS_MAX77705_RUNTIME_COMMANDS];
	uint8_t poll0[S22PLUS_MAX77705_RUNTIME_COMMANDS];
	uint8_t nonzero_count[S22PLUS_MAX77705_RUNTIME_COMMANDS];
	uint16_t raw_count;
};

struct s22plus_max77705_runtime_cursor {
	const char *value;
	const char *end;
};

struct s22plus_max77705_runtime_sha256 {
	uint32_t state[8];
	uint64_t bit_count;
	uint8_t block[64];
	size_t block_len;
};

static void s22plus_max77705_runtime_zero(void *value, size_t size)
{
	uint8_t *cursor = (uint8_t *)value;

	while (size-- > 0U)
		*cursor++ = 0U;
}

static int s22plus_max77705_runtime_expect(
		struct s22plus_max77705_runtime_cursor *cursor,
		const char *literal)
{
	while (*literal != '\0') {
		if (cursor->value == cursor->end ||
		    *cursor->value != *literal)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
		++cursor->value;
		++literal;
	}
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_decimal(
		struct s22plus_max77705_runtime_cursor *cursor,
		uint32_t maximum, uint32_t *result)
{
	const char *start = cursor->value;
	uint32_t value = 0U;

	if (start == cursor->end || *start < '0' || *start > '9')
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	if (*start == '0' && start + 1 < cursor->end &&
	    start[1] >= '0' && start[1] <= '9')
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	while (cursor->value != cursor->end &&
	       *cursor->value >= '0' && *cursor->value <= '9') {
		uint32_t digit = (uint32_t)(*cursor->value - '0');

		if (value > (maximum - digit) / 10U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_RANGE;
		value = value * 10U + digit;
		++cursor->value;
	}
	*result = value;
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_u64_decimal(
		struct s22plus_max77705_runtime_cursor *cursor,
		uint64_t *result)
{
	const char *start = cursor->value;
	uint64_t value = 0U;

	if (start == cursor->end || *start < '0' || *start > '9')
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	if (*start == '0' && start + 1 < cursor->end &&
	    start[1] >= '0' && start[1] <= '9')
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	while (cursor->value != cursor->end &&
	       *cursor->value >= '0' && *cursor->value <= '9') {
		uint64_t digit = (uint64_t)(*cursor->value - '0');

		if (value > (UINT64_MAX - digit) / 10U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_RANGE;
		value = value * 10U + digit;
		++cursor->value;
	}
	*result = value;
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_signed_decimal(
		struct s22plus_max77705_runtime_cursor *cursor, int32_t *result)
{
	int negative = 0;
	uint32_t magnitude;
	uint32_t maximum;
	int rc;

	if (cursor->value != cursor->end && *cursor->value == '-') {
		negative = 1;
		++cursor->value;
	}
	maximum = negative ? 0x80000000U : 0x7fffffffU;
	rc = s22plus_max77705_runtime_decimal(cursor, maximum, &magnitude);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	if (negative && magnitude == 0U)
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	if (negative) {
		if (magnitude == 0x80000000U)
			*result = (int32_t)(-2147483647 - 1);
		else
			*result = -(int32_t)magnitude;
	} else {
		*result = (int32_t)magnitude;
	}
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_hex_nibble(char value, uint8_t *result)
{
	if (value >= '0' && value <= '9') {
		*result = (uint8_t)(value - '0');
		return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
	}
	if (value >= 'a' && value <= 'f') {
		*result = (uint8_t)(value - 'a' + 10);
		return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
	}
	return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
}

static int s22plus_max77705_runtime_hex_byte(
		struct s22plus_max77705_runtime_cursor *cursor, uint8_t *result)
{
	uint8_t high;
	uint8_t low;
	int rc;

	if ((size_t)(cursor->end - cursor->value) < 2U)
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	rc = s22plus_max77705_runtime_hex_nibble(cursor->value[0], &high);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	rc = s22plus_max77705_runtime_hex_nibble(cursor->value[1], &low);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	cursor->value += 2;
	*result = (uint8_t)((high << 4) | low);
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_parse_u8_decimal(
		struct s22plus_max77705_runtime_cursor *cursor, uint8_t *result)
{
	uint32_t value;
	int rc = s22plus_max77705_runtime_decimal(cursor, 255U, &value);

	if (rc == S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		*result = (uint8_t)value;
	return rc;
}

static uint32_t s22plus_max77705_runtime_rotr(uint32_t value, uint32_t shift)
{
	return (value >> shift) | (value << (32U - shift));
}

static uint32_t s22plus_max77705_runtime_load32(const uint8_t *data)
{
	return ((uint32_t)data[0] << 24) |
	       ((uint32_t)data[1] << 16) |
	       ((uint32_t)data[2] << 8) |
	       (uint32_t)data[3];
}

static void s22plus_max77705_runtime_store32(uint8_t *output, uint32_t value)
{
	output[0] = (uint8_t)(value >> 24);
	output[1] = (uint8_t)(value >> 16);
	output[2] = (uint8_t)(value >> 8);
	output[3] = (uint8_t)value;
}

static void s22plus_max77705_runtime_sha256_transform(
		struct s22plus_max77705_runtime_sha256 *context,
		const uint8_t block[64])
{
	static const uint32_t constants[64] = {
		0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
		0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
		0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
		0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
		0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
		0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
		0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
		0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
		0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
		0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
		0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
		0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
		0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
		0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
		0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
		0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
	};
	uint32_t words[64];
	uint32_t a = context->state[0];
	uint32_t b = context->state[1];
	uint32_t c = context->state[2];
	uint32_t d = context->state[3];
	uint32_t e = context->state[4];
	uint32_t f = context->state[5];
	uint32_t g = context->state[6];
	uint32_t h = context->state[7];
	size_t index;

	for (index = 0U; index < 16U; ++index)
		words[index] = s22plus_max77705_runtime_load32(block + index * 4U);
	for (index = 16U; index < 64U; ++index) {
		uint32_t s0 = s22plus_max77705_runtime_rotr(words[index - 15U], 7U) ^
			s22plus_max77705_runtime_rotr(words[index - 15U], 18U) ^
			(words[index - 15U] >> 3U);
		uint32_t s1 = s22plus_max77705_runtime_rotr(words[index - 2U], 17U) ^
			s22plus_max77705_runtime_rotr(words[index - 2U], 19U) ^
			(words[index - 2U] >> 10U);

		words[index] = words[index - 16U] + s0 + words[index - 7U] + s1;
	}
	for (index = 0U; index < 64U; ++index) {
		uint32_t sum1 = s22plus_max77705_runtime_rotr(e, 6U) ^
			s22plus_max77705_runtime_rotr(e, 11U) ^
			s22plus_max77705_runtime_rotr(e, 25U);
		uint32_t choose = (e & f) ^ ((~e) & g);
		uint32_t temp1 = h + sum1 + choose + constants[index] + words[index];
		uint32_t sum0 = s22plus_max77705_runtime_rotr(a, 2U) ^
			s22plus_max77705_runtime_rotr(a, 13U) ^
			s22plus_max77705_runtime_rotr(a, 22U);
		uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
		uint32_t temp2 = sum0 + majority;

		h = g;
		g = f;
		f = e;
		e = d + temp1;
		d = c;
		c = b;
		b = a;
		a = temp1 + temp2;
	}
	context->state[0] += a;
	context->state[1] += b;
	context->state[2] += c;
	context->state[3] += d;
	context->state[4] += e;
	context->state[5] += f;
	context->state[6] += g;
	context->state[7] += h;
}

static void s22plus_max77705_runtime_sha256_init(
		struct s22plus_max77705_runtime_sha256 *context)
{
	context->state[0] = 0x6a09e667U;
	context->state[1] = 0xbb67ae85U;
	context->state[2] = 0x3c6ef372U;
	context->state[3] = 0xa54ff53aU;
	context->state[4] = 0x510e527fU;
	context->state[5] = 0x9b05688cU;
	context->state[6] = 0x1f83d9abU;
	context->state[7] = 0x5be0cd19U;
	context->bit_count = 0U;
	context->block_len = 0U;
}

static void s22plus_max77705_runtime_sha256_update(
		struct s22plus_max77705_runtime_sha256 *context,
		const uint8_t *data, size_t size)
{
	context->bit_count += (uint64_t)size * 8U;
	while (size > 0U) {
		size_t available = sizeof(context->block) - context->block_len;
		size_t amount = size < available ? size : available;
		size_t index;

		for (index = 0U; index < amount; ++index)
			context->block[context->block_len + index] = data[index];
		context->block_len += amount;
		data += amount;
		size -= amount;
		if (context->block_len == sizeof(context->block)) {
			s22plus_max77705_runtime_sha256_transform(
				context, context->block);
			context->block_len = 0U;
		}
	}
}

static void s22plus_max77705_runtime_sha256_final(
		struct s22plus_max77705_runtime_sha256 *context,
		uint8_t digest[32])
{
	uint8_t length[8];
	size_t index;

	context->block[context->block_len++] = 0x80U;
	if (context->block_len > 56U) {
		while (context->block_len < sizeof(context->block))
			context->block[context->block_len++] = 0U;
		s22plus_max77705_runtime_sha256_transform(context, context->block);
		context->block_len = 0U;
	}
	while (context->block_len < 56U)
		context->block[context->block_len++] = 0U;
	for (index = 0U; index < sizeof(length); ++index)
		length[7U - index] =
			(uint8_t)(context->bit_count >> (index * 8U));
	for (index = 0U; index < sizeof(length); ++index)
		context->block[56U + index] = length[index];
	s22plus_max77705_runtime_sha256_transform(context, context->block);
	for (index = 0U; index < 8U; ++index)
		s22plus_max77705_runtime_store32(
			digest + index * 4U, context->state[index]);
}

static int s22plus_max77705_runtime_active_timeout_slot(uint8_t stage)
{
	switch (stage) {
	case S22PLUS_MAX77705_RUNTIME_STAGE_PRE:
		return 0;
	case S22PLUS_MAX77705_RUNTIME_STAGE_WRITE:
		return 1;
	case S22PLUS_MAX77705_RUNTIME_STAGE_POST1:
		return 2;
	case S22PLUS_MAX77705_RUNTIME_STAGE_POST2:
		return 3;
	default:
		return -1;
	}
}

static int s22plus_max77705_runtime_summarize(
		const struct s22plus_max77705_runtime_result *result,
		struct s22plus_max77705_runtime_poll_summary *summary)
{
	struct s22plus_max77705_runtime_sha256 context;
	uint32_t raw_count = 0U;
	unsigned int slot;

	s22plus_max77705_runtime_zero(summary, sizeof(*summary));
	s22plus_max77705_runtime_sha256_init(&context);
	for (slot = 0U; slot < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++slot) {
		unsigned int index;

		if (result->poll_count[slot] > S22PLUS_MAX77705_RUNTIME_POLL_LIMIT)
			return S22PLUS_MAX77705_RUNTIME_PARSE_RANGE;
		raw_count += result->poll_count[slot];
		if (result->poll_count[slot] > 0U)
			summary->poll0[slot] = result->poll_bytes[slot][0];
		for (index = 0U; index < result->poll_count[slot]; ++index) {
			uint8_t value = result->poll_bytes[slot][index];

			summary->or_mask[slot] |= value;
			if (value != 0U)
				++summary->nonzero_count[slot];
		}
		s22plus_max77705_runtime_sha256_update(
			&context, result->poll_bytes[slot], result->poll_count[slot]);
	}
	if (raw_count > 400U)
		return S22PLUS_MAX77705_RUNTIME_PARSE_RANGE;
	summary->raw_count = (uint16_t)raw_count;
	s22plus_max77705_runtime_sha256_final(&context, summary->sha256);
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_validate_semantics(
		const struct s22plus_max77705_runtime_result *result,
		const struct s22plus_max77705_runtime_poll_summary *summary)
{
	uint8_t issued;
	uint8_t seen;
	unsigned int slot;

	if (result->stage < 2U ||
	    result->stage > S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE ||
	    result->pmic_valid_mask > 3U ||
	    result->initial_uic_valid > 1U ||
	    result->write_attempted > 1U ||
	    result->write_ambiguous > 1U ||
	    (result->command_issued_mask & 0xf0U) != 0U ||
	    (result->response_seen_mask & 0xf0U) != 0U ||
	    (result->response_seen_mask & ~result->command_issued_mask) != 0U ||
	    (result->timing_valid_mask & 0xf0U) != 0U)
		return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	if (((result->timing_valid_mask & 0x01U) != 0U) !=
	    (result->pre_ns != 0U) ||
	    ((result->timing_valid_mask & 0x02U) != 0U) !=
	    (result->write_ns != 0U) ||
	    ((result->timing_valid_mask & 0x04U) != 0U) !=
	    (result->post1_ns != 0U) ||
	    ((result->timing_valid_mask & 0x08U) != 0U) !=
	    (result->post2_ns != 0U) ||
	    ((result->timing_valid_mask & 0x02U) != 0U) !=
	    (result->write_attempted != 0U) ||
	    ((result->timing_valid_mask & 0x03U) == 0x03U &&
	     result->pre_ns > result->write_ns) ||
	    ((result->timing_valid_mask & 0x05U) == 0x05U &&
	     result->pre_ns > result->post1_ns) ||
	    ((result->timing_valid_mask & 0x06U) == 0x06U &&
	     result->write_ns > result->post1_ns) ||
	    ((result->timing_valid_mask & 0x0cU) == 0x0cU &&
	     (result->post1_ns > result->post2_ns ||
	      result->post2_ns - result->post1_ns <
		S22PLUS_MAX77705_RUNTIME_RETENTION_NS)))
		return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	if ((result->rc == 0) !=
	    (result->stage == S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE) ||
	    (result->command_issued_mask != 0x00U &&
	     result->command_issued_mask != 0x01U &&
	     result->command_issued_mask != 0x03U &&
	     result->command_issued_mask != 0x05U &&
	     result->command_issued_mask != 0x07U &&
	     result->command_issued_mask != 0x0dU &&
	     result->command_issued_mask != 0x0fU) ||
	    (result->response_seen_mask != 0x00U &&
	     result->response_seen_mask != 0x01U &&
	     result->response_seen_mask != 0x03U &&
	     result->response_seen_mask != 0x05U &&
	     result->response_seen_mask != 0x07U &&
	     result->response_seen_mask != 0x0dU &&
	     result->response_seen_mask != 0x0fU) ||
	    result->write_attempted !=
		((result->command_issued_mask & 0x02U) != 0U) ||
	    (result->write_ambiguous != 0U && result->write_attempted == 0U))
		return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	issued = result->command_issued_mask;
	seen = result->response_seen_mask;
	/*
	 * The module publishes the stage before each fallible operation.  These
	 * are therefore source-reachability constraints, not a second protocol
	 * implementation.  In particular, RETENTION has no fallible operation
	 * and can never be a terminal cached result.
	 */
	switch (result->stage) {
	case 2U: /* identity */
	case 3U: /* dummy client */
	case 4U: /* initial UIC read */
		if (issued != 0U || seen != 0U || result->write_attempted != 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		if (result->timing_valid_mask != 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		break;
	case S22PLUS_MAX77705_RUNTIME_STAGE_PRE:
		if (issued != 0x01U || (seen != 0U && seen != 0x01U) ||
		    result->write_attempted != 0U ||
		    result->timing_valid_mask != 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		break;
	case S22PLUS_MAX77705_RUNTIME_STAGE_WRITE:
		if (issued != 0x03U || (seen != 0x01U && seen != 0x03U) ||
		    result->response_seen_mask == 0U ||
		    result->response_opcode[0] != 0x05U ||
		    result->response_value[0] == 0x09U ||
		    result->write_attempted != 1U ||
		    result->write_ambiguous != 1U ||
		    result->timing_valid_mask != 0x03U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		break;
	case S22PLUS_MAX77705_RUNTIME_STAGE_POST1: {
		uint8_t expected_issued = result->response_value[0] == 0x09U
			? 0x05U : 0x07U;
		uint8_t prefix_seen = result->response_value[0] == 0x09U
			? 0x01U : 0x03U;

		if (issued != expected_issued ||
		    (seen != prefix_seen && seen != expected_issued) ||
		    result->response_opcode[0] != 0x05U ||
		    (result->response_value[0] == 0x09U
			? (result->write_attempted != 0U ||
			   result->response_opcode[1] != 0U ||
			   result->response_value[1] != 0U)
			: (result->write_attempted != 1U ||
			   result->write_ambiguous != 0U ||
			   result->response_opcode[1] != 0x06U ||
			   result->response_value[1] != 0U)) ||
		    result->timing_valid_mask !=
			(result->write_attempted != 0U ? 0x03U : 0x01U))
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		break;
	}
	case 8U: /* retention sleep cannot return an errno */
		return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	case S22PLUS_MAX77705_RUNTIME_STAGE_POST2: {
		uint8_t expected_issued = result->response_value[0] == 0x09U
			? 0x0dU : 0x0fU;
		uint8_t prefix_seen = result->response_value[0] == 0x09U
			? 0x05U : 0x07U;

		if (issued != expected_issued ||
		    (seen != prefix_seen && seen != expected_issued) ||
		    result->response_opcode[0] != 0x05U ||
		    result->response_opcode[2] != 0x05U ||
		    (result->response_value[0] == 0x09U
			? (result->write_attempted != 0U ||
			   result->response_opcode[1] != 0U ||
			   result->response_value[1] != 0U)
			: (result->write_attempted != 1U ||
			   result->write_ambiguous != 0U ||
			   result->response_opcode[1] != 0x06U ||
			   result->response_value[1] != 0U)) ||
		    result->timing_valid_mask !=
			(result->write_attempted != 0U ? 0x07U : 0x05U))
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		break;
	}
	case S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE:
		if (result->timing_valid_mask !=
		    (result->write_attempted != 0U ? 0x0fU : 0x0dU))
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		break;
	default:
		return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	}
	for (slot = 0U; slot < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++slot) {
		uint8_t bit = (uint8_t)(1U << slot);

		if (result->poll_count[slot] > 0U &&
		    (result->command_issued_mask & bit) == 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
		if ((result->response_seen_mask & bit) != 0U &&
		    (summary->or_mask[slot] &
		     S22PLUS_MAX77705_RUNTIME_APCMDRES) == 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	}
	if (result->rc == S22PLUS_MAX77705_RUNTIME_ETIMEDOUT) {
		int slot_index =
			s22plus_max77705_runtime_active_timeout_slot(result->stage);

		if (slot_index < 0 ||
		    (summary->or_mask[(unsigned int)slot_index] &
		     S22PLUS_MAX77705_RUNTIME_APCMDRES) != 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	}
	if (result->stage == S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE &&
	    result->rc == 0) {
		if ((result->command_issued_mask != 0x0dU &&
		     result->command_issued_mask != 0x0fU) ||
		    result->response_seen_mask != result->command_issued_mask ||
		    result->response_opcode[0] != 0x05U ||
		    result->response_opcode[2] != 0x05U ||
		    result->response_opcode[3] != 0x05U ||
		    ((result->command_issued_mask & 0x02U) != 0U &&
		     result->response_opcode[1] != 0x06U) ||
		    result->response_value[1] != 0U ||
		    result->write_attempted !=
			((result->command_issued_mask & 0x02U) != 0U) ||
		    (result->response_value[0] == 0x09U) !=
			(result->write_attempted == 0U) ||
		    result->write_ambiguous != 0U)
			return S22PLUS_MAX77705_RUNTIME_PARSE_SEMANTIC;
	}
	return S22PLUS_MAX77705_RUNTIME_PARSE_OK;
}

static int s22plus_max77705_runtime_parse_result(
		const char *input, size_t input_size,
		struct s22plus_max77705_runtime_result *result,
		struct s22plus_max77705_runtime_poll_summary *summary)
{
	struct s22plus_max77705_runtime_cursor cursor;
	uint32_t stage;
	unsigned int index;
	int rc;

	if (input == (const char *)0 || result == (void *)0 ||
	    summary == (void *)0 || input_size == 0U)
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;
	s22plus_max77705_runtime_zero(result, sizeof(*result));
	s22plus_max77705_runtime_zero(summary, sizeof(*summary));
	cursor.value = input;
	cursor.end = input + input_size;

#define S22PLUS_MAX77705_EXPECT(value) do { \
	rc = s22plus_max77705_runtime_expect(&cursor, (value)); \
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK) \
		return rc; \
} while (0)
#define S22PLUS_MAX77705_PARSE_U8(field) do { \
	rc = s22plus_max77705_runtime_parse_u8_decimal(&cursor, &(field)); \
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK) \
		return rc; \
} while (0)
#define S22PLUS_MAX77705_PARSE_HEX(field) do { \
	rc = s22plus_max77705_runtime_hex_byte(&cursor, &(field)); \
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK) \
		return rc; \
} while (0)

	S22PLUS_MAX77705_EXPECT("v=2 stage=");
	rc = s22plus_max77705_runtime_decimal(
		&cursor, S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE, &stage);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	result->stage = (uint8_t)stage;
	S22PLUS_MAX77705_EXPECT(" rc=");
	rc = s22plus_max77705_runtime_signed_decimal(&cursor, &result->rc);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	S22PLUS_MAX77705_EXPECT(" pmic_v=");
	S22PLUS_MAX77705_PARSE_HEX(result->pmic_valid_mask);
	S22PLUS_MAX77705_EXPECT(" pmic_id=");
	S22PLUS_MAX77705_PARSE_HEX(result->pmic_id);
	S22PLUS_MAX77705_EXPECT(" pmic_rev=");
	S22PLUS_MAX77705_PARSE_HEX(result->pmic_rev);
	S22PLUS_MAX77705_EXPECT(" uic0_v=");
	S22PLUS_MAX77705_PARSE_U8(result->initial_uic_valid);
	S22PLUS_MAX77705_EXPECT(" uic0=");
	S22PLUS_MAX77705_PARSE_HEX(result->initial_uic);
	S22PLUS_MAX77705_EXPECT(" issued=");
	S22PLUS_MAX77705_PARSE_HEX(result->command_issued_mask);
	S22PLUS_MAX77705_EXPECT(" seen=");
	S22PLUS_MAX77705_PARSE_HEX(result->response_seen_mask);
	S22PLUS_MAX77705_EXPECT(" wr_attempt=");
	S22PLUS_MAX77705_PARSE_U8(result->write_attempted);
	S22PLUS_MAX77705_EXPECT(" wr_amb=");
	S22PLUS_MAX77705_PARSE_U8(result->write_ambiguous);
	S22PLUS_MAX77705_EXPECT(" tm=");
	S22PLUS_MAX77705_PARSE_HEX(result->timing_valid_mask);
	S22PLUS_MAX77705_EXPECT(" tpre=");
	rc = s22plus_max77705_runtime_u64_decimal(&cursor, &result->pre_ns);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	S22PLUS_MAX77705_EXPECT(" twrite=");
	rc = s22plus_max77705_runtime_u64_decimal(&cursor, &result->write_ns);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	S22PLUS_MAX77705_EXPECT(" tpost1=");
	rc = s22plus_max77705_runtime_u64_decimal(&cursor, &result->post1_ns);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	S22PLUS_MAX77705_EXPECT(" tpost2=");
	rc = s22plus_max77705_runtime_u64_decimal(&cursor, &result->post2_ns);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	S22PLUS_MAX77705_EXPECT(" rsp=");
	for (index = 0U; index < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++index)
		S22PLUS_MAX77705_PARSE_HEX(result->response_opcode[index]);
	S22PLUS_MAX77705_EXPECT(" val=");
	for (index = 0U; index < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++index)
		S22PLUS_MAX77705_PARSE_HEX(result->response_value[index]);
	S22PLUS_MAX77705_EXPECT(" p0n=");
	for (index = 0U; index < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++index) {
		if (index != 0U) {
			char expected[6] = { ' ', 'p', (char)('0' + index),
				'n', '=', '\0' };

			S22PLUS_MAX77705_EXPECT(expected);
		}
		rc = s22plus_max77705_runtime_decimal(
			&cursor, S22PLUS_MAX77705_RUNTIME_POLL_LIMIT, &stage);
		if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
			return rc;
		result->poll_count[index] = (uint8_t)stage;
		{
			char expected[5] = { ' ', 'p', (char)('0' + index), '=', '\0' };

			S22PLUS_MAX77705_EXPECT(expected);
		}
		for (stage = 0U; stage < result->poll_count[index]; ++stage)
			S22PLUS_MAX77705_PARSE_HEX(result->poll_bytes[index][stage]);
	}
	S22PLUS_MAX77705_EXPECT("\n");
	if (cursor.value != cursor.end)
		return S22PLUS_MAX77705_RUNTIME_PARSE_SYNTAX;

#undef S22PLUS_MAX77705_PARSE_HEX
#undef S22PLUS_MAX77705_PARSE_U8
#undef S22PLUS_MAX77705_EXPECT

	rc = s22plus_max77705_runtime_summarize(result, summary);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return rc;
	return s22plus_max77705_runtime_validate_semantics(result, summary);
}
