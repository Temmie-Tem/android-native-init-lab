#!/usr/bin/env python3
"""Aggregate the four executable P3.15 prepackaging proofs."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_packaging_wiring_audit as packaging_wiring
import s22plus_fyg8_p315_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_p315_restart_source_geometry_audit as source_geometry
import s22plus_fyg8_p315_runtime_fixture as runtime_fixture


SCHEMA = design.ARTIFACT_SCHEMA
VERDICT = design.VERDICT


class HazardClosureError(ValueError):
    pass


def _proof_result(
    name: str, supplied: dict[str, Any] | None, root: Path
) -> dict[str, Any]:
    if supplied is None:
        modules = {
            "restart_source_geometry": source_geometry,
            "runtime_wrapper_fixture": runtime_fixture,
            "process_v2_adapter_fixture": adapter_fixture,
            "packaging_wiring_audit": packaging_wiring,
        }
        supplied = modules[name].audit(root)
    specification = design.PROOF_ARTIFACT_SPECS[name]
    if (
        supplied.get("schema") != specification["schema"]
        or supplied.get("verdict") != specification["verdict"]
        or supplied.get("requirements_sha256") != design.requirements_sha256()
        or supplied.get("verified") is not True
    ):
        raise HazardClosureError(f"P3.15 {name} proof differs")
    return supplied


def audit(
    root: Path | None = None,
    *,
    source_result: dict[str, Any] | None = None,
    runtime_result: dict[str, Any] | None = None,
    adapter_result: dict[str, Any] | None = None,
    packaging_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    results = {
        "restart_source_geometry": _proof_result(
            "restart_source_geometry", source_result, root
        ),
        "runtime_wrapper_fixture": _proof_result(
            "runtime_wrapper_fixture", runtime_result, root
        ),
        "process_v2_adapter_fixture": _proof_result(
            "process_v2_adapter_fixture", adapter_result, root
        ),
        "packaging_wiring_audit": _proof_result(
            "packaging_wiring_audit", packaging_result, root
        ),
    }
    requirements = design.requirements()
    value: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "verified": True,
    }
    for section in (
        "historical_authority",
        "phase_geometry",
        "restart_source_geometry",
        "restart_completion",
        "restart_result_classification",
        "live_snapshot",
        "coverage",
        "time_budget",
        "host_observer",
        "artifacts",
        "packaging",
    ):
        proof = deepcopy(requirements[section])
        proof["verified"] = True
        value[section] = proof
    value["proof_artifacts"] = {
        name: design.proof_receipt(root, name, result)
        for name, result in results.items()
    }
    design.validate_successor_artifact(value)
    return value


def main() -> int:
    try:
        result = audit()
    except (HazardClosureError, design.P315DesignError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
