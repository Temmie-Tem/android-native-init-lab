#!/usr/bin/env python3
"""Execute the materialized P3.11 trace parser on representative records."""

from __future__ import annotations

import json
from pathlib import Path

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p311_generator as generator
import s22plus_fyg8_p311_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p311_runtime_fixture_v1"
VERDICT = "PASS_P311_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
FixtureError = support.AuditError


def _runtime(root: Path) -> bytes:
    run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
    unsat = carrier.unsat_record(spec.PROFILE, run_id)
    return generator.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat[len(carrier.UNSAT_FAMILY) :],
        profile=spec.PROFILE,
    )["p290_e3_runtime_include"]


def _translation_unit(runtime: bytes) -> bytes:
    functions = b"".join(
        (
            support._definition(runtime, b"static unsigned int p303_errno_bucket("),  # noqa: SLF001
            support._definition(runtime, b"static long p311_validate_caller_pairs("),  # noqa: SLF001
            support._definition(runtime, b"static long p311_record_window("),  # noqa: SLF001
            support._definition(runtime, b"static long p311_clock_state_from_window("),  # noqa: SLF001
            support._definition(runtime, b"static long p311_parse_early_trace("),  # noqa: SLF001
            support._definition(runtime, b"static long p311_first_detail("),  # noqa: SLF001
            support._definition(runtime, b"static long p311_summary_detail("),  # noqa: SLF001
        )
    )
    macros = b"".join(
        support._macro(runtime, name)  # noqa: SLF001
        for name in (
            b"P311_CALLER_EVENT_COUNT",
            b"P311_CALLSITE_EVENT_BASE",
            b"P311_CALLSITE_COUNT",
            b"P311_PROBE_CALLSITE_BASE",
            b"P311_INIT_EUD_CALLSITE_BASE",
            b"P311_INIT_NORMAL_CALLSITE_BASE",
            b"P311_SUSPEND_CALLSITE_BASE",
            b"P311_CLOCK_STATE_COUNT",
            b"P311_FIRST_DETAIL_BASE",
            b"P311_FIRST_DETAIL_NO_CLOCK_PATH",
            b"P311_SUMMARY_DETAIL_BASE",
            b"P311_SUMMARY_DETAIL_MAX",
            b"P311_QSCRATCH_STATE_COUNT",
            b"P311_DOMAIN_PROBE",
            b"P311_DOMAIN_SET_SUSPEND",
            b"P311_DOMAIN_INIT",
            b"P311_DOMAIN_NONE",
            b"P311_DOMAIN_COUNT",
            b"P311_MULTI_PATH_COUNT",
            b"P311_REACH_MASK_COUNT",
            b"P311_REACH_PROBE",
            b"P311_REACH_INIT",
            b"P311_REACH_SET_SUSPEND_ZERO",
            b"P311_DETAIL_EARLY_PROFILE_RECORD_MISMATCH",
            b"P311_DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION",
            b"P311_DETAIL_EARLY_CALLER_PAIR_CONTRADICTION",
            b"P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION",
            b"P311_DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION",
            b"P311_DETAIL_EARLY_CFG_AHB_CONTRADICTION",
            b"P311_DETAIL_EARLY_DOMAIN_CONTRADICTION",
        )
    )
    capture = support._struct(runtime, b"struct p311_early_capture {\n")  # noqa: SLF001
    return (
        br'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define NULL ((void *)0)
#define EINVAL 22
#define EIO 5
#define ETIMEDOUT 110
#define P282_RECORD_CAPACITY 64U
#define P311_EARLY_EVENT_COUNT 30U
'''
        + macros
        + capture
        + br'''
struct p282_trace_control {
    size_t event_count;
    uint64_t profile_hits[30];
};
struct p282_trace_record {
    long pid;
    uint8_t event_index;
    uint8_t has_suspend;
    uint8_t has_rc;
    int32_t suspend;
    int32_t rc;
};
static struct p311_early_capture g_p311_early;
static struct p282_trace_record fixture[64];
static size_t fixture_count;
static long p282_parse_trace_records(
    const struct p282_trace_control *control,
    struct p282_trace_record records[P282_RECORD_CAPACITY],
    size_t *count) {
    (void)control;
    memcpy(records, fixture, fixture_count * sizeof(fixture[0]));
    *count = fixture_count;
    return 0;
}
'''
        + functions
        + br'''
static struct p282_trace_record row(long pid, uint8_t event, int has_suspend,
                                    int suspend, int has_rc, int rc) {
    return (struct p282_trace_record){
        .pid = pid, .event_index = event,
        .has_suspend = (uint8_t)has_suspend, .suspend = suspend,
        .has_rc = (uint8_t)has_rc, .rc = rc,
    };
}
static void reset(const struct p282_trace_record *rows, size_t count,
                  struct p282_trace_control *control) {
    memset(&g_p311_early, 0, sizeof(g_p311_early));
    memset(fixture, 0, sizeof(fixture));
    memcpy(fixture, rows, count * sizeof(rows[0]));
    fixture_count = count;
    memset(control, 0, sizeof(*control));
    control->event_count = 30U;
    for (size_t index = 0; index < count; ++index)
        ++control->profile_hits[rows[index].event_index];
}
static int details(uint16_t expected_a, uint16_t expected_b) {
    uint16_t a = 0, b = 0;
    if (p311_first_detail(&a) != 0 || p311_summary_detail(0U, &b) != 0)
        return 1;
    return a == expected_a && b == expected_b ? 0 : 2;
}
int main(void) {
    struct p282_trace_control control;
    static const struct p282_trace_record probe[] = {
        { .pid=1, .event_index=0 },
        { .pid=1, .event_index=6, .has_rc=1 },
        { .pid=1, .event_index=7, .has_rc=1 },
        { .pid=1, .event_index=8, .has_rc=1 },
        { .pid=1, .event_index=9, .has_rc=1 },
        { .pid=1, .event_index=1, .has_rc=1 },
        { .pid=2, .event_index=2 },
        { .pid=2, .event_index=3, .has_rc=1 },
    };
    reset(probe, sizeof(probe)/sizeof(probe[0]), &control);
    if (p311_parse_early_trace(&control) != 0 || details(0xd00U, 0x404cU)) return 10;

    struct p282_trace_record prepare_fail[7];
    memcpy(prepare_fail, probe, sizeof(prepare_fail));
    prepare_fail[1].rc = -5;
    prepare_fail[2] = probe[3];
    prepare_fail[3] = probe[4];
    prepare_fail[4] = probe[5];
    prepare_fail[5] = probe[6];
    prepare_fail[6] = probe[7];
    reset(prepare_fail, 7U, &control);
    long prepare_fail_rc = p311_parse_early_trace(&control);
    int prepare_fail_detail = prepare_fail_rc == 0 ? details(0xd12U, 0x404cU) : -1;
    if (prepare_fail_rc != 0 || prepare_fail_detail != 0) return 20;

    static const struct p282_trace_record suspend[] = {
        { .pid=1, .event_index=0 }, { .pid=1, .event_index=1, .has_rc=1 },
        { .pid=7, .event_index=4, .has_suspend=1, .suspend=0 },
        { .pid=7, .event_index=24, .has_rc=1 },
        { .pid=7, .event_index=25, .has_rc=1 },
        { .pid=7, .event_index=26, .has_rc=1 },
        { .pid=7, .event_index=27, .has_rc=1 },
        { .pid=7, .event_index=5, .has_rc=1 },
        { .pid=7, .event_index=2 }, { .pid=7, .event_index=3, .has_rc=1 },
    };
    reset(suspend, sizeof(suspend)/sizeof(suspend[0]), &control);
    if (p311_parse_early_trace(&control) != 0 || details(0xd00U, 0x4240U)) return 30;

    static const struct p282_trace_record no_clock[] = {
        { .pid=1, .event_index=0 }, { .pid=1, .event_index=1, .has_rc=1 },
        { .pid=2, .event_index=2 }, { .pid=2, .event_index=3, .has_rc=1 },
    };
    reset(no_clock, sizeof(no_clock)/sizeof(no_clock[0]), &control);
    if (p311_parse_early_trace(&control) != 0 || details(0xd51U, 0x44fcU)) return 40;

    struct p282_trace_record multiple[14];
    memcpy(multiple, probe, sizeof(probe));
    multiple[8] = row(2, 2, 0, 0, 0, 0);
    multiple[9] = row(2, 18, 0, 0, 1, 0);
    multiple[10] = row(2, 19, 0, 0, 1, 0);
    multiple[11] = row(2, 20, 0, 0, 1, 0);
    multiple[12] = row(2, 21, 0, 0, 1, 0);
    multiple[13] = row(2, 3, 0, 0, 1, 0);
    reset(multiple, 14U, &control);
    if (p311_parse_early_trace(&control) != 0 || details(0xd00U, 0x4114U)) return 50;

    struct p282_trace_record cfg[9];
    memcpy(cfg, probe, 5U * sizeof(probe[0]));
    cfg[5] = row(1, 10, 0, 0, 1, 0);
    cfg[6] = probe[5];
    cfg[7] = probe[6];
    cfg[8] = probe[7];
    reset(cfg, 9U, &control);
    if (p311_parse_early_trace(&control) != P311_DETAIL_EARLY_CFG_AHB_CONTRADICTION)
        return 60;

    reset(probe, sizeof(probe)/sizeof(probe[0]), &control);
    ++control.profile_hits[6];
    if (p311_parse_early_trace(&control) != P311_DETAIL_EARLY_PROFILE_RECORD_MISMATCH)
        return 70;

    struct p282_trace_record bad_suspend[sizeof(suspend)/sizeof(suspend[0])];
    memcpy(bad_suspend, suspend, sizeof(suspend));
    bad_suspend[2].suspend = 1;
    reset(bad_suspend, sizeof(bad_suspend)/sizeof(bad_suspend[0]), &control);
    if (p311_parse_early_trace(&control) != P311_DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION)
        return 80;

    printf("fixtures=8 prepare-failure-enable-absent=1 profile-equality=1\n");
    return 0;
}
'''
    )


def audit(root: Path) -> dict[str, object]:
    output = support._compile(  # noqa: SLF001
        _translation_unit(_runtime(root)), "p311-runtime-fixtures"
    )
    expected = "fixtures=8 prepare-failure-enable-absent=1 profile-equality=1\n"
    if output != expected:
        raise FixtureError(f"P3.11 runtime fixture output differs: {output!r}")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "fixture_count": 8,
        "materialized_runtime_functions_executed": True,
        "prepare_failure_enable_absent_expected": True,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
