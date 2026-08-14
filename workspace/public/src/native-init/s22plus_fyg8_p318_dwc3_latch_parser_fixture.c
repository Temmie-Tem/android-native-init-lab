#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "s22plus_fyg8_p318_dwc3_latch_parser.inc.c"

int main(int argc, char **argv)
{
	char input[512];
	struct s22plus_max77705_p318_latch_snapshot snapshot;
	size_t size;

	if (argc == 2 && strcmp(argv[1], "--gate") == 0) {
		size = fread(input, 1U, sizeof(input), stdin);
		return s22plus_p318_exposure_gate_readback_valid(input, size)
			? 0 : 2;
	}
	if (argc != 1)
		return 64;
	size = fread(input, 1U, sizeof(input), stdin);
	if (ferror(stdin) || !feof(stdin) || size == sizeof(input))
		return 65;
	if (s22plus_p318_parse_latch_snapshot(input, size, &snapshot) != 0) {
		puts("ERR");
		return 2;
	}
	printf("OK install=%u:%llu exposure=%u:%llu event=%u:%llu kind=%u raw=%08x\n",
		(unsigned int)snapshot.install_valid,
		(unsigned long long)snapshot.install_ns,
		(unsigned int)snapshot.exposure_valid,
		(unsigned long long)snapshot.exposure_ns,
		(unsigned int)snapshot.event_valid,
		(unsigned long long)snapshot.event_ns,
		(unsigned int)snapshot.event_kind,
		(unsigned int)snapshot.event_raw);
	return 0;
}
