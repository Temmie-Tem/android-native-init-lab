#!/usr/bin/env python3
"""Build one deterministic boot-only P3.10 FYG8 candidate host-only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_s22plus_fyg8_p286_candidate as base
import s22plus_fyg8_p310_boot_only_packager as packager
import s22plus_fyg8_p310_build_repro_check as repro
import s22plus_fyg8_p310_candidate_contract as candidate_contract
import s22plus_fyg8_p310_e2_stock_closure as closure
import s22plus_fyg8_p308_telemetry_spec as spec
import s22plus_fyg8_p310_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p310_candidate_artifact_result_v1"
VERDICT = "PASS_P310_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = candidate_contract.TARGET
P310_SOURCE_CONTRACT_ID = repro.P310_SOURCE_CONTRACT_ID
P286_SOURCE_CONTRACT_ID = P310_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = repro.DEFAULT_BUILD_A / "Image"
DEFAULT_REPRO_RESULT = Path("workspace/private/outputs/s22plus_fyg8_p310/build-repro-result.json")
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = base.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = base.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = base.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = base.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p310/candidate-a")
BOOT_SIZE = base.BOOT_SIZE
KERNEL_START = base.KERNEL_START
KERNEL_END = base.KERNEL_END
BuildError = base.BuildError
receipt = base.receipt
_BASE_ARTIFACT_SAFETY = base.artifact_safety


def _configure() -> None:
    candidate_contract._configure()
    userspace._configure()
    repro._configure()
    packager._configure()
    base.packager = packager
    base.repro = repro
    base.candidate_contract = candidate_contract
    base.userspace = userspace
    base.p286_spec = spec
    base.p286_closure = closure
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.P286_SOURCE_CONTRACT_ID = P310_SOURCE_CONTRACT_ID
    base.DEFAULT_IMAGE = DEFAULT_IMAGE
    base.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    base.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    base.DEFAULT_OUT = DEFAULT_OUT
    base.verify_repro_result = verify_repro_result
    base.artifact_safety = artifact_safety


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
    value, result_receipt = base._read_json(result_path, "P3.10 build reproducibility result")  # noqa: SLF001
    if (
        value.get("schema") != repro.SCHEMA
        or value.get("target") != TARGET
        or value.get("verdict") != repro.VERDICT
        or value.get("candidate_contract") != exact_contract
        or value.get("linked_audit", {}).get("verified") is not True
        or not isinstance(value.get("byte_identical_artifacts"), dict)
        or set(value["byte_identical_artifacts"]) != set(repro.ARTIFACT_LIMITS) - {"build-result.json"}
        or any(item is not True for item in value["byte_identical_artifacts"].values())
    ):
        raise BuildError("P3.10 build reproducibility result is not accepted")
    linked = value.get("linked_audit", {})
    if linked.get("audit_adapter") != "s22plus-fyg8-p310-linked-audit-v1" or linked.get("postbuild_audit", {}).get("verified") is not True:
        raise BuildError("P3.10 linked audit adapter mismatch")
    expected_image = value.get("build_a", {}).get("artifacts", {}).get("Image")
    if expected_image != image_receipt:
        raise BuildError("P3.10 supplied Image differs from reproducibility closure")
    if intent_path is None or patch_path is None:
        raise BuildError("P3.10 selected build-input paths are missing")
    qualification = repro.verify_p310_qualification_file(
        value.get("pre_lto_qualification"),
        exact_contract,
        intent_path=intent_path,
        patch_path=patch_path,
        root=candidate_contract.intent.repo_root(),
    )
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
    result = _BASE_ARTIFACT_SAFETY(exact_contract)
    result["candidate_module_binaries_injected"] = 0
    result["built_in_telemetry_only"] = True
    result["carrier_v2"] = True
    return result


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
