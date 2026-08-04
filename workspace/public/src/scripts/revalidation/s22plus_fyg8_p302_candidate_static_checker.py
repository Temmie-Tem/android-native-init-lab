#!/usr/bin/env python3
"""Independently audit one fixed-Image P3.02-M0 carrier candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import build_s22plus_fyg8_p302_candidate as candidate
import s22plus_fyg8_p301_candidate_static_checker as inherited
import s22plus_fyg8_p302_binary_carrier as binary_carrier
import s22plus_fyg8_p302_candidate_contract as contract
import s22plus_fyg8_p302_overlay_contract as overlay
import s22plus_fyg8_p302_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p302_candidate_static_checker_v1"
VERDICT = "PASS_P302_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path(
    "workspace/private/outputs/s22plus_fyg8_p302/candidate-b"
)
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
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p302/static-check-result.json"
)
P301_INIT = Path(
    "workspace/private/outputs/s22plus_fyg8_p301_r1/userspace/init"
)
P301_CHILD = Path(
    "workspace/private/outputs/s22plus_fyg8_p301_r1/userspace/s22-e1-child"
)
P301_INIT_RECEIPT = {
    "size": 66384,
    "sha256": "17eae28ae1e8fa0abcd47b05c3b57cfa5c54124db0192137b208a3f85978ee35",
}
P301_CHILD_RECEIPT = {
    "size": 720,
    "sha256": "9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639",
}
CheckError = inherited.CheckError
base = inherited.base


def _expected_userspace_source(exact_contract: dict) -> dict:
    return {
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "parent_overlay_contract_id": overlay.PARENT_OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "source_receipts": exact_contract["source_receipts"],
        "generated_artifacts": exact_contract["generated_artifacts"],
        "fixed_image": exact_contract["fixed_image"],
        "verified": True,
    }


def verify_userspace(
    root: Path,
    directory: Path,
    exact_contract: dict,
    intent_path: Path,
):
    previous = inherited._expected_userspace_source  # noqa: SLF001
    inherited._expected_userspace_source = _expected_userspace_source  # noqa: SLF001
    try:
        return inherited.verify_userspace(
            root, directory, exact_contract, intent_path
        )
    finally:
        inherited._expected_userspace_source = previous  # noqa: SLF001


def _carrier_identity(root: Path, userspace_dir: Path) -> dict:
    init = userspace_dir / "init"
    child = userspace_dir / "s22-e1-child"
    baseline_init = root / P301_INIT
    baseline_child = root / P301_CHILD
    baseline_init_data = base.stable_read(
        baseline_init, "P3.02 fixed P3.01-r1 init", 1024 * 1024
    )
    baseline_child_data = base.stable_read(
        baseline_child, "P3.02 fixed P3.01-r1 child", 1024 * 1024
    )
    if (
        base.receipt(baseline_init_data) != P301_INIT_RECEIPT
        or base.receipt(baseline_child_data) != P301_CHILD_RECEIPT
    ):
        raise CheckError("P3.02 fixed P3.01-r1 userspace receipt differs")
    carried_child = base.stable_read(
        child, "P3.02 carried child", 1024 * 1024
    )
    if carried_child != baseline_child_data:
        raise CheckError("P3.02 child differs from fixed P3.01-r1")
    try:
        identity = binary_carrier.verify(init, baseline_init)
    except binary_carrier.BinaryCarrierError as exc:
        raise CheckError(str(exc)) from exc
    return {
        **identity,
        "parent_init": P301_INIT_RECEIPT,
        "parent_child": P301_CHILD_RECEIPT,
        "child_byte_identical": True,
        "fixed_image_sha256": overlay.EXPECTED_IMAGE["sha256"],
        "kernel_rebuilt": False,
        "module_binaries_injected": 0,
        "verified": True,
    }


def _configure() -> None:
    candidate._configure()
    inherited.candidate = candidate
    inherited.contract = contract
    inherited.overlay = overlay
    inherited.userspace = userspace
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    inherited.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    inherited.DEFAULT_IMAGE = DEFAULT_IMAGE
    inherited.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    inherited.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    inherited.DEFAULT_SOURCE = DEFAULT_SOURCE
    inherited.DEFAULT_INTENT = DEFAULT_INTENT
    inherited.DEFAULT_PATCH = DEFAULT_PATCH
    inherited.DEFAULT_OUT = DEFAULT_OUT
    base.candidate = inherited._CANDIDATE_STATIC_VIEW  # noqa: SLF001
    base.repro = inherited.repro
    base.contract = contract
    base.p286_closure = inherited._P301_STOCK_CLOSURE_VIEW  # noqa: SLF001
    base.userspace = userspace
    base.rootfs_entrypoint_context = inherited.rootfs_entrypoint_context
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    base.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    base.DEFAULT_IMAGE = DEFAULT_IMAGE
    base.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    base.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    base.DEFAULT_BASE_BOOT = DEFAULT_BASE_BOOT
    base.DEFAULT_VENDOR_RAMDISK = DEFAULT_VENDOR_RAMDISK
    base.DEFAULT_VENDOR_BOOT = DEFAULT_VENDOR_BOOT
    base.DEFAULT_LZ4 = DEFAULT_LZ4
    base.DEFAULT_MAGISKBOOT = DEFAULT_MAGISKBOOT
    base.DEFAULT_BUILD_A = DEFAULT_BUILD_A
    base.DEFAULT_BUILD_B = DEFAULT_BUILD_B
    base.DEFAULT_SOURCE = DEFAULT_SOURCE
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH
    base.DEFAULT_NM = DEFAULT_NM
    base.DEFAULT_OBJDUMP = DEFAULT_OBJDUMP
    base.DEFAULT_OUT = DEFAULT_OUT
    base.verify_repro = inherited.verify_repro
    base.verify_userspace = verify_userspace


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    result["carrier_identity"] = _carrier_identity(
        root, base.resolve(root, args.userspace)
    )
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        args = base.parse_args(argv)
        result = audit(args)
        encoded = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode(
                "ascii"
            )
            + b"\n"
        )
        base.durable_create(base.resolve(base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        binary_carrier.BinaryCarrierError,
        base.carrier.BuildError,
        base.boot_verify.BootVerifyError,
        inherited.repro.CheckError,
        inherited.postbuild_audit.AuditError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        base.e1_static.CheckError,
        base.e2_closure.ClosureError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
