#!/usr/bin/env python3
"""Execute the materialized P3.15 live snapshot and restart seams."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p314_runtime_fixture as parent_fixture
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_generator as generator


SCHEMA = "s22plus_fyg8_p315_runtime_wrapper_fixture_v1"
VERDICT = "PASS_P315_RUNTIME_WRAPPER_FIXTURE_HOST_ONLY"


class FixtureError(ValueError):
    pass


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _cycle_tu(root: Path, runtime: bytes, descriptor: bytes) -> bytes:
    source = parent_fixture._cycle_tu(root, runtime, descriptor)  # noqa: SLF001
    source = source[: source.rfind(b"int main(void) {")]
    source = source.replace(
        b"static const uint8_t p314_stop_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 0U, 1U, 0U, 2U, 0U, 1U, 0U, 0U, 0U,\n"
        b"};\n"
        b"static const uint8_t p314_final_expected[P314_PAIR_MASK_BITS] = {\n",
        b"static const uint8_t p314_stop_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 0U, 1U, 0U, 2U, 0U, 1U, 0U, 0U, 0U,\n"
        b"};\n"
        b"static const uint8_t p315_restart_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 1U, 1U, 1U, 2U, 2U, 1U, 1U, 1U, 1U,\n"
        b"};\n"
        b"static const uint8_t p314_final_expected[P314_PAIR_MASK_BITS] = {\n",
        1,
    )
    macros = b"".join(
        support._macro(runtime, name)  # noqa: SLF001
        for name in (
            b"P313_CONTROLLER_DETAIL_BASE",
            b"P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED",
            b"P313_DETAIL_TRACE_RING_LOSS",
            b"P313_DETAIL_CYCLE_RESUME_PRECONDITION",
            b"P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED",
            b"P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION",
            b"P315_RESTART_MAX_SNAPSHOTS",
            b"P315_DETAIL_PROFILE_ONLY_NESTED_HIT",
            b"P315_DETAIL_GADGET_START_ZERO_WITHOUT_RUN_ON",
            b"P315_DETAIL_RUN_ON_PROVENANCE_CONTRADICTION",
        )
    )
    controller = b"".join(
        support._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static long p313_errno_bucket(",
            b"static long p313_controller_detail(",
        )
    )
    functions = b"".join(
        support._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static long p314_parse_live_snapshot(",
            b"static long p315_parse_restart_prefix(",
            b"static long p315_wait_restart_completion(",
            b"static long p315_relevant_profile_integrity(",
            b"static long p315_parse_restart_snapshot(",
            b"static long p315_read_live_snapshot(",
        )
    )
    return source + br'''
#include <errno.h>
#define P260_EPROTO 71
#define P313_EBUSY 16
#define P313_ENOMEM 12
struct timespec64 { long long tv_sec; long long tv_nsec; };
''' + macros + br'''
static struct p282_trace_record snapshots[2][65];
static size_t snapshot_counts[2];
static unsigned int snapshot_total;
static unsigned int snapshot_reads;
static unsigned int profile_reads;
static unsigned int poll_calls;
static int forced_read_rc;
static int forced_ring_detail;
static int profile_excess_event = -1;
static int profile_deficit_event = -1;
static int deadline_expired;

static void reset_io(void) {
    memset(snapshots, 0, sizeof(snapshots));
    memset(snapshot_counts, 0, sizeof(snapshot_counts));
    snapshot_total = snapshot_reads = profile_reads = poll_calls = 0U;
    forced_read_rc = forced_ring_detail = 0;
    profile_excess_event = profile_deficit_event = -1;
    deadline_expired = 0;
}

static void save_snapshot(unsigned int index) {
    memcpy(snapshots[index], fixture, fixture_count * sizeof(fixture[0]));
    snapshot_counts[index] = fixture_count;
    if (snapshot_total <= index) snapshot_total = index + 1U;
}

static long p282_trace_read_snapshot(
    struct p282_trace_control *control, int require_profile) {
    if (forced_read_rc != 0) return forced_read_rc;
    if (snapshot_total != 0U) {
        unsigned int selected = snapshot_reads < snapshot_total
            ? snapshot_reads : snapshot_total - 1U;
        memcpy(fixture, snapshots[selected], sizeof(fixture));
        fixture_count = snapshot_counts[selected];
    }
    ++snapshot_reads;
    if (!require_profile) return 0;
    ++profile_reads;
    memset(control->profile_hits, 0, sizeof(control->profile_hits));
    control->event_count = P313_CYCLE_EVENT_COUNT;
    for (size_t index = 0; index < fixture_count; ++index) {
        uint8_t event = fixture[index].event_index;
        if (event < P313_CYCLE_EVENT_COUNT)
            ++control->profile_hits[event];
    }
    if (profile_excess_event >= 0)
        ++control->profile_hits[(unsigned int)profile_excess_event];
    if (profile_deficit_event >= 0)
        control->profile_hits[(unsigned int)profile_deficit_event] = 0U;
    return 0;
}

static long p300_ring_stats_clean(void) { return forced_ring_detail; }
static int p282_deadline_expired(const struct timespec64 *deadline) {
    (void)deadline;
    return deadline_expired;
}
static void p282_poll_delay(void) { ++poll_calls; }
''' + controller + functions + br'''
static void compact_without_run_on(void) {
    struct p282_trace_record copy[65];
    size_t count = 0U;
    int skip_return = 0;
    for (size_t index = 0; index < fixture_count; ++index) {
        struct p282_trace_record row = fixture[index];
        if (row.event_index == 19U && row.has_on && row.on == 1) {
            skip_return = 1;
            continue;
        }
        if (skip_return && row.event_index == 20U) {
            skip_return = 0;
            continue;
        }
        copy[count++] = row;
    }
    memcpy(fixture, copy, count * sizeof(copy[0]));
    fixture_count = count;
}

static void compact_without_gadget(void) {
    struct p282_trace_record copy[65];
    size_t count = 0U;
    int skip_return = 0;
    for (size_t index = 0; index < fixture_count; ++index) {
        struct p282_trace_record row = fixture[index];
        if (row.event_index == 21U) {
            skip_return = 1;
            continue;
        }
        if (skip_return && row.event_index == 22U) {
            skip_return = 0;
            continue;
        }
        copy[count++] = row;
    }
    memcpy(fixture, copy, count * sizeof(copy[0]));
    fixture_count = count;
}

static void compact_without_pair(uint8_t entry, uint8_t returned_event) {
    struct p282_trace_record copy[65];
    size_t count = 0U;
    int skip_return = 0;
    for (size_t index = 0; index < fixture_count; ++index) {
        struct p282_trace_record row = fixture[index];
        if (!skip_return && row.event_index == entry) {
            skip_return = 1;
            continue;
        }
        if (skip_return && row.event_index == returned_event) {
            skip_return = 0;
            continue;
        }
        copy[count++] = row;
    }
    memcpy(fixture, copy, count * sizeof(copy[0]));
    fixture_count = count;
}

static int set_return_after(
    uint8_t entry, uint8_t returned_event,
    int argument_kind, int argument_value, int rc) {
    for (size_t index = 0; index < fixture_count; ++index) {
        struct p282_trace_record *row = &fixture[index];
        if (row->event_index != entry
            || !p282_record_argument_matches(
                row, argument_kind, argument_value)) continue;
        for (size_t other = index + 1U; other < fixture_count; ++other) {
            if (fixture[other].pid == row->pid
                && fixture[other].event_index == returned_event
                && fixture[other].has_rc) {
                fixture[other].rc = rc;
                return 1;
            }
        }
    }
    return 0;
}

static void truncate_after_start_on_entry(void) {
    for (size_t index = 0; index < fixture_count; ++index) {
        if (fixture[index].event_index == 0U
            && fixture[index].has_on && fixture[index].on == 1) {
            fixture_count = index + 1U;
            return;
        }
    }
}

static void remove_start_on_pair(void) {
    struct p282_trace_record copy[65];
    size_t count = 0U;
    int skip_return = 0;
    for (size_t index = 0; index < fixture_count; ++index) {
        struct p282_trace_record row = fixture[index];
        if (row.event_index == 0U && row.has_on && row.on == 1) {
            skip_return = 1;
            continue;
        }
        if (skip_return && row.event_index == 1U) {
            skip_return = 0;
            continue;
        }
        copy[count++] = row;
    }
    memcpy(fixture, copy, count * sizeof(copy[0]));
    fixture_count = count;
}

int main(void) {
    struct p282_trace_control control = {0};
    struct p313_cycle_result result = {0};
    struct timespec64 deadline = {0};
    int ready = 0;

    fill_p314_clean();
    if (p313_parse_cycle(&control, &result, P314_PHASE_PARTIAL) != 0)
        return 1;
    profile_from_result(&control, &result);
    if (p313_cycle_profile_relations(&control, &result) != 0) return 2;
    fill_p314_clean(); append_pair(0U, 0);
    if (p313_parse_cycle(&control, &result, P314_PHASE_FINAL)
        != P314_PAIR_MASK_DETAIL_BASE + 1U) return 3;

    reset_io(); fill_p314_stop();
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_STOP) != 0
        || result.total_records != 14U || profile_reads != 1U) return 10;
    reset_io(); fill_p314_stop(); forced_read_rc = -EIO;
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_STOP)
        != P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED) return 11;

    reset_io(); fill_p314_clean();
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART) != 0
        || result.total_records != 41U || profile_reads != 1U) return 20;
    reset_io(); fill_p314_clean(); append_bounded_drift();
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART) != 0
        || result.total_records != 49U || result.drift_mask == 0U) return 21;

    reset_io(); fill_p314_clean(); compact_without_run_on();
    compact_without_gadget();
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P313_DETAIL_CYCLE_RESUME_PRECONDITION
        || control.profile_hits[19] != 1U
        || control.profile_hits[20] != 1U
        || control.profile_hits[21] != 0U
        || control.profile_hits[22] != 0U) return 30;
    reset_io(); fill_p314_clean(); compact_without_run_on();
    compact_without_gadget(); profile_excess_event = 19;
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P315_DETAIL_PROFILE_ONLY_NESTED_HIT) return 31;
    reset_io(); fill_p314_clean(); compact_without_run_on();
    compact_without_gadget(); profile_deficit_event = 19;
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P313_DETAIL_PROFILE_RECORD_DEFICIT) return 32;

    reset_io(); fill_p314_clean(); compact_without_run_on();
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P315_DETAIL_GADGET_START_ZERO_WITHOUT_RUN_ON) return 40;
    reset_io(); fill_p314_clean(); compact_without_run_on();
    if (!set_return_after(21U, 22U, 0, 0, 1)
        || p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
            != P313_DETAIL_CYCLE_POSITIVE_RETURN) return 41;
    reset_io(); fill_p314_clean(); compact_without_run_on();
    if (!set_return_after(21U, 22U, 0, 0, -ETIMEDOUT)
        || p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
            != P313_CONTROLLER_DETAIL_BASE + 8U * 8U) return 42;
    reset_io(); fill_p314_clean(); compact_without_gadget();
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P315_DETAIL_RUN_ON_PROVENANCE_CONTRADICTION) return 43;
    reset_io(); fill_p314_clean();
    if (!set_return_after(21U, 22U, 0, 0, -ETIMEDOUT)
        || p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
            != P315_DETAIL_RUN_ON_PROVENANCE_CONTRADICTION) return 44;
    reset_io(); fill_p314_clean();
    if (!set_return_after(19U, 20U, 1, 1, -ETIMEDOUT)
        || p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
            != P313_CONTROLLER_DETAIL_BASE + 9U * 8U) return 45;
    reset_io(); fill_p314_clean();
    if (!set_return_after(19U, 20U, 1, 1, 1)
        || p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
            != P313_DETAIL_CYCLE_POSITIVE_RETURN) return 46;

    reset_io(); fill_p314_clean();
    for (size_t index = 0; index < fixture_count; ++index) {
        if (fixture[index].event_index == 22U) {
            memmove(&fixture[index], &fixture[index + 1U],
                (fixture_count - index - 1U) * sizeof(fixture[0]));
            --fixture_count;
            break;
        }
    }
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P313_DETAIL_CYCLE_PAIRING_CONTRADICTION) return 47;
    reset_io(); fill_p314_clean(); compact_without_pair(10U, 11U);
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P313_DETAIL_CYCLE_PAIRING_CONTRADICTION) return 48;

    reset_io(); fill_p314_stop();
    if (p315_parse_restart_prefix(&control, &ready) != 0 || ready) return 50;
    reset_io(); fill_p314_clean();
    if (p315_parse_restart_prefix(&control, &ready) != 0 || !ready) return 51;
    reset_io(); fill_p314_clean(); remove_start_on_pair();
    if (p315_parse_restart_prefix(&control, &ready)
        != P313_DETAIL_RECORD_FORMAT_CONTRADICTION) return 52;
    reset_io(); fill_p314_clean(); truncate_after_start_on_entry();
    if (p315_parse_restart_prefix(&control, &ready) != 0 || ready) return 53;

    reset_io(); fill_p314_stop(); save_snapshot(0U);
    fill_p314_clean(); save_snapshot(1U);
    if (p315_wait_restart_completion(&control, &deadline) != 0
        || snapshot_reads != 2U || poll_calls != 1U) return 60;
    reset_io(); fill_p314_stop(); save_snapshot(0U); deadline_expired = 1;
    if (p315_wait_restart_completion(&control, &deadline)
        != P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED) return 61;
    reset_io(); forced_read_rc = -EIO;
    if (p315_wait_restart_completion(&control, &deadline)
        != P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED) return 62;

    reset_io(); fill_p314_clean(); forced_ring_detail =
        P313_DETAIL_TRACE_RING_LOSS;
    if (p315_read_live_snapshot(&control, &result, P314_PHASE_RESTART)
        != P313_DETAIL_TRACE_RING_LOSS) return 70;
    reset_io(); fill_p314_clean();
    if (p315_read_live_snapshot(&control, &result, 99)
        != P313_DETAIL_RECORD_FORMAT_CONTRADICTION) return 71;

    printf("stop-profile=1 restart=41/49 absence-baseline=1/1 branches=12 wait=3\n");
    return 0;
}
'''


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    descriptor = artifacts["trace_descriptor_header"]
    output = support._compile(  # noqa: SLF001
        _cycle_tu(root, runtime, descriptor), "p315-live-snapshot-wrapper"
    )
    expected = (
        "stop-profile=1 restart=41/49 absence-baseline=1/1 "
        "branches=12 wait=3\n"
    )
    if output != expected:
        raise FixtureError(f"P3.15 runtime fixture differs: {output!r}")
    required = (
        b"p315_read_live_snapshot",
        b"p315_wait_restart_completion",
        b"p315_parse_restart_snapshot",
        b"control->profile_hits[event] > result->record_hits[event]",
    )
    if any(runtime.count(token) < 1 for token in required):
        raise FixtureError("P3.15 live seam is absent")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "stop_profile_read_executed": True,
        "restart_profile_read_executed": True,
        "restart_clean_records": 41,
        "restart_bounded_drift_records": 49,
        "run_off_profile_baseline": [1, 1],
        "absolute_zero_run_profile_rejected_as_deficit": True,
        "retained_restart_branches_executed": 12,
        "completion_wait_cases_executed": 3,
        "actual_live_wrapper_executed": True,
        "verified": True,
    }


def main() -> int:
    try:
        value = audit()
    except (FixtureError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
