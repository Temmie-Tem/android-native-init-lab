// SPDX-License-Identifier: MIT

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "s22plus_fyg8_max77705_result_parser.inc.c"
#include "s22plus_fyg8_max77705_envelope.inc.c"
#include "s22plus_fyg8_max77705_runtime_policy.inc.c"
#include "s22plus_fyg8_p317_max77705_envelope.inc.c"

/*
 * This structure and wrapper are byte-compared with the materialized PID1
 * runtime by s22plus_fyg8_p317_lifecycle_audit.py.  The claim-busy negative
 * fixture therefore executes the same policy-to-observer normalization seam
 * used by p316_observe_diagnostic(), rather than reconstructing its output.
 */
struct p316_diag_observation {
    struct s22plus_max77705_binding_witness binding;
    struct s22plus_max77705_runtime_result result;
    struct s22plus_max77705_runtime_poll_summary summary;
    uint8_t result_valid;
    uint8_t semantic_kind;
    uint8_t semantic_code;
    uint8_t observer_site;
    uint8_t observer_error_class;
};

static void p316_classify_eagain(
    struct p316_diag_observation *observation) {
    if (p316_policy_classify_eagain(
        &observation->binding,
        &observation->semantic_kind,
        &observation->semantic_code) != 0) {
        observation->semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
        observation->semantic_code =
            S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
        observation->observer_site =
            S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY;
        observation->observer_error_class =
            S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT;
    }
}

static int fixture_emit_claim_busy_normalization(void)
{
	struct p316_diag_observation observation = {
		.binding = {
			.loader_state = S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS,
			.pre_exact_parent_present = 1U,
			.pre_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_UNBOUND,
			.pre_matching_unbound_parent_count = 1U,
			.post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_DIAGNOSTIC,
			.post_diagnostic_bound_parent_count = 2U,
			.post_exact_adapter_muic_0x25_client_count = 1U,
		},
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
	uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
	uint16_t detail = 0U;
	int rc;

	if (p316_policy_classify_result(NULL, NULL, NULL, NULL) != -1)
		return 19;
	p316_classify_eagain(&observation);
	if (observation.semantic_kind != S22PLUS_MAX77705_SEMANTIC_TERMINAL ||
	    observation.semantic_code !=
		S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION ||
	    observation.observer_site !=
		S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY ||
	    observation.observer_error_class !=
		S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT)
		return 20;
	rc = s22plus_max77705_p317_encode_envelope(
		&observation.binding, &exec, observation.semantic_kind,
		observation.semantic_code, observation.observer_site,
		observation.observer_error_class,
		NULL, NULL, envelope, &detail);
	if (rc != 0)
		return 21;
	if (fwrite(envelope, 1U, sizeof(envelope), stdout) != sizeof(envelope))
		return 22;
	if (fprintf(stderr, "detail=%04x\n", detail) < 0)
		return 23;
	return 0;
}

static int fixture_u8(const char *text, uint8_t *value)
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
	(void)s22plus_max77705_encode_envelope;
	struct s22plus_max77705_binding_witness binding = {0};
	struct s22plus_max77705_p317_exec_witness exec = {0};
	struct s22plus_max77705_runtime_result result = {0};
	struct s22plus_max77705_runtime_poll_summary summary = {0};
	uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
	uint8_t binding_values[9];
	uint8_t exec_values[6];
	char input[4096];
	size_t input_size;
	unsigned long semantic_code;
	unsigned long observer_site;
	unsigned long observer_error_class;
	unsigned int semantic_kind;
	uint16_t detail = 0U;
	char *end = NULL;
	int index;
	int rc;

	if (argc == 2 && strcmp(argv[1], "claim-busy") == 0)
		return fixture_emit_claim_busy_normalization();
	if (argc != 20)
		return 2;
	if (strcmp(argv[1], "terminal") == 0)
		semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
	else if (strcmp(argv[1], "mux") == 0)
		semantic_kind = S22PLUS_MAX77705_SEMANTIC_MUX;
	else
		return 3;
	errno = 0;
	semantic_code = strtoul(argv[2], &end, 0);
	if (errno != 0 || end == argv[2] || *end != '\0')
		return 4;
	errno = 0;
	observer_site = strtoul(argv[3], &end, 0);
	if (errno != 0 || end == argv[3] || *end != '\0')
		return 4;
	errno = 0;
	observer_error_class = strtoul(argv[4], &end, 0);
	if (errno != 0 || end == argv[4] || *end != '\0')
		return 4;
	for (index = 0; index < 9; ++index) {
		if (fixture_u8(argv[index + 5], &binding_values[index]) != 0)
			return 5;
	}
	for (index = 0; index < 6; ++index) {
		if (fixture_u8(argv[index + 14], &exec_values[index]) != 0)
			return 5;
	}
	memcpy(&binding, binding_values, sizeof(binding));
	memcpy(&exec, exec_values, sizeof(exec));

	input_size = fread(input, 1U, sizeof(input), stdin);
	if (ferror(stdin) || (input_size == sizeof(input) && !feof(stdin)))
		return 6;
	if (input_size != 0U) {
		rc = s22plus_max77705_runtime_parse_result(
			input, input_size, &result, &summary);
		if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
			return 7;
	}
	rc = s22plus_max77705_p317_encode_envelope(
		&binding, &exec, semantic_kind, (unsigned int)semantic_code,
		(unsigned int)observer_site, (unsigned int)observer_error_class,
		input_size == 0U ? NULL : &result,
		input_size == 0U ? NULL : &summary,
		envelope, &detail);
	if (rc != 0)
		return 8;
	if (fwrite(envelope, 1U, sizeof(envelope), stdout) != sizeof(envelope))
		return 9;
	if (fprintf(stderr, "detail=%04x\n", detail) < 0)
		return 10;
	return 0;
}
