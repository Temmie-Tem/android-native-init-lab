// SPDX-License-Identifier: GPL-2.0-only
/* H0 command DB containing four candidate and one ordinary VRM. The entry
 * reader rejects unchecked calls beyond its simulated reserved-memory map. */
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef uint8_t u8;
typedef uint32_t u32;
#define CMD_DB_HW_VRM 4
#define MAX_SLV_ID 8
#define SLAVE_ID(addr) (((addr) >> 16) & 15)
#define le16_to_cpu(x) (x)
#define le32_to_cpu(x) (x)
#define IS_ALIGNED(x,n) (!((x) % (n)))
#define __nonstring
#define strtomem_pad(dest, src, pad) do { memset(dest,pad,sizeof(dest)); memcpy(dest,src,strlen(src)); } while (0)
struct entry_header { u8 id[8]; u32 priorities[2], addr; uint16_t len, offset; };
struct rsc_hdr { uint16_t slv_id, header_offset, data_offset, cnt, version, reserved[3]; };
struct cmd_db_header { u32 version, magic; struct rsc_hdr header[8]; u32 tail[2]; u8 data[]; };
static union { max_align_t align; u8 bytes[1024]; } mapping;
static struct cmd_db_header *cmd_db_header;
static size_t g0q_cmd_db_size;
static int cmd_db_ready(void) { return 0; }
static const struct entry_header *rsc_to_entry_header(const struct rsc_hdr *hdr)
{
	size_t start = offsetof(struct cmd_db_header, data) + hdr->header_offset;
	assert(start <= g0q_cmd_db_size && hdr->cnt <= (g0q_cmd_db_size - start)/sizeof(struct entry_header));
	return (const struct entry_header *)(mapping.bytes + start);
}
static int cmd_db_match_resource_addr(u32 a, u32 b) { return ((a ^ b) & 0xffff0U) == 0; }
#include "cmd-db.inc.c"

int main(void)
{
	const char *names[] = { "ldob6", "ldob7", "ldob9", "smpb12", "ldob5" };
	u32 output = 0;
	cmd_db_header = (struct cmd_db_header *)mapping.bytes;
	g0q_cmd_db_size = sizeof(mapping.bytes);
	struct rsc_hdr *hdr = &cmd_db_header->header[0];
	hdr->slv_id = CMD_DB_HW_VRM;
	hdr->cnt = 5;
	struct entry_header *entry = (struct entry_header *)cmd_db_header->data;
	for (unsigned int i = 0; i < 5; i++) {
		strcpy((char *)entry[i].id, names[i]);
		entry[i].addr = 0x40300 + i * 16;
	}
	for (unsigned int i = 0; i < 4; i++) {
		assert(!g0q_unique_vrm(names[i], &output));
		assert(output == entry[i].addr);
	}
	u32 original = entry[4].addr;
	entry[4].addr = entry[2].addr + 4;
	assert(g0q_unique_vrm(names[2], &output) == -EADDRINUSE);
	entry[4].addr = original;
	strcpy((char *)entry[4].id, names[3]);
	assert(g0q_unique_vrm(names[3], &output) == -EADDRINUSE);
	assert(g0q_unique_vrm("missing", &output) == -ENODEV);
	entry[0].addr++;
	assert(g0q_unique_vrm(names[0], &output) == -ENODEV);
	entry[0].addr--;
	struct rsc_hdr *next = hdr+1;
	next->slv_id = 5;
	next->header_offset = 2048;
	assert(g0q_unique_vrm(names[0], &output) == -EINVAL);
	next->header_offset = 80;
	next->cnt = 65535;
	assert(g0q_unique_vrm(names[0], &output) == -EINVAL);
	next->cnt = 1;
	next->header_offset = 7;
	assert(g0q_unique_vrm(names[0], &output) == -EINVAL);
	g0q_cmd_db_size = 2;
	assert(g0q_unique_vrm(names[0], &output) == -ENODEV);
	return 0;
}
