#!/usr/bin/env python3
"""Transform the immutable P3.09 patch to the Carrier v2 kernel ABI."""

from __future__ import annotations

import s22plus_fyg8_p252_source_contract as p252


class TransformError(ValueError):
    pass


def _replace_between(value: bytes, start: bytes, end: bytes, replacement: bytes) -> bytes:
    if value.count(start) != 1 or value.count(end) != 1:
        raise TransformError(f"carrier transform anchor differs: {start!r}/{end!r}")
    left = value.index(start)
    right = value.index(end, left)
    if right <= left:
        raise TransformError("carrier transform anchors are reversed")
    return value[:left] + replacement + value[right:]


DEFINITIONS = b'''+#define S22_FYG8_E1_LONG_SIZE\t\t192U
+#define S22_FYG8_E1_HEADER_SIZE\t\t32U
+#define S22_FYG8_E1_SLOT_SIZE\t\t80U
+#define S22_FYG8_E1_SLOT_PAYLOAD_SIZE\t67U
+#define S22_FYG8_E1_REQUEST_PAYLOAD_SIZE 64U
+#define S22_FYG8_E1_UNSAT_SIZE\t\t24U
+#define S22_FYG8_E1_REQUEST_V2_SIZE\t32U
+#define S22_FYG8_E1_REQUEST_V3_SIZE\t100U
+#define S22_FYG8_E1_REQUEST_V2\t\t2U
+#define S22_FYG8_E1_REQUEST_V3\t\t3U
+#define S22_FYG8_E1_FORMAT_VERSION\t2U
+#define S22_FYG8_E1_PAYLOAD_NONE\t0U
+#define S22_FYG8_E1_PAYLOAD_RAW_EXCERPT 1U
+#define S22_FYG8_E1_PROFILE_E1A\t\t1U
+#define S22_FYG8_E1_PROFILE_E1B\t\t2U
+#define S22_FYG8_E1_PROFILE_E2\t\t3U
+#define S22_FYG8_E1_PROGRESS\t\t0U
+#define S22_FYG8_E1_SUCCESS\t\t1U
+#define S22_FYG8_E1_FAILURE\t\t2U
+#define S22_FYG8_E1_STRATEGY\t\t3U
+#define S22_FYG8_E1_ADDRESS_CELLS\t2U
+#define S22_FYG8_E1_SIZE_CELLS\t\t2U
+
+struct s22_fyg8_e1_log_head {
+\tu32 boot_cnt;
+\tu32 magic;
+\tu32 idx;
+\tu32 prev_idx;
+\tchar buf[];
+};
+
+struct s22_fyg8_e1_slot {
+\tu8 generation;
+\tu8 stage;
+\tu8 outcome;
+\tu8 item_index;
+\tu8 payload_kind;
+\tu8 payload_len;
+\tu8 reserved;
+\t__le16 detail;
+\tu8 payload[S22_FYG8_E1_SLOT_PAYLOAD_SIZE];
+\t__le32 commit_crc;
+} __packed;
+
+struct s22_fyg8_e1_record {
+\tu8 header[S22_FYG8_E1_HEADER_SIZE];
+\tstruct s22_fyg8_e1_slot slots[2];
+} __packed;
+
+struct s22_fyg8_e1_request_v2 {
+\tu8 magic[4];
+\tu8 version;
+\tu8 profile;
+\tu8 stage;
+\tu8 outcome;
+\t__le16 detail;
+\tu8 item_index;
+\tu8 reserved;
+\tu8 run_id[16];
+\t__le32 crc32;
+} __packed;
+
+struct s22_fyg8_e1_request_v3 {
+\tu8 magic[4];
+\tu8 version;
+\tu8 profile;
+\tu8 stage;
+\tu8 outcome;
+\t__le16 detail;
+\tu8 item_index;
+\tu8 payload_kind;
+\tu8 payload_len;
+\tu8 reserved[3];
+\tu8 run_id[16];
+\tu8 payload[S22_FYG8_E1_REQUEST_PAYLOAD_SIZE];
+\t__le32 crc32;
+} __packed;
+
+struct s22_fyg8_e1_request {
+\tu8 profile;
+\tu8 stage;
+\tu8 outcome;
+\tu8 item_index;
+\t__le16 detail;
+\tu8 payload_kind;
+\tu8 payload_len;
+\tu8 run_id[16];
+\tu8 payload[S22_FYG8_E1_REQUEST_PAYLOAD_SIZE];
+};
+
+struct s22_fyg8_e1_state {
+\tbool ready;
+\tbool terminal;
+\tu8 active_slot;
+\tu8 profile;
+\tstruct s22_fyg8_e1_slot active;
+\tu32 seed_idx;
+\tu32 seed_boot_cnt;
+\tsize_t proof_pos;
+\tu8 header[S22_FYG8_E1_HEADER_SIZE];
+};
+
+static struct s22_fyg8_e1_state s22_fyg8_e1_state;
+
+static const u8 s22_fyg8_e1_long_family[] = "S22E1L2|";
+static const u8 s22_fyg8_e1_unsat_family[] = "S22E1U2|";
+static const u8 s22_fyg8_e1_v1_long[] = "S22E1L1|";
+static const u8 s22_fyg8_e1_v1_unsat[] = "S22E1U1|";
+static const u8 s22_fyg8_e1_legacy_long[] = "[[S22P1U|";
+static const u8 s22_fyg8_e1_legacy_unsat[] = "S22UNS1|";
+static const u8 s22_fyg8_e1_header_crc_domain[] =
+\t"S22PLUS-FYG8-P310-HEADER-V2";
+static const u8 s22_fyg8_e1_slot_crc_domain[] =
+\t"S22PLUS-FYG8-P310-SLOT-V2";
+
'''


FAMILY_VALIDATION = b'''+static u32 s22_fyg8_e1_header_crc(const u8 header[32]);
+
+static bool s22_fyg8_e1_header_valid(const u8 header[32])
+{
+\t__le32 recorded;
+\tu32 expected;
+
+\tif (memcmp(header, s22_fyg8_e1_long_family,
+\t\t\tsizeof(s22_fyg8_e1_long_family) - 1) ||
+\t\t\theader[8] >> 4 != S22_FYG8_E1_FORMAT_VERSION ||
+\t\t\theader[9] != S22_FYG8_E1_HEADER_SIZE ||
+\t\t\theader[10] != (S22_FYG8_E1_LONG_SIZE & 0xff) ||
+\t\t\theader[11] != (S22_FYG8_E1_LONG_SIZE >> 8))
+\t\treturn false;
+\tmemcpy(&recorded, &header[28], sizeof(recorded));
+\texpected = s22_fyg8_e1_header_crc(header);
+\treturn recorded && le32_to_cpu(recorded) == expected;
+}
+
+static bool s22_fyg8_e1_record_families_allowed(const u8 record[192])
+{
+\treturn s22_fyg8_e1_header_valid(record);
+}
+
+static bool s22_fyg8_e1_unsat_families_allowed(const u8 record[24])
+{
+\tif (memcmp(record, s22_fyg8_e1_unsat_family,
+\t\t   sizeof(s22_fyg8_e1_unsat_family) - 1))
+\t\treturn false;
+\tif (s22_fyg8_e1_contains(record + 1, S22_FYG8_E1_UNSAT_SIZE - 1,
+\t\t\ts22_fyg8_e1_unsat_family,
+\t\t\tsizeof(s22_fyg8_e1_unsat_family) - 1))
+\t\treturn false;
+\treturn !s22_fyg8_e1_contains(record, S22_FYG8_E1_UNSAT_SIZE,
+\t\t\ts22_fyg8_e1_long_family,
+\t\t\tsizeof(s22_fyg8_e1_long_family) - 1) &&
+\t\t!s22_fyg8_e1_contains(record, S22_FYG8_E1_UNSAT_SIZE,
+\t\t\ts22_fyg8_e1_v1_long,
+\t\t\tsizeof(s22_fyg8_e1_v1_long) - 1) &&
+\t\t!s22_fyg8_e1_contains(record, S22_FYG8_E1_UNSAT_SIZE,
+\t\t\ts22_fyg8_e1_v1_unsat,
+\t\t\tsizeof(s22_fyg8_e1_v1_unsat) - 1) &&
+\t\t!s22_fyg8_e1_contains(record, S22_FYG8_E1_UNSAT_SIZE,
+\t\t\ts22_fyg8_e1_legacy_long,
+\t\t\tsizeof(s22_fyg8_e1_legacy_long) - 1) &&
+\t\t!s22_fyg8_e1_contains(record, S22_FYG8_E1_UNSAT_SIZE,
+\t\t\ts22_fyg8_e1_legacy_unsat,
+\t\t\tsizeof(s22_fyg8_e1_legacy_unsat) - 1);
+}
+
'''


CRC_AND_SLOT = b'''+static u32 s22_fyg8_e1_crc32(const void *data, size_t size)
+{
+\treturn crc32_le(~0U, data, size) ^ ~0U;
+}
+
+static u32 s22_fyg8_e1_header_crc(const u8 header[32])
+{
+\tu32 value = ~0U;
+
+\tvalue = crc32_le(value, s22_fyg8_e1_header_crc_domain,
+\t\t\tsizeof(s22_fyg8_e1_header_crc_domain));
+\tvalue = crc32_le(value, header, 28);
+\treturn value ^ ~0U;
+}
+
+static u32 s22_fyg8_e1_slot_crc(const u8 header[32], u8 slot_id,
+\t\tconst struct s22_fyg8_e1_slot *slot)
+{
+\tu32 value = ~0U;
+
+\tvalue = crc32_le(value, s22_fyg8_e1_slot_crc_domain,
+\t\t\tsizeof(s22_fyg8_e1_slot_crc_domain));
+\tvalue = crc32_le(value, header, S22_FYG8_E1_HEADER_SIZE);
+\tvalue = crc32_le(value, &slot_id, sizeof(slot_id));
+\tvalue = crc32_le(value, (const u8 *)slot,
+\t\t\toffsetof(struct s22_fyg8_e1_slot, commit_crc));
+\treturn value ^ ~0U;
+}
+
+static bool s22_fyg8_e1_build_slot(struct s22_fyg8_e1_slot *slot,
+\t\tu8 slot_id, u8 generation, u8 stage, u8 outcome,
+\t\tu8 item_index, u16 detail, u8 payload_kind, u8 payload_len,
+\t\tconst u8 *payload, const u8 header[32])
+{
+\tu32 crc;
+
+\tif ((payload_kind == S22_FYG8_E1_PAYLOAD_NONE && payload_len) ||
+\t\t\t(payload_kind == S22_FYG8_E1_PAYLOAD_RAW_EXCERPT &&
+\t\t\t (!payload_len || payload_len > S22_FYG8_E1_REQUEST_PAYLOAD_SIZE)) ||
+\t\t\t(payload_kind != S22_FYG8_E1_PAYLOAD_NONE &&
+\t\t\t payload_kind != S22_FYG8_E1_PAYLOAD_RAW_EXCERPT))
+\t\treturn false;
+\tmemset(slot, 0, sizeof(*slot));
+\tslot->generation = generation;
+\tslot->stage = stage;
+\tslot->outcome = outcome;
+\tslot->item_index = item_index;
+\tslot->payload_kind = payload_kind;
+\tslot->payload_len = payload_len;
+\tslot->detail = cpu_to_le16(detail);
+\tif (payload_len)
+\t\tmemcpy(slot->payload, payload, payload_len);
+\tcrc = s22_fyg8_e1_slot_crc(header, slot_id, slot);
+\tif (!crc)
+\t\treturn false;
+\tslot->commit_crc = cpu_to_le32(crc);
+\treturn true;
+}
+
'''


REQUEST_ALLOWED = b'''+static noinline __used bool s22_fyg8_e1_request_allowed(
+\t\tconst struct s22_fyg8_e1_request *request)
+{
+\tconst u8 *sequence;
+\tsize_t count;
+\tsize_t ordinal = s22_fyg8_e1_state.active.generation;
+\tu8 expected_item;
+
+\tsequence = s22_fyg8_e1_sequence(request->profile, &count);
+\tif (!sequence || ordinal >= count ||
+\t\t\trequest->stage != sequence[ordinal] ||
+\t\t\t!s22_fyg8_e1_expected_item(request->profile, ordinal,
+\t\t\t\tcount, request->stage, &expected_item) ||
+\t\t\trequest->item_index != expected_item)
+\t\treturn false;
+\treturn s22_fyg8_e1_detail_allowed(
+\t\trequest->profile, ordinal, count, request->outcome,
+\t\tle16_to_cpu(request->detail));
+}
+
'''


RECORD_AND_WRITE = b'''+static void s22_fyg8_e1_record_entry(const char *init_filename)
+{
+\tstruct s22_fyg8_e1_log_head *head;
+\tstruct s22_fyg8_e1_record record;
+\tu8 run_id[16];
+\tu8 unsat_tag[16];
+\tu8 unsat[S22_FYG8_E1_UNSAT_SIZE];
+\tsize_t payload_size = S22_FYG8_E1_LOG_SIZE - sizeof(*head);
+\tsize_t cursor;
+\tu32 header_crc;
+\tu32 seed_idx;
+
+\tmemset(&s22_fyg8_e1_state, 0, sizeof(s22_fyg8_e1_state));
+\tif (strcmp(init_filename, "/init") || task_pid_nr(current) != 1)
+\t\treturn;
+\tif (CONFIG_S22PLUS_FYG8_E1_PROFILE != S22_FYG8_E1_PROFILE_E1A &&
+\t\t\tCONFIG_S22PLUS_FYG8_E1_PROFILE != S22_FYG8_E1_PROFILE_E1B &&
+\t\t\tCONFIG_S22PLUS_FYG8_E1_PROFILE != S22_FYG8_E1_PROFILE_E2)
+\t\treturn;
+\tif (!s22_fyg8_e1_parse_hex(CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX,
+\t\t\trun_id) ||
+\t\t\t!s22_fyg8_e1_parse_hex(CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX,
+\t\t\t\tunsat_tag))
+\t\treturn;
+\thead = s22_fyg8_e1_head();
+\tif (!head || READ_ONCE(head->magic) != S22_FYG8_E1_LOG_MAGIC)
+\t\treturn;
+\tseed_idx = READ_ONCE(head->idx);
+\ts22_fyg8_e1_state.seed_idx = seed_idx;
+\ts22_fyg8_e1_state.seed_boot_cnt = READ_ONCE(head->boot_cnt);
+\tcursor = seed_idx % payload_size;
+\tif (seed_idx < S22_FYG8_E1_UNSAT_SIZE)
+\t\treturn;
+\tif (seed_idx < S22_FYG8_E1_LONG_SIZE) {
+\t\tmemcpy(unsat, s22_fyg8_e1_unsat_family,
+\t\t       sizeof(s22_fyg8_e1_unsat_family) - 1);
+\t\tmemcpy(unsat + sizeof(s22_fyg8_e1_unsat_family) - 1,
+\t\t       unsat_tag, sizeof(unsat_tag));
+\t\tif (!s22_fyg8_e1_unsat_families_allowed(unsat))
+\t\t\treturn;
+\t\ts22_fyg8_e1_state.proof_pos = cursor - sizeof(unsat);
+\t\tif (!s22_fyg8_e1_header_matches(head))
+\t\t\treturn;
+\t\tif (!s22_fyg8_e1_store(
+\t\t\t\t&head->buf[s22_fyg8_e1_state.proof_pos], unsat,
+\t\t\t\tsizeof(unsat)) ||
+\t\t\t\t!s22_fyg8_e1_header_matches(head))
+\t\t\treturn;
+\t\treturn;
+\t}
+
+\tmemset(&record, 0, sizeof(record));
+\tmemcpy(record.header, s22_fyg8_e1_long_family,
+\t       sizeof(s22_fyg8_e1_long_family) - 1);
+\trecord.header[8] =
+\t\t(S22_FYG8_E1_FORMAT_VERSION << 4) |
+\t\tCONFIG_S22PLUS_FYG8_E1_PROFILE;
+\trecord.header[9] = S22_FYG8_E1_HEADER_SIZE;
+\trecord.header[10] = S22_FYG8_E1_LONG_SIZE & 0xff;
+\trecord.header[11] = S22_FYG8_E1_LONG_SIZE >> 8;
+\tmemcpy(&record.header[12], run_id, sizeof(run_id));
+\theader_crc = s22_fyg8_e1_header_crc(record.header);
+\tif (!header_crc)
+\t\treturn;
+\theader_crc = cpu_to_le32(header_crc);
+\tmemcpy(&record.header[28], &header_crc, sizeof(header_crc));
+\tif (!s22_fyg8_e1_build_slot(&record.slots[0], 0, 0, 0,
+\t\t\tS22_FYG8_E1_PROGRESS, 0, 0,
+\t\t\tS22_FYG8_E1_PAYLOAD_NONE, 0, NULL, record.header) ||
+\t\t\t!s22_fyg8_e1_record_families_allowed((const u8 *)&record))
+\t\treturn;
+\ts22_fyg8_e1_state.proof_pos = cursor >= sizeof(record) ?
+\t\tcursor - sizeof(record) : payload_size - sizeof(record);
+\tif (!s22_fyg8_e1_header_matches(head) ||
+\t\t\t!s22_fyg8_e1_store(
+\t\t\t\t&head->buf[s22_fyg8_e1_state.proof_pos],
+\t\t\t\t&record, sizeof(record)) ||
+\t\t\t!s22_fyg8_e1_header_matches(head))
+\t\treturn;
+\tmemcpy(s22_fyg8_e1_state.header, record.header, sizeof(record.header));
+\tmemcpy(&s22_fyg8_e1_state.active, &record.slots[0],
+\t       sizeof(s22_fyg8_e1_state.active));
+\ts22_fyg8_e1_state.profile = CONFIG_S22PLUS_FYG8_E1_PROFILE;
+\ts22_fyg8_e1_state.ready = true;
+}
+
+static bool s22_fyg8_e1_bytes_zero(const u8 *value, size_t size)
+{
+\tsize_t index;
+
+\tfor (index = 0; index < size; ++index) {
+\t\tif (value[index])
+\t\t\treturn false;
+\t}
+\treturn true;
+}
+
+static int s22_fyg8_e1_read_request(const char __user *buffer,
+\t\tsize_t count, struct s22_fyg8_e1_request *view)
+{
+\tu32 expected;
+
+\tmemset(view, 0, sizeof(*view));
+\tif (count == sizeof(struct s22_fyg8_e1_request_v2)) {
+\t\tstruct s22_fyg8_e1_request_v2 request;
+
+\t\tif (copy_from_user(&request, buffer, sizeof(request)))
+\t\t\treturn -EFAULT;
+\t\texpected = s22_fyg8_e1_crc32(&request,
+\t\t\toffsetof(struct s22_fyg8_e1_request_v2, crc32));
+\t\tif (memcmp(request.magic, "S22Q", 4) ||
+\t\t\t\trequest.version != S22_FYG8_E1_REQUEST_V2 ||
+\t\t\t\trequest.reserved || le32_to_cpu(request.crc32) != expected)
+\t\t\treturn -EBADMSG;
+\t\tview->profile = request.profile;
+\t\tview->stage = request.stage;
+\t\tview->outcome = request.outcome;
+\t\tview->item_index = request.item_index;
+\t\tview->detail = request.detail;
+\t\tmemcpy(view->run_id, request.run_id, sizeof(view->run_id));
+\t\treturn 0;
+\t}
+\tif (count == sizeof(struct s22_fyg8_e1_request_v3)) {
+\t\tstruct s22_fyg8_e1_request_v3 request;
+
+\t\tif (copy_from_user(&request, buffer, sizeof(request)))
+\t\t\treturn -EFAULT;
+\t\texpected = s22_fyg8_e1_crc32(&request,
+\t\t\toffsetof(struct s22_fyg8_e1_request_v3, crc32));
+\t\tif (memcmp(request.magic, "S22Q", 4) ||
+\t\t\t\trequest.version != S22_FYG8_E1_REQUEST_V3 ||
+\t\t\t\t!s22_fyg8_e1_bytes_zero(request.reserved,
+\t\t\t\t\tsizeof(request.reserved)) ||
+\t\t\t\trequest.payload_len > S22_FYG8_E1_REQUEST_PAYLOAD_SIZE ||
+\t\t\t\t!s22_fyg8_e1_bytes_zero(
+\t\t\t\t\trequest.payload + request.payload_len,
+\t\t\t\t\tS22_FYG8_E1_REQUEST_PAYLOAD_SIZE - request.payload_len) ||
+\t\t\t\tle32_to_cpu(request.crc32) != expected)
+\t\t\treturn -EBADMSG;
+\t\tview->profile = request.profile;
+\t\tview->stage = request.stage;
+\t\tview->outcome = request.outcome;
+\t\tview->item_index = request.item_index;
+\t\tview->detail = request.detail;
+\t\tview->payload_kind = request.payload_kind;
+\t\tview->payload_len = request.payload_len;
+\t\tmemcpy(view->run_id, request.run_id, sizeof(view->run_id));
+\t\tmemcpy(view->payload, request.payload, sizeof(view->payload));
+\t\tif ((view->payload_kind == S22_FYG8_E1_PAYLOAD_NONE &&
+\t\t\t\tview->payload_len) ||
+\t\t\t\t(view->payload_kind == S22_FYG8_E1_PAYLOAD_RAW_EXCERPT &&
+\t\t\t\t !view->payload_len) ||
+\t\t\t\t(view->payload_kind != S22_FYG8_E1_PAYLOAD_NONE &&
+\t\t\t\t view->payload_kind != S22_FYG8_E1_PAYLOAD_RAW_EXCERPT))
+\t\t\treturn -ERANGE;
+\t\treturn 0;
+\t}
+\treturn -EINVAL;
+}
+
+static ssize_t s22_fyg8_e1_write(struct file *file,
+\t\tconst char __user *buffer, size_t count, loff_t *position)
+{
+\tstruct s22_fyg8_e1_request request;
+\tstruct s22_fyg8_e1_log_head *head;
+\tstruct s22_fyg8_e1_record *record;
+\tstruct s22_fyg8_e1_slot next;
+\tstruct s22_fyg8_e1_record prospective;
+\tu8 generation;
+\tu8 next_slot;
+\tint ret;
+
+\t(void)file;
+\tif (task_pid_nr(current) != 1)
+\t\treturn -EPERM;
+\tif (!s22_fyg8_e1_state.ready)
+\t\treturn -ENODEV;
+\tif (s22_fyg8_e1_state.terminal)
+\t\treturn -EALREADY;
+\tif (*position != 0)
+\t\treturn -EINVAL;
+\tret = s22_fyg8_e1_read_request(buffer, count, &request);
+\tif (ret)
+\t\treturn ret;
+\tif (request.profile != s22_fyg8_e1_state.profile ||
+\t\t\tmemcmp(request.run_id, &s22_fyg8_e1_state.header[12], 16))
+\t\treturn -EKEYREJECTED;
+\tif (!s22_fyg8_e1_request_allowed(&request))
+\t\treturn -ERANGE;
+
+\thead = s22_fyg8_e1_head();
+\tif (!head || !s22_fyg8_e1_header_matches(head))
+\t\treturn -ESTALE;
+\trecord = (struct s22_fyg8_e1_record *)
+\t\t&head->buf[s22_fyg8_e1_state.proof_pos];
+\tif (memcmp(record->header, s22_fyg8_e1_state.header,
+\t\t   sizeof(record->header)) ||
+\t\t\tmemcmp(&record->slots[s22_fyg8_e1_state.active_slot],
+\t\t\t       &s22_fyg8_e1_state.active,
+\t\t\t       sizeof(s22_fyg8_e1_state.active)))
+\t\treturn -ESTALE;
+
+\tnext_slot = s22_fyg8_e1_state.active_slot ^ 1U;
+\tif (s22_fyg8_e1_state.active.generation == 0xff)
+\t\treturn -EOVERFLOW;
+\tgeneration = s22_fyg8_e1_state.active.generation + 1U;
+\tif (!s22_fyg8_e1_build_slot(&next, next_slot,
+\t\t\tgeneration, request.stage, request.outcome, request.item_index,
+\t\t\tle16_to_cpu(request.detail), request.payload_kind,
+\t\t\trequest.payload_len,
+\t\t\trequest.payload, s22_fyg8_e1_state.header))
+\t\treturn -EKEYREJECTED;
+\tmemcpy(&prospective, record, sizeof(prospective));
+\tmemcpy(&prospective.slots[next_slot], &next, sizeof(next));
+\tif (!s22_fyg8_e1_record_families_allowed((const u8 *)&prospective))
+\t\treturn -EKEYREJECTED;
+
+\tmemset(&record->slots[next_slot].commit_crc, 0,
+\t       sizeof(record->slots[next_slot].commit_crc));
+\t__flush_dcache_area(&record->slots[next_slot].commit_crc,
+\t\t\t    sizeof(record->slots[next_slot].commit_crc));
+\tsmp_wmb();
+\tmemcpy(&record->slots[next_slot], &next,
+\t       offsetof(struct s22_fyg8_e1_slot, commit_crc));
+\t__flush_dcache_area(&record->slots[next_slot],
+\t\t\t    offsetof(struct s22_fyg8_e1_slot, commit_crc));
+\tsmp_wmb();
+\tif (!s22_fyg8_e1_header_matches(head) ||
+\t\t\tmemcmp(record->header, s22_fyg8_e1_state.header,
+\t\t\t       sizeof(record->header)) ||
+\t\t\tmemcmp(&record->slots[s22_fyg8_e1_state.active_slot],
+\t\t\t       &s22_fyg8_e1_state.active,
+\t\t\t       sizeof(s22_fyg8_e1_state.active)))
+\t\treturn -ESTALE;
+\tmemcpy(&record->slots[next_slot].commit_crc, &next.commit_crc,
+\t       sizeof(next.commit_crc));
+\t__flush_dcache_area(&record->slots[next_slot].commit_crc,
+\t\t\t    sizeof(record->slots[next_slot].commit_crc));
+\tsmp_wmb();
+\tif (!s22_fyg8_e1_header_matches(head) ||
+\t\t\tmemcmp(record->header, s22_fyg8_e1_state.header,
+\t\t\t       sizeof(record->header)) ||
+\t\t\tmemcmp(&record->slots[next_slot], &next, sizeof(next)))
+\t\treturn -ESTALE;
+
+\ts22_fyg8_e1_state.active_slot = next_slot;
+\tmemcpy(&s22_fyg8_e1_state.active, &next,
+\t       sizeof(s22_fyg8_e1_state.active));
+\ts22_fyg8_e1_state.terminal =
+\t\trequest.outcome != S22_FYG8_E1_PROGRESS;
+\t*position += count;
+\treturn count;
+}
+
'''


BUILD_ASSERTS = b'''+\tBUILD_BUG_ON(sizeof(struct s22_fyg8_e1_record) !=
+\t\t\tS22_FYG8_E1_LONG_SIZE);
+\tBUILD_BUG_ON(sizeof(struct s22_fyg8_e1_slot) !=
+\t\t\tS22_FYG8_E1_SLOT_SIZE);
+\tBUILD_BUG_ON(sizeof(struct s22_fyg8_e1_request_v2) !=
+\t\t\tS22_FYG8_E1_REQUEST_V2_SIZE);
+\tBUILD_BUG_ON(sizeof(struct s22_fyg8_e1_request_v3) !=
+\t\t\tS22_FYG8_E1_REQUEST_V3_SIZE);
+\tBUILD_BUG_ON(offsetof(struct s22_fyg8_e1_slot, commit_crc) != 76);
+\tBUILD_BUG_ON(offsetof(struct s22_fyg8_e1_request_v2, run_id) != 12);
+\tBUILD_BUG_ON(offsetof(struct s22_fyg8_e1_request_v2, crc32) != 28);
+\tBUILD_BUG_ON(offsetof(struct s22_fyg8_e1_request_v3, run_id) != 16);
+\tBUILD_BUG_ON(offsetof(struct s22_fyg8_e1_request_v3, crc32) != 96);
'''


def transform(patch: bytes) -> bytes:
    value = patch
    value = _replace_between(
        value,
        b"+#define S22_FYG8_E1_LONG_SIZE",
        b"+static const u8 s22_fyg8_e1a_sequence[]",
        DEFINITIONS,
    )
    value = _replace_between(
        value,
        b"+static bool s22_fyg8_e1_record_families_allowed",
        b"+static u32 s22_fyg8_e1_crc32",
        FAMILY_VALIDATION,
    )
    value = _replace_between(
        value,
        b"+static u32 s22_fyg8_e1_crc32",
        b"+static bool s22_fyg8_e1_store",
        CRC_AND_SLOT,
    )
    value = _replace_between(
        value,
        b"+static noinline __used bool s22_fyg8_e1_request_allowed",
        b"+static void s22_fyg8_e1_record_entry",
        REQUEST_ALLOWED,
    )
    value = _replace_between(
        value,
        b"+static void s22_fyg8_e1_record_entry",
        b"+static const struct proc_ops s22_fyg8_e1_ops",
        RECORD_AND_WRITE,
    )
    value = _replace_between(
        value,
        b"+\tBUILD_BUG_ON(sizeof(struct s22_fyg8_e1_record)",
        b"+\tif (!proc_create(\"s22_checkpoint\"",
        BUILD_ASSERTS,
    )
    required = (
        b'S22E1L2|',
        b'S22E1U2|',
        b'S22PLUS-FYG8-P310-HEADER-V2',
        b'S22PLUS-FYG8-P310-SLOT-V2',
        b'S22_FYG8_E1_REQUEST_V3_SIZE\t100U',
        b'offsetof(struct s22_fyg8_e1_slot, commit_crc) != 76',
    )
    forbidden = (
        b'#define S22_FYG8_E1_LONG_SIZE\t\t45U',
        b'S22PLUS-FYG8-P232-SLOT-V1',
    )
    if any(value.count(token) != 1 for token in required):
        raise TransformError("Carrier v2 required token cardinality differs")
    if any(token in value for token in forbidden):
        raise TransformError("Carrier v1 or invalid descriptor token remains")
    return p252._recount_kernel_patch_hunks(value)  # noqa: SLF001
