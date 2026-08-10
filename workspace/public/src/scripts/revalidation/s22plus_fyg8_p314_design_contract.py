#!/usr/bin/env python3
"""Machine contract for the P3.14 source-normalized cycle successor design."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p313_successor_hazard_contract as predecessor


SCHEMA = "s22plus_fyg8_p314_design_requirements_v1"
ARTIFACT_SCHEMA = "s22plus_fyg8_p314_qualification_closure_v1"
PREPACKAGING_ARTIFACT_SCHEMA = (
    "s22plus_fyg8_p314_prepackaging_closure_v1"
)
VERDICT = "DESIGN_COMPLETE_P314_SOURCE_NORMALIZED_CYCLE_HOST_ONLY"
STATUS = "implementation-contract-active"
PREPACKAGING_VERDICT = "PASS_P314_PREPACKAGING_GATE_HOST_ONLY"
QUALIFICATION_VERDICT = "PASS_P314_FINAL_QUALIFICATION_HOST_ONLY"
BUILDER_PATH = Path(
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_fyg8_p314_candidate.py"
)

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

PREPACKAGING_WIRING_PROOFS = (
    "requirements_hash_in_source_closure",
    "validator_called_before_packaging",
    "validator_return_controls_package_creation",
    "missing_or_failed_artifact_blocks_packaging",
    "validator_failure_negative_fixture",
    "semantic_mutation_fixture_passed",
    "source_call_graph_reviewed",
)
FINAL_QUALIFICATION_PROOFS = (
    "validated_artifact_receipted_by_qualification",
    "receipt_binds_requirements_and_artifact_sha256",
    "embedded_prepack_receipt_rebound",
)
PACKAGING_WIRING_PROOFS = (
    *PREPACKAGING_WIRING_PROOFS,
    *FINAL_QUALIFICATION_PROOFS,
)


class P314DesignError(ValueError):
    pass


NEGATIVE_PACKAGING_FIXTURE = {
    "missing_closure_blocks_package": True,
    "invalid_closure_blocks_package": True,
    "parent_packager_call_count": 0,
    "package_output_count": 0,
    "verified": True,
}

SEMANTIC_MUTATION_FIXTURE = {
    "verdict_mutation_blocks_package": True,
    "source_receipt_mutation_blocks_package": True,
    "call_graph_mutation_blocks_package": True,
    "matrix_sha256_mutation_blocks_package": True,
    "parent_packager_call_count": 0,
    "package_output_count": 0,
    "verified": True,
}

RECEIPT_REBIND_FIXTURE = {
    "embedded_prepack_mutation_rejected": True,
    "declared_receipt_mutation_rejected": True,
    "verified": True,
}


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
            "prepackaging_required_proofs": list(
                PREPACKAGING_WIRING_PROOFS
            ),
            "final_required_proofs": list(FINAL_QUALIFICATION_PROOFS),
            "two_phase_validation_required": True,
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


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise P314DesignError(f"{label} keys differ")


def artifact_receipt(value: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("ascii") + b"\n"
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def builder_call_graph(root: Path) -> dict[str, Any]:
    path = root / BUILDER_PATH
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path.as_posix())
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "build_candidate"
        ),
        None,
    )
    if function is None:
        raise P314DesignError("P3.14 builder entrypoint is missing")
    calls: dict[str, list[int]] = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        parts: list[str] = []
        target: ast.expr = node.func
        while isinstance(target, ast.Attribute):
            parts.append(target.attr)
            target = target.value
        if isinstance(target, ast.Name):
            parts.append(target.id)
        calls.setdefault(".".join(reversed(parts)), []).append(node.lineno)
    validation = calls.get("design.validate_prepackaging_artifact", [])
    package = calls.get("parent.parent.base.build_candidate", [])
    if (
        len(validation) != 1
        or len(package) != 1
        or validation[0] >= package[0]
        or source.count("design.validate_prepackaging_artifact") != 1
    ):
        raise P314DesignError("P3.14 validator-to-packager call graph differs")
    return {
        "builder": BUILDER_PATH.as_posix(),
        "validator_line": validation[0],
        "package_line": package[0],
        "validator_precedes_package": True,
        "validator_return_controls_package_creation": True,
        "verified": True,
    }


def bound_prepackaging_authority(
    source_contract: dict[str, Any], call_graph: dict[str, Any]
) -> dict[str, Any]:
    receipts = source_contract.get("source_receipts")
    matrix = source_contract.get("matrix_fixture")
    if not isinstance(receipts, dict) or not receipts:
        raise P314DesignError("P3.14 source receipt authority missing")
    if not isinstance(matrix, dict):
        raise P314DesignError("P3.14 matrix authority missing")
    matrix_sha256 = matrix.get("matrix_sha256")
    if not isinstance(matrix_sha256, str) or len(matrix_sha256) != 64:
        raise P314DesignError("P3.14 matrix authority receipt differs")
    for key, receipt in receipts.items():
        if (
            not isinstance(key, str)
            or not isinstance(receipt, dict)
            or set(receipt) != {"size", "sha256"}
            or not isinstance(receipt.get("size"), int)
            or receipt["size"] < 0
            or not isinstance(receipt.get("sha256"), str)
            or len(receipt["sha256"]) != 64
        ):
            raise P314DesignError("P3.14 source receipt authority differs")
    return {
        "source_receipts": receipts,
        "matrix_sha256": matrix_sha256,
        "call_graph": call_graph,
    }


def prepackaging_authority(
    root: Path, source_contract: dict[str, Any]
) -> dict[str, Any]:
    return bound_prepackaging_authority(
        source_contract, builder_call_graph(root)
    )


def validate_prepackaging_artifact(
    value: dict[str, Any], *, authority: dict[str, Any]
) -> dict[str, Any]:
    """Reject packaging unless all source/runtime/wiring proofs already pass."""

    _require_exact_keys(
        authority,
        {"source_receipts", "matrix_sha256", "call_graph"},
        "prepackaging authority",
    )
    _require_exact_keys(
        value,
        {
            "schema",
            "verdict",
            "design_requirements_sha256",
            "successor_hazard_closure",
            "runtime",
            "carrier",
            "packaging_wiring",
            "artifacts",
            "source_receipts",
            "verified",
        },
        "prepackaging artifact",
    )
    _require_equal(
        value.get("schema"),
        PREPACKAGING_ARTIFACT_SCHEMA,
        "prepackaging artifact schema",
    )
    _require_equal(value.get("verdict"), PREPACKAGING_VERDICT, "prepackaging verdict")
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
    _require_exact_keys(
        runtime,
        {
            "stop_expected_counts",
            "final_expected_counts",
            "stop_clean_records",
            "final_clean_records",
            "final_drift_records",
            "record_capacity",
            "overflow_fixture_records",
            "generated_from_materialized_source",
            "all_complete_pair_returns_validated",
            "expected_counts_normalized_before_excess",
            "nonzero_excess_pair_mask_terminal",
            "legacy_0x6712_emit_sites_zero",
            "pair_mask_requires_integrity_clean_counts",
            "pair_mask_does_not_claim_exclusive_drift",
            "diagnostic_continue_enabled",
            "unclassified_contradiction_stops",
            "stop_drift_checked_before_restart",
            "trace_event_inventory_unchanged",
            "checkpoint_positions_unchanged",
            "verified",
        },
        "runtime proof",
    )
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
    _require_exact_keys(
        carrier,
        {
            "a_outputs",
            "successor_b_outputs",
            "matrix_b_values",
            "progress_zero_outputs",
            "positions",
            "matrix_cells",
            "pair_mask_detail_min",
            "pair_mask_detail_max",
            "generated_from_actual_encoders",
            "accept_reject_from_runtime_emit_sites",
            "real_process_v2_adapter_round_trip",
            "persistence_round_trip",
            "legacy_0x6712_decode_only",
            "matrix_sha256",
            "verified",
        },
        "carrier proof",
    )
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
    _require_equal(
        carrier.get("matrix_sha256"),
        authority["matrix_sha256"],
        "carrier matrix receipt",
    )

    packaging = value.get("packaging_wiring")
    if not isinstance(packaging, dict):
        raise P314DesignError("packaging wiring proof missing")
    _require_exact_keys(
        packaging,
        {
            *PREPACKAGING_WIRING_PROOFS,
            "call_graph",
            "negative_fixture",
            "semantic_mutation_fixture",
            "verified",
        },
        "packaging wiring proof",
    )
    for key in PREPACKAGING_WIRING_PROOFS:
        _require_equal(packaging.get(key), True, f"packaging wiring {key}")
    _require_equal(
        packaging.get("verified"), True, "prepackaging wiring verdict"
    )
    _require_equal(
        packaging.get("call_graph"), authority["call_graph"], "builder call graph"
    )
    _require_equal(
        packaging.get("negative_fixture"),
        NEGATIVE_PACKAGING_FIXTURE,
        "negative packaging fixture",
    )
    _require_equal(
        packaging.get("semantic_mutation_fixture"),
        SEMANTIC_MUTATION_FIXTURE,
        "semantic mutation fixture",
    )

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict):
        raise P314DesignError("artifact identity proof missing")
    _require_exact_keys(
        artifacts,
        {
            "fixed_image_unchanged",
            "kernel_hooks_unchanged",
            "module_plan_unchanged",
            "carrier_size_unchanged",
            "rollback_unchanged",
            "full_lto_performed",
            "verified",
        },
        "artifact identity proof",
    )
    for key, expected in (
        ("fixed_image_unchanged", True),
        ("kernel_hooks_unchanged", True),
        ("module_plan_unchanged", True),
        ("carrier_size_unchanged", True),
        ("rollback_unchanged", True),
        ("full_lto_performed", False),
        ("verified", True),
    ):
        _require_equal(artifacts.get(key), expected, f"artifact proof {key}")

    _require_equal(
        value.get("source_receipts"),
        authority["source_receipts"],
        "prepackaging source receipts",
    )
    _require_equal(value.get("verified"), True, "prepackaging verified flag")
    return {
        "schema": PREPACKAGING_ARTIFACT_SCHEMA,
        "design_requirements_sha256": requirements_sha256(),
        "predecessor_requirements_sha256": predecessor_result[
            "requirements_sha256"
        ],
        "matrix_cells": MATRIX_CELLS,
        "matrix_sha256": authority["matrix_sha256"],
        "source_receipts": authority["source_receipts"],
        "diagnostic_continue_enabled": False,
        "verified": True,
    }


def validate_qualification_artifact(
    value: dict[str, Any], *, authority: dict[str, Any], candidate_tree: dict[str, Any]
) -> dict[str, Any]:
    """Reject final qualification unless prepackaging and repro both pass."""

    _require_exact_keys(
        value,
        {
            "schema",
            "verdict",
            "design_requirements_sha256",
            "prepackaging_closure",
            "prepackaging_receipt",
            "packaging_wiring",
            "artifacts",
            "verified",
        },
        "qualification artifact",
    )
    _require_equal(value.get("schema"), ARTIFACT_SCHEMA, "artifact schema")
    _require_equal(value.get("verdict"), QUALIFICATION_VERDICT, "qualification verdict")
    _require_equal(
        value.get("design_requirements_sha256"),
        requirements_sha256(),
        "design requirements receipt",
    )
    prepackaging = value.get("prepackaging_closure")
    if not isinstance(prepackaging, dict):
        raise P314DesignError("prepackaging closure missing")
    prepackaging_result = validate_prepackaging_artifact(
        prepackaging, authority=authority
    )
    _require_equal(
        value.get("prepackaging_receipt"),
        artifact_receipt(prepackaging),
        "embedded prepackaging receipt",
    )

    packaging = value.get("packaging_wiring")
    if not isinstance(packaging, dict):
        raise P314DesignError("final packaging wiring proof missing")
    _require_exact_keys(
        packaging,
        {
            *FINAL_QUALIFICATION_PROOFS,
            "receipt_rebind_fixture",
            "verified",
        },
        "final packaging wiring proof",
    )
    for key in FINAL_QUALIFICATION_PROOFS:
        _require_equal(packaging.get(key), True, f"final packaging wiring {key}")
    _require_equal(
        packaging.get("verified"), True, "final packaging wiring verdict"
    )
    _require_equal(
        packaging.get("receipt_rebind_fixture"),
        RECEIPT_REBIND_FIXTURE,
        "receipt rebind fixture",
    )

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict):
        raise P314DesignError("final artifact identity proof missing")
    _require_exact_keys(
        artifacts,
        {
            "fixed_image_unchanged",
            "kernel_hooks_unchanged",
            "module_plan_unchanged",
            "carrier_size_unchanged",
            "rollback_unchanged",
            "full_lto_performed",
            "userspace_builds_reproducible",
            "packages_reproducible",
            "candidate_tree",
            "verified",
        },
        "final artifact identity proof",
    )
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
        _require_equal(artifacts.get(key), expected, f"final artifact proof {key}")

    _require_equal(
        artifacts.get("candidate_tree"), candidate_tree, "candidate tree receipt"
    )
    _require_equal(value.get("verified"), True, "qualification verified flag")
    return {
        "schema": ARTIFACT_SCHEMA,
        "design_requirements_sha256": requirements_sha256(),
        "predecessor_requirements_sha256": prepackaging_result[
            "predecessor_requirements_sha256"
        ],
        "matrix_cells": prepackaging_result["matrix_cells"],
        "diagnostic_continue_enabled": False,
        "prepackaging_verified": True,
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
