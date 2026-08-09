#!/usr/bin/env python3
"""Aggregate executable P3.13 observer-hazard closure proofs."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import s22plus_fyg8_p313_cross_gate_audit as cross_gate
import s22plus_fyg8_p313_generator as generator
import s22plus_fyg8_p313_runtime_fixture as runtime_fixture
import s22plus_fyg8_p313_telemetry_spec as telemetry


SCHEMA = "s22plus_fyg8_p313_hazard_closure_v1"
VERDICT = "PASS_P313_OBSERVER_HAZARD_CLOSURE_HOST_ONLY"


class HazardClosureError(ValueError):
    pass


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _positions(runtime: bytes, header: bytes) -> dict[str, Any]:
    rows = re.findall(
        rb"^#define (S22_P313_POSITION_[A-Z0-9_]+) ([0-9]+)U$",
        header,
        re.MULTILINE,
    )
    values = [(name.decode("ascii"), int(value)) for name, value in rows]
    expected = list(range(84, 107))
    if (
        len(values) != len(expected)
        or [value for _name, value in values] != expected
        or any(
            runtime.count(name.encode("ascii"))
            != (0 if value in (105, 106) else 1)
            for name, value in values
        )
    ):
        raise HazardClosureError("P3.13 stage/item position closure differs")
    return {
        "position_count": len(values),
        "first": values[0][1],
        "last": values[-1][1],
        "pre_pair_runtime_reference_count_each": 1,
        "pair_positions_publisher_bound": True,
        "verified": True,
    }


def _direct_window(runtime: bytes, descriptor: bytes) -> dict[str, Any]:
    requirements = {
        b"#define P282_BIND_EVENT_COUNT 15U\n": descriptor,
        b"#define P300_PREFIX_RECORD_CAPACITY 32U\n": runtime,
        b'"traceoff:1 if type == 2\\n"': runtime,
        b'"!traceoff:1 if type == 2\\n"': runtime,
        b'"/sys/kernel/tracing/instances/p282/options/overwrite"': runtime,
        b"P313_DIRECT_PREFIX_CLEAN 10U": runtime,
        b"P313_DIRECT_PREFIX_CONTRADICTION_MIN 23U": runtime,
    }
    if any(payload.count(token) < 1 for token, payload in requirements.items()):
        raise HazardClosureError("P3.13 direct-window integrity token differs")
    if runtime.count(b"event_count == P282_BIND_EVENT_COUNT") != 2:
        raise HazardClosureError("P3.13 direct-only overwrite gate differs")
    publish = runtime.find(b"p294_publish_final_pair(first_detail, terminal_detail)")
    banner = runtime.find(b"p260_write_banner(tty_fd)", publish)
    if publish < 0 or banner <= publish:
        raise HazardClosureError("P3.13 final pair does not precede banner")
    if not (
        telemetry.DIRECT_CLEAN_PREFIX < telemetry.DIRECT_PREFIX_CAPACITY
        and telemetry.DIRECT_DRIFT_PREFIX_MAX < telemetry.DIRECT_PREFIX_CAPACITY
        and telemetry.DIRECT_CONTRADICTION_PREFIX_MIN
        < telemetry.DIRECT_PREFIX_CAPACITY
    ):
        raise HazardClosureError("P3.13 direct prefix headroom differs")
    return {
        "event_count": telemetry.DIRECT_EVENT_COUNT,
        "prefix_capacity": telemetry.DIRECT_PREFIX_CAPACITY,
        "clean_prefix": telemetry.DIRECT_CLEAN_PREFIX,
        "drift_prefix_max": telemetry.DIRECT_DRIFT_PREFIX_MAX,
        "contradiction_prefix_min": telemetry.DIRECT_CONTRADICTION_PREFIX_MIN,
        "connect_done_traceoff": True,
        "overwrite_enabled_for_direct_only": True,
        "final_pair_before_banner": True,
        "verified": True,
    }


def audit(root: Path | None = None) -> dict[str, Any]:
    # Kept lazy so the Process-v2 evidence adapter can import the lightweight
    # P3.13 overlay contract without recursively importing the live adapter.
    import s22plus_fyg8_p313_guard_lifetime_fixture as guard_fixture

    root = (root or Path(__file__).resolve().parents[5]).resolve()
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    descriptor = artifacts["trace_descriptor_header"]
    cross = cross_gate.audit(root)
    fixture = runtime_fixture.audit(root)
    guard = guard_fixture.audit()
    telemetry_result = telemetry.validate()
    cycle_start = runtime.index(b"static long p313_parse_cycle(")
    cycle_end = runtime.index(b"static long p313_cycle_close_partial(", cycle_start)
    cycle_parser = runtime[cycle_start:cycle_end]
    if (
        cross.get("verdict") != cross_gate.VERDICT
        or fixture.get("verdict") != runtime_fixture.VERDICT
        or guard.get("verdict") != guard_fixture.VERDICT
        or telemetry_result.get("verified") is not True
        or cycle_parser.count(
            b"profile_hits[index] < result->record_hits[index]"
        ) != 1
        or b"profile_hits[index] != result->record_hits[index]" in cycle_parser
        or telemetry.CYCLE_DRIFT_RECORDS >= telemetry.RECORD_CAPACITY
        or telemetry.CYCLE_OVERFLOW_RECORDS <= telemetry.RECORD_CAPACITY
    ):
        raise HazardClosureError("P3.13 executable hazard proof differs")
    positions = _positions(runtime, artifacts["p290_position_header"])
    direct = _direct_window(runtime, descriptor)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "hazards": {
            "p304_stage_item_extent": positions,
            "p308_tracefs_register_abi_inherited_from_p312": True,
            "p310_carrier_v2_json_and_foreign_count_round_trip": {
                "a_outputs_validated": cross["a_outputs_validated"],
                "b_outputs_validated": cross["b_outputs_validated"],
                "retained_pair_round_trip": cross["retained_pair_round_trip"],
                "foreign_count_zero": cross["foreign_count_zero"],
                "verified": True,
            },
            "p311_profile_relation": {
                "profile_hits_greater_or_equal_records": True,
                "profile_deficit_rejected": True,
                "nmissed_and_ring_loss_remain_strict": True,
                "verified": True,
            },
            "p313_role_and_cycle_runtime": fixture,
            "p313_direct_window": direct,
            "p313_guard_lifetime": guard,
        },
        "record_budget": {
            "role_events": telemetry.ROLE_EVENT_COUNT,
            "direct_events": telemetry.DIRECT_EVENT_COUNT,
            "cycle_events": telemetry.CYCLE_EVENT_COUNT,
            "cycle_clean_records": telemetry.CYCLE_CLEAN_RECORDS,
            "cycle_drift_records": telemetry.CYCLE_DRIFT_RECORDS,
            "cycle_overflow_fixture_records": telemetry.CYCLE_OVERFLOW_RECORDS,
            "record_capacity": telemetry.RECORD_CAPACITY,
            "source_derived_not_p312_measured": True,
            "verified": True,
        },
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (HazardClosureError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
