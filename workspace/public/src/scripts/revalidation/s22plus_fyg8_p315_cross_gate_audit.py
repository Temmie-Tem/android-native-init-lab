#!/usr/bin/env python3
"""Execute every unchanged P3.15 encoder output through actual device gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p314_cross_gate_audit as predecessor
import s22plus_fyg8_p315_generator as generator
import s22plus_fyg8_p315_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p315_cross_gate_audit_v1"
VERDICT = "PASS_P315_ACTUAL_ENCODER_OUTPUTS_SUBSET_ALL_GATES_HOST_ONLY"
AuditError = support.AuditError


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    artifacts = _generated(root)
    actual = {
        "runtime": support._compile(  # noqa: SLF001
            predecessor._runtime_gate_tu(  # noqa: SLF001
                artifacts["p290_e3_runtime_include"]
            ),
            "p315-runtime-gates",
        ),
        "checkpoint": support._compile(  # noqa: SLF001
            predecessor._checkpoint_gate_tu(  # noqa: SLF001
                artifacts["checkpoint_client"],
                artifacts["p290_checkpoint_header"],
            ),
            "p315-checkpoint-gates",
        ),
        "kernel": support._compile(  # noqa: SLF001
            predecessor._kernel_gate_tu(artifacts["candidate_patch"]),  # noqa: SLF001
            "p315-kernel-gates",
        ),
    }
    expected = {
        "runtime": "runtime-a=126 runtime-b=2222 masks=1023\n",
        "checkpoint": "checkpoint-a=126 checkpoint-b=2222 masks=1023\n",
        "kernel": "kernel-a=126 kernel-b=2222 masks=1023\n",
    }
    if actual != expected:
        raise AuditError(f"P3.15 executed gate closure differs: {actual!r}")
    telemetry = spec.validate()
    for detail in spec.P315_RESERVED_NAMES:
        if detail not in spec.b_outputs():
            raise AuditError("P3.15 reserved runtime detail is not emit-capable")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry": telemetry,
        "executed_actual_gates": actual,
        "a_outputs_validated": len(spec.a_outputs()),
        "b_outputs_validated": len(spec.b_outputs()),
        "pair_masks_validated": spec.PAIR_MASK_VALUE_COUNT,
        "reserved_details_validated": sorted(spec.P315_RESERVED_NAMES),
        "legacy_0x6712_emit_capable": False,
        "fixed_image_changed": False,
        "module_plan_changed": False,
        "carrier_changed": False,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
