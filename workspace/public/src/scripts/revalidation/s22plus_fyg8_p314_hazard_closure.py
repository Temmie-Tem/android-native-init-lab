#!/usr/bin/env python3
"""Aggregate pre-packaging P3.14 hazard proofs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p313_stop_multiplicity_audit as source_audit
import s22plus_fyg8_p314_cross_gate_audit as cross_gate
import s22plus_fyg8_p314_design_contract as design
import s22plus_fyg8_p314_runtime_fixture as runtime_fixture


SCHEMA = "s22plus_fyg8_p314_hazard_closure_v1"
VERDICT = "PASS_P314_PREPACKAGING_HAZARD_CLOSURE_HOST_ONLY"


class HazardClosureError(ValueError):
    pass


def audit(
    root: Path | None = None,
    *,
    matrix_result: dict[str, Any] | None = None,
    adapter_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import s22plus_fyg8_p314_matrix_fixture as matrix_fixture
    import s22plus_fyg8_p314_process_v2_adapter_fixture as adapter_fixture

    root = (root or Path(__file__).resolve().parents[5]).resolve()
    source = source_audit.audit(root)
    runtime = runtime_fixture.audit(root)
    gates = cross_gate.audit(root)
    matrix = matrix_result or matrix_fixture.audit(root)
    adapter = adapter_result or adapter_fixture.audit(root)
    kernel = source.get("kernel_source_contract", {})
    if (
        source.get("verified") is not True
        or kernel.get("source_forced_stop_pair_count") != 2
        or kernel.get("source_forced_restart_pair_count") != 2
        or runtime.get("verified") is not True
        or gates.get("verified") is not True
        or gates.get("a_outputs_validated") != 126
        or gates.get("b_outputs_validated") != 2222
        or gates.get("pair_masks_validated") != 1023
        or matrix.get("matrix_cells") != 251_450
        or matrix.get("real_process_v2_adapter_round_trip") is not True
        or matrix.get("verified") is not True
        or adapter.get("verified") is not True
    ):
        raise HazardClosureError("P3.14 prepackaging proof differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "design_requirements_sha256": design.requirements_sha256(),
        "source_derived_pair_geometry": {
            "stop_expected_counts": design.predecessor.STOP_EXPECTED_COUNTS,
            "final_expected_counts": design.predecessor.FINAL_EXPECTED_COUNTS,
            "stop_callers": kernel["stop_suspend_callers"],
            "restart_callers": kernel["restart_suspend_callers"],
            "shared_hs_phy": kernel[
                "shared_hs_phy_from_child_usb_phy_phandle_zero"
            ],
            "verified": True,
        },
        "runtime": runtime,
        "cross_gate": gates,
        "matrix_fixture": matrix,
        "process_v2_adapter_fixture": adapter,
        "packaging_wiring_status": "pending-real-builder-qualification",
        "device_contact": False,
        "fixed_image_changed": False,
        "full_lto_required": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
