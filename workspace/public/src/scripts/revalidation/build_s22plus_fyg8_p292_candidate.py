#!/usr/bin/env python3
"""Build one deterministic boot-only P2.92 FYG8 candidate host-only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_s22plus_fyg8_p286_candidate as base
import s22plus_fyg8_p290_contract_spec as p292_spec
import s22plus_fyg8_p292_boot_only_packager as packager
import s22plus_fyg8_p292_build_repro_check as repro
import s22plus_fyg8_p292_candidate_contract as candidate_contract
import s22plus_fyg8_p292_e2_stock_closure as p292_closure
import s22plus_fyg8_p292_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p292_candidate_artifact_result_v1"
VERDICT = "PASS_P292_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = candidate_contract.TARGET
P292_SOURCE_CONTRACT_ID = repro.P292_SOURCE_CONTRACT_ID
P286_SOURCE_CONTRACT_ID = P292_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = repro.DEFAULT_BUILD_A / "Image"
DEFAULT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p292/"
    "build-repro-result.json"
)
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = base.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = base.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = base.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = base.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p292/candidate-a"
)
BOOT_SIZE = base.BOOT_SIZE
KERNEL_START = base.KERNEL_START
KERNEL_END = base.KERNEL_END
BuildError = base.BuildError
receipt = base.receipt


def _configure() -> None:
    candidate_contract._configure()
    userspace._configure()
    repro._configure()
    packager._configure()
    base.packager = packager
    base.repro = repro
    base.candidate_contract = candidate_contract
    base.userspace = userspace
    base.p286_spec = p292_spec
    base.p286_closure = p292_closure
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.P286_SOURCE_CONTRACT_ID = P292_SOURCE_CONTRACT_ID
    base.DEFAULT_IMAGE = DEFAULT_IMAGE
    base.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    base.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    base.DEFAULT_OUT = DEFAULT_OUT
    base.verify_repro_result = verify_repro_result


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def verify_repro_result(
    result_path: Path,
    image_receipt: dict[str, Any],
    exact_contract: dict[str, Any],
    *,
    intent_path: Path | None = None,
    patch_path: Path | None = None,
) -> dict[str, Any]:
    _configure()
    value, result_receipt = base._read_json(  # noqa: SLF001
        result_path, "P2.92 build reproducibility result"
    )
    if (
        value.get("schema") != repro.SCHEMA
        or value.get("target") != TARGET
        or value.get("verdict") != repro.VERDICT
        or value.get("candidate_contract") != exact_contract
        or value.get("linked_audit", {}).get("verified") is not True
        or not isinstance(value.get("byte_identical_artifacts"), dict)
        or set(value["byte_identical_artifacts"])
        != set(repro.ARTIFACT_LIMITS) - {"build-result.json"}
        or any(
            item is not True
            for item in value["byte_identical_artifacts"].values()
        )
    ):
        raise BuildError(
            "P2.92 build reproducibility result is not accepted"
        )
    linked = value.get("linked_audit", {})
    if (
        linked.get("audit_adapter")
        != "s22plus-fyg8-p292-linked-audit-v1"
        or linked.get("source_contract_validator", {})
        .get("writer_guard", {})
        .get("guard_dominates_retained_stores")
        is not True
        or linked.get("postbuild_audit", {}).get("verified") is not True
    ):
        raise BuildError("P2.92 linked audit adapter mismatch")
    expected_image = (
        value.get("build_a", {}).get("artifacts", {}).get("Image")
    )
    if expected_image != image_receipt:
        raise BuildError(
            "P2.92 supplied Image differs from reproducibility closure"
        )
    if intent_path is None or patch_path is None:
        raise BuildError("P2.92 selected build-input paths are missing")
    try:
        qualification = repro.verify_p292_qualification_file(
            value.get("pre_lto_qualification"),
            exact_contract,
            intent_path=intent_path,
            patch_path=patch_path,
            root=candidate_contract.intent.repo_root(),
        )
    except repro.CheckError as exc:
        raise BuildError(str(exc)) from exc
    return {
        "result": result_receipt,
        "verdict": value["verdict"],
        "image": image_receipt,
        "pre_lto_qualification": qualification,
        "two_clean_builds_byte_identical": True,
        "linked_audit_verified": True,
    }


def artifact_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    _configure()
    return base.artifact_safety(exact_contract)


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
