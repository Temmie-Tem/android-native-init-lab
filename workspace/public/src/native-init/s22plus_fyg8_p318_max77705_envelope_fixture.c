// SPDX-License-Identifier: MIT

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct timespec64 {
	int64_t tv_sec;
	int64_t tv_nsec;
};

#define S22PLUS_P318_BANNER_HOST_FIXTURE 1
#include "s22plus_fyg8_p318_max77705_result_parser.inc.c"
#include "s22plus_fyg8_p318_dwc3_latch_parser.inc.c"
#include "s22plus_fyg8_max77705_envelope.inc.c"
#include "s22plus_fyg8_max77705_runtime_policy.inc.c"
#include "s22plus_fyg8_p317_max77705_envelope.inc.c"
#include "s22plus_fyg8_p318_banner_writer.inc.c"
#include "s22plus_fyg8_p318_max77705_envelope.inc.c"

static int parse_u8(const char *text, uint8_t *value)
{
	char *end = NULL;
	unsigned long parsed;

	errno = 0;
	parsed = strtoul(text, &end, 0);
	if (errno != 0 || end == text || *end != '\0' || parsed > 255U)
		return -1;
	*value = (uint8_t)parsed;
	return 0;
}

int main(int argc, char **argv)
{
	char input[4096];
	struct s22plus_max77705_runtime_result result;
	struct s22plus_max77705_runtime_poll_summary summary;
	struct s22plus_max77705_binding_witness binding = {
		.loader_state = S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS,
		.pre_exact_parent_present = 1U,
		.pre_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_UNBOUND,
		.pre_matching_unbound_parent_count = 1U,
		.post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_DIAGNOSTIC,
		.post_diagnostic_bound_parent_count = 1U,
		.post_exact_adapter_muic_0x25_client_count = 1U,
	};
	struct s22plus_max77705_p317_exec_witness exec = {
		.policy = S22PLUS_MAX77705_P317_POLICY_VALID |
			S22PLUS_MAX77705_P317_POLICY_GADGET_READY |
			S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT,
		.pre_present = S22PLUS_MAX77705_P317_PROVIDER_VALID |
			S22PLUS_MAX77705_P317_PROVIDER_MASK,
		.pre_bound = S22PLUS_MAX77705_P317_PROVIDER_MASK,
		.post_present = S22PLUS_MAX77705_P317_PROVIDER_VALID |
			S22PLUS_MAX77705_P317_PROVIDER_MASK,
		.post_bound = S22PLUS_MAX77705_P317_PROVIDER_MASK,
		.link_waiting = S22PLUS_MAX77705_P317_LINK_VALID |
			S22PLUS_MAX77705_P317_WAITING_ZERO |
			(S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE <<
			 S22PLUS_MAX77705_P317_SUPPLIER_SHIFT),
	};
	struct s22plus_max77705_p318_latch_snapshot latch = {
		.install_valid = 1U,
		.gate_valid = 1U,
	};
	struct s22plus_p318_banner_result banner;
	uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
	uint8_t semantic_kind = 0U;
	uint8_t semantic_code = 0U;
	uint8_t observer_site = 0U;
	uint8_t observer_error_class = 0U;
	uint16_t detail = 0U;
	size_t input_size;
	int rc;

	if (argc != 6)
		return 2;
	if (strcmp(argv[1], "observer-gate") == 0 ||
	    strcmp(argv[1], "observer-latch") == 0) {
		if (parse_u8(argv[2], &banner.outcome) != 0 ||
		    parse_u8(argv[3], &banner.error_class) != 0 ||
		    parse_u8(argv[4], &banner.bytes_written) != 0 ||
		    parse_u8(argv[5], &observer_error_class) != 0)
			return 3;
		semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
		semantic_code = S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
		if (strcmp(argv[1], "observer-gate") == 0) {
			memset(&binding, 0, sizeof(binding));
			binding.loader_state = S22PLUS_MAX77705_LOADER_NOT_STARTED;
			memset(&exec, 0, sizeof(exec));
			exec.pre_present = S22PLUS_MAX77705_P317_PROVIDER_VALID |
				S22PLUS_MAX77705_P317_PROVIDER_MASK;
			exec.pre_bound = S22PLUS_MAX77705_P317_PROVIDER_MASK;
			observer_site =
				S22PLUS_MAX77705_P318_OBSERVER_SITE_EXPOSURE_GATE;
		} else {
			observer_site =
				S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH;
		}
		rc = s22plus_max77705_p318_encode_envelope(
			&binding, &exec, semantic_kind, semantic_code,
			observer_site, observer_error_class, NULL, NULL, NULL,
			&banner, envelope, &detail);
		if (rc != 0)
			return 7;
		if (fwrite(envelope, 1U, sizeof(envelope), stdout) !=
		    sizeof(envelope))
			return 8;
		if (fprintf(stderr, "detail=%04x\n", detail) < 0)
			return 9;
		return 0;
	}
	if (parse_u8(argv[1], &banner.outcome) != 0 ||
	    parse_u8(argv[2], &banner.error_class) != 0 ||
	    parse_u8(argv[3], &banner.bytes_written) != 0 ||
	    s22plus_p318_parse_latch_snapshot(
		argv[4], strlen(argv[4]), &latch) != 0 ||
	    !s22plus_p318_exposure_gate_readback_valid(
		argv[5], strlen(argv[5])))
		return 3;
	(void)s22plus_max77705_encode_envelope;
	(void)p316_policy_classify_eagain;
	(void)p316_policy_classify_result;
	(void)s22plus_p318_parse_latch_snapshot;
	(void)s22plus_p318_exposure_gate_readback_valid;
	(void)s22plus_p318_banner_attempt_with_ops;
	input_size = fread(input, 1U, sizeof(input), stdin);
	if (ferror(stdin) || !feof(stdin) || input_size == sizeof(input))
		return 4;
	rc = s22plus_max77705_runtime_parse_result(
		input, input_size, &result, &summary);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
		return 5;
	if (s22plus_max77705_expected_semantic(
		&binding, &result, &semantic_kind, &semantic_code) != 0)
		return 6;
	rc = s22plus_max77705_p318_encode_envelope(
		&binding, &exec, semantic_kind, semantic_code,
		observer_site, observer_error_class,
		&result, &summary, &latch, &banner, envelope, &detail);
	if (rc != 0)
		return 7;
	if (fwrite(envelope, 1U, sizeof(envelope), stdout) != sizeof(envelope))
		return 8;
	if (fprintf(stderr, "detail=%04x\n", detail) < 0)
		return 9;
	return 0;
}
