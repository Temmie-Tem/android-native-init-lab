#!/usr/bin/env python3
"""Repair P3.14 live snapshots and classify the completed restart prefix."""

from __future__ import annotations

from collections.abc import Mapping

import s22plus_fyg8_p314_runtime_transform as parent


class TransformError(ValueError):
    pass


def _replace_once(value: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if value.count(old) != 1:
        raise TransformError(f"P3.15 {label} anchor differs")
    return value.replace(old, new, 1)


def _replace_definition(value: bytes, marker: bytes, replacement: bytes) -> bytes:
    try:
        old = parent.support._definition(value, marker)  # noqa: SLF001
    except (ValueError, parent.support.AuditError) as exc:
        raise TransformError(f"P3.15 definition differs: {marker!r}") from exc
    return _replace_once(value, old, replacement, marker.decode("ascii").strip())


_P315_HELPERS = r'''static long p314_parse_live_snapshot(
    const struct p282_trace_control *control,
    struct p313_cycle_result *result,
    int phase) {
    long detail = p313_parse_cycle(control, result, phase);
    long integrity = p313_cycle_profile_relations(control, result);
    if (integrity != 0) return integrity;
    integrity = p300_ring_stats_clean();
    if (integrity != 0)
        return integrity < 0 ? P313_DETAIL_TRACE_RING_LOSS : integrity;
    return detail;
}

static long p315_parse_restart_prefix(
    const struct p282_trace_control *control,
    int *ready) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    *ready = 0;
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc == -P260_EOVERFLOW) return P313_DETAIL_CYCLE_RECORD_OVERFLOW;
    if (rc != 0) return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;

    uint64_t outer_pairs = 0;
    uint64_t start_on_pairs = 0;
    uint8_t outer_open = 0U;
    uint8_t start_on_open = 0U;
    long outer_pid = 0;
    long start_on_pid = 0;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index == 14U) {
            if (outer_open || outer_pairs >= 4U)
                return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
            outer_open = 1U;
            outer_pid = record->pid;
        } else if (record->event_index == 15U) {
            if (!outer_open || record->pid != outer_pid || !record->has_rc
                || start_on_open)
                return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
            outer_open = 0U;
            ++outer_pairs;
        } else if (record->event_index == 0U) {
            if (!record->has_on)
                return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
            if (record->on == 1) {
                if (!outer_open || start_on_open || start_on_pairs != 0U
                    || record->pid != outer_pid)
                    return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
                start_on_open = 1U;
                start_on_pid = record->pid;
            }
        } else if (record->event_index == 1U && start_on_open
            && record->pid == start_on_pid) {
            if (!record->has_rc || !outer_open || record->pid != outer_pid)
                return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
            start_on_open = 0U;
            ++start_on_pairs;
        }
    }
    if (outer_pairs == 4U && !outer_open) {
        if (start_on_open || start_on_pairs != 1U)
            return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
        *ready = 1;
    }
    return 0;
}

static long p315_wait_restart_completion(
    struct p282_trace_control *control,
    const struct timespec64 *deadline) {
    for (unsigned int attempt = 0U;
         attempt < P315_RESTART_MAX_SNAPSHOTS; ++attempt) {
        long rc = p282_trace_read_snapshot(control, 0);
        if (rc != 0) return P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED;
        int ready = 0;
        rc = p315_parse_restart_prefix(control, &ready);
        if (rc != 0) return rc;
        if (ready) return 0;
        if (attempt + 1U == P315_RESTART_MAX_SNAPSHOTS
            || p282_deadline_expired(deadline))
            return P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED;
        p282_poll_delay();
    }
    return P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED;
}

static long p315_relevant_profile_integrity(
    const struct p282_trace_control *control,
    const struct p313_cycle_result *result) {
    static const uint8_t indices[] = {19U, 20U, 21U, 22U};
    for (size_t index = 0; index < sizeof(indices); ++index) {
        uint8_t event = indices[index];
        if (control->profile_hits[event] > result->record_hits[event])
            return P315_DETAIL_PROFILE_ONLY_NESTED_HIT;
    }
    return 0;
}

static long p315_parse_restart_snapshot(
    const struct p282_trace_control *control,
    struct p313_cycle_result *result) {
    long parse_detail = p313_parse_cycle(
        control, result, P314_PHASE_PARTIAL);
    if (parse_detail != 0
        && parse_detail != P313_DETAIL_CYCLE_PAIRING_CONTRADICTION
        && parse_detail != P313_DETAIL_CYCLE_POSITIVE_RETURN)
        return parse_detail;

    long integrity = p313_cycle_profile_relations(control, result);
    if (integrity != 0) return integrity;
    integrity = p300_ring_stats_clean();
    if (integrity != 0)
        return integrity < 0 ? P313_DETAIL_TRACE_RING_LOSS : integrity;
    integrity = p315_relevant_profile_integrity(control, result);
    if (integrity != 0) return integrity;
    if (parse_detail == P313_DETAIL_CYCLE_PAIRING_CONTRADICTION)
        return parse_detail;

    int gadget_present = result->gadget_start_pairs != 0U;
    int run_on_present = result->run_on.entered && result->run_on.returned;
    if (!gadget_present && !run_on_present)
        return P313_DETAIL_CYCLE_RESUME_PRECONDITION;
    if (!gadget_present && run_on_present)
        return P315_DETAIL_RUN_ON_PROVENANCE_CONTRADICTION;
    if (result->gadget_start.rc < 0) {
        if (run_on_present)
            return P315_DETAIL_RUN_ON_PROVENANCE_CONTRADICTION;
        uint16_t detail = 0;
        long rc = p313_controller_detail(8U, result->gadget_start.rc, &detail);
        return rc != 0 ? rc : detail;
    }
    if (result->gadget_start.rc > 0)
        return P313_DETAIL_CYCLE_POSITIVE_RETURN;
    if (!run_on_present)
        return P315_DETAIL_GADGET_START_ZERO_WITHOUT_RUN_ON;
    if (result->run_on.rc < 0) {
        uint16_t detail = 0;
        long rc = p313_controller_detail(9U, result->run_on.rc, &detail);
        return rc != 0 ? rc : detail;
    }
    if (result->run_on.rc > 0 || parse_detail != 0)
        return P313_DETAIL_CYCLE_POSITIVE_RETURN;

    struct p313_cycle_result strict = {0};
    long detail = p313_parse_cycle(control, &strict, P314_PHASE_RESTART);
    if (detail != 0) return detail;
    if (strict.total_records != P314_FINAL_CLEAN_RECORDS
        && strict.total_records != P314_FINAL_DRIFT_RECORDS)
        return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
    *result = strict;
    return 0;
}

static long p315_read_live_snapshot(
    struct p282_trace_control *control,
    struct p313_cycle_result *result,
    int phase) {
    if (phase != P314_PHASE_STOP && phase != P314_PHASE_RESTART)
        return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
    long rc = p282_trace_read_snapshot(control, 1);
    if (rc != 0) return P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED;
    if (phase == P314_PHASE_RESTART)
        return p315_parse_restart_snapshot(control, result);
    return p314_parse_live_snapshot(control, result, phase);
}
'''.encode("ascii")


def transform_runtime_include(value: bytes) -> bytes:
    value = _replace_once(
        value,
        b"/* P3.14 source-normalized post-bind resume-cycle observer. */",
        b"/* P3.15 completed live-profile restart observer. */",
        "observer identity",
    )
    value = _replace_once(
        value,
        b"#define P314_PAIR_MASK_DETAIL_BASE 0x6c00U\n"
        b"static const uint8_t p314_stop_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 0U, 1U, 0U, 2U, 0U, 1U, 0U, 0U, 0U,\n"
        b"};\n"
        b"static const uint8_t p314_final_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 1U, 1U, 1U, 2U, 2U, 1U, 1U, 1U, 1U,\n"
        b"};\n",
        b"#define P314_PAIR_MASK_DETAIL_BASE 0x6c00U\n"
        b"#define P315_RESTART_MAX_SNAPSHOTS 301U\n"
        b"#define P315_DETAIL_PROFILE_ONLY_NESTED_HIT 0x6721U\n"
        b"#define P315_DETAIL_GADGET_START_ZERO_WITHOUT_RUN_ON 0x6722U\n"
        b"#define P315_DETAIL_RUN_ON_PROVENANCE_CONTRADICTION 0x6723U\n"
        b"static const uint8_t p314_stop_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 0U, 1U, 0U, 2U, 0U, 1U, 0U, 0U, 0U,\n"
        b"};\n"
        b"static const uint8_t p315_restart_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 1U, 1U, 1U, 2U, 2U, 1U, 1U, 1U, 1U,\n"
        b"};\n"
        b"static const uint8_t p314_final_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 1U, 1U, 1U, 2U, 2U, 1U, 1U, 1U, 1U,\n"
        b"};\n",
        "restart geometry and details",
    )
    value = _replace_once(
        value,
        b"        const uint8_t *expected = phase == P314_PHASE_STOP\n"
        b"            ? p314_stop_expected : p314_final_expected;\n",
        b"        const uint8_t *expected = NULL;\n"
        b"        switch (phase) {\n"
        b"        case P314_PHASE_STOP:\n"
        b"            expected = p314_stop_expected;\n"
        b"            break;\n"
        b"        case P314_PHASE_RESTART:\n"
        b"            expected = p315_restart_expected;\n"
        b"            break;\n"
        b"        case P314_PHASE_FINAL:\n"
        b"            expected = p314_final_expected;\n"
        b"            break;\n"
        b"        default:\n"
        b"            return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;\n"
        b"        }\n",
        "explicit phase geometry switch",
    )
    value = _replace_definition(
        value, b"static long p314_parse_live_snapshot(\n", _P315_HELPERS
    )
    value = _replace_once(
        value,
        b"    rc = p282_trace_read_snapshot(&cycle_control, 0);\n"
        b"    struct p313_cycle_result stop_result = {0};\n"
        b"    if (rc == 0) rc = p314_parse_live_snapshot(\n"
        b"        &cycle_control, &stop_result, P314_PHASE_STOP);\n",
        b"    struct p313_cycle_result stop_result = {0};\n"
        b"    rc = p315_read_live_snapshot(\n"
        b"        &cycle_control, &stop_result, P314_PHASE_STOP);\n",
        "stop live profile snapshot",
    )
    value = _replace_once(
        value,
        b"    rc = p282_trace_read_snapshot(&cycle_control, 0);\n"
        b"    struct p313_cycle_result restart_result = {0};\n"
        b"    if (rc == 0) rc = p314_parse_live_snapshot(\n"
        b"        &cycle_control, &restart_result, P314_PHASE_RESTART);\n",
        b"    rc = p315_wait_restart_completion(\n"
        b"        &cycle_control, &restart_deadline);\n"
        b"    if (rc != 0) p313_cycle_fail(&cycle_control, rc);\n"
        b"    struct p313_cycle_result restart_result = {0};\n"
        b"    rc = p315_read_live_snapshot(\n"
        b"        &cycle_control, &restart_result, P314_PHASE_RESTART);\n",
        "restart completion and live profile snapshot",
    )
    required = (
        b"p315_restart_expected",
        b"p315_wait_restart_completion",
        b"p315_read_live_snapshot",
        b"p315_parse_restart_snapshot",
        b"P315_DETAIL_PROFILE_ONLY_NESTED_HIT",
    )
    if any(value.count(token) < 1 for token in required):
        raise TransformError("P3.15 runtime token missing")
    if value.count(b"p282_trace_read_snapshot(&cycle_control, 0);") != 0:
        raise TransformError("P3.15 direct cycle snapshot call survived")
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    changed = {key for key in result if result[key] != source[key]}
    if changed != {"p290_e3_runtime_include"}:
        raise TransformError(f"P3.15 delta differs: {sorted(changed)}")
    return result
