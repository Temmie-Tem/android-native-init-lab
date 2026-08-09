#!/usr/bin/env python3
"""Normalize P3.13 cycle geometry without changing its trace inventory."""

from __future__ import annotations

from collections.abc import Mapping

import s22plus_fyg8_p308_cross_gate_audit as support


class TransformError(ValueError):
    pass


def _replace_once(value: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if value.count(old) != 1:
        raise TransformError(f"P3.14 {label} anchor differs")
    return value.replace(old, new, 1)


def _replace_definition(value: bytes, marker: bytes, replacement: bytes) -> bytes:
    try:
        old = support._definition(value, marker)  # noqa: SLF001
    except (ValueError, support.AuditError) as exc:
        raise TransformError(f"P3.14 definition differs: {marker!r}") from exc
    return _replace_once(value, old, replacement, marker.decode("ascii").strip())


_PAIR_COLLECT = r'''static long p313_pair_collect(
    const struct p282_trace_record *records,
    size_t count,
    uint8_t entry_event,
    uint8_t return_event,
    int argument_kind,
    int argument_value,
    struct p313_cycle_pair *first,
    uint64_t *pair_count) {
    uint64_t pairs = 0;
    if (first != NULL) {
        *first = (struct p313_cycle_pair){0};
        first->all_returns_zero = 1U;
    }
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *entry = &records[index];
        if (entry->event_index != entry_event
            || !p282_record_argument_matches(
                entry, argument_kind, argument_value)) continue;
        const struct p282_trace_record *returned = NULL;
        for (size_t other = index + 1U; other < count; ++other) {
            const struct p282_trace_record *candidate = &records[other];
            if (candidate->pid != entry->pid) continue;
            if (candidate->event_index == entry_event
                && p282_record_argument_matches(
                    candidate, argument_kind, argument_value)) {
                return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
            }
            if (candidate->event_index == return_event) {
                returned = candidate;
                break;
            }
        }
        if (returned == NULL || !returned->has_rc) {
            return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
        }
        if (pairs == 0U && first != NULL) {
            *first = (struct p313_cycle_pair){
                .entered = 1U,
                .returned = 1U,
                .all_returns_zero = returned->rc == 0,
                .positive_return_seen = returned->rc > 0,
                .pid = entry->pid,
                .rc = returned->rc,
                .first_negative_rc = returned->rc < 0 ? returned->rc : 0,
                .entry_counter = entry->counter,
                .return_counter = returned->counter,
            };
        } else if (first != NULL) {
            if (returned->rc != 0) first->all_returns_zero = 0U;
            if (returned->rc > 0) first->positive_return_seen = 1U;
            if (returned->rc < 0 && first->first_negative_rc == 0)
                first->first_negative_rc = returned->rc;
        }
        if (pairs == UINT64_MAX)
            return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
        ++pairs;
    }
    *pair_count = pairs;
    return 0;
}
'''.encode("ascii")


_PARSE_CYCLE = r'''static long p313_parse_cycle(
    const struct p282_trace_control *control,
    struct p313_cycle_result *result,
    int phase) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    *result = (struct p313_cycle_result){0};
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc == -P260_EOVERFLOW) return P313_DETAIL_CYCLE_RECORD_OVERFLOW;
    if (rc != 0) return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
    result->total_records = count;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index >= P313_CYCLE_EVENT_COUNT
            || result->record_hits[record->event_index] == UINT64_MAX) {
            return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
        }
        ++result->record_hits[record->event_index];
    }

    uint64_t count_value = 0;
#define P313_PAIR(member, entry, returned, kind, value, count_target) do { \
    rc = p313_pair_collect(records, count, entry, returned, kind, value, \
        &result->member, &count_value); \
    if (rc != 0) return rc; \
    result->count_target = count_value; \
} while (0)
    P313_PAIR(start_off, 0U, 1U, 1, 0, run_pairs);
    uint64_t start_off_count = result->run_pairs;
    P313_PAIR(start_on, 0U, 1U, 1, 1, run_pairs);
    uint64_t start_on_count = result->run_pairs;
    P313_PAIR(child_suspend, 2U, 3U, 0, 0, run_pairs);
    uint64_t child_suspend_count = result->run_pairs;
    P313_PAIR(child_resume, 4U, 5U, 0, 0, run_pairs);
    uint64_t child_resume_count = result->run_pairs;
    P313_PAIR(phy_suspend_off, 6U, 7U, 2, 1, run_pairs);
    uint64_t phy_suspend_off_count = result->run_pairs;
    P313_PAIR(phy_suspend_on, 6U, 7U, 2, 0, run_pairs);
    uint64_t phy_suspend_on_count = result->run_pairs;
    P313_PAIR(power_off, 8U, 9U, 1, 0, run_pairs);
    uint64_t power_off_count = result->run_pairs;
    P313_PAIR(power_on, 8U, 9U, 1, 1, run_pairs);
    uint64_t power_on_count = result->run_pairs;
    P313_PAIR(phy_init, 10U, 11U, 0, 0, run_pairs);
    uint64_t phy_init_count = result->run_pairs;
    P313_PAIR(notify_connect, 12U, 13U, 0, 0, run_pairs);
    uint64_t notify_count = result->run_pairs;
    struct p313_cycle_pair outer_first = {0};
    rc = p313_pair_collect(records, count, 14U, 15U, 0, 0,
        &outer_first, &result->outer_pairs);
    if (rc != 0) return rc;
    struct p313_cycle_pair pull_first = {0};
    rc = p313_pair_collect(records, count, 17U, 18U, 0, 0,
        &pull_first, &result->pullup_pairs);
    if (rc != 0) return rc;
    P313_PAIR(run_off, 19U, 20U, 1, 0, run_pairs);
    uint64_t run_off_count = result->run_pairs;
    P313_PAIR(run_on, 19U, 20U, 1, 1, run_pairs);
    uint64_t run_on_count = result->run_pairs;
    result->run_pairs = run_off_count + run_on_count;
    rc = p313_pair_collect(records, count, 21U, 22U, 0, 0,
        &result->gadget_start, &result->gadget_start_pairs);
    if (rc != 0) return rc;
#undef P313_PAIR

    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index == 16U) {
            if (!record->has_rc || result->qscratch_hits == UINT64_MAX)
                return P313_DETAIL_CYCLE_QSCRATCH_CONTRADICTION;
            if (result->qscratch_hits == 0U) {
                result->qscratch = (uint32_t)record->rc;
                result->qscratch_counter = record->counter;
            }
            ++result->qscratch_hits;
        } else if (record->event_index == 23U) {
            if (!record->has_link || !record->has_run_stop
                || !record->has_devctrlhlt || !record->has_coreidle
                || !record->has_prtcap || !record->has_susphy
                || !record->has_connect_speed)
                return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
            ++result->state_hits;
            if (result->state_hits == 1U) {
                result->snapshot_seen = 1U;
                result->state_counter = record->counter;
                result->link_state = (uint8_t)record->link;
                result->run_stop = (uint8_t)record->run_stop;
                result->devctrlhlt = (uint8_t)record->devctrlhlt;
                result->coreidle = (uint8_t)record->coreidle;
                result->prtcap = (uint8_t)record->prtcap;
                result->susphy = (uint8_t)record->susphy;
                result->connect_speed = (uint8_t)record->connect_speed;
            }
        } else if (record->event_index == 24U) {
            if (!record->has_dwc || !record->has_evt || !record->has_devten
                || !record->has_gevntsiz || !record->has_gevntcount
                || !record->has_evt_length || !record->has_evt_count
                || !record->has_evt_flags)
                return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
            ++result->config_hits;
            if (result->config_hits == 1U) {
                result->event_config_seen = 1U;
                result->config_counter = record->counter;
                result->event_dwc = record->dwc;
                result->event_evt = record->evt;
                result->devten = record->devten;
                result->gevntsiz = record->gevntsiz;
                result->gevntcount = record->gevntcount;
                result->evt_length = record->evt_length;
                result->evt_count = record->evt_count;
                result->evt_flags = record->evt_flags;
            }
        }
    }

    if (result->record_hits[0] != start_off_count + start_on_count
        || result->record_hits[1] != start_off_count + start_on_count
        || result->record_hits[2] != child_suspend_count
        || result->record_hits[3] != child_suspend_count
        || result->record_hits[4] != child_resume_count
        || result->record_hits[5] != child_resume_count
        || result->record_hits[6]
            != phy_suspend_off_count + phy_suspend_on_count
        || result->record_hits[7]
            != phy_suspend_off_count + phy_suspend_on_count
        || result->record_hits[8] != power_off_count + power_on_count
        || result->record_hits[9] != power_off_count + power_on_count
        || result->record_hits[10] != phy_init_count
        || result->record_hits[11] != phy_init_count
        || result->record_hits[12] != notify_count
        || result->record_hits[13] != notify_count
        || result->record_hits[14] != result->outer_pairs
        || result->record_hits[15] != result->outer_pairs
        || result->record_hits[16] != result->qscratch_hits
        || result->record_hits[17] != result->pullup_pairs
        || result->record_hits[18] != result->pullup_pairs
        || result->record_hits[19] != result->run_pairs
        || result->record_hits[20] != result->run_pairs
        || result->record_hits[21] != result->gadget_start_pairs
        || result->record_hits[22] != result->gadget_start_pairs
        || result->record_hits[23] != result->state_hits
        || result->record_hits[24] != result->config_hits)
        return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;

    if (phase != P314_PHASE_PARTIAL) {
        const uint64_t observed[P314_PAIR_MASK_BITS] = {
            start_off_count, start_on_count,
            child_suspend_count, child_resume_count,
            phy_suspend_off_count, phy_suspend_on_count,
            power_off_count, power_on_count, phy_init_count, notify_count,
        };
        const uint8_t *expected = phase == P314_PHASE_STOP
            ? p314_stop_expected : p314_final_expected;
        unsigned int excess_mask = 0U;
        for (size_t index = 0; index < P314_PAIR_MASK_BITS; ++index) {
            if (observed[index] < expected[index])
                return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
            if (observed[index] > expected[index]) excess_mask |= 1U << index;
        }
        if (result->start_off.positive_return_seen
            || result->start_on.positive_return_seen
            || result->child_suspend.positive_return_seen
            || result->child_resume.positive_return_seen
            || result->phy_suspend_off.positive_return_seen
            || result->phy_suspend_on.positive_return_seen
            || result->power_off.positive_return_seen
            || result->power_on.positive_return_seen
            || result->phy_init.positive_return_seen
            || result->notify_connect.positive_return_seen)
            return P313_DETAIL_CYCLE_POSITIVE_RETURN;
        if (!result->phy_suspend_off.all_returns_zero
            || !result->phy_suspend_on.all_returns_zero)
            return P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
        if (excess_mask != 0U) {
            if (result->start_off.first_negative_rc != 0
                || result->start_on.first_negative_rc != 0
                || result->child_suspend.first_negative_rc != 0
                || result->child_resume.first_negative_rc != 0
                || result->power_off.first_negative_rc != 0
                || result->power_on.first_negative_rc != 0
                || result->phy_init.first_negative_rc != 0
                || result->notify_connect.first_negative_rc != 0)
                return P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
            return (long)(P314_PAIR_MASK_DETAIL_BASE + excess_mask);
        }
    }

    if (outer_first.positive_return_seen || pull_first.positive_return_seen
        || result->run_off.positive_return_seen
        || result->run_on.positive_return_seen
        || result->gadget_start.positive_return_seen)
        return P313_DETAIL_CYCLE_POSITIVE_RETURN;
    if (phase == P314_PHASE_PARTIAL) return 0;

    if (phase == P314_PHASE_STOP) {
        if (result->outer_pairs != 1U)
            result->drift_mask |= P313_DRIFT_OUTER_WORK;
        if (result->pullup_pairs != 0U)
            result->drift_mask |= P313_DRIFT_PULLUP;
        if (result->run_pairs != 1U || result->gadget_start_pairs != 0U
            || result->qscratch_hits != 0U || result->state_hits != 0U
            || result->config_hits != 0U)
            result->drift_mask |= P313_DRIFT_START_QSCRATCH;
        if (!p313_counter_nested(&result->start_off, &result->child_suspend)
            || !p313_counter_nested(&result->child_suspend, &result->run_off))
            result->drift_mask |= P313_DRIFT_RESUME_NESTING;
        if (result->drift_mask == 0U && count != P314_STOP_CLEAN_RECORDS)
            return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
        return 0;
    }

    if (phase != P314_PHASE_RESTART && phase != P314_PHASE_FINAL)
        return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
    if (phase == P314_PHASE_FINAL
        && count != P314_FINAL_CLEAN_RECORDS
        && count != P314_FINAL_DRIFT_RECORDS)
        return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
    if (!result->start_off.all_returns_zero
        || !result->start_on.all_returns_zero
        || !result->notify_connect.all_returns_zero)
        return P313_DETAIL_CYCLE_POSITIVE_RETURN;
    if (result->snapshot_seen
        && (result->link_state > 15U || result->run_stop > 1U
            || result->devctrlhlt > 1U || result->coreidle > 1U
            || result->prtcap > 3U || result->susphy > 1U
            || result->connect_speed > 7U))
        return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
    if (result->event_config_seen
        && (result->event_dwc == 0U || result->event_evt == 0U
            || (result->devten & 6U) != 6U
            || result->evt_length != 4096U
            || (result->gevntsiz & 0xffffU) != result->evt_length
            || result->evt_count > result->evt_length
            || (result->evt_count & 3U) != 0U
            || result->evt_flags > 1U
            || (result->gevntcount & 0xfffcU) > result->evt_length))
        return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
    if (result->outer_pairs != 4U) result->drift_mask |= P313_DRIFT_OUTER_WORK;
    if (result->pullup_pairs != 0U) result->drift_mask |= P313_DRIFT_PULLUP;
    if (result->qscratch_hits != 1U || result->gadget_start_pairs != 1U
        || result->run_pairs != 2U || result->state_hits != 1U
        || result->config_hits != 1U)
        result->drift_mask |= P313_DRIFT_START_QSCRATCH;
    if (!p313_counter_nested(&result->start_off, &result->child_suspend)
        || !p313_counter_nested(&result->child_suspend, &result->run_off)
        || !p313_counter_nested(&result->start_on, &result->child_resume)
        || !p313_counter_nested(&result->child_resume, &result->phy_init)
        || !p313_counter_nested(&result->child_resume, &result->gadget_start)
        || !p313_counter_nested(&result->child_resume, &result->run_on))
        result->drift_mask |= P313_DRIFT_RESUME_NESTING;
    if (result->qscratch_hits == 1U
        && !(result->start_on.entry_counter < result->qscratch_counter
             && result->qscratch_counter < result->start_on.return_counter))
        result->drift_mask |= P313_DRIFT_RESUME_NESTING;
    if (result->state_hits == 1U && result->config_hits == 1U
        && (!(result->run_on.entry_counter < result->state_counter
              && result->state_counter < result->run_on.return_counter)
            || !(result->run_on.entry_counter < result->config_counter
                 && result->config_counter < result->run_on.return_counter)))
        result->drift_mask |= P313_DRIFT_RESUME_NESTING;
    return 0;
}
'''.encode("ascii")


_SNAPSHOT_HELPER = r'''static long p314_parse_live_snapshot(
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
'''.encode("ascii")


def transform_runtime_include(value: bytes) -> bytes:
    value = _replace_once(
        value,
        b"/* P3.13 post-bind same-boot resume-cycle observer. */",
        b"/* P3.14 source-normalized post-bind resume-cycle observer. */",
        "observer identity",
    )
    value = _replace_once(
        value,
        b"#define P313_CYCLE_CLEAN_RECORDS 37U\n"
        b"#define P313_CYCLE_DRIFT_RECORDS 45U\n",
        b"#define P314_STOP_CLEAN_RECORDS 14U\n"
        b"#define P314_FINAL_CLEAN_RECORDS 41U\n"
        b"#define P314_FINAL_DRIFT_RECORDS 49U\n"
        b"#define P314_PHASE_PARTIAL 0\n"
        b"#define P314_PHASE_FINAL 1\n"
        b"#define P314_PHASE_STOP 2\n"
        b"#define P314_PHASE_RESTART 3\n"
        b"#define P314_PAIR_MASK_BITS 10U\n"
        b"#define P314_PAIR_MASK_DETAIL_BASE 0x6c00U\n"
        b"static const uint8_t p314_stop_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 0U, 1U, 0U, 2U, 0U, 1U, 0U, 0U, 0U,\n"
        b"};\n"
        b"static const uint8_t p314_final_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 1U, 1U, 1U, 2U, 2U, 1U, 1U, 1U, 1U,\n"
        b"};\n",
        "cycle geometry constants",
    )
    value = _replace_once(
        value,
        b"_Static_assert(P313_CYCLE_DRIFT_RECORDS < P282_RECORD_CAPACITY,\n"
        b"    \"P3.13 cycle record headroom\");\n",
        b"_Static_assert(P314_FINAL_DRIFT_RECORDS < P282_RECORD_CAPACITY,\n"
        b"    \"P3.14 cycle record headroom\");\n"
        b"_Static_assert(P314_PAIR_MASK_DETAIL_BASE + 0x3ffU <= 0x6fffU,\n"
        b"    \"P3.14 pair-mask detail band\");\n",
        "record headroom assertion",
    )
    value = _replace_once(
        value,
        b"    uint8_t entered;\n    uint8_t returned;\n    long pid;\n"
        b"    int32_t rc;\n",
        b"    uint8_t entered;\n    uint8_t returned;\n"
        b"    uint8_t all_returns_zero;\n"
        b"    uint8_t positive_return_seen;\n    long pid;\n"
        b"    int32_t rc;\n    int32_t first_negative_rc;\n",
        "pair aggregate fields",
    )
    value = _replace_definition(value, b"static long p313_pair_collect(\n", _PAIR_COLLECT)
    value = _replace_definition(value, b"static long p313_parse_cycle(\n", _PARSE_CYCLE)
    marker = b"static long p313_cycle_finish(\n"
    if value.count(marker) != 1:
        raise TransformError("P3.14 cycle-finish insertion anchor differs")
    value = value.replace(marker, _SNAPSHOT_HELPER + b"\n" + marker, 1)
    value = _replace_once(
        value,
        b"    if (detail == 0) detail = p313_parse_cycle(control, result, 1);\n"
        b"    if (detail == 0) detail = p313_cycle_profile_relations(control, result);\n"
        b"    if (detail == 0) detail = p300_ring_stats_clean();\n",
        b"    long parse_detail = 0;\n"
        b"    if (detail == 0)\n"
        b"        parse_detail = p313_parse_cycle(control, result, P314_PHASE_FINAL);\n"
        b"    if (detail == 0) detail = p313_cycle_profile_relations(control, result);\n"
        b"    if (detail == 0) detail = p300_ring_stats_clean();\n"
        b"    if (detail == 0) detail = parse_detail;\n",
        "final integrity priority",
    )
    value = _replace_once(
        value,
        b"    if (detail == 0) detail = p313_parse_cycle(control, result, 0);\n"
        b"    if (detail == 0) detail = p313_cycle_profile_relations(control, result);\n"
        b"    if (detail == 0) detail = p300_ring_stats_clean();\n",
        b"    long parse_detail = 0;\n"
        b"    if (detail == 0)\n"
        b"        parse_detail = p313_parse_cycle(control, result, P314_PHASE_PARTIAL);\n"
        b"    if (detail == 0) detail = p313_cycle_profile_relations(control, result);\n"
        b"    if (detail == 0) detail = p300_ring_stats_clean();\n"
        b"    if (detail == 0) detail = parse_detail;\n",
        "partial integrity priority",
    )
    value = _replace_once(
        value,
        b"    if (rc == 0) rc = p313_parse_cycle(&cycle_control, &stop_result, 0);\n"
        b"    if (rc != 0) p313_cycle_fail(&cycle_control, rc);\n",
        b"    if (rc == 0) rc = p314_parse_live_snapshot(\n"
        b"        &cycle_control, &stop_result, P314_PHASE_STOP);\n"
        b"    if (rc != 0) p313_cycle_fail(&cycle_control, rc);\n"
        b"    if (stop_result.drift_mask != 0U)\n"
        b"        p313_cycle_terminal(&cycle_control, tty_fd, 1U,\n"
        b"            (uint16_t)(P313_DRIFT_DETAIL_BASE\n"
        b"                + stop_result.drift_mask - 1U));\n",
        "stop normalized parse",
    )
    value = _replace_once(
        value,
        b"    if (rc == 0) rc = p313_parse_cycle(&cycle_control, &restart_result, 0);\n"
        b"    if (rc != 0) p313_cycle_fail(&cycle_control, rc);\n",
        b"    if (rc == 0) rc = p314_parse_live_snapshot(\n"
        b"        &cycle_control, &restart_result, P314_PHASE_RESTART);\n"
        b"    if (rc != 0) p313_cycle_fail(&cycle_control, rc);\n",
        "restart normalized parse",
    )
    value = _replace_once(
        value,
        b"        || (detail >= 0x6701U && detail <= 0x673fU);\n",
        b"        || (detail >= 0x6701U && detail <= 0x673fU)\n"
        b"        || (detail >= 0x6c01U && detail <= 0x6fffU);\n",
        "P3.14 terminal gate",
    )
    if value.count(b"return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;") != 0:
        raise TransformError("P3.14 legacy 0x6712 emit survived")
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    changed = {key for key in result if result[key] != source[key]}
    if changed != {"p290_e3_runtime_include"}:
        raise TransformError(f"P3.14 delta differs: {sorted(changed)}")
    return result
