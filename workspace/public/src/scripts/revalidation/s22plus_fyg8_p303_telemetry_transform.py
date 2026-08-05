#!/usr/bin/env python3
"""Transform P3.01 userspace into the P3.03 HS-PHY observer."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p300_telemetry_transform as p300
import s22plus_fyg8_p301_telemetry_transform as inherited
import s22plus_fyg8_p303_telemetry_spec as spec


base = inherited.base


class TelemetryTransformError(ValueError):
    pass


def _clock_event_rows() -> bytes:
    rows = []
    for name, _branch, _clock, _call, offset, _consumer in spec.CALLSITES:
        rows.append(
            f'    {{"p303_{name}", "p:p282/p303_{name} '
            f'{spec.MODULE_RUNTIME_NAME}:{spec.CALLSITE_SYMBOL}+0x{offset:x} '
            'rc=%x0:s32\\n", "common_pid >= 0"},\n'.encode("ascii")
        )
    return b"".join(rows)


def transform_trace_descriptor(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_CYCLE_EVENT_COUNT 16U\n",
        b"#define P282_CYCLE_EVENT_COUNT 28U\n",
        label="P3.03 cycle event capacity",
    )
    start = value.find(
        b"static const struct p282_event_descriptor p282_cycle_events[] = {\n"
    )
    end = value.find(
        b"};\n\nstatic const struct p282_event_descriptor p282_bind_events[]", start
    )
    if start < 0 or end < 0:
        raise TelemetryTransformError("P3.03 cycle descriptor table differs")
    return value[:end] + _clock_event_rows() + value[end:]


P303_CLOCK_RESULT_FIELDS = b"""    uint64_t p303_clock_hits[12];
    int32_t p303_clock_rc[12];
"""


P303_CLOCK_PARSE = b"""    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index < 16U || record->event_index >= 28U) {
            continue;
        }
        size_t clock_index = (size_t)record->event_index - 16U;
        if (!record->has_rc
            || result->p303_clock_hits[clock_index] == UINT64_MAX) {
            return -P260_EPROTO;
        }
        if (result->p303_clock_hits[clock_index] == 0U) {
            result->p303_clock_rc[clock_index] = record->rc;
        }
        ++result->p303_clock_hits[clock_index];
    }

"""


P303_RUNTIME_SUPPORT = br'''
#define P303_CLOCK_CALLSITE_COUNT 12U
#define P303_CLOCK_DETAIL_BASE 0xd00U
#define P303_CLOCK_RESULT_STATES 9U
#define P303_CLOCK_PAIR_STATES 81U
#define P303_CLOCK_EUD_INDEX_BASE 1U
#define P303_CLOCK_NORMAL_INDEX_BASE 82U
#define P303_LOG_DETAIL_BASE 0x4001U

#define P303_DETAIL_CALLSITE_COUNT_CONTRADICTION 0x6001U
#define P303_DETAIL_CALLSITE_BRANCH_CONTRADICTION 0x6002U
#define P303_DETAIL_CFG_AHB_PRESENCE_CONTRADICTION 0x6003U
#define P303_DETAIL_CALLSITE_RETURN_DOMAIN_CONTRADICTION 0x6004U
#define P303_DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION 0x6005U
#define P303_DETAIL_KMSG_OPEN_FAILED 0x6006U
#define P303_DETAIL_KMSG_READ_FAILED 0x6007U
#define P303_DETAIL_KMSG_RING_LOSS 0x6008U
#define P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION 0x6009U
#define P303_DETAIL_KMSG_PATH_NOT_REACHED 0x600aU
#define P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION 0x600bU
#define P303_DETAIL_KMSG_COUNT_OVERFLOW 0x600cU
#define P303_DETAIL_CLOCK_INIT_PATH_CONTRADICTION 0x600dU
#define P303_DETAIL_CLOCK_PROFILE_RECORD_MISMATCH 0x600eU
#define P303_DETAIL_TERMINAL_DOMAIN_CONTRADICTION 0x600fU

#define P303_NR_LSEEK 62
#define P303_SEEK_END 2
#define P303_EPIPE 32
#define P303_KMSG_RECORD_CAPACITY 4096U

struct p303_clock_capture {
    uint64_t hits[P303_CLOCK_CALLSITE_COUNT];
    int32_t rc[P303_CLOCK_CALLSITE_COUNT];
    uint8_t final;
};

struct p303_kmsg_capture {
    int fd;
    uint8_t started;
    uint8_t final;
    uint8_t path_seen;
    uint8_t reset_mask;
    uint8_t sequence_seen;
    uint32_t readback_count;
    uint32_t first_offset;
    uint64_t previous_sequence;
};

static struct p303_clock_capture g_p303_clock;
static struct p303_kmsg_capture g_p303_kmsg = {.fd = -1};

static long p303_lseek(int fd, long offset, int whence) {
    return syscall6(P303_NR_LSEEK, fd, offset, whence, 0, 0, 0);
}

static long p303_parse_hex(
    const char *start, const char *end, uint32_t *value) {
    if (start == end || value == NULL) return -P260_EPROTO;
    uint32_t result = 0;
    for (const char *cursor = start; cursor < end; ++cursor) {
        unsigned int digit = 0;
        if (*cursor >= '0' && *cursor <= '9') {
            digit = (unsigned int)(*cursor - '0');
        } else if (*cursor >= 'a' && *cursor <= 'f') {
            digit = 10U + (unsigned int)(*cursor - 'a');
        } else if (*cursor >= 'A' && *cursor <= 'F') {
            digit = 10U + (unsigned int)(*cursor - 'A');
        } else {
            return -P260_EPROTO;
        }
        if (result > (UINT32_MAX - digit) / 16U) return -P260_EOVERFLOW;
        result = result * 16U + digit;
    }
    *value = result;
    return 0;
}

static long p303_kmsg_begin(void) {
    if (g_p303_kmsg.started || g_p303_kmsg.fd >= 0) {
        return P303_DETAIL_KMSG_OPEN_FAILED;
    }
    long rc = sys_mknodat(
        "/dev/kmsg", S_IFCHR | 0600U, make_dev(1U, 11U));
    if (rc != 0 && rc != -EEXIST) return P303_DETAIL_KMSG_OPEN_FAILED;
    long fd = sys_openat(
        "/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC, 0);
    if (fd < 0) return P303_DETAIL_KMSG_OPEN_FAILED;
    rc = p303_lseek((int)fd, 0, P303_SEEK_END);
    if (rc < 0) {
        (void)sys_close((int)fd);
        return P303_DETAIL_KMSG_OPEN_FAILED;
    }
    g_p303_kmsg.fd = (int)fd;
    g_p303_kmsg.started = 1U;
    return 0;
}

static long p303_kmsg_record(const char *record, size_t length) {
    const char *end = record + length;
    const char *first_comma = p282_find_bytes(record, length, ",");
    const char *second_comma = first_comma == NULL
        ? NULL : p282_find_bytes(
            first_comma + 1, (size_t)(end - first_comma - 1), ",");
    const char *semicolon = p282_find_bytes(record, length, ";");
    if (first_comma == NULL || second_comma == NULL || semicolon == NULL
        || !(first_comma < second_comma && second_comma < semicolon)) {
        return P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION;
    }
    uint64_t sequence = 0;
    long rc = p282_parse_unsigned(first_comma + 1, second_comma, &sequence);
    if (rc != 0
        || (g_p303_kmsg.sequence_seen
            && sequence != g_p303_kmsg.previous_sequence + 1U)) {
        return P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION;
    }
    g_p303_kmsg.sequence_seen = 1U;
    g_p303_kmsg.previous_sequence = sequence;
    const char *message = semicolon + 1;
    size_t message_length = (size_t)(end - message);
    if (p282_find_bytes(
            message, message_length, "msm_hsphy_enable_clocks():") != NULL) {
        g_p303_kmsg.path_seen = 1U;
    }
    if (p282_find_bytes(
            message, message_length, "phy_reset assert failed") != NULL) {
        g_p303_kmsg.reset_mask |= 1U;
    }
    if (p282_find_bytes(
            message, message_length, "phy_reset deassert failed") != NULL) {
        g_p303_kmsg.reset_mask |= 2U;
    }
    const char *writeback = p282_find_bytes(
        message, message_length, "msm_usb_write_readback: write:");
    if (writeback == NULL) return 0;
    const char *offset = p282_find_bytes(message, message_length, "QSCRATCH:");
    const char *failed = p282_find_bytes(message, message_length, "FAILED");
    if (offset == NULL || failed == NULL || offset >= failed) {
        return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
    }
    offset += cstr_len("QSCRATCH:");
    while (offset < failed && p282_is_space(*offset)) ++offset;
    const char *offset_end = offset;
    while (offset_end < failed
        && ((*offset_end >= '0' && *offset_end <= '9')
            || (*offset_end >= 'a' && *offset_end <= 'f')
            || (*offset_end >= 'A' && *offset_end <= 'F'))) {
        ++offset_end;
    }
    uint32_t parsed_offset = 0;
    rc = p303_parse_hex(offset, offset_end, &parsed_offset);
    if (rc != 0 || parsed_offset > 0x1f8U || (parsed_offset & 3U) != 0U) {
        return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
    }
    if (g_p303_kmsg.readback_count == UINT32_MAX) {
        return P303_DETAIL_KMSG_COUNT_OVERFLOW;
    }
    if (g_p303_kmsg.readback_count == 0U) {
        g_p303_kmsg.first_offset = parsed_offset;
    }
    ++g_p303_kmsg.readback_count;
    return 0;
}

static long p303_kmsg_drain(void) {
    if (!g_p303_kmsg.started || g_p303_kmsg.fd < 0 || g_p303_kmsg.final) {
        return P303_DETAIL_KMSG_READ_FAILED;
    }
    char record[P303_KMSG_RECORD_CAPACITY];
    for (;;) {
        long amount = sys_read(
            g_p303_kmsg.fd, record, sizeof(record));
        if (amount == -EAGAIN) return 0;
        if (amount == -P303_EPIPE) return P303_DETAIL_KMSG_RING_LOSS;
        if (amount <= 0 || amount > (long)sizeof(record)) {
            return P303_DETAIL_KMSG_READ_FAILED;
        }
        long rc = p303_kmsg_record(record, (size_t)amount);
        if (rc != 0) return rc;
    }
}

static long p303_kmsg_finish(void) {
    long rc = p303_kmsg_drain();
    long close_rc = g_p303_kmsg.fd >= 0
        ? sys_close(g_p303_kmsg.fd) : -P260_EPROTO;
    g_p303_kmsg.fd = -1;
    if (rc == 0 && close_rc != 0) rc = P303_DETAIL_KMSG_READ_FAILED;
    if (rc == 0) g_p303_kmsg.final = 1U;
    return rc;
}

static long p303_capture_clock(
    const struct p282_trace_control *control,
    const struct p282_cycle_trace_result *result) {
    if (control == NULL || result == NULL || g_p303_clock.final) {
        return P303_DETAIL_CLOCK_INIT_PATH_CONTRADICTION;
    }
    if (!result->phy_init.entered || !result->phy_init.returned
        || result->phy_init.rc != 0) {
        return P303_DETAIL_CLOCK_INIT_PATH_CONTRADICTION;
    }
    for (size_t index = 0; index < P303_CLOCK_CALLSITE_COUNT; ++index) {
        uint64_t hits = result->p303_clock_hits[index];
        if (control->profile_hits[16U + index] != hits) {
            return P303_DETAIL_CLOCK_PROFILE_RECORD_MISMATCH;
        }
        g_p303_clock.hits[index] = hits;
        g_p303_clock.rc[index] = result->p303_clock_rc[index];
    }
    g_p303_clock.final = 1U;
    return 0;
}

static unsigned int p303_errno_bucket(int32_t rc) {
    if (rc == -EINVAL) return 0U;
    if (rc == -EIO) return 1U;
    if (rc == -ETIMEDOUT) return 2U;
    return 3U;
}

static long p303_clock_state(
    size_t prepare_index, size_t enable_index, unsigned int *state) {
    uint64_t prepare_hits = g_p303_clock.hits[prepare_index];
    uint64_t enable_hits = g_p303_clock.hits[enable_index];
    int32_t prepare_rc = g_p303_clock.rc[prepare_index];
    int32_t enable_rc = g_p303_clock.rc[enable_index];
    if (prepare_hits != 1U) {
        return P303_DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION;
    }
    if (prepare_rc > 0 || (enable_hits != 0U && enable_hits != 1U)
        || (enable_hits != 0U && enable_rc > 0)) {
        return P303_DETAIL_CALLSITE_RETURN_DOMAIN_CONTRADICTION;
    }
    if (prepare_rc < 0) {
        if (enable_hits != 0U) {
            return P303_DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION;
        }
        *state = 1U + p303_errno_bucket(prepare_rc);
        return 0;
    }
    if (enable_hits != 1U) {
        return P303_DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION;
    }
    *state = enable_rc < 0
        ? 5U + p303_errno_bucket(enable_rc) : 0U;
    return 0;
}

static long p303_clock_detail(uint16_t *detail) {
    if (detail == NULL || !g_p303_clock.final) {
        return P303_DETAIL_CLOCK_INIT_PATH_CONTRADICTION;
    }
    unsigned int eud_active = 0U;
    unsigned int normal_active = 0U;
    for (size_t index = 0; index < P303_CLOCK_CALLSITE_COUNT; ++index) {
        if (g_p303_clock.hits[index] > 1U) {
            return P303_DETAIL_CALLSITE_COUNT_CONTRADICTION;
        }
        if (g_p303_clock.hits[index] != 0U) {
            if (g_p303_clock.rc[index] > 0) {
                return P303_DETAIL_CALLSITE_RETURN_DOMAIN_CONTRADICTION;
            }
            if (index < 6U) eud_active = 1U;
            else normal_active = 1U;
        }
    }
    if (eud_active && normal_active) {
        return P303_DETAIL_CALLSITE_BRANCH_CONTRADICTION;
    }
    if (!eud_active && !normal_active) {
        *detail = P303_CLOCK_DETAIL_BASE;
        return 0;
    }
    size_t start = eud_active ? 0U : 6U;
    size_t inactive = eud_active ? 6U : 0U;
    for (size_t index = inactive; index < inactive + 6U; ++index) {
        if (g_p303_clock.hits[index] != 0U) {
            return P303_DETAIL_CALLSITE_BRANCH_CONTRADICTION;
        }
    }
    if (g_p303_clock.hits[start + 4U] != 0U
        || g_p303_clock.hits[start + 5U] != 0U) {
        return P303_DETAIL_CFG_AHB_PRESENCE_CONTRADICTION;
    }
    unsigned int ref_src_state = 0;
    unsigned int ref_state = 0;
    long rc = p303_clock_state(start, start + 1U, &ref_src_state);
    if (rc == 0) {
        rc = p303_clock_state(start + 2U, start + 3U, &ref_state);
    }
    if (rc != 0) return rc;
    unsigned int pair =
        ref_src_state * P303_CLOCK_RESULT_STATES + ref_state;
    unsigned int index = (eud_active
        ? P303_CLOCK_EUD_INDEX_BASE : P303_CLOCK_NORMAL_INDEX_BASE) + pair;
    if (index >= 163U) return P303_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
    *detail = (uint16_t)(P303_CLOCK_DETAIL_BASE + index);
    return 0;
}

static long p303_log_detail(uint16_t *detail) {
    if (detail == NULL || !g_p303_kmsg.final) {
        return P303_DETAIL_KMSG_READ_FAILED;
    }
    if (!g_p303_kmsg.path_seen) return P303_DETAIL_KMSG_PATH_NOT_REACHED;
    unsigned int offset_code = 0U;
    unsigned int bucket = 0U;
    if (g_p303_kmsg.readback_count != 0U) {
        if (g_p303_kmsg.first_offset > 0x1f8U
            || (g_p303_kmsg.first_offset & 3U) != 0U) {
            return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
        }
        offset_code = g_p303_kmsg.first_offset / 4U + 1U;
        bucket = g_p303_kmsg.readback_count == 1U ? 1U
            : (g_p303_kmsg.readback_count <= 3U ? 2U : 3U);
    }
    unsigned int index =
        (offset_code * 4U + bucket) * 4U + g_p303_kmsg.reset_mask;
    if (index >= 2048U) return P303_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
    *detail = (uint16_t)(P303_LOG_DETAIL_BASE + index);
    return 0;
}

'''


def transform_runtime_include(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"    uint8_t outer_open;\n};\n",
        b"    uint8_t outer_open;\n" + P303_CLOCK_RESULT_FIELDS + b"};\n",
        label="P3.03 cycle clock result fields",
    )
    value = base.replace_exact(
        value,
        b"    (void)p282_classify_final_pair;\n",
        b"    (void)p282_classify_final_pair;\n"
        b"    (void)p301_terminal_detail;\n",
        label="P3.03 retained P3.01 helper reference",
    )
    anchor = b"    long stop_pid = 0;\n"
    value = base.replace_exact(
        value,
        anchor,
        P303_CLOCK_PARSE + anchor,
        label="P3.03 cycle callsite parsing",
    )
    support_anchor = b"static long p282_parse_role_result(\n"
    if value.count(support_anchor) != 1:
        raise TelemetryTransformError("P3.03 runtime support anchor differs")
    value = value.replace(support_anchor, P303_RUNTIME_SUPPORT + support_anchor, 1)
    value = base.replace_exact(
        value,
        b"    cycle->observed = final_result;\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_RESTART_CAPTURE_RETURNED, 0U);\n",
        b"    cycle->observed = final_result;\n"
        b"    long p303_clock_capture_rc = p303_capture_clock(\n"
        b"        &cycle->trace, &final_result);\n"
        b"    if (p303_clock_capture_rc != 0) {\n"
        b"        p290_fail_next(p303_clock_capture_rc);\n"
        b"    }\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_RESTART_CAPTURE_RETURNED, 0U);\n",
        label="P3.03 final clock capture",
    )
    value = base.replace_exact(
        value,
        b"    for (;;) {\n"
        b"        rc = p298_revalidate_detail();\n",
        b"    for (;;) {\n"
        b"        long p303_kmsg_rc = p303_kmsg_drain();\n"
        b"        if (p303_kmsg_rc != 0) p290_fail_next(p303_kmsg_rc);\n"
        b"        rc = p298_revalidate_detail();\n",
        label="P3.03 periodic kmsg drain",
    )
    old = (
        b"            uint16_t p301_detail = 0;\n"
        b"            rc = p301_terminal_detail(\n"
        b"                &final_result, (unsigned int)ingress_class,\n"
        b"                terminal_detail, &p301_detail);\n"
        b"            if (rc != 0) {\n"
        b"                p290_fail_next(\n"
        b"                    P301_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);\n"
        b"            }\n"
        b"            rc = p294_publish_final_pair(first_detail, p301_detail);\n"
    )
    new = (
        b"            (void)first_detail;\n"
        b"            (void)terminal_detail;\n"
        b"            uint16_t p303_clock = 0;\n"
        b"            uint16_t p303_log = 0;\n"
        b"            rc = p303_clock_detail(&p303_clock);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_kmsg_finish();\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_log_detail(&p303_log);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p294_publish_final_pair(p303_clock, p303_log);\n"
    )
    value = base.replace_exact(
        value, old, new, label="P3.03 final clock and kmsg publication"
    )
    return value


def transform_runtime_wrapper(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"    E1_REQUIRE(\n"
        b"        S22_R4W1E_STAGE_DEV_NODES_VERIFIED,\n"
        b"        0U,\n"
        b"        setup_and_verify_dev_null());\n",
        b"    E1_REQUIRE(\n"
        b"        S22_R4W1E_STAGE_DEV_NODES_VERIFIED,\n"
        b"        0U,\n"
        b"        setup_and_verify_dev_null());\n"
        b"    long p303_kmsg_begin_rc = p303_kmsg_begin();\n"
        b"    if (p303_kmsg_begin_rc != 0) {\n"
        b"        p290_fail_next(p303_kmsg_begin_rc);\n"
        b"    }\n",
        label="P3.03 kmsg start before modules",
    )
    value = base.replace_exact(
        value,
        b"    }\n\n"
        b"    struct timespec64 deadline = {0};\n"
        b"    if (p241_clock_gettime(&deadline) != 0) {\n",
        b"    }\n\n"
        b"    long p303_kmsg_module_rc = p303_kmsg_drain();\n"
        b"    if (p303_kmsg_module_rc != 0) {\n"
        b"        p290_fail_next(p303_kmsg_module_rc);\n"
        b"    }\n\n"
        b"    struct timespec64 deadline = {0};\n"
        b"    if (p241_clock_gettime(&deadline) != 0) {\n",
        label="P3.03 post-module kmsg drain",
    )
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["trace_descriptor_header"] = transform_trace_descriptor(
        source["trace_descriptor_header"]
    )
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    result["runtime_wrapper"] = transform_runtime_wrapper(
        source["runtime_wrapper"]
    )
    return result
