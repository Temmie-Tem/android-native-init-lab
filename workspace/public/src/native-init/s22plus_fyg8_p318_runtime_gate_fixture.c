// SPDX-License-Identifier: MIT

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define P260_EPROTO 71
#define S22PLUS_P318_RUNTIME_HELPER_ONLY 1

static int fixture_mode;
static unsigned int fixture_reads;
static unsigned int fixture_snapshot_reads;
static unsigned int fixture_writes;

static long p282_read_file(
	const char *path, char *value, size_t capacity, size_t *length);
static long p282_write_control(const char *path, const char *value);

#include "s22plus_fyg8_p318_dwc3_latch_parser.inc.c"
#include "s22plus_fyg8_p318_max77705_runtime.inc.c"

static const char snapshot_pre[] =
	"v=1 install_v=1 install_ns=100 gate_v=0 gate_ns=0 "
	"event_v=0 event_ns=0 kind=0 raw=00000000\n";
static const char snapshot_pre_exposed[] =
	"v=1 install_v=1 install_ns=100 gate_v=1 gate_ns=200 "
	"event_v=0 event_ns=0 kind=0 raw=00000000\n";
static const char snapshot_pre_event[] =
	"v=1 install_v=1 install_ns=100 gate_v=1 gate_ns=200 "
	"event_v=1 event_ns=300 kind=1 raw=01ff0101\n";
static const char snapshot_after[] =
	"v=1 install_v=1 install_ns=100 gate_v=1 gate_ns=200 "
	"event_v=0 event_ns=0 kind=0 raw=00000000\n";
static const char snapshot_after_drift[] =
	"v=1 install_v=1 install_ns=101 gate_v=1 gate_ns=200 "
	"event_v=0 event_ns=0 kind=0 raw=00000000\n";
static const char snapshot_terminal[] =
	"v=1 install_v=1 install_ns=100 gate_v=1 gate_ns=200 "
	"event_v=1 event_ns=300 kind=1 raw=01ff0101\n";

static long fixture_copy(
	const char *source, char *value, size_t capacity, size_t *length)
{
	size_t amount = strlen(source);

	if (amount > capacity)
		return -75;
	memcpy(value, source, amount);
	*length = amount;
	return 0;
}

static long p282_read_file(
	const char *path, char *value, size_t capacity, size_t *length)
{
	const char *source;

	++fixture_reads;
	if (strcmp(path, P318_LATCH_GATE_PATH) == 0)
		return fixture_copy(
			fixture_mode == 3 ? "0\n" : "1\n",
			value, capacity, length);
	if (strcmp(path, P318_LATCH_SNAPSHOT_PATH) != 0)
		return -2;
	++fixture_snapshot_reads;
	if (fixture_mode == 6)
		source = snapshot_terminal;
	else if (fixture_snapshot_reads == 1U)
		source = fixture_mode == 1 ? snapshot_pre_exposed :
			(fixture_mode == 5 ? snapshot_pre_event : snapshot_pre);
	else
		source = fixture_mode == 4 ? snapshot_after_drift : snapshot_after;
	return fixture_copy(source, value, capacity, length);
}

static long p282_write_control(const char *path, const char *value)
{
	++fixture_writes;
	if (strcmp(path, P318_LATCH_GATE_PATH) != 0 || strcmp(value, "1\n") != 0)
		return -P260_EPROTO;
	return fixture_mode == 2 ? -5 : 0;
}

static void fixture_reset(int mode)
{
	fixture_mode = mode;
	fixture_reads = 0U;
	fixture_snapshot_reads = 0U;
	fixture_writes = 0U;
}

int main(void)
{
	struct s22plus_max77705_p318_latch_snapshot snapshot = {0};
	unsigned int negative = 0U;

	fixture_reset(0);
	if (p318_arm_exposure_gate() != 0 || fixture_reads != 3U ||
	    fixture_snapshot_reads != 2U || fixture_writes != 1U)
		return 1;
	for (int mode = 1; mode <= 5; ++mode) {
		fixture_reset(mode);
		if (p318_arm_exposure_gate() == 0)
			return 2;
		++negative;
	}
	fixture_reset(6);
	if (p318_capture_terminal_latch(&snapshot) != 0 ||
	    snapshot.event_kind != 1U || snapshot.event_raw != 0x01ff0101U ||
	    fixture_reads != 2U || fixture_snapshot_reads != 1U ||
	    fixture_writes != 0U)
		return 3;
	printf(
		"{\"schema\":\"s22plus_fyg8_p318_runtime_gate_fixture_v1\","
		"\"positive\":2,\"negative\":%u,\"verdict\":\"PASS\"}\n",
		negative);
	return 0;
}
