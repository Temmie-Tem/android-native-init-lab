#!/usr/bin/env python3
"""Build a P3.15 candidate only after the live proof closure validates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

# Root-bound validation imports the packaging-wiring audit, which imports this
# module by its canonical name. A direct script invocation otherwise creates a
# second module object (``__main__`` plus the canonical import), so the
# validated gate state and the late artifact-safety callback can diverge.
if __name__ == "__main__":
    sys.modules.setdefault("build_s22plus_fyg8_p315_candidate", sys.modules[__name__])

import build_s22plus_fyg8_p314_candidate as parent
import s22plus_fyg8_p315_candidate_contract as candidate_contract
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_e2_stock_closure as closure
import s22plus_fyg8_p315_overlay_contract as contract
import s22plus_fyg8_p315_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p315_candidate_artifact_result_v1"
VERDICT = "PASS_P315_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
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
    "workspace/private/outputs/s22plus_fyg8_p315/qualification/"
    "prepackaging-closure.json"
)
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p315/candidate-a")
BOOT_SIZE = parent.BOOT_SIZE
KERNEL_START = parent.KERNEL_START
KERNEL_END = parent.KERNEL_END
BuildError = parent.BuildError
receipt = parent.receipt

_PREPACKAGING_RECEIPT: dict[str, Any] | None = None
_PREPACKAGING_VALIDATION: dict[str, Any] | None = None


def _generic_base():
    return parent.parent.parent.base


def _read_prepackaging(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = candidate_contract.stable_read(
        path, "P3.15 prepackaging closure", 32 * 1024 * 1024
    )
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError("P3.15 prepackaging closure is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BuildError("P3.15 prepackaging closure root differs")
    return value, {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def verify_repro_result(
    result_path: Path,
    image_receipt: dict[str, Any],
    exact_contract: dict[str, Any],
    **_ignored: Any,
) -> dict[str, Any]:
    return parent.verify_repro_result(result_path, image_receipt, exact_contract)


def artifact_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    if _PREPACKAGING_RECEIPT is None or _PREPACKAGING_VALIDATION is None:
        raise BuildError("P3.15 prepackaging gate was not established")
    result = parent.parent.parent._BASE_ARTIFACT_SAFETY(  # noqa: SLF001
        exact_contract
    )
    result.update(
        {
            "candidate_module_binaries_injected": 0,
            "stock_vendor_ramdisk_module_reused": True,
            "p315_kernel_rebuild": False,
            "p315_full_lto_ab": False,
            "p315_observer": exact_contract["observer"],
            "p315_cross_gate_audit": exact_contract["cross_gate_audit"],
            "p315_restart_source_geometry": exact_contract[
                "restart_source_geometry"
            ],
            "p315_runtime_fixture": exact_contract["runtime_fixture"],
            "p315_prepackaging_closure": _PREPACKAGING_RECEIPT,
            "p315_prepackaging_validation": _PREPACKAGING_VALIDATION,
            "fixed_image_sha256": contract.EXPECTED_IMAGE["sha256"],
        }
    )
    return result


def _configure() -> None:
    parent._configure()  # noqa: SLF001
    candidate_contract._configure()  # noqa: SLF001
    base = _generic_base()
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
        raise BuildError(f"P3.15 candidate output already exists: {output}")
    value, closure_receipt = _read_prepackaging(
        candidate_contract.intent.resolve(root, args.prepackaging)
    )
    validation = design.validate_successor_artifact(value, root=root)
    _PREPACKAGING_RECEIPT = closure_receipt
    _PREPACKAGING_VALIDATION = validation
    try:
        _configure()
        return parent.parent.parent.base.build_candidate(args)
    finally:
        _PREPACKAGING_RECEIPT = None
        _PREPACKAGING_VALIDATION = None


def __getattr__(name: str):
    _configure()
    return getattr(_generic_base(), name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    _configure()
    base = _generic_base()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--prepackaging", type=Path, default=DEFAULT_PREPACKAGING)
    selected, remaining = parser.parse_known_args(argv)
    args = base.parse_args(remaining)
    args.prepackaging = selected.prepackaging
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_candidate(parse_args(argv))
    except (
        BuildError,
        design.P315DesignError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
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
