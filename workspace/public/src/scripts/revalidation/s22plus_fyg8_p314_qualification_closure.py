#!/usr/bin/env python3
"""Create P3.14 prepackaging and final reproducibility closures."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import build_s22plus_fyg8_p314_candidate as builder
import s22plus_fyg8_p313_successor_hazard_contract as predecessor
import s22plus_fyg8_p314_design_contract as design
import s22plus_fyg8_p314_overlay_contract as overlay


SCHEMA = design.ARTIFACT_SCHEMA
PREPACKAGING_SCHEMA = design.PREPACKAGING_ARTIFACT_SCHEMA
PREPACKAGING_VERDICT = design.PREPACKAGING_VERDICT
VERDICT = design.QUALIFICATION_VERDICT
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_PREPACKAGING = builder.DEFAULT_PREPACKAGING
DEFAULT_USERSPACE = Path("workspace/private/outputs/s22plus_fyg8_p314/userspace")
DEFAULT_CANDIDATE_A = builder.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p314/candidate-b")
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p314/qualification/"
    "qualification-closure.json"
)


class QualificationError(ValueError):
    pass


def _receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _read_json(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or before.st_size > 64 * 1024 * 1024:
            raise QualificationError(f"{label} is not a bounded regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise QualificationError(f"{label} is unavailable") from exc
    if (
        len(payload) != before.st_size
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        raise QualificationError(f"{label} changed while reading")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{label} root differs")
    return payload, value


def _write_new(path: Path, value: dict[str, Any]) -> None:
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n"
    if path.exists() or path.is_symlink():
        raise QualificationError(f"qualification output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise QualificationError("short qualification write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _builder_call_graph(root: Path) -> dict[str, Any]:
    return design.builder_call_graph(root)


def _negative_packaging_fixture(root: Path) -> dict[str, Any]:
    parent_build = builder.parent.parent.base.build_candidate
    calls = 0

    def forbidden_parent_build(_args: argparse.Namespace) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError("parent packager ran after failed P3.14 gate")

    builder.parent.parent.base.build_candidate = forbidden_parent_build
    outcomes: dict[str, bool] = {}
    try:
        private = root / "workspace/private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="p314-prepack-negative-", dir=private) as name:
            directory = Path(name)
            output = directory / "candidate"
            missing = directory / "missing.json"
            invalid = directory / "invalid.json"
            invalid.write_text("{}\n", encoding="ascii")
            for label, closure in (("missing", missing), ("invalid", invalid)):
                args = builder.parse_args(
                    [
                        "--prepackaging",
                        closure.relative_to(root).as_posix(),
                        "--out",
                        output.relative_to(root).as_posix(),
                    ]
                )
                try:
                    builder.build_candidate(args)
                except (builder.BuildError, design.P314DesignError, OSError, ValueError):
                    outcomes[label] = not output.exists() and not output.is_symlink()
                else:
                    outcomes[label] = False
    finally:
        builder.parent.parent.base.build_candidate = parent_build
    if calls != 0 or outcomes != {"missing": True, "invalid": True}:
        raise QualificationError("P3.14 failed-gate packaging fixture differs")
    return {
        "missing_closure_blocks_package": True,
        "invalid_closure_blocks_package": True,
        "parent_packager_call_count": calls,
        "package_output_count": 0,
        "verified": True,
    }


def _semantic_packaging_fixture(
    root: Path, value: dict[str, Any]
) -> dict[str, Any]:
    parent_build = builder.parent.parent.base.build_candidate
    calls = 0

    def forbidden_parent_build(_args: argparse.Namespace) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError("parent packager ran after mutated P3.14 gate")

    def mutate_verdict(candidate: dict[str, Any]) -> None:
        candidate["verdict"] = "PASS_P314_MUTATED"

    def mutate_source(candidate: dict[str, Any]) -> None:
        candidate["source_receipts"]["p314_candidate_builder"][  # type: ignore[index]
            "sha256"
        ] = "0" * 64

    def mutate_call_graph(candidate: dict[str, Any]) -> None:
        candidate["packaging_wiring"]["call_graph"][  # type: ignore[index]
            "validator_line"
        ] += 1

    def mutate_matrix(candidate: dict[str, Any]) -> None:
        candidate["carrier"]["matrix_sha256"] = "0" * 64  # type: ignore[index]

    mutations = (
        ("verdict", mutate_verdict),
        ("source_receipt", mutate_source),
        ("call_graph", mutate_call_graph),
        ("matrix_sha256", mutate_matrix),
    )
    outcomes: dict[str, bool] = {}
    builder.parent.parent.base.build_candidate = forbidden_parent_build
    try:
        private = root / "workspace/private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="p314-prepack-semantic-", dir=private
        ) as name:
            directory = Path(name)
            for label, mutate in mutations:
                closure = directory / f"{label}.json"
                output = directory / f"candidate-{label}"
                candidate = deepcopy(value)
                mutate(candidate)
                closure.write_text(
                    json.dumps(
                        candidate, indent=2, sort_keys=True, allow_nan=False
                    )
                    + "\n",
                    encoding="ascii",
                )
                args = builder.parse_args(
                    [
                        "--prepackaging",
                        closure.relative_to(root).as_posix(),
                        "--out",
                        output.relative_to(root).as_posix(),
                    ]
                )
                try:
                    builder.build_candidate(args)
                except (
                    builder.BuildError,
                    design.P314DesignError,
                    OSError,
                    ValueError,
                ):
                    outcomes[label] = not output.exists() and not output.is_symlink()
                else:
                    outcomes[label] = False
    finally:
        builder.parent.parent.base.build_candidate = parent_build
    expected = {
        "verdict": True,
        "source_receipt": True,
        "call_graph": True,
        "matrix_sha256": True,
    }
    if calls != 0 or outcomes != expected:
        raise QualificationError("P3.14 semantic packaging fixture differs")
    return {
        "verdict_mutation_blocks_package": True,
        "source_receipt_mutation_blocks_package": True,
        "call_graph_mutation_blocks_package": True,
        "matrix_sha256_mutation_blocks_package": True,
        "parent_packager_call_count": calls,
        "package_output_count": 0,
        "verified": True,
    }


def _successor_hazard_closure(exact: dict[str, Any]) -> dict[str, Any]:
    runtime = exact["runtime_fixture"]
    matrix = exact["matrix_fixture"]
    gates = exact["cross_gate_audit"]
    return {
        "schema": predecessor.ARTIFACT_SCHEMA,
        "requirements_sha256": predecessor.requirements_sha256(),
        "hazards": {
            "source_derived_pair_geometry": {
                "stop_expected_counts": predecessor.STOP_EXPECTED_COUNTS,
                "final_expected_counts": predecessor.FINAL_EXPECTED_COUNTS,
                "clean_records": 41,
                "bounded_drift_records": 49,
                "record_capacity": 64,
                "generated_from_materialized_source": True,
                "verified": True,
            },
            "continuation_partition": {
                "expected_geometry_normalized_before_contradiction": True,
                "default_unclassified_contradiction_stops": True,
                "immediate_stop_conditions": list(predecessor.IMMEDIATE_STOP_CONDITIONS),
                "diagnostic_continue_predicates": list(
                    predecessor.DIAGNOSTIC_CONTINUE_PREDICATES
                ),
                "diagnostic_data_never_cycle_causal": True,
                "verified": True,
            },
            "carrier_value_position_matrix": {
                "inherited_a_outputs": predecessor.INHERITED_A_OUTPUT_COUNT,
                "inherited_b_outputs": predecessor.INHERITED_B_OUTPUT_COUNT,
                "successor_b_outputs": matrix["successor_b_outputs"],
                "matrix_b_values": matrix["matrix_b_values"],
                "progress_zero_outputs": matrix["progress_zero_outputs"],
                "positions": matrix["positions"],
                "matrix_cells": matrix["matrix_cells"],
                "legacy_generic_multiplicity_decode_covered": True,
                "generated_from_actual_encoders": matrix[
                    "generated_from_actual_encoders"
                ],
                "accept_reject_derived_from_runtime_emit_sites": matrix[
                    "accept_reject_from_runtime_gates"
                ],
                "real_process_v2_adapter_round_trip": matrix[
                    "real_process_v2_adapter_round_trip"
                ],
                "persistence_round_trip": matrix["persistence_round_trip"],
                "verified": True,
            },
            "pair_specific_multiplicity_detail": {
                "pair_names": list(predecessor.PAIR_NAMES),
                "detail_min": predecessor.PAIR_MASK_DETAIL_MIN,
                "detail_max": predecessor.PAIR_MASK_DETAIL_MAX,
                "output_count": predecessor.PAIR_MASK_VALUE_COUNT,
                "trace_record_cost": 0,
                "legacy_generic_0x6712_not_emitted": runtime[
                    "legacy_0x6712_emit_sites_zero"
                ],
                "historical_p311_range_disjoint": True,
                "all_masks_runtime_gate": gates["pair_masks_validated"] == 1023,
                "all_masks_checkpoint_gate": gates["pair_masks_validated"] == 1023,
                "all_masks_fixed_image_gate": gates["pair_masks_validated"] == 1023,
                "all_masks_model_decoder_adapter_round_trip": matrix[
                    "real_process_v2_adapter_round_trip"
                ],
                "verified": True,
            },
            "qualification_wiring": {
                "requirements_hash_in_source_closure": True,
                "validator_called_before_packaging": True,
                "missing_or_failed_artifact_blocks_packaging": True,
                "validated_artifact_receipted_by_qualification": True,
                "verified": True,
            },
        },
        "verified": True,
    }


def create_prepackaging_value(root: Path, intent_path: Path) -> dict[str, Any]:
    exact = overlay.verify_intent(root, intent_path)
    authority = design.prepackaging_authority(root, exact)
    call_graph = authority["call_graph"]
    negative = _negative_packaging_fixture(root)
    required_keys = {
        "p313_successor_hazard_contract",
        "p314_design_contract",
        "p314_e2_stock_closure",
        "p314_candidate_builder",
        "p314_qualification_closure",
    }
    if not required_keys.issubset(exact["source_receipts"]):
        raise QualificationError("P3.14 requirements are absent from SOURCE_KEYS")
    value = {
        "schema": PREPACKAGING_SCHEMA,
        "verdict": PREPACKAGING_VERDICT,
        "design_requirements_sha256": design.requirements_sha256(),
        "successor_hazard_closure": _successor_hazard_closure(exact),
        "runtime": {
            "stop_expected_counts": predecessor.STOP_EXPECTED_COUNTS,
            "final_expected_counts": predecessor.FINAL_EXPECTED_COUNTS,
            "stop_clean_records": 14,
            "final_clean_records": 41,
            "final_drift_records": 49,
            "record_capacity": 64,
            "overflow_fixture_records": 65,
            "generated_from_materialized_source": True,
            "all_complete_pair_returns_validated": True,
            "expected_counts_normalized_before_excess": True,
            "nonzero_excess_pair_mask_terminal": True,
            "legacy_0x6712_emit_sites_zero": True,
            "pair_mask_requires_integrity_clean_counts": True,
            "pair_mask_does_not_claim_exclusive_drift": True,
            "diagnostic_continue_enabled": False,
            "unclassified_contradiction_stops": True,
            "stop_drift_checked_before_restart": True,
            "trace_event_inventory_unchanged": True,
            "checkpoint_positions_unchanged": True,
            "verified": True,
        },
        "carrier": {
            "a_outputs": 126,
            "successor_b_outputs": 2222,
            "matrix_b_values": 2223,
            "progress_zero_outputs": 1,
            "positions": 107,
            "matrix_cells": 251450,
            "pair_mask_detail_min": predecessor.PAIR_MASK_DETAIL_MIN,
            "pair_mask_detail_max": predecessor.PAIR_MASK_DETAIL_MAX,
            "generated_from_actual_encoders": True,
            "accept_reject_from_runtime_emit_sites": True,
            "real_process_v2_adapter_round_trip": True,
            "persistence_round_trip": True,
            "legacy_0x6712_decode_only": True,
            "matrix_sha256": exact["matrix_fixture"]["matrix_sha256"],
            "verified": True,
        },
        "packaging_wiring": {
            "requirements_hash_in_source_closure": True,
            "validator_called_before_packaging": True,
            "validator_return_controls_package_creation": True,
            "missing_or_failed_artifact_blocks_packaging": True,
            "validator_failure_negative_fixture": True,
            "semantic_mutation_fixture_passed": True,
            "source_call_graph_reviewed": True,
            "call_graph": call_graph,
            "negative_fixture": negative,
            "semantic_mutation_fixture": design.SEMANTIC_MUTATION_FIXTURE,
            "verified": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "module_plan_unchanged": True,
            "carrier_size_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_performed": False,
            "verified": True,
        },
        "source_receipts": exact["source_receipts"],
        "verified": True,
    }
    semantic = _semantic_packaging_fixture(root, value)
    if semantic != design.SEMANTIC_MUTATION_FIXTURE:
        raise QualificationError("P3.14 semantic mutation receipt differs")
    value["packaging_wiring"]["semantic_mutation_fixture"] = semantic
    design.validate_prepackaging_artifact(value, authority=authority)
    return value


def _tree_receipts(directory: Path) -> dict[str, dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir():
        raise QualificationError(f"candidate tree is unavailable: {directory}")
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise QualificationError("candidate tree contains a symlink")
        if path.is_file():
            rows[path.relative_to(directory).as_posix()] = _receipt(path.read_bytes())
    return rows


def create_final_value(
    root: Path,
    intent_path: Path,
    prepackaging_path: Path,
    userspace_path: Path,
    candidate_a: Path,
    candidate_b: Path,
) -> dict[str, Any]:
    exact = overlay.verify_intent(root, intent_path)
    authority = design.prepackaging_authority(root, exact)
    prepack_payload, prepack = _read_json(prepackaging_path, "P3.14 prepackaging closure")
    prepack_validation = design.validate_prepackaging_artifact(
        prepack, authority=authority
    )
    if _receipt(prepack_payload) != design.artifact_receipt(prepack):
        raise QualificationError("P3.14 prepackaging canonical receipt differs")
    _, userspace = _read_json(
        userspace_path / "userspace-result.json", "P3.14 userspace result"
    )
    if userspace.get("two_build_byte_identical") is not True:
        raise QualificationError("P3.14 userspace reproducibility differs")
    trees = (_tree_receipts(candidate_a), _tree_receipts(candidate_b))
    if trees[0] != trees[1]:
        raise QualificationError("P3.14 package trees are not byte-identical")
    for directory in (candidate_a, candidate_b):
        _, result = _read_json(directory / "artifact-result.json", "P3.14 artifact result")
        safety = result.get("safety", {})
        if safety.get("p314_prepackaging_closure") != _receipt(prepack_payload):
            raise QualificationError("P3.14 package omitted prepackaging receipt")
        if safety.get("p314_prepackaging_validation") != prepack_validation:
            raise QualificationError("P3.14 package omitted prepackaging validation")
    value = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "design_requirements_sha256": design.requirements_sha256(),
        "prepackaging_closure": prepack,
        "prepackaging_receipt": design.artifact_receipt(prepack),
        "packaging_wiring": {
            "validated_artifact_receipted_by_qualification": True,
            "receipt_binds_requirements_and_artifact_sha256": True,
            "embedded_prepack_receipt_rebound": True,
            "receipt_rebind_fixture": design.RECEIPT_REBIND_FIXTURE,
            "verified": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "module_plan_unchanged": True,
            "carrier_size_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_performed": False,
            "userspace_builds_reproducible": True,
            "packages_reproducible": True,
            "candidate_tree": trees[0],
            "verified": True,
        },
        "verified": True,
    }
    for label, mutated in (
        ("embedded", deepcopy(value)),
        ("declared", deepcopy(value)),
    ):
        if label == "embedded":
            mutated["prepackaging_closure"]["verified"] = False
        else:
            mutated["prepackaging_receipt"]["sha256"] = "0" * 64
        try:
            design.validate_qualification_artifact(
                mutated, authority=authority, candidate_tree=trees[0]
            )
        except design.P314DesignError:
            continue
        raise QualificationError(f"P3.14 {label} receipt mutation was accepted")
    design.validate_qualification_artifact(
        value, authority=authority, candidate_tree=trees[0]
    )
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepackaging", "final"), required=True)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--prepackaging", type=Path, default=DEFAULT_PREPACKAGING)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--candidate-a", type=Path, default=DEFAULT_CANDIDATE_A)
    parser.add_argument("--candidate-b", type=Path, default=DEFAULT_CANDIDATE_B)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parents[5]
    try:
        if args.phase == "prepackaging":
            output = args.out or DEFAULT_PREPACKAGING
            value = create_prepackaging_value(root, root / args.intent)
        else:
            output = args.out or DEFAULT_OUT
            value = create_final_value(
                root,
                root / args.intent,
                root / args.prepackaging,
                root / args.userspace,
                root / args.candidate_a,
                root / args.candidate_b,
            )
        _write_new(root / output, value)
    except (QualificationError, design.P314DesignError, OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": value["schema"], "verdict": value["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
