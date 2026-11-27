// SPDX-License-Identifier: GPL-2.0-only
/* Phase 2a: a fixed, read-only UTP sequence after a completed link.
 * Commands: NOP OUT, query set/read flag fDeviceInit, TEST UNIT READY,
 * READ CAPACITY(16), READ(10) of LBAs 1-3 and of the one test block, on LU 0.
 * No write, no other opcode, no query write except fDeviceInit, no other LUN.
 */
#ifndef G0Q_UFS_STORAGE_H
#define G0Q_UFS_STORAGE_H
#include <linux/types.h>

/* LU0 geometry of the live Android32 GPT (4096-byte blocks). */
#define G0Q_LU0_LAST_LBA        62305279ULL
#define G0Q_LU0_LAST_USABLE     62305270ULL
#define G0Q_NATIVE_LAST_LBA     62305023ULL
#define G0Q_TEST_LBA            62305152U
#define G0Q_BLOCK               4096U
/* SHA-256 of the live primary GPT header and entry blocks, LBAs 1-3.
 * Only the host fixture supplies its own synthetic table digest. */
#ifndef G0Q_GPT_SHA256
#define G0Q_GPT_SHA256 \
	"\xa0\xde\x44\x21\x7c\x34\x30\x9c\xf8\x39\x7e\x5e\xcc\xc7\x71\xc6" \
	"\x47\xd0\x6b\x07\xf6\xe8\x89\x26\x54\x91\xec\xe1\xf9\x38\xc5\x53"
#endif

enum g0q_storage_step {
	G0Q_ST_ADMIT = 1, G0Q_ST_LIST, G0Q_ST_NOP, G0Q_ST_INIT_SET, G0Q_ST_INIT_POLL,
	G0Q_ST_TUR, G0Q_ST_CAPACITY, G0Q_ST_GPT, G0Q_ST_BLOCK, G0Q_ST_DONE,
};

enum g0q_storage_flag {
	G0Q_SF_LIST = 1U << 0, G0Q_SF_NOP = 1U << 1, G0Q_SF_INIT_SET = 1U << 2,
	G0Q_SF_INIT_CLEAR = 1U << 3, G0Q_SF_UNIT_ATTENTION = 1U << 4, G0Q_SF_TUR = 1U << 5,
	G0Q_SF_CAPACITY = 1U << 6, G0Q_SF_GPT_READ = 1U << 7, G0Q_SF_GPT_MATCH = 1U << 8,
	G0Q_SF_RANGE = 1U << 9, G0Q_SF_BLOCK_READ = 1U << 10, G0Q_SF_BLOCK_ZERO = 1U << 11,
	G0Q_SF_UNCERTAIN = 1U << 12,
#ifdef G0Q_STORAGE_HEADER
	/* V15: a CHECK CONDITION carried a nonzero Total EHS Length, so its sense
	 * bytes were not located; and the TEST UNIT READY repeat was attempted. */
	G0Q_SF_SENSE_UNPARSED = 1U << 13, G0Q_SF_TUR_REPEAT = 1U << 14,
#endif
#ifdef G0Q_STORAGE_RESPONSE
	/* V16: a CHECK CONDITION carried response Target Failure (0x01). */
	G0Q_SF_TARGET_FAILURE = 1U << 15,
#endif
};

struct g0q_storage {
	int rc;
	u32 step, flags, init_polls, sense, last_status, capacity_low, gpt_word;
	u32 block_digest[8];
#ifdef G0Q_STORAGE_HEADER
	/* V15: header bytes 8-11 of the last response (Total EHS Length, Device
	 * Information, Data Segment Length), big-endian as on the wire. */
	u32 rsp_header;
#endif
};

struct device;
struct reset_control;
struct g0q_link;
/* Runs once, only after the link completed with Device Present. Never retries
 * a command, never clears an uncertain slot, never writes media. */
void g0q_storage_read(struct g0q_link *link, struct device *dev, struct g0q_storage *out,
		      bool *list_started);
/* Stops the list, clears HCE and asserts the host block reset; driver shutdown only. */
void g0q_storage_shutdown(struct g0q_link *link, struct reset_control *host);
#endif
