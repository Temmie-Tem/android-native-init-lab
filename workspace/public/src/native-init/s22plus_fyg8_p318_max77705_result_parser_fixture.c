#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "s22plus_fyg8_p318_max77705_result_parser.inc.c"

static void print_hex(const uint8_t *value, size_t size)
{
	static const char digits[] = "0123456789abcdef";
	size_t index;

	for (index = 0U; index < size; ++index) {
		putchar(digits[value[index] >> 4]);
		putchar(digits[value[index] & 0x0fU]);
	}
}

static int sha_abc(void)
{
	struct s22plus_max77705_runtime_sha256 context;
	uint8_t digest[32];

	s22plus_max77705_runtime_sha256_init(&context);
	s22plus_max77705_runtime_sha256_update(
		&context, (const uint8_t *)"abc", 3U);
	s22plus_max77705_runtime_sha256_final(&context, digest);
	print_hex(digest, sizeof(digest));
	putchar('\n');
	return 0;
}

int main(int argc, char **argv)
{
	char input[4096];
	struct s22plus_max77705_runtime_result result;
	struct s22plus_max77705_runtime_poll_summary summary;
	size_t size;
	int rc;

	if (argc == 2 && strcmp(argv[1], "--sha-abc") == 0)
		return sha_abc();
	if (argc != 1)
		return 64;
	size = fread(input, 1U, sizeof(input), stdin);
	if (ferror(stdin) || !feof(stdin) || size == sizeof(input))
		return 65;
	rc = s22plus_max77705_runtime_parse_result(
		input, size, &result, &summary);
	if (rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK) {
		printf("ERR rc=%d\n", rc);
		return 2;
	}
	printf("OK stage=%u rc=%d raw=%u sha=",
		(unsigned int)result.stage, (int)result.rc,
		(unsigned int)summary.raw_count);
	print_hex(summary.sha256, sizeof(summary.sha256));
	printf(" or=");
	print_hex(summary.or_mask, sizeof(summary.or_mask));
	printf(" poll0=");
	print_hex(summary.poll0, sizeof(summary.poll0));
	printf(" nz=");
	print_hex(summary.nonzero_count, sizeof(summary.nonzero_count));
	printf(" issued=%02x seen=%02x val=",
		(unsigned int)result.command_issued_mask,
		(unsigned int)result.response_seen_mask);
	print_hex(result.response_value, sizeof(result.response_value));
	printf(" tm=%02x tpre=%llu twrite=%llu tpost1=%llu tpost2=%llu\n",
		(unsigned int)result.timing_valid_mask,
		(unsigned long long)result.pre_ns,
		(unsigned long long)result.write_ns,
		(unsigned long long)result.post1_ns,
		(unsigned long long)result.post2_ns);
	return 0;
}
