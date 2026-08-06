#!/usr/bin/env python3
"""Audit the P3.08 loss-resistant boot-only candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import build_s22plus_fyg8_p308_candidate as candidate
import s22plus_fyg8_p307_candidate_static_checker as parent
import s22plus_fyg8_p308_candidate_contract as contract
import s22plus_fyg8_p308_overlay_contract as overlay
import s22plus_fyg8_p308_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p308_candidate_static_checker_v1"
VERDICT = "PASS_P308_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p308/candidate-b")
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = parent.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = parent.DEFAULT_BUILD_A
DEFAULT_BUILD_B = parent.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = parent.DEFAULT_NM
DEFAULT_OBJDUMP = parent.DEFAULT_OBJDUMP
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p308/static-check-result.json")
CheckError = parent.CheckError
base = parent.base
ARTIFACT_LIMITS = parent.ARTIFACT_LIMITS
stable_read = parent.stable_read
repo_root = parent.repo_root
resolve = parent.resolve


def _expected_userspace_source(exact: dict) -> dict:
    return userspace._source_contract(exact)  # noqa: SLF001


def _configure() -> None:
    parent._configure()  # noqa: SLF001
    candidate._configure()  # noqa: SLF001
    userspace.module_count_context = parent.parent_userspace.module_count_context
    parent.candidate = candidate
    parent.contract = contract
    parent.overlay = overlay
    parent.userspace = userspace
    parent.SCHEMA = SCHEMA
    parent.VERDICT = VERDICT
    parent.TARGET = TARGET
    parent.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    parent.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    parent.DEFAULT_IMAGE = DEFAULT_IMAGE
    parent.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    parent.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    parent.DEFAULT_BASE_BOOT = DEFAULT_BASE_BOOT
    parent.DEFAULT_VENDOR_RAMDISK = DEFAULT_VENDOR_RAMDISK
    parent.DEFAULT_VENDOR_BOOT = DEFAULT_VENDOR_BOOT
    parent.DEFAULT_LZ4 = DEFAULT_LZ4
    parent.DEFAULT_MAGISKBOOT = DEFAULT_MAGISKBOOT
    parent.DEFAULT_BUILD_A = DEFAULT_BUILD_A
    parent.DEFAULT_BUILD_B = DEFAULT_BUILD_B
    parent.DEFAULT_SOURCE = DEFAULT_SOURCE
    parent.DEFAULT_INTENT = DEFAULT_INTENT
    parent.DEFAULT_PATCH = DEFAULT_PATCH
    parent.DEFAULT_NM = DEFAULT_NM
    parent.DEFAULT_OBJDUMP = DEFAULT_OBJDUMP
    parent.DEFAULT_OUT = DEFAULT_OUT
    parent._expected_userspace_source = _expected_userspace_source  # noqa: SLF001

    p305 = parent.parent
    p305.candidate = candidate
    p305.contract = contract
    p305.overlay = overlay
    p305.userspace = userspace
    p305.SCHEMA = SCHEMA
    p305.VERDICT = VERDICT
    p305.TARGET = TARGET
    p305.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    p305.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    p305.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    p305.DEFAULT_SOURCE = DEFAULT_SOURCE
    p305.DEFAULT_INTENT = DEFAULT_INTENT
    p305.DEFAULT_PATCH = DEFAULT_PATCH
    p305.DEFAULT_OUT = DEFAULT_OUT
    p305._expected_userspace_source = _expected_userspace_source  # noqa: SLF001

    p304 = p305.parent
    p304.candidate = candidate
    p304.contract = contract
    p304.overlay = overlay
    p304.userspace = userspace
    p304.SCHEMA = SCHEMA
    p304.VERDICT = VERDICT
    p304.TARGET = TARGET
    p304.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    p304.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    p304.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    p304.DEFAULT_SOURCE = DEFAULT_SOURCE
    p304.DEFAULT_INTENT = DEFAULT_INTENT
    p304.DEFAULT_PATCH = DEFAULT_PATCH
    p304.DEFAULT_OUT = DEFAULT_OUT
    p304._expected_userspace_source = _expected_userspace_source  # noqa: SLF001

    inherited = p304.inherited
    inherited.candidate = candidate
    inherited.contract = contract
    inherited.overlay = overlay
    inherited.userspace = userspace
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    inherited.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    inherited.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    inherited.DEFAULT_SOURCE = DEFAULT_SOURCE
    inherited.DEFAULT_INTENT = DEFAULT_INTENT
    inherited.DEFAULT_PATCH = DEFAULT_PATCH
    inherited.DEFAULT_OUT = DEFAULT_OUT

    base.candidate = inherited.inherited._CANDIDATE_STATIC_VIEW  # noqa: SLF001
    base.contract = contract
    base.p286_closure = parent.closure
    base.userspace = userspace
    base.rootfs_entrypoint_context = parent.rootfs_entrypoint_context
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
    base.verify_repro = inherited.inherited.verify_repro
    base.verify_userspace = p304.verify_userspace


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    inherited = parent.parent.parent.inherited
    clock = inherited.callsite_audit.audit(
        root,
        Path(inherited.spec.MODULE_PATH),
        args.objdump,
        "readelf",
    )
    qscratch = parent.qscratch_audit.audit(
        root, Path(parent.spec.DWC3_MODULE_PATH), args.objdump, "readelf"
    )
    if clock != exact["callsite_audit"]:
        raise CheckError("P3.08 inherited post-BL clock audit changed")
    if qscratch != exact["qscratch_audit"]:
        raise CheckError("P3.08 QSCRATCH callsite audit changed")
    if exact["telemetry"].get("verified") is not True:
        raise CheckError("P3.08 telemetry contract differs")
    if exact["observer"].get("local_parser_failure_drain_continues") is not True:
        raise CheckError("P3.08 loss-resistant observer boundary differs")
    result["p303_callsite_audit"] = clock
    result["p307_qscratch_audit"] = qscratch
    result["p308_telemetry"] = exact["telemetry"]
    result["p308_observer"] = exact["observer"]
    result["p308_cross_gate_audit"] = exact["cross_gate_audit"]
    if result["p308_cross_gate_audit"].get("verified") is not True:
        raise CheckError("P3.08 cross-gate audit differs")
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return parent.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        args = parent.parse_args(argv)
        result = audit(args)
        encoded = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii")
            + b"\n"
        )
        parent.base.durable_create(parent.base.resolve(parent.base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        base.carrier.BuildError,
        base.boot_verify.BootVerifyError,
        parent.parent.parent.inherited.inherited.repro.CheckError,
        parent.parent.parent.inherited.inherited.postbuild_audit.AuditError,
        parent.parent.parent.inherited.callsite_audit.AuditError,
        parent.qscratch_audit.AuditError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        base.e1_static.CheckError,
        base.e2_closure.ClosureError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
