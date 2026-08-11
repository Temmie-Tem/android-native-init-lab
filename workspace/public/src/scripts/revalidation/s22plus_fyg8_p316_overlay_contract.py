#!/usr/bin/env python3
"""Bind the P3.16 Max77705 userspace/module delta to fixed P3.10 Image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_max77705_envelope_fixture as envelope_fixture
import s22plus_fyg8_max77705_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_max77705_runtime_policy_fixture as policy_fixture
import s22plus_fyg8_max77705_telemetry as telemetry
import s22plus_fyg8_max77705_telemetry_decoder as decoder
import s22plus_fyg8_p308_overlay_contract as helpers
import s22plus_fyg8_p315_overlay_contract as parent
import s22plus_fyg8_p316_generator as generator
import s22plus_fyg8_p316_lifecycle_audit as lifecycle_audit
import s22plus_fyg8_p316_runtime_fixture as runtime_fixture
import s22plus_fyg8_p316_sidecar_positive_control as sidecar_control


SCHEMA = "s22plus_fyg8_p316_userspace_overlay_contract_v1"
CONTRACT_ID = decoder.OVERLAY_CONTRACT_ID
INTENT_SCHEMA = "s22plus_fyg8_p316_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P316_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P316_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P316_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent.TARGET
PROFILE = parent.PROFILE
PARENT_SOURCE_CONTRACT_ID = parent.PARENT_SOURCE_CONTRACT_ID
PARENT_SOURCE = parent.PARENT_SOURCE
PARENT_PATCH = parent.PARENT_PATCH
PARENT_IMAGE = parent.PARENT_IMAGE
PARENT_REPRO_RESULT = parent.PARENT_REPRO_RESULT
EXPECTED_IMAGE = parent.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p316/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
NATIVE = Path("workspace/public/src/native-init")
KERNEL_MODULE = Path(
    "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag"
)
SOURCE_PATHS = {
    "max77705_diag_source": KERNEL_MODULE / "s22plus_max77705_mux_diag.c",
    "max77705_result_parser": NATIVE / "s22plus_fyg8_max77705_result_parser.inc.c",
    "max77705_envelope": NATIVE / "s22plus_fyg8_max77705_envelope.inc.c",
    "max77705_runtime_policy": NATIVE / "s22plus_fyg8_max77705_runtime_policy.inc.c",
    "max77705_runtime_core": NATIVE / "s22plus_fyg8_max77705_runtime_core.inc.c",
    "max77705_envelope_fixture_c": NATIVE / "s22plus_fyg8_max77705_envelope_fixture.c",
    "max77705_runtime_policy_fixture_c": NATIVE / "s22plus_fyg8_max77705_runtime_policy_fixture.c",
    "max77705_checkpoint_transform": PREFIX / "s22plus_fyg8_max77705_checkpoint_transform.py",
    "max77705_custom_surface": PREFIX / "s22plus_fyg8_max77705_custom_surface_contract.py",
    "max77705_diag_build": PREFIX / "s22plus_fyg8_max77705_mux_diag_build.py",
    "max77705_telemetry": PREFIX / "s22plus_fyg8_max77705_telemetry.py",
    "max77705_decoder": PREFIX / "s22plus_fyg8_max77705_telemetry_decoder.py",
    "max77705_envelope_fixture": PREFIX / "s22plus_fyg8_max77705_envelope_fixture.py",
    "max77705_policy_fixture": PREFIX / "s22plus_fyg8_max77705_runtime_policy_fixture.py",
    "max77705_adapter_fixture": PREFIX / "s22plus_fyg8_max77705_process_v2_adapter_fixture.py",
    "p316_generator": PREFIX / "s22plus_fyg8_p316_generator.py",
    "p316_runtime_fixture": PREFIX / "s22plus_fyg8_p316_runtime_fixture.py",
    "p316_lifecycle_audit": PREFIX / "s22plus_fyg8_p316_lifecycle_audit.py",
    "p316_sidecar_control": PREFIX / "s22plus_fyg8_p316_sidecar_positive_control.py",
    "p316_overlay_contract": PREFIX / "s22plus_fyg8_p316_overlay_contract.py",
    "p316_overlay_intent": PREFIX / "s22plus_fyg8_p316_overlay_intent.py",
    "p316_candidate_contract": PREFIX / "s22plus_fyg8_p316_candidate_contract.py",
    "p316_e2_stock_closure": PREFIX / "s22plus_fyg8_p316_e2_stock_closure.py",
    "p316_userspace_build": PREFIX / "s22plus_fyg8_p316_userspace_build.py",
    "p316_candidate_builder": PREFIX / "build_s22plus_fyg8_p316_candidate.py",
    "p316_static_checker": PREFIX / "s22plus_fyg8_p316_candidate_static_checker.py",
    "p316_qualification": PREFIX / "s22plus_fyg8_p316_qualification_closure.py",
    "p316_process_promotion": PREFIX / "prepare_s22plus_fyg8_p316_process_v2.py",
    "p316_ready_manifest": PREFIX / "prepare_s22plus_fyg8_p316_ready_manifest.py",
    "process_v2_live_adapter": PREFIX / "device_action_f1_live_v2.py",
    "process_v2_evidence_adapter": PREFIX / "device_action_f1_evidence_v2.py",
    "process_v2_runner": PREFIX / "device_action_f1_v2.py",
    "p316_process_v2_tests": Path("tests/test_s22plus_fyg8_p316_process_v2.py"),
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = helpers.OverlayContractError
_receipt = helpers._receipt  # noqa: SLF001
_canonical = helpers._canonical  # noqa: SLF001
_read_regular = helpers._read_regular  # noqa: SLF001


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.16 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.16 SOURCE_KEYS differ")
    return rows


def _json_regular(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    payload = _read_regular(path, label, 8 * 1024 * 1024)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError(f"{label} is not an object")
    return payload, value


def verify_parent(root: Path) -> dict[str, Any]:
    value = generator._intent(root)  # noqa: SLF001
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    generator._frozen_bytes(  # noqa: SLF001
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    payload = _read_regular(
        root / generator.P315_INTENT, "P3.16 frozen P3.15 intent", 2**21
    )
    if (
        value.get("contract_id") != parent.CONTRACT_ID
        or value.get("target") != TARGET
        or value.get("profile") != PROFILE
        or value.get("parent_source_contract_id") != PARENT_SOURCE_CONTRACT_ID
    ):
        raise OverlayContractError("P3.16 frozen P3.15 parent differs")
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
        "frozen_p314_baseline": value["frozen_p314_baseline"],
        "design_requirements_sha256": value["design_requirements_sha256"],
        "restart_source_geometry": value["restart_source_geometry"],
        "cross_gate_audit": value["cross_gate_audit"],
        "runtime_fixture": value["runtime_fixture"],
        "tracefs_abi": value["tracefs_abi"],
        "prepackaging_closure": value["prepackaging_closure"],
        "matrix_fixture": value["matrix_fixture"],
        "process_v2_adapter_fixture": value[
            "process_v2_adapter_fixture"
        ],
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


def _surface_gate(root: Path) -> dict[str, Any]:
    value = surface.audit(root)
    contract = value.get("custom_contract", {})
    diagnostic = contract.get("diagnostic", {})
    linked_build = diagnostic.get("linked_build", {})
    linked_validation = linked_build.get("validation", {})
    if (
        value.get("schema") != surface.SCHEMA
        or value.get("host_only") is not True
        or contract.get("status")
        != "SOURCE_AND_LINKED_AB_ABI_QUALIFIED_RUNTIME_NOT_SATISFIED"
        or diagnostic.get("module") != "s22plus_max77705_mux_diag.ko"
        or linked_validation.get("linked_build_satisfied") is not True
        or (
            linked_validation.get("module_size"),
            linked_validation.get("module_sha256"),
        )
        != surface.DIAG_MODULE_IDENTITY
    ):
        raise OverlayContractError("P3.16 Max77705 predecessor gate differs")
    return {
        "schema": value["schema"],
        "custom_contract_sha256": value["custom_contract_sha256"],
        "diagnostic_source": diagnostic["source"],
        "diagnostic_linked_build": diagnostic["linked_build"],
        "preferred_total_module_count": contract["preferred_total_module_count"],
        "selected_design": contract["selected_design"],
        "verified": True,
    }


def create_intent_value(root: Path) -> dict[str, Any]:
    parent_contract = verify_parent(root)
    generated = generated_bytes(root, parent_contract)
    runtime = runtime_fixture.audit(root)
    lifecycle = lifecycle_audit.audit(root)
    envelope = envelope_fixture.audit(root)
    policy = policy_fixture.audit(root)
    adapter = adapter_fixture.audit()
    sidecar = sidecar_control.audit(root)
    surface_gate = _surface_gate(root)
    telemetry_value = {
        **telemetry.validate(),
        "decoder_id": decoder.DECODER_ID,
        "decoder_policy_id": decoder.POLICY_ID,
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
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "max77705_surface_gate": surface_gate,
        "runtime_fixture": runtime,
        "late_loader_lifecycle": lifecycle,
        "envelope_fixture": envelope,
        "runtime_policy_fixture": policy,
        "process_v2_adapter_fixture": adapter,
        "sidecar_positive_control": sidecar,
        "telemetry": telemetry_value,
        "observer": {
            "candidate_window_sec": 300,
            "guard_lifetime_sec": 1200,
            "final_pair_before_banner": True,
            "usb_sidecar_required": True,
            "usb_sidecar_positive_control": sidecar["verdict"],
            "fixed_image": True,
            "verified": True,
        },
        "packaging_requirements": {
            "early_stock_module_count": 64,
            "late_diagnostic_payload_count": 1,
            "total_effective_module_count": 65,
            "diagnostic_absent_from_early_plan": True,
            "diagnostic_staged_exactly_once_in_boot_ramdisk": True,
            "diagnostic_module_identity": list(surface.DIAG_MODULE_IDENTITY),
            "stock_mfd_pdic_spu_absent_from_early_plan": True,
            "actual_15_device_fixture_required": runtime["verdict"],
            "real_process_v2_round_trip_required": adapter["verdict"],
            "late_loader_lifecycle_required": lifecycle["verdict"],
            "sidecar_positive_control_required": sidecar["verdict"],
            "two_userspace_builds_and_two_packages_byte_identical": True,
            "independent_boot_ramdisk_reconstruction_required": True,
            "blocks_packaging_until_validated": True,
        },
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "module_plan_changed": True,
            "early_stock_modules_added": 3,
            "custom_module_binaries_injected": 1,
            "boot_only": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload, value = _json_regular(intent_path, "P3.16 overlay intent")
    if value != create_intent_value(root):
        raise OverlayContractError("P3.16 overlay intent content differs")
    generated = generated_bytes(root, value["parent_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative, f"P3.16 materialized {key}"
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.16 materialized source differs: {key}")
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
        "parent_candidate_contract": value["parent_contract"]["parent_candidate_contract"],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "max77705_surface_gate": value["max77705_surface_gate"],
        "runtime_fixture": value["runtime_fixture"],
        "late_loader_lifecycle": value["late_loader_lifecycle"],
        "envelope_fixture": value["envelope_fixture"],
        "runtime_policy_fixture": value["runtime_policy_fixture"],
        "process_v2_adapter_fixture": value["process_v2_adapter_fixture"],
        "sidecar_positive_control": value["sidecar_positive_control"],
        "telemetry": value["telemetry"],
        "observer": value["observer"],
        "packaging_requirements": value["packaging_requirements"],
        "safety": value["safety"],
        "verified": True,
    }
