#!/usr/bin/env python3
"""Bind the P3.05 generic folded-tail checkpoint overlay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p304_overlay_contract as parent
import s22plus_fyg8_p305_generator as generator


SCHEMA = "s22plus_fyg8_p305_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p305-generic-folded-module-tail-v1"
INTENT_SCHEMA = "s22plus_fyg8_p305_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P305_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P305_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P305_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent.TARGET
PROFILE = parent.PROFILE
PARENT_OVERLAY_CONTRACT_ID = parent.CONTRACT_ID
PARENT_SOURCE_CONTRACT_ID = parent.PARENT_SOURCE_CONTRACT_ID
PARENT_INTENT = parent.DEFAULT_INTENT
PARENT_PATCH = parent.PARENT_PATCH
PARENT_SOURCE = parent.PARENT_SOURCE
PARENT_IMAGE = parent.PARENT_IMAGE
PARENT_REPRO_RESULT = parent.PARENT_REPRO_RESULT
EXPECTED_IMAGE = parent.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p305/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p305_runtime_transform": PREFIX / "s22plus_fyg8_p305_runtime_transform.py",
    "p305_generator": PREFIX / "s22plus_fyg8_p305_generator.py",
    "p305_overlay_contract": PREFIX / "s22plus_fyg8_p305_overlay_contract.py",
    "p305_overlay_intent": PREFIX / "s22plus_fyg8_p305_overlay_intent.py",
    "p305_candidate_contract": PREFIX / "s22plus_fyg8_p305_candidate_contract.py",
    "p305_userspace_build": PREFIX / "s22plus_fyg8_p305_userspace_build.py",
    "p305_candidate_builder": PREFIX / "build_s22plus_fyg8_p305_candidate.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = parent.OverlayContractError
_receipt = parent._receipt  # noqa: SLF001
_canonical = parent._canonical  # noqa: SLF001
_read_regular = parent._read_regular  # noqa: SLF001


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.05 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.05 SOURCE_KEYS differ")
    return rows


def verify_parent(root: Path) -> dict[str, Any]:
    value = parent.verify_intent(root, root / PARENT_INTENT)
    if (
        value.get("userspace_overlay_contract_id") != PARENT_OVERLAY_CONTRACT_ID
        or value.get("source_contract_id") != PARENT_SOURCE_CONTRACT_ID
        or value.get("profile") != PROFILE
        or value.get("fixed_image", {}).get("sha256") != EXPECTED_IMAGE["sha256"]
        or value.get("verified") is not True
    ):
        raise OverlayContractError("P3.05 parent P3.04 contract differs")
    return value


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
    value = {
        "schema": INTENT_SCHEMA,
        "verdict": INTENT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "run_id": parent_contract["run_id"],
        "unsat_tag_hex": parent_contract["unsat_tag_hex"],
        "parent_overlay_contract_id": PARENT_OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "parent_overlay_contract": parent_contract,
        "parent_overlay_intent": {
            "path": PARENT_INTENT.as_posix(),
            **_receipt(_read_regular(root / PARENT_INTENT, "P3.05 parent intent")),
        },
        "fixed_image": {"path": PARENT_IMAGE.as_posix(), **EXPECTED_IMAGE},
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "callsite_audit": parent_contract["callsite_audit"],
        "telemetry": parent_contract["telemetry"],
        "module_delta": parent_contract["module_delta"],
        "folded_tail": {
            "individual_module_indices": [0, 58],
            "folded_module_indices": [59, 60],
            "success_stage": 0x7B,
            "success_item_index": 59,
            "first_gate_stage": 0x7C,
            "first_gate_item_index": 0,
            "failure_detail_base": 0x700,
            "notifier_failure_detail": 0x73B,
            "ucsi_failure_detail": 0x73C,
            "maximum_module_count": 256,
            "later_ordinals_unchanged": True,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "module_binaries_injected": 0,
            "stock_vendor_ramdisk_module_reused": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload = _read_regular(intent_path, "P3.05 overlay intent")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError("P3.05 overlay intent is not ASCII JSON") from exc
    expected = create_intent_value(root)
    if value != expected:
        raise OverlayContractError("P3.05 overlay intent content differs")
    generated = generated_bytes(root, value["parent_overlay_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative,
            f"P3.05 materialized {key}",
            4 * 1024 * 1024,
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.05 materialized source differs: {key}")
    parent_contract = value["parent_overlay_contract"]
    return {
        "schema": SCHEMA,
        "verdict": CONTRACT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": parent_contract["profile_number"],
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": CONTRACT_ID,
        "parent_overlay_contract_id": PARENT_OVERLAY_CONTRACT_ID,
        "parent_overlay_contract": parent_contract,
        "parent_candidate_contract": parent_contract["parent_candidate_contract"],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "callsite_audit": value["callsite_audit"],
        "telemetry": value["telemetry"],
        "module_delta": value["module_delta"],
        "folded_tail": value["folded_tail"],
        "verified": True,
        "safety": value["safety"],
    }
