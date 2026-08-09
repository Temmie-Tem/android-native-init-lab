#!/usr/bin/env python3
"""Add the P3.11 pending-module early clock observer to P3.10 userspace."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p308_runtime_transform as inherited
import s22plus_fyg8_p311_telemetry_spec as spec


base = inherited.base


class TransformError(ValueError):
    pass


def _descriptor_rows() -> bytes:
    rows = []
    for event in spec.EARLY_EVENTS:
        definition = event.definition.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        rows.append(
            f'    {{"{event.name}", "{definition}", "{event.filter}"}},\n'
        )
    return "".join(rows).encode("ascii")


def transform_trace_descriptor(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_BIND_EVENT_COUNT 15U\n",
        b"#define P282_BIND_EVENT_COUNT 15U\n"
        + f"#define P311_EARLY_EVENT_COUNT {spec.EARLY_EVENT_COUNT}U\n".encode("ascii"),
        label="P3.11 early event capacity",
    )
    anchor = b"static const struct p282_event_descriptor p282_role_events[] = {\n"
    table = (
        b"static const struct p282_event_descriptor p311_early_events[] = {\n"
        + _descriptor_rows()
        + b"};\n\n"
    )
    if value.count(anchor) != 1 or table in value:
        raise TransformError("P3.11 early descriptor anchor differs")
    return value.replace(anchor, table + anchor, 1)


_EARLY_SUPPORT = f'''
#define P311_CALLER_EVENT_COUNT 6U
#define P311_CALLSITE_EVENT_BASE {spec.CALLSITE_EVENT_BASE}U
#define P311_CALLSITE_COUNT {spec.CALLSITE_COUNT}U
#define P311_PROBE_CALLSITE_BASE 6U
#define P311_INIT_EUD_CALLSITE_BASE 12U
#define P311_INIT_NORMAL_CALLSITE_BASE 18U
#define P311_SUSPEND_CALLSITE_BASE 24U
#define P311_CLOCK_STATE_COUNT {spec.CLOCK_STATE_COUNT}U
#define P311_FIRST_DETAIL_BASE 0x{spec.FIRST_DETAIL_BASE:x}U
#define P311_FIRST_DETAIL_NO_CLOCK_PATH 0x{spec.FIRST_DETAIL_NO_CLOCK_PATH:x}U
#define P311_SUMMARY_DETAIL_BASE 0x{spec.SUMMARY_DETAIL_BASE:x}U
#define P311_SUMMARY_DETAIL_MAX 0x{spec.SUMMARY_DETAIL_MAX:x}U
#define P311_QSCRATCH_STATE_COUNT {spec.QSCRATCH_STATE_COUNT}U
#define P311_DOMAIN_PROBE {spec.DOMAIN_PROBE}U
#define P311_DOMAIN_SET_SUSPEND {spec.DOMAIN_SET_SUSPEND}U
#define P311_DOMAIN_INIT {spec.DOMAIN_INIT}U
#define P311_DOMAIN_NONE {spec.DOMAIN_NONE}U
#define P311_DOMAIN_COUNT {spec.DOMAIN_COUNT}U
#define P311_MULTI_PATH_COUNT {spec.MULTI_PATH_COUNT}U
#define P311_REACH_MASK_COUNT {spec.REACH_MASK_COUNT}U
#define P311_REACH_PROBE {spec.REACH_PROBE}U
#define P311_REACH_INIT {spec.REACH_INIT}U
#define P311_REACH_SET_SUSPEND_ZERO {spec.REACH_SET_SUSPEND_ZERO}U

#define P311_DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE 0x{spec.DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE:x}U
#define P311_DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE 0x{spec.DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE:x}U
#define P311_DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED 0x{spec.DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED:x}U
#define P311_DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED 0x{spec.DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED:x}U
#define P311_DETAIL_EARLY_PROFILE_RECORD_MISMATCH 0x{spec.DETAIL_EARLY_PROFILE_RECORD_MISMATCH:x}U
#define P311_DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION 0x{spec.DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION:x}U
#define P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION 0x{spec.DETAIL_EARLY_CALLER_PAIR_CONTRADICTION:x}U
#define P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION 0x{spec.DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION:x}U
#define P311_DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION 0x{spec.DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION:x}U
#define P311_DETAIL_EARLY_CFG_AHB_CONTRADICTION 0x{spec.DETAIL_EARLY_CFG_AHB_CONTRADICTION:x}U
#define P311_DETAIL_EARLY_DOMAIN_CONTRADICTION 0x{spec.DETAIL_EARLY_DOMAIN_CONTRADICTION:x}U
#define P311_DETAIL_EARLY_TRACE_RING_LOSS 0x{spec.DETAIL_EARLY_TRACE_RING_LOSS:x}U

_Static_assert(
    P311_CALLER_EVENT_COUNT + P311_CALLSITE_COUNT == P311_EARLY_EVENT_COUNT,
    "P3.11 exact early event extent");
_Static_assert(
    P311_FIRST_DETAIL_NO_CLOCK_PATH <= 0xdafU,
    "P3.11 first detail fixed Image band");
_Static_assert(
    P311_SUMMARY_DETAIL_MAX <= 0x4fffU,
    "P3.11 summary fixed Image band");

struct p311_early_capture {{
    uint8_t final;
    uint8_t domain;
    uint8_t multi_path;
    uint8_t reach_mask;
    uint8_t ref_src_state;
    uint8_t ref_state;
    uint8_t no_clock_path;
}};

static struct p311_early_capture g_p311_early;

static long p311_trace_setup_detail(long condition) {{
    if (condition == P282_CONTROL_TRACE_CONTROL_UNAVAILABLE) {{
        return P311_DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE;
    }}
    if (condition == P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE) {{
        return P311_DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE;
    }}
    if (condition == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {{
        return P311_DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED;
    }}
    return condition == 0 ? 0 : P311_DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE;
}}

static long p311_validate_caller_pairs(
    const struct p282_trace_record *records,
    size_t count,
    uint8_t entry_event,
    uint8_t return_event,
    unsigned int *entry_count,
    unsigned int *zero_suspend_count) {{
    uint8_t used_return[P282_RECORD_CAPACITY] = {{0}};
    unsigned int entries = 0;
    unsigned int returns = 0;
    unsigned int zero_suspend = 0;
    for (size_t index = 0; index < count; ++index) {{
        const struct p282_trace_record *record = &records[index];
        if (record->event_index == return_event) {{
            if (!record->has_rc || record->has_suspend || record->rc != 0) {{
                return P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION;
            }}
            ++returns;
            continue;
        }}
        if (record->event_index != entry_event) continue;
        if (entry_event == 4U) {{
            if (!record->has_suspend
                || (record->suspend != 0 && record->suspend != 1)) {{
                return P311_DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION;
            }}
            if (record->suspend == 0) ++zero_suspend;
        }} else if (record->has_suspend || record->has_rc) {{
            return P311_DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION;
        }}
        ++entries;
        size_t matched = count;
        for (size_t other = index + 1U; other < count; ++other) {{
            const struct p282_trace_record *candidate = &records[other];
            if (candidate->pid != record->pid) continue;
            if (candidate->event_index == entry_event) {{
                return P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION;
            }}
            if (candidate->event_index == return_event) {{
                matched = other;
                break;
            }}
        }}
        if (matched == count || used_return[matched]) {{
            return P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION;
        }}
        used_return[matched] = 1U;
    }}
    if (entries != returns) {{
        return P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION;
    }}
    *entry_count = entries;
    *zero_suspend_count = zero_suspend;
    return 0;
}}

static long p311_record_window(
    const struct p282_trace_record *records,
    size_t count,
    size_t record_index,
    uint8_t entry_event,
    uint8_t return_event,
    int require_suspend_zero,
    size_t *window_start,
    size_t *window_end) {{
    const struct p282_trace_record *target = &records[record_index];
    size_t start = count;
    for (size_t cursor = record_index; cursor != 0U; ) {{
        --cursor;
        const struct p282_trace_record *candidate = &records[cursor];
        if (candidate->pid != target->pid) continue;
        if (candidate->event_index == return_event) break;
        if (candidate->event_index == entry_event) {{
            if (require_suspend_zero
                && (!candidate->has_suspend || candidate->suspend != 0)) {{
                return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
            }}
            start = cursor;
            break;
        }}
    }}
    if (start == count) return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
    size_t end = count;
    for (size_t cursor = record_index + 1U; cursor < count; ++cursor) {{
        const struct p282_trace_record *candidate = &records[cursor];
        if (candidate->pid != target->pid) continue;
        if (candidate->event_index == entry_event) {{
            return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
        }}
        if (candidate->event_index == return_event) {{
            end = cursor;
            break;
        }}
    }}
    if (end == count) return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
    *window_start = start;
    *window_end = end;
    return 0;
}}

static long p311_clock_state_from_window(
    const struct p282_trace_record *records,
    size_t start,
    size_t end,
    long pid,
    uint8_t prepare_event,
    uint8_t enable_event,
    unsigned int *state) {{
    uint64_t prepare_hits = 0;
    uint64_t enable_hits = 0;
    int32_t prepare_rc = 0;
    int32_t enable_rc = 0;
    for (size_t index = start + 1U; index < end; ++index) {{
        const struct p282_trace_record *record = &records[index];
        if (record->pid != pid) continue;
        if (record->event_index == prepare_event) {{
            if (!record->has_rc || ++prepare_hits != 1U) {{
                return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
            }}
            prepare_rc = record->rc;
        }} else if (record->event_index == enable_event) {{
            if (!record->has_rc || ++enable_hits != 1U) {{
                return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
            }}
            enable_rc = record->rc;
        }}
    }}
    if (prepare_hits != 1U || prepare_rc > 0
        || enable_hits > 1U || (enable_hits != 0U && enable_rc > 0)) {{
        return prepare_rc > 0 || enable_rc > 0
            ? P311_DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION
            : P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
    }}
    if (prepare_rc < 0) {{
        if (enable_hits != 0U) {{
            return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
        }}
        *state = 1U + p303_errno_bucket(prepare_rc);
        return 0;
    }}
    if (enable_hits != 1U) {{
        return P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION;
    }}
    *state = enable_rc < 0 ? 5U + p303_errno_bucket(enable_rc) : 0U;
    return 0;
}}

static long p311_parse_early_trace(
    const struct p282_trace_control *control) {{
    if (control == NULL || g_p311_early.final
        || control->event_count != P311_EARLY_EVENT_COUNT) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc != 0) return P311_DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION;
    uint64_t record_hits[P311_EARLY_EVENT_COUNT] = {{0}};
    for (size_t index = 0; index < count; ++index) {{
        const struct p282_trace_record *record = &records[index];
        if (record->event_index >= P311_EARLY_EVENT_COUNT
            || record_hits[record->event_index] == UINT64_MAX) {{
            return P311_DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION;
        }}
        ++record_hits[record->event_index];
    }}
    for (size_t index = 0; index < P311_EARLY_EVENT_COUNT; ++index) {{
        if (control->profile_hits[index] != record_hits[index]) {{
            return P311_DETAIL_EARLY_PROFILE_RECORD_MISMATCH;
        }}
    }}

    unsigned int probe_entries = 0;
    unsigned int init_entries = 0;
    unsigned int suspend_entries = 0;
    unsigned int ignored_zero = 0;
    unsigned int suspend_zero = 0;
    rc = p311_validate_caller_pairs(
        records, count, 0U, 1U, &probe_entries, &ignored_zero);
    if (rc == 0) rc = p311_validate_caller_pairs(
        records, count, 2U, 3U, &init_entries, &ignored_zero);
    if (rc == 0) rc = p311_validate_caller_pairs(
        records, count, 4U, 5U, &suspend_entries, &suspend_zero);
    if (rc != 0) return rc;
    if (probe_entries != 1U || init_entries == 0U) {{
        return P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION;
    }}

    uint8_t reach = P311_REACH_PROBE | P311_REACH_INIT;
    if (suspend_zero != 0U) reach |= P311_REACH_SET_SUSPEND_ZERO;
    unsigned int path_mask = 0U;
    size_t first_callsite = count;
    unsigned int first_domain = P311_DOMAIN_NONE;
    uint8_t first_base = 0U;
    size_t first_window_start = 0;
    size_t first_window_end = 0;
    for (size_t index = 0; index < count; ++index) {{
        const struct p282_trace_record *record = &records[index];
        if (record->event_index < P311_CALLSITE_EVENT_BASE) continue;
        if (!record->has_rc || record->rc > 0) {{
            return P311_DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION;
        }}
        unsigned int domain;
        unsigned int path_bit;
        uint8_t base_event;
        uint8_t entry_event;
        uint8_t return_event;
        int require_suspend_zero = 0;
        if (record->event_index < P311_INIT_EUD_CALLSITE_BASE) {{
            domain = P311_DOMAIN_PROBE;
            path_bit = 1U << 0U;
            base_event = P311_PROBE_CALLSITE_BASE;
            entry_event = 0U;
            return_event = 1U;
        }} else if (record->event_index < P311_INIT_NORMAL_CALLSITE_BASE) {{
            domain = P311_DOMAIN_INIT;
            path_bit = 1U << 1U;
            base_event = P311_INIT_EUD_CALLSITE_BASE;
            entry_event = 2U;
            return_event = 3U;
        }} else if (record->event_index < P311_SUSPEND_CALLSITE_BASE) {{
            domain = P311_DOMAIN_INIT;
            path_bit = 1U << 2U;
            base_event = P311_INIT_NORMAL_CALLSITE_BASE;
            entry_event = 2U;
            return_event = 3U;
        }} else {{
            domain = P311_DOMAIN_SET_SUSPEND;
            path_bit = 1U << 3U;
            base_event = P311_SUSPEND_CALLSITE_BASE;
            entry_event = 4U;
            return_event = 5U;
            require_suspend_zero = 1;
        }}
        size_t window_start = 0;
        size_t window_end = 0;
        rc = p311_record_window(
            records, count, index, entry_event, return_event,
            require_suspend_zero, &window_start, &window_end);
        if (rc != 0) return rc;
        path_mask |= path_bit;
        if (first_callsite == count) {{
            first_callsite = index;
            first_domain = domain;
            first_base = base_event;
            first_window_start = window_start;
            first_window_end = window_end;
        }}
    }}
    for (size_t index = 0; index < P311_CALLSITE_COUNT; ++index) {{
        if ((index % 6U == 4U || index % 6U == 5U)
            && record_hits[P311_CALLSITE_EVENT_BASE + index] != 0U) {{
            return P311_DETAIL_EARLY_CFG_AHB_CONTRADICTION;
        }}
    }}

    g_p311_early.reach_mask = reach;
    if (first_callsite == count) {{
        g_p311_early.domain = P311_DOMAIN_NONE;
        g_p311_early.no_clock_path = 1U;
        g_p311_early.final = 1U;
        return 0;
    }}
    unsigned int path_count = 0;
    for (unsigned int value = path_mask; value != 0U; value >>= 1U) {{
        path_count += value & 1U;
    }}
    unsigned int ref_src_state = 0;
    unsigned int ref_state = 0;
    long pid = records[first_callsite].pid;
    rc = p311_clock_state_from_window(
        records, first_window_start, first_window_end, pid,
        first_base, (uint8_t)(first_base + 1U), &ref_src_state);
    if (rc == 0) rc = p311_clock_state_from_window(
        records, first_window_start, first_window_end, pid,
        (uint8_t)(first_base + 2U), (uint8_t)(first_base + 3U),
        &ref_state);
    if (rc != 0) return rc;
    if (ref_src_state >= P311_CLOCK_STATE_COUNT
        || ref_state >= P311_CLOCK_STATE_COUNT
        || first_domain >= P311_DOMAIN_NONE) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    g_p311_early.domain = (uint8_t)first_domain;
    g_p311_early.multi_path = path_count > 1U;
    g_p311_early.ref_src_state = (uint8_t)ref_src_state;
    g_p311_early.ref_state = (uint8_t)ref_state;
    g_p311_early.final = 1U;
    return 0;
}}

static long p311_early_trace_begin(struct p282_trace_control *control) {{
    if (control == NULL || g_p311_early.final) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    return p311_trace_setup_detail(p282_trace_setup(P282_PHASE_P311_EARLY, control));
}}

static long p311_early_trace_finish(struct p282_trace_control *control) {{
    if (control == NULL || !control->active) {{
        return P311_DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED;
    }}
    long quality = p282_trace_disable(control);
    if (quality == 0) quality = p282_trace_read_snapshot(control, 1);
    long ring_quality = quality == 0 ? p300_ring_stats_clean() : 0;
    long cleanup_rc = p282_trace_cleanup(control);
    if (cleanup_rc != 0) return P311_DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED;
    if (quality != 0) return P311_DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED;
    if (ring_quality != 0) return P311_DETAIL_EARLY_TRACE_RING_LOSS;
    return p311_parse_early_trace(control);
}}

static long p311_first_detail(uint16_t *detail) {{
    if (detail == NULL || !g_p311_early.final) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    if (g_p311_early.no_clock_path) {{
        *detail = P311_FIRST_DETAIL_NO_CLOCK_PATH;
        return 0;
    }}
    unsigned int index =
        (unsigned int)g_p311_early.ref_src_state * P311_CLOCK_STATE_COUNT
        + (unsigned int)g_p311_early.ref_state;
    if (index >= P311_CLOCK_STATE_COUNT * P311_CLOCK_STATE_COUNT) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    *detail = (uint16_t)(P311_FIRST_DETAIL_BASE + index);
    return 0;
}}

static long p311_summary_detail(
    unsigned int qscratch_state, uint16_t *detail) {{
    if (detail == NULL || !g_p311_early.final
        || g_p311_early.domain >= P311_DOMAIN_COUNT
        || g_p311_early.multi_path >= P311_MULTI_PATH_COUNT
        || g_p311_early.reach_mask >= P311_REACH_MASK_COUNT
        || qscratch_state >= P311_QSCRATCH_STATE_COUNT) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    unsigned int index = g_p311_early.domain;
    index = index * P311_MULTI_PATH_COUNT + g_p311_early.multi_path;
    index = index * P311_REACH_MASK_COUNT + g_p311_early.reach_mask;
    index = index * P311_QSCRATCH_STATE_COUNT + qscratch_state;
    unsigned int encoded = P311_SUMMARY_DETAIL_BASE + index;
    if (encoded > P311_SUMMARY_DETAIL_MAX) {{
        return P311_DETAIL_EARLY_DOMAIN_CONTRADICTION;
    }}
    *detail = (uint16_t)encoded;
    return 0;
}}

'''.encode("ascii")


def transform_runtime_include(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_PHASE_BIND 3U\n",
        b"#define P282_PHASE_BIND 3U\n#define P282_PHASE_P311_EARLY 4U\n",
        label="P3.11 trace phase",
    )
    value = base.replace_exact(
        value,
        b"    uint64_t profile_hits[P282_CYCLE_EVENT_COUNT];\n",
        b"    uint64_t profile_hits[P311_EARLY_EVENT_COUNT];\n",
        label="P3.11 profile capacity",
    )
    value = base.replace_exact(
        value,
        b"    uint8_t seen[P282_CYCLE_EVENT_COUNT] = {0};\n",
        b"    uint8_t seen[P311_EARLY_EVENT_COUNT] = {0};\n",
        label="P3.11 profile seen capacity",
    )
    old_phase = (
        b"    } else if (phase == P282_PHASE_BIND) {\n"
        b"        events = p282_bind_events;\n"
        b"        event_count = P282_BIND_EVENT_COUNT;\n"
        b"    }\n"
    )
    new_phase = (
        b"    } else if (phase == P282_PHASE_BIND) {\n"
        b"        events = p282_bind_events;\n"
        b"        event_count = P282_BIND_EVENT_COUNT;\n"
        b"    } else if (phase == P282_PHASE_P311_EARLY) {\n"
        b"        events = p311_early_events;\n"
        b"        event_count = P311_EARLY_EVENT_COUNT;\n"
        b"    }\n"
    )
    value = base.replace_exact(
        value, old_phase, new_phase, label="P3.11 trace phase selection"
    )
    value = base.replace_exact(
        value,
        b"event_count > P282_CYCLE_EVENT_COUNT",
        b"event_count > P311_EARLY_EVENT_COUNT",
        label="P3.11 maximum event count",
    )
    support_anchor = b"static long p300_profile_relations(\n"
    if value.count(support_anchor) != 1 or _EARLY_SUPPORT in value:
        raise TransformError("P3.11 early support anchor differs")
    value = value.replace(support_anchor, _EARLY_SUPPORT + support_anchor, 1)

    legacy_summary = (
        b"static long p307_summary_detail(\n"
        b"    uint16_t clock_detail, unsigned int qscratch_state, uint16_t *detail) {\n"
        b"    if (detail == NULL\n"
        b"        || clock_detail < P303_CLOCK_DETAIL_BASE\n"
        b"        || clock_detail >= P303_CLOCK_DETAIL_BASE + 163U\n"
        b"        || qscratch_state >= P307_QSCRATCH_STATE_COUNT) {\n"
        b"        return P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION;\n"
        b"    }\n"
        b"    unsigned int index =\n"
        b"        (clock_detail - P303_CLOCK_DETAIL_BASE) * P307_QSCRATCH_STATE_COUNT\n"
        b"        + qscratch_state;\n"
        b"    if (index >= 4075U) {\n"
        b"        return P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION;\n"
        b"    }\n"
        b"    *detail = (uint16_t)(P307_SUMMARY_DETAIL_BASE + index);\n"
        b"    return 0;\n"
        b"}\n\n"
    )
    value = base.replace_exact(
        value,
        legacy_summary,
        b"",
        label="P3.11 retired P3.07 summary encoder",
    )

    old_final = (
        b"            (void)p303_log_detail;\n"
        b"            uint16_t p303_clock = 0;\n"
        b"            uint16_t p308_first = 0;\n"
        b"            uint16_t p308_terminal = 0;\n"
        b"            rc = p303_clock_detail(&p303_clock);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_kmsg_finish();\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            unsigned int p307_qscratch = p307_qscratch_state();\n"
        b"            if (g_p308_parser.failure_latched) {\n"
        b"                p308_first = p303_clock;\n"
        b"                rc = p308_degraded_detail(\n"
        b"                    p307_qscratch, &p308_terminal);\n"
        b"            } else {\n"
        b"                rc = p307_attribution_detail(&p308_first);\n"
        b"                if (rc == 0) {\n"
        b"                    rc = p307_summary_detail(\n"
        b"                        p303_clock, p307_qscratch,\n"
        b"                        &p308_terminal);\n"
        b"                }\n"
        b"            }\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p294_publish_final_pair(\n"
        b"                p308_first, p308_terminal);\n"
    )
    new_final = (
        b"            (void)p303_log_detail;\n"
        b"            (void)p303_clock_detail;\n"
        b"            (void)p307_attribution_detail;\n"
        b"            uint16_t p311_first = 0;\n"
        b"            uint16_t p311_terminal = 0;\n"
        b"            rc = p311_first_detail(&p311_first);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_kmsg_finish();\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            unsigned int p307_qscratch = p307_qscratch_state();\n"
        b"            if (g_p308_parser.failure_latched) {\n"
        b"                rc = p308_degraded_detail(\n"
        b"                    p307_qscratch, &p311_terminal);\n"
        b"            } else {\n"
        b"                rc = p311_summary_detail(\n"
        b"                    p307_qscratch, &p311_terminal);\n"
        b"            }\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p294_publish_final_pair(\n"
        b"                p311_first, p311_terminal);\n"
    )
    return base.replace_exact(
        value, old_final, new_final, label="P3.11 final pair publication"
    )


def transform_runtime_wrapper(data: bytes) -> bytes:
    loop_anchor = (
        b"    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {\n"
        b"        E1_REQUIRE(\n"
    )
    loop_replacement = (
        b"    struct p282_trace_control p311_early_trace = {0};\n"
        b"    int p311_early_armed = 0;\n"
        b"    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {\n"
        b"        if (index == 55U) {\n"
        b"            long p311_begin_rc = p311_early_trace_begin(\n"
        b"                &p311_early_trace);\n"
        b"            if (p311_begin_rc != 0) p290_fail_next(p311_begin_rc);\n"
        b"            p311_early_armed = 1;\n"
        b"        }\n"
        b"        E1_REQUIRE(\n"
    )
    value = base.replace_exact(
        data, loop_anchor, loop_replacement, label="P3.11 pre-module-55 arm"
    )
    finish_anchor = (
        b"    long p303_kmsg_module_rc = p303_kmsg_drain();\n"
    )
    finish = (
        b"    if (!p311_early_armed) {\n"
        b"        p290_fail_next(P311_DETAIL_EARLY_DOMAIN_CONTRADICTION);\n"
        b"    }\n"
        b"    long p311_finish_rc = p311_early_trace_finish(\n"
        b"        &p311_early_trace);\n"
        b"    if (p311_finish_rc != 0) p290_fail_next(p311_finish_rc);\n"
        b"\n"
        b"    long p303_kmsg_module_rc = p303_kmsg_drain();\n"
    )
    return base.replace_exact(
        value, finish_anchor, finish, label="P3.11 post-module trace finish"
    )


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
