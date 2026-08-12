/*
 * P3.17 Max77705 Carrier-v2 payload envelope v3.
 *
 * The fixed Image still retains exactly two 64-byte request payloads.  This
 * schema therefore keeps the 128-byte envelope and the full 76-byte poll
 * payload area.  It compacts the P3.16 binding witness into three bytes and
 * uses the released six header bytes for the boot-specific experiment-
 * executability witness.
 */

#define S22PLUS_MAX77705_P317_ENVELOPE_VERSION 3U
#define S22PLUS_MAX77705_P317_FLAG_EXEC_PRESENT (1U << 4)

#define S22PLUS_MAX77705_P317_POLICY_STATE_MASK 0x07U
#define S22PLUS_MAX77705_P317_POLICY_GADGET_READY (1U << 3)
#define S22PLUS_MAX77705_P317_POLICY_VALID (1U << 7)

#define S22PLUS_MAX77705_P317_PROVIDER_MASK 0x07U
#define S22PLUS_MAX77705_P317_PROVIDER_DUPLICATE_SHIFT 4U
#define S22PLUS_MAX77705_P317_PROVIDER_VALID (1U << 7)

#define S22PLUS_MAX77705_P317_WAITING_MASK 0x03U
#define S22PLUS_MAX77705_P317_SUPPLIER_SHIFT 2U
#define S22PLUS_MAX77705_P317_SUPPLIER_MASK 0x0cU
#define S22PLUS_MAX77705_P317_LINK_VALID (1U << 7)

enum s22plus_max77705_p317_policy_state {
	S22PLUS_MAX77705_P317_POLICY_UNAVAILABLE = 0,
	S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT = 1,
	S22PLUS_MAX77705_P317_POLICY_FW_DEVLINK_TOKEN = 2,
	S22PLUS_MAX77705_P317_POLICY_STRICT_TOKEN = 3,
	S22PLUS_MAX77705_P317_POLICY_BOTH_TOKENS = 4,
};

enum s22plus_max77705_p317_waiting_state {
	S22PLUS_MAX77705_P317_WAITING_UNAVAILABLE = 0,
	S22PLUS_MAX77705_P317_WAITING_FILE_ABSENT = 1,
	S22PLUS_MAX77705_P317_WAITING_ZERO = 2,
	S22PLUS_MAX77705_P317_WAITING_ONE = 3,
};

enum s22plus_max77705_p317_supplier_state {
	S22PLUS_MAX77705_P317_SUPPLIER_UNAVAILABLE = 0,
	S22PLUS_MAX77705_P317_SUPPLIER_LINK_ABSENT = 1,
	S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE = 2,
	S22PLUS_MAX77705_P317_SUPPLIER_FOREIGN_OR_MULTIPLE = 3,
};

enum s22plus_max77705_p317_terminal_code {
	S22PLUS_MAX77705_P317_TERMINAL_POLICY_PRECONDITION = 10,
	S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_PRECONDITION = 11,
	S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_POSTCONDITION = 12,
	S22PLUS_MAX77705_P317_TERMINAL_SUPPLIER_PRECONDITION = 13,
	S22PLUS_MAX77705_P317_TERMINAL_WAITING_PRECONDITION = 14,
	S22PLUS_MAX77705_P317_TERMINAL_EXEC_CONTRADICTION = 15,
};

enum s22plus_max77705_p317_observer_site {
	S22PLUS_MAX77705_P317_OBSERVER_SITE_CMDLINE = 8,
	S22PLUS_MAX77705_P317_OBSERVER_SITE_PROVIDER_PRE = 9,
	S22PLUS_MAX77705_P317_OBSERVER_SITE_PROVIDER_POST = 10,
	S22PLUS_MAX77705_P317_OBSERVER_SITE_SUPPLIER = 11,
	S22PLUS_MAX77705_P317_OBSERVER_SITE_WAITING = 12,
};

struct s22plus_max77705_p317_exec_witness {
	uint8_t policy;
	uint8_t pre_present;
	uint8_t pre_bound;
	uint8_t post_present;
	uint8_t post_bound;
	uint8_t link_waiting;
};

_Static_assert(sizeof(struct s22plus_max77705_p317_exec_witness) == 6U,
	"P3.17 execution witness extent");

static uint8_t s22plus_max77705_p317_count_class(uint8_t value)
{
	return value == 0U ? 0U : (value == 1U ? 1U : 2U);
}

static int s22plus_max77705_p317_pack_binding(
		const struct s22plus_max77705_binding_witness *binding,
		uint8_t output[3])
{
	if (!s22plus_max77705_binding_valid(binding) || output == NULL)
		return -1;
	output[0] = (uint8_t)(binding->loader_state |
		(binding->pre_exact_parent_present << 2U) |
		(binding->pre_exact_parent_driver_state << 3U) |
		(binding->post_exact_parent_driver_state << 5U));
	output[1] = (uint8_t)(
		s22plus_max77705_p317_count_class(
			binding->pre_matching_unbound_parent_count) |
		(s22plus_max77705_p317_count_class(
			binding->pre_wrong_address_compatible_parent_count) << 2U) |
		(s22plus_max77705_p317_count_class(
			binding->post_diagnostic_bound_parent_count) << 4U) |
		(s22plus_max77705_p317_count_class(
			binding->post_exact_adapter_muic_0x25_client_count) << 6U));
	output[2] = s22plus_max77705_p317_count_class(
		binding->post_foreign_0x25_client_count);
	return 0;
}

static int s22plus_max77705_p317_exec_valid(
		const struct s22plus_max77705_p317_exec_witness *exec)
{
	uint8_t policy_state;
	uint8_t waiting;
	uint8_t supplier;

	if (exec == NULL)
		return 0;
	policy_state = exec->policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK;
	waiting = exec->link_waiting & S22PLUS_MAX77705_P317_WAITING_MASK;
	supplier = (exec->link_waiting & S22PLUS_MAX77705_P317_SUPPLIER_MASK) >>
		S22PLUS_MAX77705_P317_SUPPLIER_SHIFT;
	return (exec->policy & 0x70U) == 0U && policy_state <=
		S22PLUS_MAX77705_P317_POLICY_BOTH_TOKENS &&
		(exec->pre_present & 0x08U) == 0U &&
		(exec->pre_bound & 0x88U) == 0U &&
		(exec->post_present & 0x08U) == 0U &&
		(exec->post_bound & 0x88U) == 0U &&
		(exec->link_waiting & 0x70U) == 0U && waiting <=
		S22PLUS_MAX77705_P317_WAITING_ONE && supplier <=
		S22PLUS_MAX77705_P317_SUPPLIER_FOREIGN_OR_MULTIPLE;
}

static int s22plus_max77705_p317_provider_ready(
		uint8_t present, uint8_t bound)
{
	return (present & S22PLUS_MAX77705_P317_PROVIDER_VALID) != 0U &&
		(present & S22PLUS_MAX77705_P317_PROVIDER_MASK) ==
			S22PLUS_MAX77705_P317_PROVIDER_MASK &&
		((present >> S22PLUS_MAX77705_P317_PROVIDER_DUPLICATE_SHIFT) &
			S22PLUS_MAX77705_P317_PROVIDER_MASK) == 0U &&
		(bound & S22PLUS_MAX77705_P317_PROVIDER_MASK) ==
			S22PLUS_MAX77705_P317_PROVIDER_MASK &&
		((bound >> S22PLUS_MAX77705_P317_PROVIDER_DUPLICATE_SHIFT) &
			S22PLUS_MAX77705_P317_PROVIDER_MASK) == 0U;
}

static int s22plus_max77705_p317_exec_causal_ready(
		const struct s22plus_max77705_p317_exec_witness *exec)
{
	uint8_t waiting;
	uint8_t supplier;

	if (!s22plus_max77705_p317_exec_valid(exec) ||
	    (exec->policy & S22PLUS_MAX77705_P317_POLICY_VALID) == 0U ||
	    (exec->policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK) !=
		S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT ||
	    (exec->policy & S22PLUS_MAX77705_P317_POLICY_GADGET_READY) == 0U ||
	    !s22plus_max77705_p317_provider_ready(
		exec->pre_present, exec->pre_bound) ||
	    !s22plus_max77705_p317_provider_ready(
		exec->post_present, exec->post_bound) ||
	    (exec->link_waiting & S22PLUS_MAX77705_P317_LINK_VALID) == 0U)
		return 0;
	waiting = exec->link_waiting & S22PLUS_MAX77705_P317_WAITING_MASK;
	supplier = (exec->link_waiting & S22PLUS_MAX77705_P317_SUPPLIER_MASK) >>
		S22PLUS_MAX77705_P317_SUPPLIER_SHIFT;
	return waiting == S22PLUS_MAX77705_P317_WAITING_ZERO &&
		(supplier == S22PLUS_MAX77705_P317_SUPPLIER_LINK_ABSENT ||
		 supplier == S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE);
}

static int s22plus_max77705_p317_terminal_witness_consistent(
		unsigned int semantic_code,
		const struct s22plus_max77705_p317_exec_witness *exec)
{
	uint8_t policy_state;
	uint8_t waiting;
	uint8_t supplier;

	if (!s22plus_max77705_p317_exec_valid(exec))
		return 0;
	policy_state = exec->policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK;
	waiting = exec->link_waiting & S22PLUS_MAX77705_P317_WAITING_MASK;
	supplier = (exec->link_waiting & S22PLUS_MAX77705_P317_SUPPLIER_MASK) >>
		S22PLUS_MAX77705_P317_SUPPLIER_SHIFT;
	switch (semantic_code) {
	case S22PLUS_MAX77705_P317_TERMINAL_POLICY_PRECONDITION:
		return (exec->policy & S22PLUS_MAX77705_P317_POLICY_VALID) != 0U &&
			policy_state !=
			S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT;
	case S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_PRECONDITION:
		return (exec->pre_present &
			S22PLUS_MAX77705_P317_PROVIDER_VALID) != 0U &&
			!s22plus_max77705_p317_provider_ready(
				exec->pre_present, exec->pre_bound);
	case S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_POSTCONDITION:
		return s22plus_max77705_p317_provider_ready(
			exec->pre_present, exec->pre_bound) &&
			(exec->post_present &
			 S22PLUS_MAX77705_P317_PROVIDER_VALID) != 0U &&
			!s22plus_max77705_p317_provider_ready(
				exec->post_present, exec->post_bound);
	case S22PLUS_MAX77705_P317_TERMINAL_SUPPLIER_PRECONDITION:
		return (exec->link_waiting &
			S22PLUS_MAX77705_P317_LINK_VALID) != 0U &&
			supplier !=
			S22PLUS_MAX77705_P317_SUPPLIER_LINK_ABSENT &&
			supplier != S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE;
	case S22PLUS_MAX77705_P317_TERMINAL_WAITING_PRECONDITION:
		return (exec->link_waiting &
			S22PLUS_MAX77705_P317_LINK_VALID) != 0U &&
			waiting != S22PLUS_MAX77705_P317_WAITING_ZERO;
	case S22PLUS_MAX77705_P317_TERMINAL_EXEC_CONTRADICTION:
		return 1;
	default:
		return 1;
	}
}

static uint32_t s22plus_max77705_p317_envelope_crc32(
		const uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE])
{
	static const uint8_t domain[] =
		"S22PLUS-FYG8-MAX77705-DIAG-V3\0";
	uint32_t crc = ~0U;

	crc = s22plus_max77705_envelope_crc_update(
		crc, domain, sizeof(domain) - 1U);
	crc = s22plus_max77705_envelope_crc_update(
		crc, envelope, S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET);
	return crc ^ ~0U;
}

static int s22plus_max77705_p317_encode_envelope(
		const struct s22plus_max77705_binding_witness *binding,
		const struct s22plus_max77705_p317_exec_witness *exec,
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
	uint8_t packed_binding[3];
	size_t raw_size = 0U;
	size_t encoded_size = 0U;
	uint8_t flags = S22PLUS_MAX77705_FLAG_BINDING_PRESENT |
		S22PLUS_MAX77705_P317_FLAG_EXEC_PRESENT;
	unsigned int slot;
	uint32_t crc;

	if (s22plus_max77705_p317_pack_binding(binding, packed_binding) != 0 ||
	    !s22plus_max77705_p317_exec_valid(exec) || envelope == NULL ||
	    terminal_detail == NULL)
		return -1;
	if (observer_site > S22PLUS_MAX77705_P317_OBSERVER_SITE_WAITING ||
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
	     (semantic_code < 1U || semantic_code > 15U)) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_MUX &&
	     (semantic_code < 1U || semantic_code > 5U)) ||
	    (semantic_kind != S22PLUS_MAX77705_SEMANTIC_TERMINAL &&
	     semantic_kind != S22PLUS_MAX77705_SEMANTIC_MUX) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_MUX && result == NULL) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_MUX &&
	     (!s22plus_max77705_binding_causal_ready(binding) ||
	      !s22plus_max77705_p317_exec_causal_ready(exec))) ||
	    ((result == NULL) != (summary == NULL)) ||
	    (semantic_kind == S22PLUS_MAX77705_SEMANTIC_TERMINAL &&
	     semantic_code >= 10U &&
	     (result != NULL || observer_site != 0U ||
	      !s22plus_max77705_p317_terminal_witness_consistent(
		semantic_code, exec))))
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
	envelope[3] = '3';
	envelope[4] = S22PLUS_MAX77705_P317_ENVELOPE_VERSION;
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

	s22plus_max77705_envelope_copy(envelope + 34U, packed_binding, 3U);
	s22plus_max77705_envelope_copy(
		envelope + 37U, (const uint8_t *)exec, sizeof(*exec));
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
	crc = s22plus_max77705_p317_envelope_crc32(envelope);
	s22plus_max77705_store_le32(
		envelope + S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET, crc);
	*terminal_detail = envelope[5] != 0U
		? (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + envelope[5] - 1U)
		: (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + 0x0fU +
			envelope[6] - 1U);
	return 0;
}
