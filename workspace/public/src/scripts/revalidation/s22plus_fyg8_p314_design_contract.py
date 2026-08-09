#!/usr/bin/env python3
"""Machine contract for the P3.14 source-normalized cycle successor design."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import s22plus_fyg8_p313_successor_hazard_contract as predecessor


SCHEMA = "s22plus_fyg8_p314_design_requirements_v1"
ARTIFACT_SCHEMA = "s22plus_fyg8_p314_qualification_closure_v1"
VERDICT = "DESIGN_COMPLETE_P314_SOURCE_NORMALIZED_CYCLE_HOST_ONLY"
STATUS = "design-complete-implementation-not-started"

STOP_CLEAN_RECORDS = 14
FINAL_CLEAN_RECORDS = 41
FINAL_DRIFT_RECORDS = 49
RECORD_CAPACITY = 64
OVERFLOW_FIXTURE_RECORDS = 65

SUCCESSOR_A_OUTPUTS = predecessor.INHERITED_A_OUTPUT_COUNT
SUCCESSOR_B_OUTPUTS = predecessor.MINIMUM_SUCCESSOR_B_OUTPUT_COUNT
MATRIX_B_VALUES = predecessor.MINIMUM_MATRIX_B_VALUE_COUNT
MATRIX_POSITIONS = predecessor.POSITION_COUNT
MATRIX_CELLS = predecessor.MINIMUM_MATRIX_CELL_COUNT

DIAGNOSTIC_CONTINUE_ENABLED = False

PACKAGING_WIRING_PROOFS = (
    "requirements_hash_in_source_closure",
    "validator_called_before_packaging",
    "validator_return_controls_package_creation",
    "missing_or_failed_artifact_blocks_packaging",
    "validator_failure_negative_fixture",
    "validated_artifact_receipted_by_qualification",
    "receipt_binds_requirements_and_artifact_sha256",
    "source_call_graph_reviewed",
)


class P314DesignError(ValueError):
    pass


def requirements() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "predecessor_requirements_sha256": predecessor.requirements_sha256(),
        "runtime": {
            "stop_expected_counts": predecessor.STOP_EXPECTED_COUNTS,
            "final_expected_counts": predecessor.FINAL_EXPECTED_COUNTS,
            "stop_clean_records": STOP_CLEAN_RECORDS,
            "final_clean_records": FINAL_CLEAN_RECORDS,
            "final_drift_records": FINAL_DRIFT_RECORDS,
            "record_capacity": RECORD_CAPACITY,
            "overflow_fixture_records": OVERFLOW_FIXTURE_RECORDS,
            "normalize_expected_counts_before_excess": True,
            "validate_every_complete_pair_return": True,
            "zero_excess_is_clean": True,
            "nonzero_excess_uses_pair_mask": True,
            "legacy_0x6712_emit_sites_zero": True,
            "pair_mask_requires_integrity_clean_counts": True,
            "pair_mask_does_not_claim_exclusive_drift": True,
            "diagnostic_continue_enabled": DIAGNOSTIC_CONTINUE_ENABLED,
            "all_genuine_contradictions_stop": True,
            "stop_drift_checked_before_restart": True,
            "trace_event_inventory_unchanged": True,
            "checkpoint_positions_unchanged": True,
        },
        "carrier": {
            "a_outputs": SUCCESSOR_A_OUTPUTS,
            "successor_b_outputs": SUCCESSOR_B_OUTPUTS,
            "matrix_b_values": MATRIX_B_VALUES,
            "progress_zero_outputs": predecessor.PROGRESS_ZERO_OUTPUT_COUNT,
            "positions": MATRIX_POSITIONS,
            "matrix_cells": MATRIX_CELLS,
            "pair_mask_detail_min": predecessor.PAIR_MASK_DETAIL_MIN,
            "pair_mask_detail_max": predecessor.PAIR_MASK_DETAIL_MAX,
            "legacy_0x6712_decode_only": True,
            "real_process_v2_adapter_required": True,
            "persistence_round_trip_required": True,
        },
        "packaging_wiring": {
            "status": "required-not-satisfied",
            "required_proofs": list(PACKAGING_WIRING_PROOFS),
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "module_plan_unchanged": True,
            "carrier_size_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_required": False,
            "userspace_rebuild_and_repackage_required": True,
        },
    }


def requirements_sha256() -> str:
    encoded = json.dumps(
        requirements(), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise P314DesignError(f"{label} differs")


def validate_qualification_artifact(value: dict[str, Any]) -> dict[str, Any]:
    """Reject a future P3.14 qualification missing design or wiring proof."""

    _require_equal(value.get("schema"), ARTIFACT_SCHEMA, "artifact schema")
    _require_equal(
        value.get("design_requirements_sha256"),
        requirements_sha256(),
        "design requirements receipt",
    )
    predecessor_closure = value.get("successor_hazard_closure")
    if not isinstance(predecessor_closure, dict):
        raise P314DesignError("predecessor hazard closure missing")
    try:
        predecessor_result = predecessor.validate_successor_artifact(
            predecessor_closure
        )
    except predecessor.SuccessorHazardError as exc:
        raise P314DesignError("predecessor hazard closure differs") from exc

    runtime = value.get("runtime")
    if not isinstance(runtime, dict):
        raise P314DesignError("runtime proof missing")
    for key, expected in (
        ("stop_expected_counts", predecessor.STOP_EXPECTED_COUNTS),
        ("final_expected_counts", predecessor.FINAL_EXPECTED_COUNTS),
        ("stop_clean_records", STOP_CLEAN_RECORDS),
        ("final_clean_records", FINAL_CLEAN_RECORDS),
        ("final_drift_records", FINAL_DRIFT_RECORDS),
        ("record_capacity", RECORD_CAPACITY),
        ("overflow_fixture_records", OVERFLOW_FIXTURE_RECORDS),
        ("generated_from_materialized_source", True),
        ("all_complete_pair_returns_validated", True),
        ("expected_counts_normalized_before_excess", True),
        ("nonzero_excess_pair_mask_terminal", True),
        ("legacy_0x6712_emit_sites_zero", True),
        ("pair_mask_requires_integrity_clean_counts", True),
        ("pair_mask_does_not_claim_exclusive_drift", True),
        ("diagnostic_continue_enabled", False),
        ("unclassified_contradiction_stops", True),
        ("stop_drift_checked_before_restart", True),
        ("trace_event_inventory_unchanged", True),
        ("checkpoint_positions_unchanged", True),
        ("verified", True),
    ):
        _require_equal(runtime.get(key), expected, f"runtime {key}")

    carrier = value.get("carrier")
    if not isinstance(carrier, dict):
        raise P314DesignError("carrier proof missing")
    for key, expected in (
        ("a_outputs", SUCCESSOR_A_OUTPUTS),
        ("successor_b_outputs", SUCCESSOR_B_OUTPUTS),
        ("matrix_b_values", MATRIX_B_VALUES),
        ("progress_zero_outputs", predecessor.PROGRESS_ZERO_OUTPUT_COUNT),
        ("positions", MATRIX_POSITIONS),
        ("matrix_cells", MATRIX_CELLS),
        ("pair_mask_detail_min", predecessor.PAIR_MASK_DETAIL_MIN),
        ("pair_mask_detail_max", predecessor.PAIR_MASK_DETAIL_MAX),
        ("generated_from_actual_encoders", True),
        ("accept_reject_from_runtime_emit_sites", True),
        ("real_process_v2_adapter_round_trip", True),
        ("persistence_round_trip", True),
        ("legacy_0x6712_decode_only", True),
        ("verified", True),
    ):
        _require_equal(carrier.get(key), expected, f"carrier {key}")

    packaging = value.get("packaging_wiring")
    if not isinstance(packaging, dict):
        raise P314DesignError("packaging wiring proof missing")
    for key in PACKAGING_WIRING_PROOFS:
        _require_equal(packaging.get(key), True, f"packaging wiring {key}")
    _require_equal(packaging.get("verified"), True, "packaging wiring verdict")

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict):
        raise P314DesignError("artifact identity proof missing")
    for key, expected in (
        ("fixed_image_unchanged", True),
        ("kernel_hooks_unchanged", True),
        ("module_plan_unchanged", True),
        ("carrier_size_unchanged", True),
        ("rollback_unchanged", True),
        ("full_lto_performed", False),
        ("userspace_builds_reproducible", True),
        ("packages_reproducible", True),
        ("verified", True),
    ):
        _require_equal(artifacts.get(key), expected, f"artifact proof {key}")

    _require_equal(value.get("verified"), True, "qualification verdict")
    return {
        "schema": ARTIFACT_SCHEMA,
        "design_requirements_sha256": requirements_sha256(),
        "predecessor_requirements_sha256": predecessor_result[
            "requirements_sha256"
        ],
        "matrix_cells": MATRIX_CELLS,
        "diagnostic_continue_enabled": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "verdict": VERDICT,
                "requirements_sha256": requirements_sha256(),
                "requirements": requirements(),
            },
            indent=2,
            sort_keys=True,
        )
    )
