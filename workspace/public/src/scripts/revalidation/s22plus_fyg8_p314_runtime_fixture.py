#!/usr/bin/env python3
"""Compile the materialized P3.14 cycle parser against boundary fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p313_runtime_fixture as parent_fixture
import s22plus_fyg8_p314_generator as generator


SCHEMA = "s22plus_fyg8_p314_runtime_fixture_v1"
VERDICT = "PASS_P314_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"


class FixtureError(ValueError):
    pass


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _replace_definition(source: bytes, marker: bytes, replacement: bytes) -> bytes:
    old = support._definition(source, marker)  # noqa: SLF001
    if source.count(old) != 1:
        raise FixtureError(f"P3.14 fixture definition differs: {marker!r}")
    return source.replace(old, replacement, 1)


def _cycle_tu(root: Path, runtime: bytes, descriptor: bytes) -> bytes:
    p313_runtime = (
        root
        / "workspace/private/outputs/s22plus_fyg8_p313/intent/materialized-sources"
        / "s22plus_fyg8_p290_e3_runtime.inc.c"
    ).read_bytes()
    source = parent_fixture._cycle_tu(p313_runtime, descriptor)  # noqa: SLF001
    source = source[: source.rfind(b"int main(void) {")]
    source = source.replace(
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
        b"#define P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION 0x671fU\n"
        b"static const uint8_t p314_stop_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 0U, 1U, 0U, 2U, 0U, 1U, 0U, 0U, 0U,\n"
        b"};\n"
        b"static const uint8_t p314_final_expected[P314_PAIR_MASK_BITS] = {\n"
        b"    1U, 1U, 1U, 1U, 2U, 2U, 1U, 1U, 1U, 1U,\n"
        b"};\n",
        1,
    )
    source = _replace_definition(
        source,
        b"struct p313_cycle_pair {\n",
        support._struct(runtime, b"struct p313_cycle_pair {\n"),  # noqa: SLF001
    )
    for marker in (
        b"static long p313_pair_collect(\n",
        b"static long p313_parse_cycle(\n",
    ):
        source = _replace_definition(
            source, marker, support._definition(runtime, marker)  # noqa: SLF001
        )
    return source + br'''
static void fill_p314_clean(void) {
    fill_clean();
    entry_suspend(6U, 9, 1); returned(7U, 9, 0);
    entry_suspend(6U, 9, 0); returned(7U, 9, 0);
}
static void fill_p314_stop(void) {
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
    entry_suspend(6U, pid, 1);
    returned(7U, pid, 0);
    returned(15U, pid, 0);
}
static void append_pair(unsigned int bit, int rc) {
    long pid = 9;
    switch (bit) {
    case 0U: entry_on(0U, pid, 0); returned(1U, pid, rc); break;
    case 1U: entry_on(0U, pid, 1); returned(1U, pid, rc); break;
    case 2U: push(2U, pid); returned(3U, pid, rc); break;
    case 3U: push(4U, pid); returned(5U, pid, rc); break;
    case 4U: entry_suspend(6U, pid, 1); returned(7U, pid, rc); break;
    case 5U: entry_suspend(6U, pid, 0); returned(7U, pid, rc); break;
    case 6U: entry_on(8U, pid, 0); returned(9U, pid, rc); break;
    case 7U: entry_on(8U, pid, 1); returned(9U, pid, rc); break;
    case 8U: push(10U, pid); returned(11U, pid, rc); break;
    case 9U: push(12U, pid); returned(13U, pid, rc); break;
    default: break;
    }
}
int main(void) {
    (void)profile_from_result;
    (void)p313_cycle_profile_relations;
    struct p282_trace_control control = {0};
    struct p313_cycle_result result = {0};

    fill_p314_stop();
    if (fixture_count != P314_STOP_CLEAN_RECORDS
        || p313_parse_cycle(&control, &result, P314_PHASE_STOP) != 0
        || result.total_records != 14U || result.drift_mask != 0U
        || result.record_hits[6] != 2U || result.record_hits[7] != 2U)
        return 10;

    fill_p314_clean();
    if (fixture_count != P314_FINAL_CLEAN_RECORDS
        || p313_parse_cycle(&control, &result, P314_PHASE_FINAL) != 0
        || result.total_records != 41U || result.drift_mask != 0U
        || !result.phy_suspend_off.all_returns_zero
        || !result.phy_suspend_on.all_returns_zero)
        return 11;

    fill_p314_clean(); append_bounded_drift();
    if (fixture_count != P314_FINAL_DRIFT_RECORDS
        || p313_parse_cycle(&control, &result, P314_PHASE_FINAL) != 0
        || result.total_records != 49U || result.drift_mask == 0U)
        return 12;

    for (unsigned int mask = 1U; mask <= 0x3ffU; ++mask) {
        fill_p314_clean();
        for (unsigned int bit = 0U; bit < 10U; ++bit) {
            if (mask & (1U << bit)) append_pair(bit, 0);
        }
        long rc = p313_parse_cycle(&control, &result, P314_PHASE_FINAL);
        if (rc != (long)(P314_PAIR_MASK_DETAIL_BASE + mask)) return 20;
    }

    fill_p314_clean(); append_pair(4U, -1);
    if (p313_parse_cycle(&control, &result, P314_PHASE_FINAL)
        != P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION) return 21;
    fill_p314_clean(); append_pair(0U, 1);
    if (p313_parse_cycle(&control, &result, P314_PHASE_FINAL)
        != P313_DETAIL_CYCLE_POSITIVE_RETURN) return 22;

    fill_p314_stop();
    push(17U, 9); returned(18U, 9, 0);
    if (p313_parse_cycle(&control, &result, P314_PHASE_STOP) != 0
        || (result.drift_mask & P313_DRIFT_PULLUP) == 0U) return 23;

    memset(fixture, 0, sizeof(fixture));
    fixture_count = 65U;
    if (p313_parse_cycle(&control, &result, P314_PHASE_FINAL)
        != P313_DETAIL_CYCLE_RECORD_OVERFLOW) return 24;

    printf("stop=14 clean=41 drift=49 masks=1023 overflow=65\n");
    return 0;
}
'''


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    descriptor = artifacts["trace_descriptor_header"]
    output = support._compile(  # noqa: SLF001
        _cycle_tu(root, runtime, descriptor), "p314-source-normalized-cycle"
    )
    expected = "stop=14 clean=41 drift=49 masks=1023 overflow=65\n"
    if output != expected:
        raise FixtureError(f"P3.14 runtime fixture differs: {output!r}")
    if runtime.count(b"return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;") != 0:
        raise FixtureError("P3.14 legacy 0x6712 emit site survived")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "stop_clean_records": 14,
        "final_clean_records": 41,
        "final_drift_records": 49,
        "overflow_fixture_records": 65,
        "pair_masks_exercised": 1023,
        "all_complete_pair_returns_validated": True,
        "legacy_0x6712_emit_sites_zero": True,
        "diagnostic_continue_enabled": False,
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
