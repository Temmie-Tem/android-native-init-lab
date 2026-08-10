#!/usr/bin/env python3
"""Independently audit one reproducible P3.15 candidate pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import build_s22plus_fyg8_p315_candidate as candidate
import s22plus_fyg8_p314_candidate_static_checker as inherited
import s22plus_fyg8_p315_candidate_contract as contract
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_e2_stock_closure as closure
import s22plus_fyg8_p315_overlay_contract as overlay
import s22plus_fyg8_p315_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_p315_qualification_closure as qualification
import s22plus_fyg8_p315_runtime_fixture as runtime_fixture
import s22plus_fyg8_p315_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p315_candidate_static_checker_v1"
VERDICT = "PASS_P315_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = qualification.DEFAULT_CANDIDATE_B
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = inherited.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = inherited.DEFAULT_BUILD_A
DEFAULT_BUILD_B = inherited.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = inherited.DEFAULT_NM
DEFAULT_OBJDUMP = inherited.DEFAULT_OBJDUMP
DEFAULT_QUALIFICATION = qualification.DEFAULT_OUT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p315/static-check-result.json")
CheckError = inherited.CheckError


def _configure() -> None:
    inherited.candidate = candidate
    inherited.contract = contract
    inherited.closure = closure
    inherited.overlay = overlay
    inherited.runtime_fixture = runtime_fixture
    inherited.adapter_fixture = adapter_fixture
    inherited.userspace = userspace
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    inherited.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    inherited.DEFAULT_IMAGE = DEFAULT_IMAGE
    inherited.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    inherited.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    inherited.DEFAULT_BASE_BOOT = DEFAULT_BASE_BOOT
    inherited.DEFAULT_VENDOR_RAMDISK = DEFAULT_VENDOR_RAMDISK
    inherited.DEFAULT_VENDOR_BOOT = DEFAULT_VENDOR_BOOT
    inherited.DEFAULT_LZ4 = DEFAULT_LZ4
    inherited.DEFAULT_MAGISKBOOT = DEFAULT_MAGISKBOOT
    inherited.DEFAULT_SOURCE = DEFAULT_SOURCE
    inherited.DEFAULT_INTENT = DEFAULT_INTENT
    inherited.DEFAULT_PATCH = DEFAULT_PATCH
    inherited.DEFAULT_OUT = DEFAULT_OUT
    inherited._configure()  # noqa: SLF001


def _base():
    _configure()
    return inherited._base()  # noqa: SLF001


def __getattr__(name: str):
    return getattr(_base(), name)


def audit(args: argparse.Namespace) -> dict:
    base = _base()
    root = base.repo_root()
    payload = contract.stable_read(
        base.resolve(root, args.qualification),
        "P3.15 final qualification closure",
        64 * 1024 * 1024,
    )
    try:
        qualified = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("P3.15 final qualification is not ASCII JSON") from exc
    if not isinstance(qualified, dict):
        raise CheckError("P3.15 final qualification root differs")
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    trees = (
        qualification._tree_receipts(base.resolve(root, args.candidate)),  # noqa: SLF001
        qualification._tree_receipts(base.resolve(root, args.candidate_b)),  # noqa: SLF001
    )
    if trees[0] != trees[1]:
        raise CheckError("P3.15 candidate tree receipts differ")
    design.validate_qualification_artifact(
        qualified, root=root, candidate_tree=trees[0]
    )
    prepackaging = qualified.get("prepackaging_closure")
    prepackaging_receipt = qualified.get("prepackaging_receipt")
    if not isinstance(prepackaging, dict) or not isinstance(prepackaging_receipt, dict):
        raise CheckError("P3.15 prepackaging receipt differs")
    candidate._PREPACKAGING_RECEIPT = prepackaging_receipt  # noqa: SLF001
    candidate._PREPACKAGING_VALIDATION = design.validate_successor_artifact(  # noqa: SLF001
        prepackaging, root=root
    )
    try:
        result = base.audit(args)
    finally:
        candidate._PREPACKAGING_RECEIPT = None  # noqa: SLF001
        candidate._PREPACKAGING_VALIDATION = None  # noqa: SLF001
    fixture = runtime_fixture.audit(root)
    adapter = adapter_fixture.audit(root)
    if (
        fixture.get("verified") is not True
        or adapter.get("verified") is not True
        or exact["matrix_fixture"].get("matrix_cells") != 251_450
        or exact["prepackaging_closure"] != prepackaging
    ):
        raise CheckError("P3.15 qualification inputs differ")
    result.update(
        {
            "p315_tracefs_abi": exact["tracefs_abi"],
            "p315_cross_gate_audit": exact["cross_gate_audit"],
            "p315_restart_source_geometry": exact["restart_source_geometry"],
            "p315_runtime_fixture": fixture,
            "p315_matrix_fixture": exact["matrix_fixture"],
            "p315_process_v2_adapter_fixture": adapter,
            "p315_prepackaging_closure": prepackaging,
            "p315_qualification_closure": qualified,
            "p315_telemetry": exact["telemetry"],
            "p315_observer": exact["observer"],
        }
    )
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--qualification", type=Path, default=DEFAULT_QUALIFICATION)
    selected, remaining = parser.parse_known_args(argv)
    args = _base().parse_args(remaining)
    args.qualification = selected.qualification
    return args


def main(argv: list[str] | None = None) -> int:
    base = _base()
    try:
        args = parse_args(argv)
        result = audit(args)
        encoded = json.dumps(
            result, indent=2, sort_keys=True, allow_nan=False
        ).encode("ascii") + b"\n"
        base.durable_create(base.resolve(base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        design.P315DesignError,
        qualification.QualificationError,
        subprocess.TimeoutExpired,
        OSError,
        ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
