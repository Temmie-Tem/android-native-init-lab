#!/usr/bin/env python3
"""Execute the P3.12 materialized profile relation on representative records."""

from __future__ import annotations

import json
from pathlib import Path

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p311_runtime_fixture as inherited
import s22plus_fyg8_p312_generator as generator
import s22plus_fyg8_p312_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p312_runtime_fixture_v1"
VERDICT = "PASS_P312_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
FixtureError = support.AuditError


def _runtime(root: Path) -> bytes:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )["p290_e3_runtime_include"]


def _translation_unit(runtime: bytes) -> bytes:
    value = inherited._translation_unit(runtime)  # noqa: SLF001
    old = br'''    reset(probe, sizeof(probe)/sizeof(probe[0]), &control);
    ++control.profile_hits[6];
    if (p311_parse_early_trace(&control) != P311_DETAIL_EARLY_PROFILE_RECORD_MISMATCH)
        return 70;
'''
    new = br'''    reset(probe, sizeof(probe)/sizeof(probe[0]), &control);
    ++control.profile_hits[6];
    if (p311_parse_early_trace(&control) != 0 || details(0xd00U, 0x404cU))
        return 70;

    reset(probe, sizeof(probe)/sizeof(probe[0]), &control);
    --control.profile_hits[6];
    if (p311_parse_early_trace(&control) != P311_DETAIL_EARLY_PROFILE_RECORD_MISMATCH)
        return 71;
'''
    if value.count(old) != 1:
        raise FixtureError("P3.12 inherited profile fixture anchor differs")
    value = value.replace(old, new, 1)
    value = value.replace(
        b'printf("fixtures=8 prepare-failure-enable-absent=1 profile-equality=1\\n");',
        b'printf("fixtures=9 prepare-failure-enable-absent=1 profile-lower-bound=1\\n");',
        1,
    )
    return value


def audit(root: Path) -> dict[str, object]:
    output = support._compile(_translation_unit(_runtime(root)), "p312-runtime-fixtures")  # noqa: SLF001
    expected = "fixtures=9 prepare-failure-enable-absent=1 profile-lower-bound=1\n"
    if output != expected:
        raise FixtureError(f"P3.12 runtime fixture output differs: {output!r}")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "fixture_count": 9,
        "materialized_runtime_functions_executed": True,
        "profile_excess_accepted": True,
        "profile_below_records_rejected": True,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
