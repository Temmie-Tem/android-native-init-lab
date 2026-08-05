#!/usr/bin/env python3
"""Build a P3.04 fixed-Image candidate with the stock USB notifier bridge."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import build_s22plus_fyg8_p286_candidate as base
import s22plus_fyg8_p300_build_repro_check as p300_repro
import s22plus_fyg8_p300_e2_stock_closure as p300_closure
import s22plus_fyg8_p300_telemetry_spec as p300_spec
import s22plus_fyg8_p303_boot_only_packager as packager
import s22plus_fyg8_p304_candidate_contract as candidate_contract
import s22plus_fyg8_p304_overlay_contract as contract
import s22plus_fyg8_p304_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p304_candidate_artifact_result_v1"
VERDICT = "PASS_P304_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = contract.TARGET
P286_SOURCE_CONTRACT_ID = contract.PARENT_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = contract.PARENT_IMAGE
DEFAULT_REPRO_RESULT = contract.PARENT_REPRO_RESULT
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = base.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = base.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = base.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = base.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p304/candidate-a")
BOOT_SIZE = base.BOOT_SIZE
KERNEL_START = base.KERNEL_START
KERNEL_END = base.KERNEL_END
BuildError = base.BuildError
receipt = base.receipt
_BASE_ARTIFACT_SAFETY = base.artifact_safety


def _read_json(path: Path, label: str) -> tuple[dict, dict]:
    payload = candidate_contract.stable_read(path, label, 16 * 1024 * 1024)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BuildError(f"{label} root differs")
    return value, {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def verify_repro_result(
    result_path: Path,
    image_receipt: dict[str, Any],
    exact_contract: dict[str, Any],
    *,
    intent_path: Path | None = None,
    patch_path: Path | None = None,
) -> dict[str, Any]:
    del intent_path, patch_path
    root = candidate_contract.intent.repo_root()
    if result_path != root / contract.PARENT_REPRO_RESULT:
        raise BuildError("P3.04 parent reproducibility path differs")
    value, result_receipt = _read_json(result_path, "P3.04 fixed P3.00 reproducibility result")
    parent_candidate = exact_contract.get("parent_candidate_contract")
    byte_identical = value.get("byte_identical_artifacts")
    linked = value.get("linked_audit", {})
    qualification = value.get("pre_lto_qualification", {})
    if (
        value.get("schema") != p300_repro.SCHEMA
        or value.get("verdict") != p300_repro.VERDICT
        or value.get("target") != TARGET
        or value.get("candidate_contract") != parent_candidate
        or not isinstance(byte_identical, dict)
        or set(byte_identical) != set(p300_repro.ARTIFACT_LIMITS) - {"build-result.json"}
        or any(item is not True for item in byte_identical.values())
        or value.get("build_a", {}).get("artifacts", {}).get("Image") != image_receipt
        or linked.get("verified") is not True
        or qualification.get("verified") is not True
        or qualification.get("source_contract_id") != contract.PARENT_SOURCE_CONTRACT_ID
        or qualification.get("run_id") != exact_contract.get("run_id")
    ):
        raise BuildError("P3.04 fixed P3.00 reproducibility closure differs")
    return {
        "result": result_receipt,
        "verdict": value["verdict"],
        "image": image_receipt,
        "parent_source_contract_id": contract.PARENT_SOURCE_CONTRACT_ID,
        "two_clean_builds_byte_identical": True,
        "linked_audit_verified": True,
        "kernel_rebuilt_for_p304": False,
    }


def artifact_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    result = _BASE_ARTIFACT_SAFETY(exact_contract)
    result.update({
        "candidate_module_binaries_injected": 0,
        "stock_vendor_ramdisk_module_reused": True,
        "p304_kernel_rebuild": False,
        "p304_full_lto_ab": False,
        "fixed_image_sha256": contract.EXPECTED_IMAGE["sha256"],
        "usb_notifier_qcom": exact_contract["module_delta"],
    })
    return result


def _configure() -> None:
    base.packager = packager
    base.repro = p300_repro
    base.candidate_contract = candidate_contract
    base.userspace = userspace
    base.p286_spec = p300_spec
    base.p286_closure = p300_closure
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.P286_SOURCE_CONTRACT_ID = P286_SOURCE_CONTRACT_ID
    base.DEFAULT_IMAGE = DEFAULT_IMAGE
    base.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    base.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    base.DEFAULT_OUT = DEFAULT_OUT
    base.verify_repro_result = verify_repro_result
    base.artifact_safety = artifact_safety


def build_candidate(args):  # noqa: ANN001, ANN201
    _configure()
    return base.build_candidate(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
