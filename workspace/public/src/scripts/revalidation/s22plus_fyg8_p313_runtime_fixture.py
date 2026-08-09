#!/usr/bin/env python3
"""Execute P3.13 materialized role, direct, and cycle parser contracts."""

from __future__ import annotations

import json
from pathlib import Path

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p313_generator as generator


SCHEMA = "s22plus_fyg8_p313_runtime_fixture_v1"
VERDICT = "PASS_P313_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
FixtureError = support.AuditError


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _frozen_p312_runtime(root: Path) -> bytes:
    return (
        root
        / "workspace/private/outputs/s22plus_fyg8_p312/intent/materialized-sources"
        / "s22plus_fyg8_p290_e3_runtime.inc.c"
    ).read_bytes()


def _common_structs(runtime: bytes) -> bytes:
    return b"".join(
        support._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"struct p282_trace_control {\n",
            b"struct p282_trace_record {\n",
        )
    )


def _role_tu(runtime: bytes, descriptor: bytes, *, strict: bool) -> bytes:
    macros = support._macro(runtime, b"P282_RECORD_CAPACITY")  # noqa: SLF001
    macros += support._macro(descriptor, b"P311_EARLY_EVENT_COUNT")  # noqa: SLF001
    if strict:
        macros += b"".join(
            support._macro(runtime, name)  # noqa: SLF001
            for name in (
                b"P313_DETAIL_RECORD_FORMAT_CONTRADICTION",
                b"P313_DETAIL_ROLE_QSCRATCH_MISSING",
                b"P313_DETAIL_ROLE_QSCRATCH_DUPLICATE",
                b"P313_DETAIL_ROLE_QSCRATCH_FOREIGN_PID",
                b"P313_DETAIL_ROLE_QSCRATCH_ORDER",
                b"P313_DETAIL_ROLE_QSCRATCH_VALUE",
            )
        )
    structures = _common_structs(runtime) + b"".join(
        support._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"enum p282_role_classification {\n",
            b"struct p282_role_result {\n",
        )
    )
    parser = support._definition(  # noqa: SLF001
        runtime, b"static long p282_parse_role_result("
    )
    globals_source = (
        b"static uint32_t g_p313_role_qscratch;\n"
        b"static uint8_t g_p313_role_qscratch_valid;\n"
        if strict
        else b""
    )
    strict_cases = br'''
    reset_rows(valid, 5U);
    if (p282_parse_role_result(&control, &result) != 0
        || result.classification != P282_ROLE_COMPLETE
        || result.pid != 7 || !g_p313_role_qscratch_valid
        || g_p313_role_qscratch != QSCRATCH) return 10;

    reset_rows(valid, 4U);
    rows[3] = valid[4];
    if (p282_parse_role_result(&control, &result)
        != P313_DETAIL_ROLE_QSCRATCH_MISSING) return 11;

    reset_rows(valid, 5U);
    rows[4] = rows[3];
    rows[4].counter = 5U;
    if (p282_parse_role_result(&control, &result)
        != P313_DETAIL_ROLE_QSCRATCH_DUPLICATE) return 12;

    reset_rows(valid, 5U);
    rows[3].pid = 8;
    if (p282_parse_role_result(&control, &result)
        != P313_DETAIL_ROLE_QSCRATCH_FOREIGN_PID) return 13;

    reset_rows(valid, 5U);
    struct p282_trace_record swap = rows[2];
    rows[2] = rows[3];
    rows[3] = swap;
    rows[2].counter = 3U;
    rows[3].counter = 4U;
    if (p282_parse_role_result(&control, &result)
        != P313_DETAIL_ROLE_QSCRATCH_ORDER) return 14;

    reset_rows(valid, 5U);
    rows[3].rc = 0;
    if (p282_parse_role_result(&control, &result)
        != P313_DETAIL_ROLE_QSCRATCH_VALUE) return 15;

    reset_rows(valid, 5U);
    rows[3].has_rc = 0U;
    if (p282_parse_role_result(&control, &result)
        != P313_DETAIL_RECORD_FORMAT_CONTRADICTION) return 16;

    reset_rows(valid, 5U);
    rows[1].rc = -5;
    if (p282_parse_role_result(&control, &result) != 0
        || result.classification != P282_ROLE_PARENT_PM_NEGATIVE) return 17;

    printf("strict-role=8 exact-five=1 failure-matrix=5\n");
'''
    legacy_cases = br'''
    reset_rows(valid, 4U);
    rows[3] = valid[4];
    if (p282_parse_role_result(&control, &result) != 0
        || result.classification != P282_ROLE_COMPLETE
        || result.pid != 7) return 10;
    reset_rows(valid, 5U);
    if (p282_parse_role_result(&control, &result) == 0) return 11;
    printf("legacy-role=2 exact-four=1 index-four-rejected=1\n");
'''
    return (
        br'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define NULL ((void *)0)
#define P260_EPROTO 71
#define QSCRATCH ((int32_t)((1U << 20U) | (1U << 28U)))
struct p282_event_descriptor;
'''
        + macros
        + structures
        + globals_source
        + br'''
static struct p282_trace_record rows[P282_RECORD_CAPACITY];
static size_t row_count;
static long p282_parse_trace_records(
    const struct p282_trace_control *control,
    struct p282_trace_record records[P282_RECORD_CAPACITY],
    size_t *count) {
    (void)control;
    memcpy(records, rows, row_count * sizeof(rows[0]));
    *count = row_count;
    return 0;
}
'''
        + parser
        + br'''
static void reset_rows(const struct p282_trace_record *source, size_t count) {
    memset(rows, 0, sizeof(rows));
    memcpy(rows, source, count * sizeof(source[0]));
    row_count = count;
'''
        + (br'''    g_p313_role_qscratch = 0U;
    g_p313_role_qscratch_valid = 0U;
''' if strict else b"")
        + br'''}
int main(void) {
    struct p282_trace_control control = {0};
    struct p282_role_result result = {0};
    static const struct p282_trace_record valid[] = {
        {.counter=1U, .pid=7, .event_index=0U, .has_on=1U, .on=1},
        {.counter=2U, .pid=7, .event_index=1U, .has_rc=1U, .rc=0},
        {.counter=3U, .pid=7, .event_index=2U, .has_rc=1U, .rc=0},
        {.counter=4U, .pid=7, .event_index=4U, .has_rc=1U, .rc=QSCRATCH},
        {.counter=5U, .pid=7, .event_index=3U, .has_rc=1U, .rc=0},
    };
'''
        + (strict_cases if strict else legacy_cases)
        + br'''    return 0;
}
'''
    )


def _direct_tu(runtime: bytes, descriptor: bytes, classifier: bytes) -> bytes:
    macros = b"".join(
        support._macro(descriptor, name)  # noqa: SLF001
        for name in (b"P311_EARLY_EVENT_COUNT", b"P282_CYCLE_EVENT_COUNT")
    )
    macros += b"".join(
        support._macro(runtime, name)  # noqa: SLF001
        for name in (
            b"P300_PREFIX_RECORD_CAPACITY",
            b"P313_DIRECT_PREFIX_CLEAN",
            b"P313_DIRECT_PREFIX_CONTRADICTION_MIN",
            b"P313_DETAIL_DIRECT_PREFIX_MULTIPLICITY",
        )
    )
    structures = b"".join(
        support._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"struct p282_trace_control {\n",
            b"struct p282_trace_record {\n",
            b"struct p282_bind_trace_result {\n",
            b"struct p300_stream_state {\n",
        )
    )
    functions = b"".join(
        (
            support._definition(  # noqa: SLF001
                runtime, b"static int p313_direct_known_baseline("
            ),
            support._definition(  # noqa: SLF001
                runtime, b"static long p313_finish_direct("
            ),
        )
    )
    return (
        br'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
struct p282_event_descriptor;
'''
        + macros
        + support._struct(classifier, b"enum p282_bind_branch {\n")  # noqa: SLF001
        + structures
        + br'''
_Static_assert(P300_PREFIX_RECORD_CAPACITY == 32U,
    "P3.13 materialized direct prefix capacity");
static long inherited_detail;
static long p298_finish_observer(
    struct p282_trace_control *control,
    struct p282_bind_trace_result *result,
    int final) {
    (void)control;
    (void)result;
    (void)final;
    return inherited_detail;
}
'''
        + functions
        + br'''
static struct p282_bind_trace_result baseline(void) {
    return (struct p282_bind_trace_result){
        .prefix_records = 10U,
        .pullup_returned_zero = 1U,
        .branch = P282_BIND_DIRECT,
        .start_entered = 1U,
        .start_returned = 1U,
        .start_rc = 0,
        .ep_enable_hits = 2U,
        .run_stop_seen = 1U,
        .run_stop_rc = 0,
        .snapshot_seen = 1U,
        .event_config_seen = 1U,
    };
}
int main(void) {
    struct p282_trace_control control = {0};
    struct p282_bind_trace_result result = baseline();
    if (!p313_direct_known_baseline(&result)) return 10;
    result.prefix_records = 22U;
    if (p313_direct_known_baseline(&result)) return 11;
    inherited_detail = 0;
    if (p313_finish_direct(&control, &result) != 0) return 12;
    result.prefix_records = 23U;
    if (p313_finish_direct(&control, &result)
        != P313_DETAIL_DIRECT_PREFIX_MULTIPLICITY) return 13;
    inherited_detail = 0x1234;
    result.prefix_records = 10U;
    if (p313_finish_direct(&control, &result) != 0x1234) return 14;
    printf("direct=5 capacity=32 clean=10 drift=22 contradiction=23\n");
    return 0;
}
'''
    )


def _cycle_tu(runtime: bytes, descriptor: bytes) -> bytes:
    macro_names = (
        b"P282_RECORD_CAPACITY",
        b"P313_CYCLE_EVENT_COUNT",
        b"P313_CYCLE_CLEAN_RECORDS",
        b"P313_CYCLE_DRIFT_RECORDS",
        b"P313_DETAIL_PROFILE_RECORD_DEFICIT",
        b"P313_DETAIL_RECORD_FORMAT_CONTRADICTION",
        b"P313_DETAIL_CYCLE_RECORD_OVERFLOW",
        b"P313_DETAIL_CYCLE_EVENT_MULTIPLICITY",
        b"P313_DETAIL_CYCLE_PAIRING_CONTRADICTION",
        b"P313_DETAIL_CYCLE_POSITIVE_RETURN",
        b"P313_DETAIL_CYCLE_QSCRATCH_CONTRADICTION",
        b"P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION",
        b"P313_DRIFT_PULLUP",
        b"P313_DRIFT_START_QSCRATCH",
        b"P313_DRIFT_OUTER_WORK",
        b"P313_DRIFT_RESUME_NESTING",
    )
    macros = b"".join(
        support._macro(runtime, name) for name in macro_names  # noqa: SLF001
    )
    macros += support._macro(descriptor, b"P311_EARLY_EVENT_COUNT")  # noqa: SLF001
    structures = _common_structs(runtime) + b"".join(
        support._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"struct p313_cycle_pair {\n",
            b"struct p313_cycle_result {\n",
        )
    )
    functions = b"".join(
        support._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static int p282_record_argument_matches(\n",
            b"static long p313_pair_collect(\n",
            b"static int p313_counter_nested(\n",
            b"static long p313_parse_cycle(\n",
            b"static long p313_cycle_profile_relations(\n",
        )
    )
    return (
        br'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define NULL ((void *)0)
#define P260_EOVERFLOW 75
struct p282_event_descriptor;
'''
        + macros
        + structures
        + br'''
static struct p282_trace_record fixture[65];
static size_t fixture_count;
static long p282_parse_trace_records(
    const struct p282_trace_control *control,
    struct p282_trace_record records[P282_RECORD_CAPACITY],
    size_t *count) {
    (void)control;
    if (fixture_count > P282_RECORD_CAPACITY) return -P260_EOVERFLOW;
    memcpy(records, fixture, fixture_count * sizeof(fixture[0]));
    *count = fixture_count;
    return 0;
}
'''
        + functions
        + br'''
static void push(uint8_t event, long pid) {
    fixture[fixture_count] = (struct p282_trace_record){
        .counter = fixture_count + 1U, .pid = pid, .event_index = event,
    };
    ++fixture_count;
}
static void entry_on(uint8_t event, long pid, int on) {
    push(event, pid);
    fixture[fixture_count - 1U].has_on = 1U;
    fixture[fixture_count - 1U].on = on;
}
static void entry_suspend(uint8_t event, long pid, int suspend) {
    push(event, pid);
    fixture[fixture_count - 1U].has_suspend = 1U;
    fixture[fixture_count - 1U].suspend = suspend;
}
static void returned(uint8_t event, long pid, int rc) {
    push(event, pid);
    fixture[fixture_count - 1U].has_rc = 1U;
    fixture[fixture_count - 1U].rc = rc;
}
static void state_record(long pid) {
    push(23U, pid);
    struct p282_trace_record *row = &fixture[fixture_count - 1U];
    row->has_link = row->has_run_stop = row->has_devctrlhlt = 1U;
    row->has_coreidle = row->has_prtcap = row->has_susphy = 1U;
    row->has_connect_speed = 1U;
    row->link = 0; row->run_stop = 1; row->devctrlhlt = 0;
    row->coreidle = 1; row->prtcap = 2; row->susphy = 0;
    row->connect_speed = 0;
}
static void config_record(long pid) {
    push(24U, pid);
    struct p282_trace_record *row = &fixture[fixture_count - 1U];
    row->has_dwc = row->has_evt = row->has_devten = 1U;
    row->has_gevntsiz = row->has_gevntcount = 1U;
    row->has_evt_length = row->has_evt_count = row->has_evt_flags = 1U;
    row->dwc = 1U; row->evt = 2U; row->devten = 6U;
    row->gevntsiz = 4096U; row->gevntcount = 0U;
    row->evt_length = 4096U; row->evt_count = 0U; row->evt_flags = 0U;
}
static void qscratch(long pid) {
    returned(16U, pid, (int32_t)((1U << 20U) | (1U << 28U)));
}
static void outer_pair(long pid) {
    push(14U, pid); returned(15U, pid, 0);
}
static void fill_clean(void) {
    memset(fixture, 0, sizeof(fixture));
    fixture_count = 0U;
    long pid = 9;
    push(14U, pid);
    entry_on(0U, pid, 0);
    push(2U, pid);
    entry_suspend(6U, pid, 1);
    entry_on(8U, pid, 0);
    entry_on(19U, pid, 0);
    returned(20U, pid, 0);
    returned(9U, pid, 0);
    returned(7U, pid, 0);
    returned(3U, pid, 0);
    returned(1U, pid, 0);
    returned(15U, pid, 0);
    outer_pair(pid);
    outer_pair(pid);
    push(14U, pid);
    entry_on(0U, pid, 1);
    push(4U, pid);
    entry_suspend(6U, pid, 0);
    entry_on(8U, pid, 1);
    push(10U, pid);
    push(12U, pid);
    push(21U, pid);
    entry_on(19U, pid, 1);
    qscratch(pid);
    state_record(pid);
    config_record(pid);
    returned(20U, pid, 0);
    returned(22U, pid, 0);
    returned(13U, pid, 0);
    returned(11U, pid, 0);
    returned(9U, pid, 0);
    returned(7U, pid, 0);
    returned(5U, pid, 0);
    returned(1U, pid, 0);
    returned(15U, pid, 0);
}
static void append_bounded_drift(void) {
    long pid = 9;
    push(17U, pid); returned(18U, pid, 0);
    push(21U, pid); returned(22U, pid, 0);
    entry_on(19U, pid, 1); returned(20U, pid, 0);
    state_record(pid); config_record(pid);
}
static void profile_from_result(
    struct p282_trace_control *control,
    const struct p313_cycle_result *result) {
    memset(control, 0, sizeof(*control));
    control->event_count = P313_CYCLE_EVENT_COUNT;
    for (size_t index = 0; index < P313_CYCLE_EVENT_COUNT; ++index)
        control->profile_hits[index] = result->record_hits[index];
}
int main(void) {
    struct p282_trace_control control = {0};
    struct p313_cycle_result result = {0};
    fill_clean();
    if (fixture_count != P313_CYCLE_CLEAN_RECORDS
        || p313_parse_cycle(&control, &result, 1) != 0
        || result.total_records != 37U || result.drift_mask != 0U) return 10;
    profile_from_result(&control, &result);
    if (p313_cycle_profile_relations(&control, &result) != 0) return 11;
    ++control.profile_hits[0];
    if (p313_cycle_profile_relations(&control, &result) != 0) return 12;
    control.profile_hits[0] = result.record_hits[0] - 1U;
    if (p313_cycle_profile_relations(&control, &result)
        != P313_DETAIL_PROFILE_RECORD_DEFICIT) return 13;

    fill_clean(); append_bounded_drift();
    if (fixture_count != P313_CYCLE_DRIFT_RECORDS
        || p313_parse_cycle(&control, &result, 1) != 0
        || result.total_records != 45U
        || (result.drift_mask & (P313_DRIFT_PULLUP | P313_DRIFT_START_QSCRATCH))
            != (P313_DRIFT_PULLUP | P313_DRIFT_START_QSCRATCH)) return 20;

    fill_clean();
    entry_on(0U, 9, 0); returned(1U, 9, 0);
    if (p313_parse_cycle(&control, &result, 0)
        != P313_DETAIL_CYCLE_EVENT_MULTIPLICITY) return 30;

    fill_clean();
    fixture[10].event_index = 15U;
    fixture[35].event_index = 15U;
    if (p313_parse_cycle(&control, &result, 0)
        != P313_DETAIL_CYCLE_PAIRING_CONTRADICTION) return 31;

    fill_clean();
    fixture[10].rc = 1;
    if (p313_parse_cycle(&control, &result, 1)
        != P313_DETAIL_CYCLE_POSITIVE_RETURN) return 32;

    fill_clean();
    for (size_t index = 0; index < fixture_count; ++index) {
        if (fixture[index].event_index == 23U) {
            fixture[index].link = 16;
            break;
        }
    }
    if (p313_parse_cycle(&control, &result, 1)
        != P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION) return 33;

    memset(fixture, 0, sizeof(fixture));
    fixture_count = 65U;
    if (p313_parse_cycle(&control, &result, 1)
        != P313_DETAIL_CYCLE_RECORD_OVERFLOW) return 34;

    printf("cycle=9 clean=37 drift=45 overflow=65 profile-lower-bound=1\n");
    return 0;
}
'''
    )


def audit(root: Path) -> dict[str, object]:
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    descriptor = artifacts["trace_descriptor_header"]
    frozen_descriptor = (
        root
        / "workspace/private/outputs/s22plus_fyg8_p312/intent/materialized-sources"
        / "s22plus_fyg8_p286_trace_descriptor.h"
    ).read_bytes()
    legacy = support._compile(  # noqa: SLF001
        _role_tu(_frozen_p312_runtime(root), frozen_descriptor, strict=False),
        "p313-legacy-role",
    )
    strict = support._compile(  # noqa: SLF001
        _role_tu(runtime, descriptor, strict=True), "p313-strict-role"
    )
    direct = support._compile(  # noqa: SLF001
        _direct_tu(runtime, descriptor, artifacts["classifier_include"]),
        "p313-direct",
    )
    cycle = support._compile(  # noqa: SLF001
        _cycle_tu(runtime, descriptor), "p313-cycle"
    )
    expected = {
        "legacy": "legacy-role=2 exact-four=1 index-four-rejected=1\n",
        "strict": "strict-role=8 exact-five=1 failure-matrix=5\n",
        "direct": "direct=5 capacity=32 clean=10 drift=22 contradiction=23\n",
        "cycle": "cycle=9 clean=37 drift=45 overflow=65 profile-lower-bound=1\n",
    }
    actual = {"legacy": legacy, "strict": strict, "direct": direct, "cycle": cycle}
    if actual != expected:
        raise FixtureError(f"P3.13 materialized runtime fixtures differ: {actual!r}")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "executed_materialized_runtime": actual,
        "legacy_four_event_semantics_preserved": True,
        "strict_five_event_role_matrix": True,
        "direct_prefix_capacity_and_thresholds": [10, 22, 23, 32],
        "cycle_record_contract": [37, 45, 65],
        "profile_excess_accepted": True,
        "profile_deficit_rejected": True,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
