#!/usr/bin/env python3
"""Bind P3.15 live-profile userspace to the unchanged fixed Image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p308_overlay_contract as helpers
import s22plus_fyg8_p314_overlay_contract as parent
import s22plus_fyg8_p315_cross_gate_audit as cross_gate
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_generator as generator
import s22plus_fyg8_p315_restart_source_geometry_audit as source_geometry
import s22plus_fyg8_p315_runtime_fixture as runtime_fixture
import s22plus_fyg8_p315_telemetry_decoder as telemetry_decoder
import s22plus_fyg8_p315_telemetry_spec as telemetry


SCHEMA = "s22plus_fyg8_p315_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p315-live-profile-restart-carrier-v2-observer-v1"
INTENT_SCHEMA = "s22plus_fyg8_p315_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P315_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P315_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P315_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent.TARGET
PROFILE = parent.PROFILE
PARENT_SOURCE_CONTRACT_ID = parent.PARENT_SOURCE_CONTRACT_ID
PARENT_SOURCE = parent.PARENT_SOURCE
PARENT_PATCH = parent.PARENT_PATCH
PARENT_IMAGE = parent.PARENT_IMAGE
PARENT_REPRO_RESULT = parent.PARENT_REPRO_RESULT
EXPECTED_IMAGE = parent.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p315/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    **parent.SOURCE_PATHS,
    "p315_design_contract": PREFIX / "s22plus_fyg8_p315_design_contract.py",
    "p315_telemetry_spec": PREFIX / "s22plus_fyg8_p315_telemetry_spec.py",
    "p315_carrier_model": PREFIX / "s22plus_fyg8_p315_carrier_model.py",
    "p315_telemetry_decoder": PREFIX / "s22plus_fyg8_p315_telemetry_decoder.py",
    "p315_runtime_transform": PREFIX / "s22plus_fyg8_p315_runtime_transform.py",
    "p315_generator": PREFIX / "s22plus_fyg8_p315_generator.py",
    "p315_restart_source_geometry": PREFIX
    / "s22plus_fyg8_p315_restart_source_geometry_audit.py",
    "p315_cross_gate_audit": PREFIX / "s22plus_fyg8_p315_cross_gate_audit.py",
    "p315_runtime_fixture": PREFIX / "s22plus_fyg8_p315_runtime_fixture.py",
    "p315_matrix_fixture": PREFIX / "s22plus_fyg8_p315_matrix_fixture.py",
    "p315_process_v2_adapter_fixture": PREFIX
    / "s22plus_fyg8_p315_process_v2_adapter_fixture.py",
    "p315_packaging_wiring_audit": PREFIX
    / "s22plus_fyg8_p315_packaging_wiring_audit.py",
    "p315_hazard_closure": PREFIX / "s22plus_fyg8_p315_hazard_closure.py",
    "p315_qualification_closure": PREFIX
    / "s22plus_fyg8_p315_qualification_closure.py",
    "p315_overlay_contract": PREFIX / "s22plus_fyg8_p315_overlay_contract.py",
    "p315_overlay_intent": PREFIX / "s22plus_fyg8_p315_overlay_intent.py",
    "p315_candidate_contract": PREFIX / "s22plus_fyg8_p315_candidate_contract.py",
    "p315_e2_stock_closure": PREFIX / "s22plus_fyg8_p315_e2_stock_closure.py",
    "p315_userspace_build": PREFIX / "s22plus_fyg8_p315_userspace_build.py",
    "p315_candidate_builder": PREFIX / "build_s22plus_fyg8_p315_candidate.py",
    "p315_static_checker": PREFIX
    / "s22plus_fyg8_p315_candidate_static_checker.py",
    "p315_process_promotion": PREFIX / "prepare_s22plus_fyg8_p315_process_v2.py",
    "p315_ready_manifest": PREFIX / "prepare_s22plus_fyg8_p315_ready_manifest.py",
    "process_v2_live_adapter": PREFIX / "device_action_f1_live_v2.py",
    "process_v2_evidence_adapter": PREFIX / "device_action_f1_evidence_v2.py",
    "p315_design_tests": PREFIX / "test_s22plus_fyg8_p315_design_contract.py",
    "p315_process_v2_tests": Path("tests/test_s22plus_fyg8_p315_process_v2.py"),
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = helpers.OverlayContractError
_receipt = helpers._receipt  # noqa: SLF001
_canonical = helpers._canonical  # noqa: SLF001
_read_regular = helpers._read_regular  # noqa: SLF001


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.15 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.15 SOURCE_KEYS differ")
    return rows


def _json_regular(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    payload = _read_regular(path, label, 4 * 1024 * 1024)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError(f"{label} is not an object")
    return payload, value


def verify_parent(root: Path) -> dict[str, Any]:
    payload, value = generator._intent(root)  # noqa: SLF001
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    generator._frozen_p314_bytes(  # noqa: SLF001
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    if (
        value.get("contract_id") != parent.CONTRACT_ID
        or value.get("target") != TARGET
        or value.get("profile") != PROFILE
        or value.get("parent_source_contract_id") != PARENT_SOURCE_CONTRACT_ID
    ):
        raise OverlayContractError("P3.15 frozen P3.14 parent differs")
    return {
        "schema": parent.SCHEMA,
        "verdict": parent.CONTRACT_VERDICT,
        "contract_id": parent.CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": 3,
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": parent.CONTRACT_ID,
        "parent_contract": value["parent_contract"],
        "parent_candidate_contract": value["parent_contract"][
            "parent_candidate_contract"
        ],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "tracefs_abi": value["tracefs_abi"],
        "cross_gate_audit": value["cross_gate_audit"],
        "runtime_fixture": value["runtime_fixture"],
        "hazard_closure": value["hazard_closure"],
        "matrix_fixture": value["matrix_fixture"],
        "process_v2_adapter_fixture": value["process_v2_adapter_fixture"],
        "telemetry": value["telemetry"],
        "observer": value["observer"],
        "safety": value["safety"],
        "verified": True,
    }


def generated_bytes(root: Path, parent_contract: Mapping[str, Any]) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(parent_contract["run_id"])),
        unsat_tag=bytes.fromhex(str(parent_contract["unsat_tag_hex"])),
        profile=str(parent_contract["profile"]),
    )


def create_intent_value(root: Path) -> dict[str, Any]:
    import s22plus_fyg8_p315_hazard_closure as hazard_closure
    import s22plus_fyg8_p315_matrix_fixture as matrix_fixture
    import s22plus_fyg8_p315_process_v2_adapter_fixture as adapter_fixture

    parent_contract = verify_parent(root)
    parent_payload, parent_intent = generator._intent(root)  # noqa: SLF001
    generated = generated_bytes(root, parent_contract)
    geometry = source_geometry.audit(root)
    gates = cross_gate.audit(root)
    fixture = runtime_fixture.audit(root)
    matrix = matrix_fixture.audit(root)
    adapter = adapter_fixture.audit(root, matrix_result=matrix)
    prepackaging = hazard_closure.audit(
        root,
        source_result=geometry,
        runtime_result=fixture,
        adapter_result=adapter,
    )
    telemetry_value = {
        **telemetry.validate(),
        "decoder_id": telemetry_decoder.DECODER_ID,
        "decoder_policy_id": telemetry_decoder.POLICY_ID,
    }
    observer = {
        "role_event_count": telemetry.ROLE_EVENT_COUNT,
        "direct_event_count": telemetry.DIRECT_EVENT_COUNT,
        "cycle_event_count": telemetry.CYCLE_EVENT_COUNT,
        "record_capacity": telemetry.RECORD_CAPACITY,
        "direct_prefix_capacity": telemetry.DIRECT_PREFIX_CAPACITY,
        "cycle_record_contract": [14, 41, 49, 65],
        "restart_completion_max_snapshots": 301,
        "stop_and_restart_profile_reads": 2,
        "profile_hits_lower_bound_records": True,
        "relevant_profile_excess_rejected": True,
        "profile_missed_must_be_zero": True,
        "ring_loss_must_be_zero": True,
        "final_pair_before_banner": True,
        "candidate_window_sec": 300,
        "guard_lifetime_sec": 1200,
        "fixed_image": True,
        "kernel_changed": False,
        "module_plan_changed": False,
        "carrier_changed": False,
        "read_only_observer": True,
        "verified": True,
    }
    value = {
        "schema": INTENT_SCHEMA,
        "verdict": INTENT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "run_id": parent_contract["run_id"],
        "unsat_tag_hex": parent_contract["unsat_tag_hex"],
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "parent_contract": parent_contract,
        "fixed_image": parent_contract["fixed_image"],
        "frozen_p314_baseline": {
            "path": generator.P314_INTENT.as_posix(),
            **_receipt(parent_payload),
            "generated_artifacts": parent_intent["generated_artifacts"],
            "verified": True,
        },
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "design_requirements_sha256": design.requirements_sha256(),
        "restart_source_geometry": geometry,
        "cross_gate_audit": gates,
        "runtime_fixture": fixture,
        "tracefs_abi": parent_contract["tracefs_abi"],
        "prepackaging_closure": prepackaging,
        "matrix_fixture": matrix,
        "process_v2_adapter_fixture": adapter,
        "telemetry": telemetry_value,
        "observer": observer,
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "new_hazard_class": False,
            "module_binaries_injected": 0,
            "stock_vendor_ramdisk_module_reused": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload, value = _json_regular(intent_path, "P3.15 overlay intent")
    if value != create_intent_value(root):
        raise OverlayContractError("P3.15 overlay intent content differs")
    generated = generated_bytes(root, value["parent_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative, f"P3.15 materialized {key}"
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.15 materialized source differs: {key}")
    return {
        "schema": SCHEMA,
        "verdict": CONTRACT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": 3,
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": CONTRACT_ID,
        "parent_contract": value["parent_contract"],
        "parent_candidate_contract": value["parent_contract"][
            "parent_candidate_contract"
        ],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "frozen_p314_baseline": value["frozen_p314_baseline"],
        "design_requirements_sha256": value["design_requirements_sha256"],
        "restart_source_geometry": value["restart_source_geometry"],
        "cross_gate_audit": value["cross_gate_audit"],
        "runtime_fixture": value["runtime_fixture"],
        "tracefs_abi": value["tracefs_abi"],
        "prepackaging_closure": value["prepackaging_closure"],
        "matrix_fixture": value["matrix_fixture"],
        "process_v2_adapter_fixture": value["process_v2_adapter_fixture"],
        "telemetry": value["telemetry"],
        "observer": value["observer"],
        "safety": value["safety"],
        "verified": True,
    }
