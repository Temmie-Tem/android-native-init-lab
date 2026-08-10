#!/usr/bin/env python3
"""Build a P3.14 candidate only after the prepackaging gate passes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import build_s22plus_fyg8_p313_candidate as parent
import s22plus_fyg8_p314_candidate_contract as candidate_contract
import s22plus_fyg8_p314_design_contract as design
import s22plus_fyg8_p314_e2_stock_closure as closure
import s22plus_fyg8_p314_overlay_contract as contract
import s22plus_fyg8_p314_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p314_candidate_artifact_result_v1"
VERDICT = "PASS_P314_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = contract.TARGET
P286_SOURCE_CONTRACT_ID = contract.PARENT_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = contract.PARENT_IMAGE
DEFAULT_REPRO_RESULT = contract.PARENT_REPRO_RESULT
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = parent.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = parent.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = parent.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = parent.DEFAULT_MAGISKBOOT
DEFAULT_PREPACKAGING = Path(
    "workspace/private/outputs/s22plus_fyg8_p314/qualification/"
    "prepackaging-closure.json"
)
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p314/candidate-a")
BOOT_SIZE = parent.BOOT_SIZE
KERNEL_START = parent.KERNEL_START
KERNEL_END = parent.KERNEL_END
BuildError = parent.BuildError
receipt = parent.receipt

_PREPACKAGING_RECEIPT: dict[str, Any] | None = None
_PREPACKAGING_VALIDATION: dict[str, Any] | None = None


def _read_prepackaging(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = candidate_contract.stable_read(
        path, "P3.14 prepackaging closure", 32 * 1024 * 1024
    )
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError("P3.14 prepackaging closure is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BuildError("P3.14 prepackaging closure root differs")
    return value, {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _read_intent_authority(root: Path, path: Path) -> dict[str, Any]:
    payload = candidate_contract.stable_read(
        path, "P3.14 overlay intent authority", 64 * 1024 * 1024
    )
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError("P3.14 overlay intent authority is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BuildError("P3.14 overlay intent authority root differs")
    return design.prepackaging_authority(root, value)


def verify_repro_result(
    result_path: Path,
    image_receipt: dict[str, Any],
    exact_contract: dict[str, Any],
    **_ignored: Any,
) -> dict[str, Any]:
    return parent.verify_repro_result(result_path, image_receipt, exact_contract)


def artifact_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    if _PREPACKAGING_RECEIPT is None or _PREPACKAGING_VALIDATION is None:
        raise BuildError("P3.14 prepackaging gate was not established")
    result = parent.artifact_safety(exact_contract)
    result.update(
        {
            "p314_kernel_rebuild": False,
            "p314_full_lto_ab": False,
            "p314_observer": exact_contract["observer"],
            "p314_cross_gate_audit": exact_contract["cross_gate_audit"],
            "p314_hazard_closure": exact_contract["hazard_closure"],
            "p314_matrix_fixture": exact_contract["matrix_fixture"],
            "p314_process_v2_adapter_fixture": exact_contract[
                "process_v2_adapter_fixture"
            ],
            "p314_design_requirements_sha256": design.requirements_sha256(),
            "p314_prepackaging_closure": _PREPACKAGING_RECEIPT,
            "p314_prepackaging_validation": _PREPACKAGING_VALIDATION,
        }
    )
    return result


def _configure() -> None:
    parent._configure()  # noqa: SLF001
    base = parent.parent.base
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


def build_candidate(args: argparse.Namespace) -> dict[str, Any]:
    global _PREPACKAGING_RECEIPT, _PREPACKAGING_VALIDATION

    root = candidate_contract.intent.repo_root()
    output = candidate_contract.intent.resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"P3.14 candidate output already exists: {output}")
    value, closure_receipt = _read_prepackaging(
        candidate_contract.intent.resolve(root, args.prepackaging)
    )
    authority = _read_intent_authority(
        root, candidate_contract.intent.resolve(root, args.intent)
    )
    validation = design.validate_prepackaging_artifact(
        value, authority=authority
    )
    _PREPACKAGING_RECEIPT = closure_receipt
    _PREPACKAGING_VALIDATION = validation
    try:
        _configure()
        return parent.parent.base.build_candidate(args)
    finally:
        _PREPACKAGING_RECEIPT = None
        _PREPACKAGING_VALIDATION = None


def __getattr__(name: str):
    _configure()
    return getattr(parent.parent.base, name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=candidate_contract.DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=candidate_contract.DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=candidate_contract.DEFAULT_PATCH)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--prepackaging", type=Path, default=DEFAULT_PREPACKAGING)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_candidate(parse_args(argv))
    except (
        BuildError,
        design.P314DesignError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
        ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": result["verdict"],
                "boot_sha256": result["outputs"]["boot_img"]["sha256"],
                "ap_sha256": result["outputs"]["ap_tar_md5"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
