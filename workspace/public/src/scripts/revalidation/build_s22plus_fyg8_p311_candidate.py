#!/usr/bin/env python3
"""Build a P3.11 fixed-P3.10-Image boot-only candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import build_s22plus_fyg8_p304_candidate as parent
import s22plus_fyg8_p311_candidate_contract as candidate_contract
import s22plus_fyg8_p311_e2_stock_closure as closure
import s22plus_fyg8_p311_overlay_contract as contract
import s22plus_fyg8_p311_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p311_candidate_artifact_result_v1"
VERDICT = "PASS_P311_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = contract.TARGET
P286_SOURCE_CONTRACT_ID = contract.PARENT_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = contract.PARENT_IMAGE
DEFAULT_REPRO_RESULT = contract.PARENT_REPRO_RESULT
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = parent.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = parent.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = parent.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = parent.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p311/candidate-a")
BOOT_SIZE = parent.BOOT_SIZE
KERNEL_START = parent.KERNEL_START
KERNEL_END = parent.KERNEL_END
BuildError = parent.BuildError
receipt = parent.receipt


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
    **_ignored,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    if result_path != root / contract.PARENT_REPRO_RESULT:
        raise BuildError("P3.11 P3.10 closure path differs")
    value, result_receipt = _read_json(result_path, "P3.11 P3.10 independent closure")
    if (
        value.get("verdict") != "PASS_P310_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
        or value.get("build_repro", {}).get("image") != image_receipt
        or image_receipt != contract.EXPECTED_IMAGE
        or value.get("candidate_contract") != exact_contract.get("parent_candidate_contract")
    ):
        raise BuildError("P3.11 fixed P3.10 closure differs")
    return {
        "result": result_receipt,
        "verdict": value["verdict"],
        "image": image_receipt,
        "parent_source_contract_id": contract.PARENT_SOURCE_CONTRACT_ID,
        "two_clean_builds_byte_identical": True,
        "linked_audit_verified": True,
        "kernel_rebuilt_for_p311": False,
    }


def artifact_safety(exact_contract: dict) -> dict:
    result = parent._BASE_ARTIFACT_SAFETY(exact_contract)  # noqa: SLF001
    result.update({
        "candidate_module_binaries_injected": 0,
        "stock_vendor_ramdisk_module_reused": True,
        "p311_kernel_rebuild": False,
        "p311_full_lto_ab": False,
        "p311_observer": exact_contract["observer"],
        "p311_cross_gate_audit": exact_contract["cross_gate_audit"],
        "p311_tracefs_abi": exact_contract["tracefs_abi"],
        "fixed_image_sha256": contract.EXPECTED_IMAGE["sha256"],
    })
    return result


def _configure() -> None:
    parent._configure()
    candidate_contract._configure()  # noqa: SLF001
    base = parent.base
    base.candidate_contract = candidate_contract
    base.userspace = userspace
    base.p286_closure = closure
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


def __getattr__(name: str):
    _configure()
    return getattr(parent.base, name)


def build_candidate(args):
    _configure()
    return parent.base.build_candidate(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return parent.base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return parent.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
