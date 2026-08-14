/* Strict parser for the P3.18 early DWC3 latch module parameters. */

struct s22plus_max77705_p318_latch_snapshot {
	uint8_t install_valid;
	uint8_t exposure_valid;
	uint8_t event_valid;
	uint8_t event_kind;
	uint64_t install_ns;
	uint64_t exposure_ns;
	uint64_t event_ns;
	uint32_t event_raw;
};

struct s22plus_p318_latch_cursor {
	const char *value;
	const char *end;
};

static int s22plus_p318_latch_expect(
		struct s22plus_p318_latch_cursor *cursor, const char *literal)
{
	while (*literal != '\0') {
		if (cursor->value == cursor->end || *cursor->value != *literal)
			return -1;
		++cursor->value;
		++literal;
	}
	return 0;
}

static int s22plus_p318_latch_u64(
		struct s22plus_p318_latch_cursor *cursor, uint64_t maximum,
		uint64_t *output)
{
	const char *start = cursor->value;
	uint64_t value = 0U;

	if (start == cursor->end || *start < '0' || *start > '9')
		return -1;
	if (*start == '0' && start + 1 < cursor->end &&
	    start[1] >= '0' && start[1] <= '9')
		return -1;
	while (cursor->value != cursor->end &&
	       *cursor->value >= '0' && *cursor->value <= '9') {
		uint64_t digit = (uint64_t)(*cursor->value - '0');

		if (value > (maximum - digit) / 10U)
			return -1;
		value = value * 10U + digit;
		++cursor->value;
	}
	*output = value;
	return 0;
}

static int s22plus_p318_latch_hex8(
		struct s22plus_p318_latch_cursor *cursor, uint32_t *output)
{
	uint32_t value = 0U;
	unsigned int index;

	if ((size_t)(cursor->end - cursor->value) < 8U)
		return -1;
	for (index = 0U; index < 8U; ++index) {
		char byte = cursor->value[index];
		uint32_t nibble;

		if (byte >= '0' && byte <= '9')
			nibble = (uint32_t)(byte - '0');
		else if (byte >= 'a' && byte <= 'f')
			nibble = (uint32_t)(byte - 'a' + 10);
		else
			return -1;
		value = (value << 4U) | nibble;
	}
	cursor->value += 8U;
	*output = value;
	return 0;
}

static int s22plus_p318_latch_raw_matches(uint8_t kind, uint32_t raw)
{
	uint32_t event_class = (raw >> 1U) & 0x7fU;

	if (kind == 1U || kind == 2U)
		return (raw & 1U) != 0U && event_class == 0U &&
			((raw >> 8U) & 0x0fU) == kind;
	if (kind == 3U)
		return (raw & 1U) == 0U && ((raw >> 1U) & 0x1fU) == 0U &&
			((raw >> 6U) & 0x0fU) == 1U;
	return kind == 0U && raw == 0U;
}

static int s22plus_p318_latch_snapshot_valid(
		const struct s22plus_max77705_p318_latch_snapshot *snapshot)
{
	if (snapshot == NULL || snapshot->install_valid != 1U ||
	    snapshot->exposure_valid > 1U || snapshot->event_valid > 1U ||
	    snapshot->install_ns == 0U ||
	    (snapshot->exposure_valid == 0U && snapshot->exposure_ns != 0U) ||
	    (snapshot->exposure_valid != 0U &&
	     (snapshot->exposure_ns == 0U ||
	      snapshot->install_ns > snapshot->exposure_ns)) ||
	    (snapshot->event_valid == 0U &&
	     (snapshot->event_ns != 0U || snapshot->event_kind != 0U ||
	      snapshot->event_raw != 0U)) ||
	    (snapshot->event_valid != 0U &&
	     (snapshot->exposure_valid == 0U || snapshot->event_ns == 0U ||
	      snapshot->event_ns < snapshot->exposure_ns ||
	      snapshot->event_kind < 1U || snapshot->event_kind > 3U ||
	      !s22plus_p318_latch_raw_matches(
		 snapshot->event_kind, snapshot->event_raw))))
		return 0;
	return 1;
}

static int s22plus_p318_parse_latch_snapshot(
		const char *input, size_t input_size,
		struct s22plus_max77705_p318_latch_snapshot *snapshot)
{
	struct s22plus_p318_latch_cursor cursor;
	uint64_t value;
	uint8_t *bytes;
	size_t index;

	if (input == NULL || snapshot == NULL || input_size == 0U)
		return -1;
	bytes = (uint8_t *)snapshot;
	for (index = 0U; index < sizeof(*snapshot); ++index)
		bytes[index] = 0U;
	cursor.value = input;
	cursor.end = input + input_size;
#define P318_LATCH_EXPECT(literal) do { \
	if (s22plus_p318_latch_expect(&cursor, (literal)) != 0) return -1; \
} while (0)
#define P318_LATCH_DECIMAL(field, maximum) do { \
	if (s22plus_p318_latch_u64(&cursor, (maximum), &value) != 0) return -1; \
	(field) = (uint8_t)value; \
} while (0)
	P318_LATCH_EXPECT("v=1 install_v=");
	P318_LATCH_DECIMAL(snapshot->install_valid, 1U);
	P318_LATCH_EXPECT(" install_ns=");
	if (s22plus_p318_latch_u64(&cursor, UINT64_MAX, &snapshot->install_ns) != 0)
		return -1;
	P318_LATCH_EXPECT(" gate_v=");
	P318_LATCH_DECIMAL(snapshot->exposure_valid, 1U);
	P318_LATCH_EXPECT(" gate_ns=");
	if (s22plus_p318_latch_u64(&cursor, UINT64_MAX, &snapshot->exposure_ns) != 0)
		return -1;
	P318_LATCH_EXPECT(" event_v=");
	P318_LATCH_DECIMAL(snapshot->event_valid, 1U);
	P318_LATCH_EXPECT(" event_ns=");
	if (s22plus_p318_latch_u64(&cursor, UINT64_MAX, &snapshot->event_ns) != 0)
		return -1;
	P318_LATCH_EXPECT(" kind=");
	P318_LATCH_DECIMAL(snapshot->event_kind, 3U);
	P318_LATCH_EXPECT(" raw=");
	if (s22plus_p318_latch_hex8(&cursor, &snapshot->event_raw) != 0)
		return -1;
	P318_LATCH_EXPECT("\n");
#undef P318_LATCH_DECIMAL
#undef P318_LATCH_EXPECT
	if (cursor.value != cursor.end ||
	    !s22plus_p318_latch_snapshot_valid(snapshot))
		return -1;
	return 0;
}

static int s22plus_p318_exposure_gate_readback_valid(
		const char *input, size_t input_size)
{
	return input != NULL && input_size == 2U &&
		input[0] == '1' && input[1] == '\n';
}
