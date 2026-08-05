#!/usr/bin/env python3
"""Bind the one-line P3.04 stock USB-notifier module-plan overlay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Mapping

import s22plus_fyg8_p303_overlay_contract as parent
import s22plus_fyg8_p304_generator as generator
import s22plus_fyg8_p304_plan_transform as plan


SCHEMA = "s22plus_fyg8_p304_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p304-stock-usb-notifier-bridge-v1"
INTENT_SCHEMA = "s22plus_fyg8_p304_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P304_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P304_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P304_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
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
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p304/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"
MODULE_PATH = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules/usb_notifier_qcom.ko"
)
MODULE_SIZE = 26344
MODULE_SHA256 = "73f937efc9302d5fa8c2758b5e71b80f52063141d72c063bfe73b1583c781ccb"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p304_plan_transform": PREFIX / "s22plus_fyg8_p304_plan_transform.py",
    "p304_generator": PREFIX / "s22plus_fyg8_p304_generator.py",
    "p304_overlay_contract": PREFIX / "s22plus_fyg8_p304_overlay_contract.py",
    "p304_overlay_intent": PREFIX / "s22plus_fyg8_p304_overlay_intent.py",
    "p304_candidate_contract": PREFIX / "s22plus_fyg8_p304_candidate_contract.py",
    "p304_userspace_build": PREFIX / "s22plus_fyg8_p304_userspace_build.py",
    "p304_candidate_builder": PREFIX / "build_s22plus_fyg8_p304_candidate.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)


class OverlayContractError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    ).encode("ascii") + b"\n"


def _read_regular(path: Path, label: str, maximum: int = 32 * 1024 * 1024) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise OverlayContractError(f"{label} is missing") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise OverlayContractError(f"{label} is indirect or not regular")
    if metadata.st_size <= 0 or metadata.st_size > maximum:
        raise OverlayContractError(f"{label} size is invalid")
    data = path.read_bytes()
    after = path.stat()
    if (
        len(data) != metadata.st_size
        or after.st_dev != metadata.st_dev
        or after.st_ino != metadata.st_ino
        or after.st_size != metadata.st_size
        or after.st_mtime_ns != metadata.st_mtime_ns
    ):
        raise OverlayContractError(f"{label} changed while reading")
    return data


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.04 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.04 SOURCE_KEYS differ")
    return rows


def verify_parent(root: Path) -> dict[str, Any]:
    try:
        value = parent.verify_intent(root, root / PARENT_INTENT)
    except (parent.OverlayContractError, OSError) as exc:
        raise OverlayContractError(str(exc)) from exc
    if (
        value.get("userspace_overlay_contract_id") != PARENT_OVERLAY_CONTRACT_ID
        or value.get("source_contract_id") != PARENT_SOURCE_CONTRACT_ID
        or value.get("profile") != PROFILE
        or value.get("fixed_image", {}).get("sha256") != EXPECTED_IMAGE["sha256"]
        or value.get("verified") is not True
    ):
        raise OverlayContractError("P3.04 parent P3.03 contract differs")
    return value


def generated_bytes(root: Path, parent_contract: Mapping[str, Any]) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(parent_contract["run_id"])),
        unsat_tag=bytes.fromhex(str(parent_contract["unsat_tag_hex"])),
        profile=str(parent_contract["profile"]),
    )


def module_receipt(root: Path) -> dict[str, Any]:
    data = _read_regular(root / MODULE_PATH, "P3.04 exact stock notifier module")
    value = {"path": MODULE_PATH.as_posix(), **_receipt(data)}
    if value["size"] != MODULE_SIZE or value["sha256"] != MODULE_SHA256:
        raise OverlayContractError("P3.04 stock notifier module receipt differs")
    return value


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
            **_receipt(_read_regular(root / PARENT_INTENT, "P3.04 parent intent")),
        },
        "fixed_image": {"path": PARENT_IMAGE.as_posix(), **EXPECTED_IMAGE},
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "callsite_audit": parent_contract["callsite_audit"],
        "telemetry": parent_contract["telemetry"],
        "module_delta": {
            "module": module_receipt(root),
            "runtime_name": plan.MODULE_RUNTIME,
            "plan_count_before": plan.MODULE_PLAN_COUNT - 1,
            "plan_count_after": plan.MODULE_PLAN_COUNT,
            "insert_after": "dwc3-msm.ko",
            "insert_before": "ucsi_glink.ko",
            "direct_dependencies_already_preceding": [
                "common_muic.ko",
                "dwc3-msm.ko",
                "usb_notify_layer.ko",
                "usb_typec_manager.ko",
                "vbus_notifier.ko",
            ],
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
    payload = _read_regular(intent_path, "P3.04 overlay intent")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError("P3.04 overlay intent is not ASCII JSON") from exc
    expected = create_intent_value(root)
    if value != expected:
        raise OverlayContractError("P3.04 overlay intent content differs")
    generated = generated_bytes(root, value["parent_overlay_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative, f"P3.04 materialized {key}", 4 * 1024 * 1024
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.04 materialized source differs: {key}")
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
        "verified": True,
        "safety": value["safety"],
    }
