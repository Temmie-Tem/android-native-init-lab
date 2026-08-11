// SPDX-License-Identifier: MIT

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "s22plus_fyg8_max77705_result_parser.inc.c"
#include "s22plus_fyg8_max77705_envelope.inc.c"

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
	struct s22plus_max77705_binding_witness binding = {0};
	struct s22plus_max77705_runtime_result result = {0};
	struct s22plus_max77705_runtime_poll_summary summary = {0};
	uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
	uint8_t binding_values[9];
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

	if (argc != 14)
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
	memcpy(&binding, binding_values, sizeof(binding));

	input_size = fread(input, 1U, sizeof(input), stdin);
	if (ferror(stdin) || (input_size == sizeof(input) && !feof(stdin)))
		return 6;
	if (input_size != 0U) {
		rc = s22plus_max77705_runtime_parse_result(
			input, input_size, &result, &summary);
		if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK)
			return 7;
	}
	rc = s22plus_max77705_encode_envelope(
		&binding, semantic_kind, (unsigned int)semantic_code,
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
