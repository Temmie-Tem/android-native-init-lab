/*
 * Native Max77705 Carrier-v2 envelope encoder.
 *
 * This file is included after s22plus_fyg8_max77705_result_parser.inc.c and
 * the inherited checkpoint CRC helper.  It deliberately consumes the exact
 * parsed result structure instead of re-parsing or reimplementing the module
 * ABI at the publication seam.
 */

#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U
#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U
#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET 48U
#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE 76U
#define S22PLUS_MAX77705_ENVELOPE_OVERFLOW_SIZE 44U
#define S22PLUS_MAX77705_A_DETAIL 0xda3U
#define S22PLUS_MAX77705_B_DETAIL_BASE 0x6701U

#define S22PLUS_MAX77705_FLAG_RESULT_PRESENT (1U << 0)
#define S22PLUS_MAX77705_FLAG_POLL_OVERFLOW (1U << 1)
#define S22PLUS_MAX77705_FLAG_BINDING_PRESENT (1U << 2)
#define S22PLUS_MAX77705_FLAG_POLL_LOSSLESS (1U << 3)

#define S22PLUS_MAX77705_POLL_ENCODING_PACKBITS 1U
#define S22PLUS_MAX77705_POLL_ENCODING_SHA256_SUMMARY 2U

#define S22PLUS_MAX77705_LOADER_NOT_STARTED 0U
#define S22PLUS_MAX77705_LOADER_IN_PROGRESS 1U
#define S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS 2U
#define S22PLUS_MAX77705_LOADER_FAILED 3U

#define S22PLUS_MAX77705_DRIVER_ABSENT 0U
#define S22PLUS_MAX77705_DRIVER_UNBOUND 1U
#define S22PLUS_MAX77705_DRIVER_OTHER 2U
#define S22PLUS_MAX77705_DRIVER_DIAGNOSTIC 3U

enum s22plus_max77705_envelope_semantic_kind {
	S22PLUS_MAX77705_SEMANTIC_TERMINAL = 1,
	S22PLUS_MAX77705_SEMANTIC_MUX = 2,
};

enum s22plus_max77705_terminal_code {
	S22PLUS_MAX77705_TERMINAL_LATE_LOAD_FAILURE = 1,
	S22PLUS_MAX77705_TERMINAL_NO_MATCH = 2,
	S22PLUS_MAX77705_TERMINAL_PARENT_IDENTITY = 3,
	S22PLUS_MAX77705_TERMINAL_PARENT_OWNERSHIP = 4,
	S22PLUS_MAX77705_TERMINAL_PROBE_FAILURE = 5,
	S22PLUS_MAX77705_TERMINAL_NOT_READY = 6,
	S22PLUS_MAX77705_TERMINAL_READ_TIMEOUT = 7,
	S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION = 8,
	S22PLUS_MAX77705_TERMINAL_PAYLOAD_OVERFLOW = 9,
};

enum s22plus_max77705_mux_code {
	S22PLUS_MAX77705_MUX_PRE_NONUSB_STABLE_USB = 1,
	S22PLUS_MAX77705_MUX_PRE_USB_STABLE_USB = 2,
	S22PLUS_MAX77705_MUX_POST_REVERSION = 3,
	S22PLUS_MAX77705_MUX_COMPLETE_OTHER = 4,
	S22PLUS_MAX77705_MUX_TRANSACTION_FAILURE = 5,
};

enum s22plus_max77705_observer_site {
	S22PLUS_MAX77705_OBSERVER_SITE_NONE = 0,
	S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE = 1,
	S22PLUS_MAX77705_OBSERVER_SITE_SUBSTRATE_VERIFY = 2,
	S22PLUS_MAX77705_OBSERVER_SITE_PRE_TOPOLOGY = 3,
	S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER = 4,
	S22PLUS_MAX77705_OBSERVER_SITE_POST_TOPOLOGY = 5,
	S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY = 6,
	S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ = 7,
};

enum s22plus_max77705_observer_error_class {
	S22PLUS_MAX77705_OBSERVER_ERROR_NONE = 0,
	S22PLUS_MAX77705_OBSERVER_ERROR_NOT_FOUND = 1,
	S22PLUS_MAX77705_OBSERVER_ERROR_BUSY = 2,
	S22PLUS_MAX77705_OBSERVER_ERROR_TIMEOUT_RETRY = 3,
	S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT = 4,
	S22PLUS_MAX77705_OBSERVER_ERROR_INTERRUPTED = 5,
	S22PLUS_MAX77705_OBSERVER_ERROR_OTHER_NEGATIVE = 6,
	S22PLUS_MAX77705_OBSERVER_ERROR_NONNEGATIVE = 7,
};

struct s22plus_max77705_binding_witness {
	uint8_t loader_state;
	uint8_t pre_exact_parent_present;
	uint8_t pre_exact_parent_driver_state;
	uint8_t pre_matching_unbound_parent_count;
	uint8_t pre_wrong_address_compatible_parent_count;
	uint8_t post_exact_parent_driver_state;
	uint8_t post_diagnostic_bound_parent_count;
	uint8_t post_exact_adapter_muic_0x25_client_count;
	uint8_t post_foreign_0x25_client_count;
};

_Static_assert(sizeof(struct s22plus_max77705_binding_witness) == 9U,
	"Max77705 binding witness extent");

static void s22plus_max77705_envelope_copy(
		uint8_t *output, const uint8_t *input, size_t size)
{
	size_t index;

	for (index = 0U; index < size; ++index)
		output[index] = input[index];
}

static uint32_t s22plus_max77705_envelope_crc_update(
		uint32_t crc, const uint8_t *data, size_t size)
{
	size_t index;

	for (index = 0U; index < size; ++index) {
		unsigned int bit;

		crc ^= data[index];
		for (bit = 0U; bit < 8U; ++bit) {
			uint32_t mask = 0U - (crc & 1U);

			crc = (crc >> 1U) ^ (0xedb88320U & mask);
		}
	}
	return crc;
}

static uint32_t s22plus_max77705_envelope_crc32(
		const uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE])
{
	static const uint8_t domain[] =
		"S22PLUS-FYG8-MAX77705-DIAG-V2\0";
	uint32_t crc = ~0U;

	/* sizeof includes the C terminator; the literal also embeds one. */
	crc = s22plus_max77705_envelope_crc_update(
		crc, domain, sizeof(domain) - 1U);
	crc = s22plus_max77705_envelope_crc_update(
		crc, envelope, S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET);
	return crc ^ ~0U;
}

static void s22plus_max77705_store_le16(uint8_t *output, uint16_t value)
{
	output[0] = (uint8_t)value;
	output[1] = (uint8_t)(value >> 8U);
}

static void s22plus_max77705_store_le32(uint8_t *output, uint32_t value)
{
	output[0] = (uint8_t)value;
	output[1] = (uint8_t)(value >> 8U);
	output[2] = (uint8_t)(value >> 16U);
	output[3] = (uint8_t)(value >> 24U);
}

static int s22plus_max77705_binding_valid(
		const struct s22plus_max77705_binding_witness *binding)
{
	return binding != NULL && binding->loader_state <=
		S22PLUS_MAX77705_LOADER_FAILED &&
		binding->pre_exact_parent_present <= 1U &&
		binding->pre_exact_parent_driver_state <=
			S22PLUS_MAX77705_DRIVER_DIAGNOSTIC &&
		binding->post_exact_parent_driver_state <=
			S22PLUS_MAX77705_DRIVER_DIAGNOSTIC;
}

static int s22plus_max77705_binding_causal_ready(
		const struct s22plus_max77705_binding_witness *binding)
{
	return s22plus_max77705_binding_valid(binding) &&
		binding->loader_state ==
			S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS &&
		binding->pre_exact_parent_present == 1U &&
		binding->pre_exact_parent_driver_state ==
			S22PLUS_MAX77705_DRIVER_UNBOUND &&
		binding->pre_matching_unbound_parent_count == 1U &&
		binding->pre_wrong_address_compatible_parent_count == 0U &&
		binding->post_exact_parent_driver_state ==
			S22PLUS_MAX77705_DRIVER_DIAGNOSTIC &&
		binding->post_diagnostic_bound_parent_count == 1U &&
		binding->post_exact_adapter_muic_0x25_client_count == 1U &&
		binding->post_foreign_0x25_client_count == 0U;
}

static int s22plus_max77705_summary_equal(
		const struct s22plus_max77705_runtime_poll_summary *left,
		const struct s22plus_max77705_runtime_poll_summary *right)
{
	const uint8_t *left_bytes = (const uint8_t *)left;
	const uint8_t *right_bytes = (const uint8_t *)right;
	size_t index;

	for (index = 0U; index < sizeof(*left); ++index) {
		if (left_bytes[index] != right_bytes[index])
			return 0;
	}
	return 1;
}

static int s22plus_max77705_expected_semantic(
		const struct s22plus_max77705_binding_witness *binding,
		const struct s22plus_max77705_runtime_result *result,
		uint8_t *semantic_kind, uint8_t *semantic_code)
{
	if (!s22plus_max77705_binding_valid(binding) || result == NULL ||
	    semantic_kind == NULL || semantic_code == NULL)
		return -1;
	if (result->rc > 0) {
		*semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
		*semantic_code = S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
		return 0;
	}
	if (result->rc < 0) {
		if (result->stage == 2U && result->rc == -19) {
			*semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
			*semantic_code = S22PLUS_MAX77705_TERMINAL_PARENT_IDENTITY;
		} else if (result->stage <= 4U) {
			*semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
			*semantic_code = S22PLUS_MAX77705_TERMINAL_PROBE_FAILURE;
		} else if (result->stage == 5U || result->stage == 6U ||
			   result->stage == 7U || result->stage == 9U) {
			if (!s22plus_max77705_binding_causal_ready(binding)) {
				*semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
				*semantic_code =
					S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
			} else {
				*semantic_kind = S22PLUS_MAX77705_SEMANTIC_MUX;
				*semantic_code =
					S22PLUS_MAX77705_MUX_TRANSACTION_FAILURE;
			}
		} else {
			return -1;
		}
		return 0;
	}
	if (result->stage != S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE)
		return -1;
	if (!s22plus_max77705_binding_causal_ready(binding)) {
		*semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
		*semantic_code = S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
	} else if (result->response_value[2] == 0x09U &&
		   result->response_value[3] != 0x09U) {
		*semantic_kind = S22PLUS_MAX77705_SEMANTIC_MUX;
		*semantic_code = S22PLUS_MAX77705_MUX_POST_REVERSION;
	} else if (result->response_value[0] != 0x09U &&
		   result->response_value[2] == 0x09U &&
		   result->response_value[3] == 0x09U) {
		*semantic_kind = S22PLUS_MAX77705_SEMANTIC_MUX;
		*semantic_code = S22PLUS_MAX77705_MUX_PRE_NONUSB_STABLE_USB;
	} else if (result->response_value[0] == 0x09U &&
		   result->response_value[2] == 0x09U &&
		   result->response_value[3] == 0x09U) {
		*semantic_kind = S22PLUS_MAX77705_SEMANTIC_MUX;
		*semantic_code = S22PLUS_MAX77705_MUX_PRE_USB_STABLE_USB;
	} else {
		*semantic_kind = S22PLUS_MAX77705_SEMANTIC_MUX;
		*semantic_code = S22PLUS_MAX77705_MUX_COMPLETE_OTHER;
	}
	return 0;
}

static size_t s22plus_max77705_packbits(
		const uint8_t *input, size_t input_size,
		uint8_t *output, size_t capacity)
{
	size_t cursor = 0U;
	size_t produced = 0U;

	while (cursor < input_size) {
		size_t run = 1U;
		size_t start;
		size_t literal_size;

		while (cursor + run < input_size && run < 128U &&
		       input[cursor + run] == input[cursor])
			++run;
		if (run >= 3U) {
			if (produced + 2U > capacity)
				return capacity + 1U;
			output[produced++] = (uint8_t)(0x80U | (run - 1U));
			output[produced++] = input[cursor];
			cursor += run;
			continue;
		}
		start = cursor;
		cursor += run;
		while (cursor < input_size && cursor - start < 128U) {
			size_t next_run = 1U;

			while (cursor + next_run < input_size &&
			       next_run < 128U &&
			       input[cursor + next_run] == input[cursor])
				++next_run;
			if (next_run >= 3U || cursor - start + next_run > 128U)
				break;
			cursor += next_run;
		}
		literal_size = cursor - start;
		if (produced + 1U + literal_size > capacity)
			return capacity + 1U;
		output[produced++] = (uint8_t)(literal_size - 1U);
		s22plus_max77705_envelope_copy(
			output + produced, input + start, literal_size);
		produced += literal_size;
	}
	return produced;
}

static int s22plus_max77705_encode_envelope(
		const struct s22plus_max77705_binding_witness *binding,
		unsigned int semantic_kind, unsigned int semantic_code,
		unsigned int observer_site, unsigned int observer_error_class,
		const struct s22plus_max77705_runtime_result *result,
		const struct s22plus_max77705_runtime_poll_summary *summary,
		uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE],
		uint16_t *terminal_detail)
{
	struct s22plus_max77705_runtime_poll_summary derived_summary;
	uint8_t raw[S22PLUS_MAX77705_RUNTIME_COMMANDS *
		S22PLUS_MAX77705_RUNTIME_POLL_LIMIT];
	uint8_t encoded[S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE];
	size_t raw_size = 0U;
	size_t encoded_size = 0U;
	uint8_t flags = S22PLUS_MAX77705_FLAG_BINDING_PRESENT;
	unsigned int slot;
	uint32_t crc;

	if (!s22plus_max77705_binding_valid(binding) || envelope == NULL ||
	    terminal_detail == NULL)
		return -1;
	if (observer_site > S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ ||
	    observer_error_class >
		S22PLUS_MAX77705_OBSERVER_ERROR_NONNEGATIVE ||
	    ((observer_site == S22PLUS_MAX77705_OBSERVER_SITE_NONE) !=
	     (observer_error_class == S22PLUS_MAX77705_OBSERVER_ERROR_NONE)) ||
	    (observer_site != S22PLUS_MAX77705_OBSERVER_SITE_NONE &&
	     (semantic_kind != S22PLUS_MAX77705_SEMANTIC_TERMINAL ||
	      semantic_code != S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION ||
	      result != NULL)))
		return -1;
	if ((semantic_kind == S22PLUS_MAX77705_SEMANTIC_TERMINAL &&
	     (semantic_code < 1U || semantic_code > 9U)) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_MUX &&
	     (semantic_code < 1U || semantic_code > 5U)) ||
	    (semantic_kind != S22PLUS_MAX77705_SEMANTIC_TERMINAL &&
	     semantic_kind != S22PLUS_MAX77705_SEMANTIC_MUX) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_MUX && result == NULL) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_MUX &&
	     !s22plus_max77705_binding_causal_ready(binding)) ||
	    ((result == NULL) != (summary == NULL)))
		return -1;
	if (result != NULL) {
		uint8_t expected_kind = 0U;
		uint8_t expected_code = 0U;

		if (s22plus_max77705_runtime_summarize(result, &derived_summary) !=
		    S22PLUS_MAX77705_RUNTIME_PARSE_OK ||
		    s22plus_max77705_runtime_validate_semantics(
			result, &derived_summary) !=
			S22PLUS_MAX77705_RUNTIME_PARSE_OK ||
		    !s22plus_max77705_summary_equal(summary, &derived_summary) ||
		    s22plus_max77705_expected_semantic(
			binding, result, &expected_kind, &expected_code) != 0 ||
		    expected_kind != semantic_kind || expected_code != semantic_code)
			return -1;
	}

	memset(envelope, 0, S22PLUS_MAX77705_ENVELOPE_SIZE);
	envelope[0] = 'M';
	envelope[1] = 'X';
	envelope[2] = 'D';
	envelope[3] = '2';
	envelope[4] = 2U;
	if (semantic_kind == S22PLUS_MAX77705_SEMANTIC_TERMINAL)
		envelope[5] = (uint8_t)semantic_code;
	else
		envelope[6] = (uint8_t)semantic_code;

	if (result != NULL) {
		flags |= S22PLUS_MAX77705_FLAG_RESULT_PRESENT;
		envelope[8] = result->stage;
		s22plus_max77705_store_le32(envelope + 9U, (uint32_t)result->rc);
		envelope[13] = result->pmic_valid_mask;
		envelope[14] = result->pmic_id;
		envelope[15] = result->pmic_rev;
		envelope[16] = result->initial_uic_valid;
		envelope[17] = result->initial_uic;
		envelope[18] = result->command_issued_mask;
		envelope[19] = result->response_seen_mask;
		envelope[20] = result->write_attempted;
		envelope[21] = result->write_ambiguous;
		s22plus_max77705_envelope_copy(
			envelope + 22U, result->response_opcode, 4U);
		s22plus_max77705_envelope_copy(
			envelope + 26U, result->response_value, 4U);
		s22plus_max77705_envelope_copy(
			envelope + 30U, result->poll_count, 4U);
		for (slot = 0U; slot < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++slot) {
			if (raw_size + result->poll_count[slot] > sizeof(raw))
				return -1;
			s22plus_max77705_envelope_copy(
				raw + raw_size, result->poll_bytes[slot],
				result->poll_count[slot]);
			raw_size += result->poll_count[slot];
		}
		if (raw_size != summary->raw_count)
			return -1;
		encoded_size = s22plus_max77705_packbits(
			raw, raw_size, encoded, sizeof(encoded));
	}

	s22plus_max77705_envelope_copy(
		envelope + 34U, (const uint8_t *)binding, sizeof(*binding));
	s22plus_max77705_store_le16(envelope + 44U, (uint16_t)raw_size);
	envelope[47] = (uint8_t)((observer_site << 4U) | observer_error_class);
	if (encoded_size > sizeof(encoded)) {
		if (result == NULL)
			return -1;
		envelope[5] = S22PLUS_MAX77705_TERMINAL_PAYLOAD_OVERFLOW;
		envelope[6] = 0U;
		flags |= S22PLUS_MAX77705_FLAG_POLL_OVERFLOW;
		envelope[43] = S22PLUS_MAX77705_POLL_ENCODING_SHA256_SUMMARY;
		envelope[46] = S22PLUS_MAX77705_ENVELOPE_OVERFLOW_SIZE;
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET,
			summary->sha256, 32U);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 32U,
			summary->or_mask, 4U);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 36U,
			summary->poll0, 4U);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 40U,
			summary->nonzero_count, 4U);
	} else {
		flags |= S22PLUS_MAX77705_FLAG_POLL_LOSSLESS;
		envelope[43] = S22PLUS_MAX77705_POLL_ENCODING_PACKBITS;
		envelope[46] = (uint8_t)encoded_size;
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET,
			encoded, encoded_size);
	}
	envelope[7] = flags;
	crc = s22plus_max77705_envelope_crc32(envelope);
	s22plus_max77705_store_le32(
		envelope + S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET, crc);
	*terminal_detail = envelope[5] != 0U
		? (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + envelope[5] - 1U)
		: (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + 0x0fU +
			envelope[6] - 1U);
	return 0;
}
