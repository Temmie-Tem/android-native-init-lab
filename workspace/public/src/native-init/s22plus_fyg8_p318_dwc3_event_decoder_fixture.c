// SPDX-License-Identifier: GPL-2.0-only

#include <stdint.h>
#include <stdio.h>

#include "../kernel-modules/s22plus_dwc3_event_latch/s22plus_dwc3_event_decode.h"

static int expect_kind(uint32_t raw, uint32_t ep0state,
		enum s22plus_dwc3_event_kind expected)
{
	enum s22plus_dwc3_event_kind actual =
		s22plus_dwc3_decode_host_event(raw, ep0state);

	if (actual == expected)
		return 0;
	fprintf(stderr, "raw=%08x ep0=%u actual=%u expected=%u\n",
		raw, ep0state, (unsigned int)actual, (unsigned int)expected);
	return 1;
}

int main(void)
{
	unsigned int positive = 0;
	unsigned int negative = 0;

#define EXPECT_POSITIVE(raw, state, kind) do { \
	if (expect_kind((raw), (state), (kind)) != 0) return 1; \
	++positive; \
} while (0)
#define EXPECT_NEGATIVE(raw, state) do { \
	if (expect_kind((raw), (state), S22PLUS_DWC3_EVENT_NONE) != 0) return 1; \
	++negative; \
} while (0)

	EXPECT_POSITIVE(0x00000101U, 0U, S22PLUS_DWC3_EVENT_RESET);
	EXPECT_POSITIVE(0x01ff0101U, 3U, S22PLUS_DWC3_EVENT_RESET);
	EXPECT_POSITIVE(0x00000201U, 0U, S22PLUS_DWC3_EVENT_CONNECT_DONE);
	EXPECT_POSITIVE(0x01ff0201U, 2U, S22PLUS_DWC3_EVENT_CONNECT_DONE);
	EXPECT_POSITIVE(0x00000040U, 1U,
		S22PLUS_DWC3_EVENT_EP0_SETUP_COMPLETE);
	EXPECT_POSITIVE(0xabcd3040U, 1U,
		S22PLUS_DWC3_EVENT_EP0_SETUP_COMPLETE);

	EXPECT_NEGATIVE(0x00000001U, 1U); /* device disconnect */
	EXPECT_NEGATIVE(0x00000007U, 1U); /* CARKIT class */
	EXPECT_NEGATIVE(0x00000009U, 1U); /* I2C class */
	EXPECT_NEGATIVE(0x00000107U, 1U); /* CARKIT with reset-like type */
	EXPECT_NEGATIVE(0x00000209U, 1U); /* I2C with connect-like type */
	EXPECT_NEGATIVE(0x00000042U, 1U); /* EP1 XFERCOMPLETE */
	EXPECT_NEGATIVE(0x00000044U, 1U); /* EP2 XFERCOMPLETE */
	EXPECT_NEGATIVE(0x000000c0U, 1U); /* EP0 XFERNOTREADY */
	EXPECT_NEGATIVE(0xabcd3040U, 0U); /* EP0 unconnected */
	EXPECT_NEGATIVE(0xabcd3040U, 2U); /* EP0 data phase */
	EXPECT_NEGATIVE(0xabcd3040U, 3U); /* EP0 status phase */

	printf("{\"schema\":\"s22plus_fyg8_p318_dwc3_decoder_fixture_v1\","
	       "\"positive\":%u,\"negative\":%u,\"verdict\":\"PASS\"}\n",
	       positive, negative);
	return 0;
}
