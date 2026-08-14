/*
 * P3.18 Max77705 Carrier-v2 payload envelope v4.
 *
 * The 48-byte metadata header and 4-byte CRC remain fixed.  The 76-byte
 * payload begins with one same-clock timing witness (26 bytes) and the exact
 * bounded banner result (3 bytes).  Lossless PackBits therefore has 47 bytes;
 * overflow stores the existing 44-byte summary and leaves three bytes zero.
 *
 * This file is included after the P3.18 result parser, the base envelope,
 * runtime policy, P3.17 envelope, and P3.18 banner writer definitions.
 */

#define S22PLUS_MAX77705_P318_ENVELOPE_VERSION 4U
#define S22PLUS_MAX77705_P318_TIMING_SIZE 26U
#define S22PLUS_MAX77705_P318_BANNER_SIZE 3U
#define S22PLUS_MAX77705_P318_PREFIX_SIZE 29U
#define S22PLUS_MAX77705_P318_LOSSLESS_CAPACITY 47U
#define S22PLUS_MAX77705_P318_OVERFLOW_USED 73U
#define S22PLUS_MAX77705_P318_OVERFLOW_SPARE 3U

#define S22PLUS_MAX77705_P318_TIME_PRE (1U << 0)
#define S22PLUS_MAX77705_P318_TIME_WRITE (1U << 1)
#define S22PLUS_MAX77705_P318_TIME_POST1 (1U << 2)
#define S22PLUS_MAX77705_P318_TIME_POST2 (1U << 3)
#define S22PLUS_MAX77705_P318_TIME_HOST_EVENT (1U << 4)
#define S22PLUS_MAX77705_P318_TIME_INSTALL (1U << 5)
#define S22PLUS_MAX77705_P318_TIME_EXPOSURE (1U << 6)
#define S22PLUS_MAX77705_P318_TIME_MASK 0x7fU
#define S22PLUS_MAX77705_P318_CAUSAL_NO_EVENT 0x6fU
#define S22PLUS_MAX77705_P318_CAUSAL_WITH_EVENT 0x7fU

enum s22plus_max77705_p318_observer_site {
	S22PLUS_MAX77705_P318_OBSERVER_SITE_EXPOSURE_GATE = 13,
	S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH = 14,
};

enum s22plus_max77705_p318_host_event_kind {
	S22PLUS_MAX77705_P318_HOST_EVENT_NONE = 0,
	S22PLUS_MAX77705_P318_HOST_EVENT_RESET = 1,
	S22PLUS_MAX77705_P318_HOST_EVENT_CONNECT_DONE = 2,
	S22PLUS_MAX77705_P318_HOST_EVENT_SETUP = 3,
};

struct s22plus_max77705_p318_timing_witness {
	uint8_t valid_mask;
	uint8_t first_host_event_kind;
	int32_t latch_install_delta_us;
	int32_t gadget_exposure_delta_us;
	int32_t write_delta_us;
	int32_t post1_delta_us;
	int32_t post2_delta_us;
	int32_t first_host_event_delta_us;
};

_Static_assert(S22PLUS_MAX77705_P318_TIMING_SIZE +
	S22PLUS_MAX77705_P318_BANNER_SIZE +
	S22PLUS_MAX77705_P318_LOSSLESS_CAPACITY ==
	S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE,
	"P3.18 lossless payload geometry");
_Static_assert(S22PLUS_MAX77705_P318_PREFIX_SIZE +
	S22PLUS_MAX77705_ENVELOPE_OVERFLOW_SIZE ==
	S22PLUS_MAX77705_P318_OVERFLOW_USED,
	"P3.18 overflow used extent");
_Static_assert(S22PLUS_MAX77705_P318_OVERFLOW_USED +
	S22PLUS_MAX77705_P318_OVERFLOW_SPARE ==
	S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE,
	"P3.18 overflow spare extent");
_Static_assert(sizeof(struct s22plus_p318_banner_result) ==
	S22PLUS_MAX77705_P318_BANNER_SIZE,
	"P3.18 banner result prefix extent");

static int s22plus_max77705_p318_delta_us(
		uint64_t sample_ns, uint64_t origin_ns, int32_t *output)
{
	uint64_t magnitude;
	uint64_t microseconds;

	if (output == NULL)
		return -1;
	if (sample_ns >= origin_ns) {
		magnitude = sample_ns - origin_ns;
		microseconds = magnitude / 1000U;
		if (microseconds > 0x7fffffffU)
			return -1;
		*output = (int32_t)microseconds;
		return 0;
	}
	magnitude = origin_ns - sample_ns;
	microseconds = magnitude / 1000U;
	if (microseconds > 0x80000000ULL)
		return -1;
	if (microseconds == 0x80000000ULL)
		*output = (int32_t)(-2147483647 - 1);
	else
		*output = -(int32_t)microseconds;
	return 0;
}

static int s22plus_max77705_p318_banner_valid(
		const struct s22plus_p318_banner_result *banner)
{
	if (banner == NULL ||
	    banner->outcome > S22PLUS_P318_BANNER_PARTIAL ||
	    banner->error_class > S22PLUS_P318_BANNER_ERROR_OTHER ||
	    banner->bytes_written > S22PLUS_P318_BANNER_SIZE)
		return 0;
	switch (banner->outcome) {
	case S22PLUS_P318_BANNER_NOT_ATTEMPTED:
		return banner->error_class == S22PLUS_P318_BANNER_ERROR_NONE &&
			banner->bytes_written == 0U;
	case S22PLUS_P318_BANNER_WRITTEN:
		return banner->error_class == S22PLUS_P318_BANNER_ERROR_NONE &&
			banner->bytes_written == S22PLUS_P318_BANNER_SIZE;
	case S22PLUS_P318_BANNER_EAGAIN_TIMEOUT:
		return banner->error_class ==
			S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE &&
			banner->bytes_written == 0U;
	case S22PLUS_P318_BANNER_FAILURE:
		return banner->error_class != S22PLUS_P318_BANNER_ERROR_NONE &&
			banner->error_class !=
				S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE &&
			banner->bytes_written == 0U;
	case S22PLUS_P318_BANNER_PARTIAL:
		return banner->error_class != S22PLUS_P318_BANNER_ERROR_NONE &&
			banner->bytes_written > 0U &&
			banner->bytes_written < S22PLUS_P318_BANNER_SIZE;
	default:
		return 0;
	}
}

static int s22plus_max77705_p318_latch_valid(
		const struct s22plus_max77705_p318_latch_snapshot *latch)
{
	return latch == NULL || s22plus_p318_latch_snapshot_valid(latch);
}

static int s22plus_max77705_p318_derive_timing(
		const struct s22plus_max77705_runtime_result *result,
		const struct s22plus_max77705_p318_latch_snapshot *latch,
		struct s22plus_max77705_p318_timing_witness *timing)
{
	uint64_t origin;

	if (timing == NULL || !s22plus_max77705_p318_latch_valid(latch))
		return -1;
	memset(timing, 0, sizeof(*timing));
	if (result == NULL) {
		return latch == NULL ? 0 : -1;
	}
	if ((result->timing_valid_mask & 0xf0U) != 0U)
		return -1;
	timing->valid_mask = result->timing_valid_mask;
	if ((timing->valid_mask & S22PLUS_MAX77705_P318_TIME_PRE) == 0U)
		return latch == NULL ? 0 : -1;
	origin = result->pre_ns;
	if ((timing->valid_mask & S22PLUS_MAX77705_P318_TIME_WRITE) != 0U &&
	    s22plus_max77705_p318_delta_us(
		result->write_ns, origin, &timing->write_delta_us) != 0)
		return -1;
	if ((timing->valid_mask & S22PLUS_MAX77705_P318_TIME_POST1) != 0U &&
	    s22plus_max77705_p318_delta_us(
		result->post1_ns, origin, &timing->post1_delta_us) != 0)
		return -1;
	if ((timing->valid_mask & S22PLUS_MAX77705_P318_TIME_POST2) != 0U &&
	    s22plus_max77705_p318_delta_us(
		result->post2_ns, origin, &timing->post2_delta_us) != 0)
		return -1;
	if (latch == NULL)
		return 0;
	if (latch->install_valid != 0U) {
		timing->valid_mask |= S22PLUS_MAX77705_P318_TIME_INSTALL;
		if (s22plus_max77705_p318_delta_us(
			latch->install_ns, origin,
			&timing->latch_install_delta_us) != 0)
			return -1;
	}
	if (latch->exposure_valid != 0U) {
		timing->valid_mask |= S22PLUS_MAX77705_P318_TIME_EXPOSURE;
		if (s22plus_max77705_p318_delta_us(
			latch->exposure_ns, origin,
			&timing->gadget_exposure_delta_us) != 0)
			return -1;
	}
	if (latch->event_valid != 0U) {
		timing->valid_mask |= S22PLUS_MAX77705_P318_TIME_HOST_EVENT;
		timing->first_host_event_kind = latch->event_kind;
		if (s22plus_max77705_p318_delta_us(
			latch->event_ns, origin,
			&timing->first_host_event_delta_us) != 0)
			return -1;
	}
	return 0;
}

static int s22plus_max77705_p318_timing_valid(
		const struct s22plus_max77705_p318_timing_witness *timing)
{
	uint8_t mask;

	if (timing == NULL || (timing->valid_mask & 0x80U) != 0U)
		return 0;
	mask = timing->valid_mask;
	if (((mask & S22PLUS_MAX77705_P318_TIME_HOST_EVENT) != 0U) !=
	    (timing->first_host_event_kind !=
	     S22PLUS_MAX77705_P318_HOST_EVENT_NONE) ||
	    timing->first_host_event_kind >
		S22PLUS_MAX77705_P318_HOST_EVENT_SETUP)
		return 0;
	if ((mask & S22PLUS_MAX77705_P318_TIME_INSTALL) == 0U &&
	    timing->latch_install_delta_us != 0)
		return 0;
	if ((mask & S22PLUS_MAX77705_P318_TIME_EXPOSURE) == 0U &&
	    timing->gadget_exposure_delta_us != 0)
		return 0;
	if ((mask & S22PLUS_MAX77705_P318_TIME_WRITE) == 0U &&
	    timing->write_delta_us != 0)
		return 0;
	if ((mask & S22PLUS_MAX77705_P318_TIME_POST1) == 0U &&
	    timing->post1_delta_us != 0)
		return 0;
	if ((mask & S22PLUS_MAX77705_P318_TIME_POST2) == 0U &&
	    timing->post2_delta_us != 0)
		return 0;
	if ((mask & S22PLUS_MAX77705_P318_TIME_HOST_EVENT) == 0U &&
	    timing->first_host_event_delta_us != 0)
		return 0;
	if ((mask & (S22PLUS_MAX77705_P318_TIME_PRE |
		    S22PLUS_MAX77705_P318_TIME_INSTALL |
		    S22PLUS_MAX77705_P318_TIME_EXPOSURE)) ==
	    (S22PLUS_MAX77705_P318_TIME_PRE |
	     S22PLUS_MAX77705_P318_TIME_INSTALL |
	     S22PLUS_MAX77705_P318_TIME_EXPOSURE) &&
	    (timing->latch_install_delta_us >
		timing->gadget_exposure_delta_us ||
	     timing->gadget_exposure_delta_us > 0))
		return 0;
	return 1;
}

static void s22plus_max77705_p318_store_timing(
		uint8_t *output,
		const struct s22plus_max77705_p318_timing_witness *timing)
{
	const int32_t values[6] = {
		timing->latch_install_delta_us,
		timing->gadget_exposure_delta_us,
		timing->write_delta_us,
		timing->post1_delta_us,
		timing->post2_delta_us,
		timing->first_host_event_delta_us,
	};
	unsigned int index;

	output[0] = timing->valid_mask;
	output[1] = timing->first_host_event_kind;
	for (index = 0U; index < 6U; ++index)
		s22plus_max77705_store_le32(
			output + 2U + index * 4U, (uint32_t)values[index]);
}

static uint32_t s22plus_max77705_p318_envelope_crc32(
		const uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE])
{
	static const uint8_t domain[] =
		"S22PLUS-FYG8-MAX77705-DIAG-V4\0";
	uint32_t crc = ~0U;

	crc = s22plus_max77705_envelope_crc_update(
		crc, domain, sizeof(domain) - 1U);
	crc = s22plus_max77705_envelope_crc_update(
		crc, envelope, S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET);
	return crc ^ ~0U;
}

static int s22plus_max77705_p318_encode_envelope(
		const struct s22plus_max77705_binding_witness *binding,
		const struct s22plus_max77705_p317_exec_witness *exec,
		unsigned int semantic_kind, unsigned int semantic_code,
		unsigned int observer_site, unsigned int observer_error_class,
		const struct s22plus_max77705_runtime_result *result,
		const struct s22plus_max77705_runtime_poll_summary *summary,
		const struct s22plus_max77705_p318_latch_snapshot *latch,
		const struct s22plus_p318_banner_result *banner,
		uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE],
		uint16_t *terminal_detail)
{
	struct s22plus_max77705_p318_timing_witness timing;
	uint8_t raw[S22PLUS_MAX77705_RUNTIME_COMMANDS *
		S22PLUS_MAX77705_RUNTIME_POLL_LIMIT];
	uint8_t encoded[S22PLUS_MAX77705_P318_LOSSLESS_CAPACITY];
	size_t raw_size = 0U;
	size_t encoded_size = 0U;
	uint8_t flags;
	unsigned int base_observer_site;
	unsigned int slot;
	uint32_t crc;
	uint16_t base_detail;

	if (envelope == NULL || terminal_detail == NULL ||
	    !s22plus_max77705_p318_banner_valid(banner) ||
	    s22plus_max77705_p318_derive_timing(result, latch, &timing) != 0 ||
	    !s22plus_max77705_p318_timing_valid(&timing))
		return -1;
	if (observer_site > S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH)
		return -1;
	base_observer_site = observer_site;
	if (observer_site ==
	    S22PLUS_MAX77705_P318_OBSERVER_SITE_EXPOSURE_GATE)
		base_observer_site =
			S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE;
	else if (observer_site ==
		 S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH)
		base_observer_site = S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ;
	/* Reuse the actual v3 semantic and authority checks.  The two v4-only
	 * sites map to source-equivalent v3 authority rows for validation, then
	 * the original site is restored before the v4 CRC is committed. */
	if (s22plus_max77705_p317_encode_envelope(
		binding, exec, semantic_kind, semantic_code, base_observer_site,
		observer_error_class, result, summary, envelope, &base_detail) != 0)
		return -1;
	(void)base_detail;
	if (result != NULL) {
		for (slot = 0U; slot < S22PLUS_MAX77705_RUNTIME_COMMANDS; ++slot) {
			if (raw_size + result->poll_count[slot] > sizeof(raw))
				return -1;
			s22plus_max77705_envelope_copy(
				raw + raw_size, result->poll_bytes[slot],
				result->poll_count[slot]);
			raw_size += result->poll_count[slot];
		}
		encoded_size = s22plus_max77705_packbits(
			raw, raw_size, encoded, sizeof(encoded));
	}

	flags = envelope[7] & (S22PLUS_MAX77705_FLAG_RESULT_PRESENT |
		S22PLUS_MAX77705_FLAG_BINDING_PRESENT |
		S22PLUS_MAX77705_P317_FLAG_EXEC_PRESENT);
	memset(envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET, 0,
		S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE);
	envelope[0] = 'M';
	envelope[1] = 'X';
	envelope[2] = 'D';
	envelope[3] = '4';
	envelope[4] = S22PLUS_MAX77705_P318_ENVELOPE_VERSION;
	if (semantic_kind == S22PLUS_MAX77705_SEMANTIC_TERMINAL) {
		envelope[5] = (uint8_t)semantic_code;
		envelope[6] = 0U;
	} else {
		envelope[5] = 0U;
		envelope[6] = (uint8_t)semantic_code;
	}
	s22plus_max77705_p318_store_timing(
		envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET, &timing);
	envelope[S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 26U] =
		banner->outcome;
	envelope[S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 27U] =
		banner->error_class;
	envelope[S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 28U] =
		banner->bytes_written;
	if (encoded_size > sizeof(encoded)) {
		if (result == NULL || summary == NULL)
			return -1;
		envelope[5] = S22PLUS_MAX77705_TERMINAL_PAYLOAD_OVERFLOW;
		envelope[6] = 0U;
		flags |= S22PLUS_MAX77705_FLAG_POLL_OVERFLOW;
		envelope[43] = S22PLUS_MAX77705_POLL_ENCODING_SHA256_SUMMARY;
		envelope[46] = S22PLUS_MAX77705_P318_OVERFLOW_USED;
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET +
				S22PLUS_MAX77705_P318_PREFIX_SIZE,
			summary->sha256, 32U);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 61U,
			summary->or_mask, 4U);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 65U,
			summary->poll0, 4U);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET + 69U,
			summary->nonzero_count, 4U);
	} else {
		flags |= S22PLUS_MAX77705_FLAG_POLL_LOSSLESS;
		envelope[43] = S22PLUS_MAX77705_POLL_ENCODING_PACKBITS;
		envelope[46] = (uint8_t)(
			S22PLUS_MAX77705_P318_PREFIX_SIZE + encoded_size);
		s22plus_max77705_envelope_copy(
			envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET +
				S22PLUS_MAX77705_P318_PREFIX_SIZE,
			encoded, encoded_size);
	}
	envelope[7] = flags;
	envelope[47] = (uint8_t)(
		(observer_site << 4U) | observer_error_class);
	crc = s22plus_max77705_p318_envelope_crc32(envelope);
	s22plus_max77705_store_le32(
		envelope + S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET, crc);
	*terminal_detail = envelope[5] != 0U
		? (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + envelope[5] - 1U)
		: (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + 0x0fU +
			envelope[6] - 1U);
	return 0;
}
