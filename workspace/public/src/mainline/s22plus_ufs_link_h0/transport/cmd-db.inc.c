// SPDX-License-Identifier: GPL-2.0-only
/* Inspect the immutable command DB before an experimental regulator is
 * registered. Any other entry sharing the four-register VRM window,
 * or a duplicate name at another address, makes that mapping ambiguous.
 */
#include <soc/qcom/g0q-ml030.h>

int g0q_unique_vrm(const char *name, u32 *address)
{
	const struct entry_header *selected = NULL;
	const size_t prefix = offsetof(struct cmd_db_header, data);
	u8 query[sizeof(selected->id)] __nonstring;
	u32 base = 0;

	if (g0q_cmd_db_size < prefix || cmd_db_ready())
		return -ENODEV;
	strtomem_pad(query, name, 0);
	/* The stock lookup assumes trusted offsets. This full-table walk
	 * needs checked extents even for unrelated entries after our rail.
	 */
	for (int i = 0; i < MAX_SLV_ID; i++) {
		const struct rsc_hdr *hdr = &cmd_db_header->header[i];
		const struct entry_header *entry;
		size_t offset = le16_to_cpu(hdr->header_offset);
		size_t count = le16_to_cpu(hdr->cnt);

		if (!hdr->slv_id)
			break;
		if (!IS_ALIGNED(offset, __alignof__(*entry)) ||
		    offset > g0q_cmd_db_size - prefix ||
		    count > (g0q_cmd_db_size - prefix - offset) / sizeof(*entry))
			return -EINVAL;
		entry = rsc_to_entry_header(hdr);
		for (size_t j = 0; j < count; j++, entry++) {
			if (memcmp(entry->id, query, sizeof(query)))
				continue;
			if (selected)
				return -EADDRINUSE;
			selected = entry;
			base = le32_to_cpu(entry->addr);
			if (le16_to_cpu(hdr->slv_id) != CMD_DB_HW_VRM ||
			    SLAVE_ID(base) != CMD_DB_HW_VRM || (base & ~0xffff0U))
				return -ENODEV;
		}
	}
	if (!selected)
		return -ENODEV;
	for (int i = 0; i < MAX_SLV_ID; i++) {
		const struct rsc_hdr *hdr = &cmd_db_header->header[i];
		const struct entry_header *entry;

		if (!hdr->slv_id)
			break;
		entry = rsc_to_entry_header(hdr);
		for (int j = 0; j < le16_to_cpu(hdr->cnt); j++, entry++)
			if (entry != selected &&
			    cmd_db_match_resource_addr(base, le32_to_cpu(entry->addr)))
				return -EADDRINUSE;
	}
	*address = base;
	return 0;
}
