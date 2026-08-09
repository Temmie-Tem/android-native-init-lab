#!/usr/bin/env python3
"""Bind P3.13 post-bind resume-cycle userspace to the fixed P3.10 Image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p308_overlay_contract as helpers
import s22plus_fyg8_p312_overlay_contract as parent
import s22plus_fyg8_p313_cross_gate_audit as cross_gate
import s22plus_fyg8_p313_generator as generator
import s22plus_fyg8_p313_guard_lifetime as guard_lifetime
import s22plus_fyg8_p313_hazard_closure as hazard_closure
import s22plus_fyg8_p313_runtime_fixture as runtime_fixture
import s22plus_fyg8_p313_telemetry_decoder as telemetry_decoder
import s22plus_fyg8_p313_telemetry_spec as telemetry
import s22plus_fyg8_p313_tracefs_abi_audit as tracefs_abi


SCHEMA = "s22plus_fyg8_p313_userspace_overlay_contract_v1"
CONTRACT_ID = guard_lifetime.OVERLAY_CONTRACT_ID
INTENT_SCHEMA = "s22plus_fyg8_p313_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P313_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P313_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P313_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent.TARGET
PROFILE = parent.PROFILE
PARENT_SOURCE_CONTRACT_ID = parent.PARENT_SOURCE_CONTRACT_ID
PARENT_SOURCE = parent.PARENT_SOURCE
PARENT_PATCH = parent.PARENT_PATCH
PARENT_IMAGE = parent.PARENT_IMAGE
PARENT_REPRO_RESULT = parent.PARENT_REPRO_RESULT
EXPECTED_IMAGE = parent.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p313/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    **parent.SOURCE_PATHS,
    "p313_telemetry_spec": PREFIX / "s22plus_fyg8_p313_telemetry_spec.py",
    "p313_telemetry_decoder": PREFIX / "s22plus_fyg8_p313_telemetry_decoder.py",
    "p313_runtime_transform": PREFIX / "s22plus_fyg8_p313_runtime_transform.py",
    "p313_generator": PREFIX / "s22plus_fyg8_p313_generator.py",
    "p313_cross_gate_audit": PREFIX / "s22plus_fyg8_p313_cross_gate_audit.py",
    "p313_runtime_fixture": PREFIX / "s22plus_fyg8_p313_runtime_fixture.py",
    "p313_guard_lifetime": PREFIX / "s22plus_fyg8_p313_guard_lifetime.py",
    "p313_guard_lifetime_fixture": PREFIX
    / "s22plus_fyg8_p313_guard_lifetime_fixture.py",
    "p313_hazard_closure": PREFIX / "s22plus_fyg8_p313_hazard_closure.py",
    "p313_tracefs_abi_audit": PREFIX / "s22plus_fyg8_p313_tracefs_abi_audit.py",
    "p313_process_v2_adapter_fixture": PREFIX
    / "s22plus_fyg8_p313_process_v2_adapter_fixture.py",
    "p313_overlay_contract": PREFIX / "s22plus_fyg8_p313_overlay_contract.py",
    "p313_overlay_intent": PREFIX / "s22plus_fyg8_p313_overlay_intent.py",
    "p313_candidate_contract": PREFIX / "s22plus_fyg8_p313_candidate_contract.py",
    "p313_stock_closure": PREFIX / "s22plus_fyg8_p313_e2_stock_closure.py",
    "p313_userspace_build": PREFIX / "s22plus_fyg8_p313_userspace_build.py",
    "p313_candidate_builder": PREFIX / "build_s22plus_fyg8_p313_candidate.py",
    "p313_static_checker": PREFIX / "s22plus_fyg8_p313_candidate_static_checker.py",
    "p313_process_promotion": PREFIX / "prepare_s22plus_fyg8_p313_process_v2.py",
    "p313_ready_manifest": PREFIX / "prepare_s22plus_fyg8_p313_ready_manifest.py",
    "process_v2_live_adapter": PREFIX / "device_action_f1_live_v2.py",
    "process_v2_cdc_observer": PREFIX / "device_action_cdc_acm_observer_v1.py",
    "p313_process_v2_tests": Path("tests/test_s22plus_fyg8_p313_process_v2.py"),
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = helpers.OverlayContractError
_receipt = helpers._receipt  # noqa: SLF001
_canonical = helpers._canonical  # noqa: SLF001
_read_regular = helpers._read_regular  # noqa: SLF001


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.13 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.13 SOURCE_KEYS differ")
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
    payload, value = _json_regular(
        root / generator.P312_INTENT, "P3.13 frozen P3.12 intent"
    )
    if (
        _receipt(payload) != generator.EXPECTED_P312_INTENT
        or value.get("schema") != parent.INTENT_SCHEMA
        or value.get("verdict") != parent.INTENT_VERDICT
        or value.get("contract_id") != parent.CONTRACT_ID
        or value.get("target") != parent.TARGET
        or value.get("profile") != parent.PROFILE
        or value.get("parent_source_contract_id")
        != parent.PARENT_SOURCE_CONTRACT_ID
        or value.get("verified") is not None
    ):
        raise OverlayContractError("P3.13 frozen P3.12 intent identity differs")
    # The parent is deliberately frozen: P3.13 changes common Process-v2
    # adapters, so asking P3.12 to re-receipt today's sources would mutate the
    # historical parent instead of validating it.  The exact intent receipt
    # above and generator._frozen_p312_bytes() below bind both the contract and
    # every materialized parent artifact.
    generator._frozen_p312_bytes(  # noqa: SLF001
        root,
        run_id=bytes.fromhex(value["run_id"]),
        unsat_tag=bytes.fromhex(value["unsat_tag_hex"]),
        profile=value["profile"],
    )
    try:
        parent_contract = value["parent_contract"]
        parent_candidate_contract = parent_contract["parent_candidate_contract"]
    except (KeyError, TypeError) as exc:
        raise OverlayContractError("P3.13 frozen P3.12 parent is incomplete") from exc
    return {
        "schema": parent.SCHEMA,
        "verdict": parent.CONTRACT_VERDICT,
        "contract_id": parent.CONTRACT_ID,
        "target": parent.TARGET,
        "profile": parent.PROFILE,
        "profile_number": 3,
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": parent.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": parent.CONTRACT_ID,
        "parent_contract": parent_contract,
        "parent_candidate_contract": parent_candidate_contract,
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "frozen_p311_baseline": value["frozen_p311_baseline"],
        "callsite_audit": value["callsite_audit"],
        "delayed_arm_qemu": value["delayed_arm_qemu"],
        "tracefs_abi": value["tracefs_abi"],
        "cross_gate_audit": value["cross_gate_audit"],
        "carrier_decoder_authority": value["carrier_decoder_authority"],
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
    parent_contract = verify_parent(root)
    p312_payload, p312_intent = _json_regular(
        root / generator.P312_INTENT, "P3.13 frozen P3.12 intent"
    )
    if (
        _receipt(p312_payload) != generator.EXPECTED_P312_INTENT
        or p312_intent.get("schema") != parent.INTENT_SCHEMA
        or p312_intent.get("verdict") != parent.INTENT_VERDICT
        or p312_intent.get("run_id") != parent_contract["run_id"]
        or p312_intent.get("unsat_tag_hex") != parent_contract["unsat_tag_hex"]
        or p312_intent.get("profile") != parent_contract["profile"]
    ):
        raise OverlayContractError("P3.13 frozen P3.12 intent differs")
    generated = generated_bytes(root, parent_contract)
    abi = tracefs_abi.audit(root, generated["trace_descriptor_header"])
    gates = cross_gate.audit(root)
    fixture = runtime_fixture.audit(root)
    hazards = hazard_closure.audit(root)
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
        "cycle_record_contract": [
            telemetry.CYCLE_CLEAN_RECORDS,
            telemetry.CYCLE_DRIFT_RECORDS,
            telemetry.CYCLE_OVERFLOW_RECORDS,
        ],
        "profile_hits_lower_bound_records": True,
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
        "frozen_p312_baseline": {
            "path": generator.P312_INTENT.as_posix(),
            **_receipt(p312_payload),
            "generated_artifacts": p312_intent["generated_artifacts"],
            "verified": True,
        },
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "tracefs_abi": abi,
        "cross_gate_audit": gates,
        "runtime_fixture": fixture,
        "hazard_closure": hazards,
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
    payload, value = _json_regular(intent_path, "P3.13 overlay intent")
    if value != create_intent_value(root):
        raise OverlayContractError("P3.13 overlay intent content differs")
    generated = generated_bytes(root, value["parent_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative, f"P3.13 materialized {key}"
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.13 materialized source differs: {key}")
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
        "frozen_p312_baseline": value["frozen_p312_baseline"],
        "tracefs_abi": value["tracefs_abi"],
        "cross_gate_audit": value["cross_gate_audit"],
        "runtime_fixture": value["runtime_fixture"],
        "hazard_closure": value["hazard_closure"],
        "telemetry": value["telemetry"],
        "observer": value["observer"],
        "safety": value["safety"],
        "verified": True,
    }
