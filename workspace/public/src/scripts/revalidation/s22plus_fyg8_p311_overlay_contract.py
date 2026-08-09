#!/usr/bin/env python3
"""Bind P3.11 userspace to the exact qualified P3.10 Carrier-v2 Image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p308_overlay_contract as helpers
import s22plus_fyg8_p311_callsite_audit as callsite_audit
import s22plus_fyg8_p311_cross_gate_audit as cross_gate
import s22plus_fyg8_p311_generator as generator
import s22plus_fyg8_p311_telemetry_decoder as telemetry_decoder
import s22plus_fyg8_p311_telemetry_spec as telemetry
import s22plus_fyg8_p311_tracefs_abi_audit as tracefs_abi


SCHEMA = "s22plus_fyg8_p311_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p311-early-hsphy-clock-observer-v1"
INTENT_SCHEMA = "s22plus_fyg8_p311_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P311_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P311_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P311_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PROFILE = "E2"
PARENT_SOURCE_CONTRACT_ID = "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
PARENT_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p310/intent-v7/candidate-intent.json"
)
PARENT_PATCH = PARENT_INTENT.parent / "candidate.patch"
PARENT_SOURCE = Path("workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae")
PARENT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_p311/fixed-p310-ready-1/Image"
)
PARENT_REPRO_RESULT = Path(
    "workspace/private/device-action/s22plus_fyg8_p310_ready_1/evidence/candidate-static.json"
)
EXPECTED_IMAGE = {
    "size": 41490944,
    "sha256": "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8",
}
CALLSITE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p311_callsite_audit/result.json"
)
QEMU_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p311_delayed_module_kprobe_qemu_control/result.json"
)
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p311/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p311_callsite_spec": PREFIX / "s22plus_fyg8_p311_callsite_spec.py",
    "p311_callsite_audit": PREFIX / "s22plus_fyg8_p311_callsite_audit.py",
    "p311_delayed_qemu_source": Path(
        "workspace/public/src/native-init/s22plus_fyg8_p311_delayed_module_kprobe_qemu_control.c"
    ),
    "p311_delayed_qemu_control": PREFIX / "s22plus_fyg8_p311_delayed_module_kprobe_qemu_control.py",
    "p311_telemetry_spec": PREFIX / "s22plus_fyg8_p311_telemetry_spec.py",
    "p311_telemetry_model": PREFIX / "s22plus_fyg8_p311_telemetry_model.py",
    "p311_telemetry_decoder": PREFIX / "s22plus_fyg8_p311_telemetry_decoder.py",
    "p310_telemetry_decoder_replacement": PREFIX
    / "s22plus_fyg8_p310_telemetry_decoder.py",
    "p311_runtime_transform": PREFIX / "s22plus_fyg8_p311_runtime_transform.py",
    "p311_generator": PREFIX / "s22plus_fyg8_p311_generator.py",
    "p311_tracefs_abi_audit": PREFIX / "s22plus_fyg8_p311_tracefs_abi_audit.py",
    "p311_cross_gate_audit": PREFIX / "s22plus_fyg8_p311_cross_gate_audit.py",
    "p311_runtime_fixture": PREFIX / "s22plus_fyg8_p311_runtime_fixture.py",
    "p311_overlay_contract": PREFIX / "s22plus_fyg8_p311_overlay_contract.py",
    "p311_overlay_intent": PREFIX / "s22plus_fyg8_p311_overlay_intent.py",
    "p311_candidate_contract": PREFIX / "s22plus_fyg8_p311_candidate_contract.py",
    "p311_stock_closure": PREFIX / "s22plus_fyg8_p311_e2_stock_closure.py",
    "p311_userspace_build": PREFIX / "s22plus_fyg8_p311_userspace_build.py",
    "p311_candidate_builder": PREFIX / "build_s22plus_fyg8_p311_candidate.py",
    "p311_static_checker": PREFIX / "s22plus_fyg8_p311_candidate_static_checker.py",
    "p311_process_promotion": PREFIX / "prepare_s22plus_fyg8_p311_process_v2.py",
    "p311_ready_manifest": PREFIX / "prepare_s22plus_fyg8_p311_ready_manifest.py",
    "process_v2_evidence": PREFIX / "device_action_f1_evidence_v2.py",
    "process_v2_runner": PREFIX / "device_action_f1_v2.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = helpers.OverlayContractError
_receipt = helpers._receipt  # noqa: SLF001
_canonical = helpers._canonical  # noqa: SLF001
_read_regular = helpers._read_regular  # noqa: SLF001


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.11 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.11 SOURCE_KEYS differ")
    return rows


def _json_regular(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    payload = _read_regular(path, label, 2 * 1024 * 1024)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError(f"{label} is not an object")
    return payload, value


def verify_parent(root: Path) -> dict[str, Any]:
    intent_payload, intent = _json_regular(root / PARENT_INTENT, "P3.11 parent intent")
    static_payload, static = _json_regular(root / PARENT_REPRO_RESULT, "P3.11 parent closure")
    image = _read_regular(root / PARENT_IMAGE, "P3.11 fixed P3.10 Image", 64 * 1024 * 1024)
    if _receipt(image) != EXPECTED_IMAGE:
        raise OverlayContractError("P3.11 fixed P3.10 Image differs")
    if (
        intent.get("schema") != "s22plus_fyg8_p310_candidate_intent_v1"
        or intent.get("verdict") != "PASS_P310_CANDIDATE_INTENT_HOST_ONLY"
        or intent.get("source_contract_id") != PARENT_SOURCE_CONTRACT_ID
        or intent.get("profile") != PROFILE
        or intent.get("profile_number") != 3
        or intent.get("run_id") != "b9cc424d0d184f5accbce94a844e817d"
        or intent.get("unsat_tag_hex") != "ecbfff41d2c5ed22383db45dedfb622d"
    ):
        raise OverlayContractError("P3.11 parent P3.10 identity differs")
    patch = _read_regular(root / PARENT_PATCH, "P3.11 parent patch")
    if _receipt(patch) != {
        "size": intent["patch"]["size"],
        "sha256": intent["patch"]["sha256"],
    }:
        raise OverlayContractError("P3.11 parent patch receipt differs")
    for row in intent.get("materialized_sources", {}).values():
        path = PARENT_INTENT.parent / row["path"]
        data = _read_regular(root / path, "P3.11 parent materialized source")
        if _receipt(data) != {"size": row["size"], "sha256": row["sha256"]}:
            raise OverlayContractError("P3.11 parent materialized receipt differs")
    if (
        static.get("verdict") != "PASS_P310_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
        or static.get("build_repro", {}).get("image") != EXPECTED_IMAGE
        or static.get("candidate_contract", {}).get("run_id") != intent["run_id"]
        or static.get("candidate_contract", {}).get("intent") != _receipt(intent_payload)
    ):
        raise OverlayContractError("P3.11 P3.10 independent closure differs")
    return {
        "schema": "s22plus_fyg8_p311_exact_parent_v1",
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": 3,
        "run_id": intent["run_id"],
        "unsat_tag_hex": intent["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "candidate_intent": {"path": PARENT_INTENT.as_posix(), **_receipt(intent_payload)},
        "candidate_patch": {"path": PARENT_PATCH.as_posix(), **_receipt(patch)},
        "independent_closure": {"path": PARENT_REPRO_RESULT.as_posix(), **_receipt(static_payload)},
        "parent_candidate_contract": static["candidate_contract"],
        "fixed_image": {"path": PARENT_IMAGE.as_posix(), **EXPECTED_IMAGE},
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
    parent_contract = verify_parent(root)
    generated = generated_bytes(root, parent_contract)
    callsite_payload, callsites = _json_regular(root / CALLSITE_RESULT, "P3.11 callsite result")
    qemu_payload, qemu = _json_regular(root / QEMU_RESULT, "P3.11 delayed-arm result")
    if callsites.get("verified") is not True or callsites.get("callsite_count") != 24:
        raise OverlayContractError("P3.11 callsite proof differs")
    if qemu.get("verdict") != "PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY":
        raise OverlayContractError("P3.11 delayed-arm proof differs")
    abi = tracefs_abi.audit(root, generated["trace_descriptor_header"])
    gates = cross_gate.audit(root)
    telemetry_value = {
        **telemetry.validate(),
        "decoder_id": telemetry_decoder.DECODER_ID,
        "decoder_policy_id": telemetry_decoder.POLICY_ID,
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
        "callsite_audit": {"path": CALLSITE_RESULT.as_posix(), **_receipt(callsite_payload), "result": callsites},
        "delayed_arm_qemu": {"path": QEMU_RESULT.as_posix(), **_receipt(qemu_payload), "result": qemu},
        "tracefs_abi": abi,
        "cross_gate_audit": gates,
        "telemetry": telemetry_value,
        "observer": {
            "pending_module_local_probes": True,
            "arm_before_module_index": 55,
            "finish_after_module_plan": True,
            "global_clock_probe": False,
            "event_count": telemetry.EARLY_EVENT_COUNT,
            "record_capacity": telemetry.RECORD_CAPACITY,
            "profile_hits_equal_records": True,
            "ring_loss_must_be_zero": True,
            "kernel_changed": False,
            "module_plan_changed": False,
            "carrier_changed": False,
            "log_level_changed": False,
            "read_only": True,
            "verified": True,
        },
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
    payload, value = _json_regular(intent_path, "P3.11 overlay intent")
    if value != create_intent_value(root):
        raise OverlayContractError("P3.11 overlay intent content differs")
    generated = generated_bytes(root, value["parent_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(intent_path.parent / relative, f"P3.11 materialized {key}")
        if actual != generated[key]:
            raise OverlayContractError(f"P3.11 materialized source differs: {key}")
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
        "callsite_audit": value["callsite_audit"],
        "delayed_arm_qemu": value["delayed_arm_qemu"],
        "tracefs_abi": value["tracefs_abi"],
        "cross_gate_audit": value["cross_gate_audit"],
        "telemetry": value["telemetry"],
        "observer": value["observer"],
        "safety": value["safety"],
        "verified": True,
    }
