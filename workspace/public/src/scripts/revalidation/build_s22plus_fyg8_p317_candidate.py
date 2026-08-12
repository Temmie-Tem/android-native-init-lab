#!/usr/bin/env python3
"""Build one P3.17 boot-only candidate after its closure validates."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
from typing import Any, Iterator

import build_s22plus_fyg8_p310_candidate as p310_builder
import build_s22plus_fyg8_p316_candidate as base
import s22plus_fyg8_p317_candidate_contract as candidate_contract
import s22plus_fyg8_p317_e2_stock_closure as closure
import s22plus_fyg8_p317_overlay_contract as contract
import s22plus_fyg8_p317_qualification_closure as qualification
import s22plus_fyg8_p317_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p317_candidate_artifact_result_v1"
VERDICT = "PASS_P317_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = contract.TARGET
P286_SOURCE_CONTRACT_ID = contract.PARENT_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = contract.PARENT_IMAGE
DEFAULT_REPRO_RESULT = contract.PARENT_REPRO_RESULT
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = base.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = base.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = base.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = base.DEFAULT_MAGISKBOOT
DEFAULT_DIAGNOSTIC = base.DEFAULT_DIAGNOSTIC
DEFAULT_PREPACKAGING = qualification.DEFAULT_PREPACKAGING
DEFAULT_OUT = qualification.DEFAULT_CANDIDATE_A
DIAGNOSTIC_NAME = base.DIAGNOSTIC_NAME
DIAGNOSTIC_RAMDISK_PATH = base.DIAGNOSTIC_RAMDISK_PATH
BOOT_SIZE = base.BOOT_SIZE
KERNEL_START = base.KERNEL_START
KERNEL_END = base.KERNEL_END
BuildError = base.BuildError
receipt = base.receipt


def artifact_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    if base._PREPACKAGING_RECEIPT is None or base._PREPACKAGING_VALIDATION is None:  # noqa: SLF001
        raise BuildError("P3.17 prepackaging gate was not established")
    result = p310_builder._BASE_ARTIFACT_SAFETY(exact_contract)  # noqa: SLF001
    result.update({
        "fixed_p310_image": True,
        "p317_kernel_rebuild": False,
        "p317_full_lto_ab": False,
        "early_stock_module_count": 69,
        "custom_module_binaries_injected": 1,
        "diagnostic_late_load_only": True,
        "diagnostic_absent_from_early_plan": True,
        "p317_prepackaging_closure": base._PREPACKAGING_RECEIPT,  # noqa: SLF001
        "p317_prepackaging_validation": base._PREPACKAGING_VALIDATION,  # noqa: SLF001
        "p317_runtime_fixture": exact_contract["runtime_fixture"],
        "p317_late_loader_lifecycle": exact_contract["late_loader_lifecycle"],
        "p317_executability_gates": exact_contract["executability_gates"],
        "p317_sidecar_positive_control": exact_contract["sidecar_positive_control"],
        "fixed_image_sha256": contract.EXPECTED_IMAGE["sha256"],
    })
    return result


@contextmanager
def _configured() -> Iterator[None]:
    names = (
        "candidate_contract", "closure", "contract", "qualification",
        "userspace", "SCHEMA", "VERDICT", "TARGET", "P286_SOURCE_CONTRACT_ID",
        "DEFAULT_IMAGE", "DEFAULT_REPRO_RESULT", "DEFAULT_USERSPACE",
        "DEFAULT_PREPACKAGING", "DEFAULT_OUT", "artifact_safety",
    )
    values = {
        "candidate_contract": candidate_contract, "closure": closure,
        "contract": contract, "qualification": qualification,
        "userspace": userspace, "SCHEMA": SCHEMA, "VERDICT": VERDICT,
        "TARGET": TARGET, "P286_SOURCE_CONTRACT_ID": P286_SOURCE_CONTRACT_ID,
        "DEFAULT_IMAGE": DEFAULT_IMAGE, "DEFAULT_REPRO_RESULT": DEFAULT_REPRO_RESULT,
        "DEFAULT_USERSPACE": DEFAULT_USERSPACE,
        "DEFAULT_PREPACKAGING": DEFAULT_PREPACKAGING, "DEFAULT_OUT": DEFAULT_OUT,
        "artifact_safety": artifact_safety,
    }
    previous = {name: getattr(base, name) for name in names}
    for name, value in values.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def build_candidate(args: argparse.Namespace) -> dict[str, Any]:
    with _configured():
        return base.build_candidate(args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    with _configured():
        return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_candidate(parse_args(argv))
    except (
        BuildError, qualification.QualificationError,
        candidate_contract.ContractError, candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired, OSError, ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({
        "schema": SCHEMA, "verdict": result["verdict"],
        "boot_sha256": result["outputs"]["boot_img"]["sha256"],
        "ap_sha256": result["outputs"]["ap_tar_md5"]["sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
