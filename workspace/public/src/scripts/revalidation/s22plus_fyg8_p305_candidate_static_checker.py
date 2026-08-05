#!/usr/bin/env python3
"""Audit the P3.05 generic folded-tail boot-only candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import build_s22plus_fyg8_p305_candidate as candidate
import s22plus_fyg8_p304_candidate_static_checker as parent
import s22plus_fyg8_p304_e2_stock_closure as closure
import s22plus_fyg8_p304_userspace_build as parent_userspace
import s22plus_fyg8_p305_candidate_contract as contract
import s22plus_fyg8_p305_overlay_contract as overlay
import s22plus_fyg8_p305_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p305_candidate_static_checker_v1"
VERDICT = "PASS_P305_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p305/candidate-b")
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
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p305/static-check-result-v2.json")
CheckError = parent.CheckError
base = parent.base
ARTIFACT_LIMITS = parent.ARTIFACT_LIMITS
stable_read = parent.stable_read
repo_root = parent.repo_root
resolve = parent.resolve


def _expected_userspace_source(exact: dict) -> dict:
    return userspace._source_contract(exact)  # noqa: SLF001


def rootfs_entrypoint_context(_closure_api, exact, payloads):  # noqa: ANN001, ANN201
    return parent.inherited.rootfs_entrypoint_context(
        parent.inherited._P303_STOCK_CLOSURE_VIEW, exact, payloads  # noqa: SLF001
    )


def _configure() -> None:
    parent._configure()
    candidate._configure()
    candidate.packager = candidate.parent.packager
    userspace.module_count_context = parent_userspace.module_count_context
    parent.candidate = candidate
    parent.contract = contract
    parent.overlay = overlay
    parent.userspace = userspace
    parent.SCHEMA = SCHEMA
    parent.VERDICT = VERDICT
    parent.TARGET = TARGET
    parent.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    parent.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    parent.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    parent.DEFAULT_SOURCE = DEFAULT_SOURCE
    parent.DEFAULT_INTENT = DEFAULT_INTENT
    parent.DEFAULT_PATCH = DEFAULT_PATCH
    parent.DEFAULT_OUT = DEFAULT_OUT
    parent._expected_userspace_source = _expected_userspace_source  # noqa: SLF001

    inherited = parent.inherited
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
    base.p286_closure = closure
    base.userspace = userspace
    base.rootfs_entrypoint_context = rootfs_entrypoint_context
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
    base.verify_userspace = parent.verify_userspace


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    proved = parent.inherited.callsite_audit.audit(
        root, Path(parent.inherited.spec.MODULE_PATH), args.objdump, "readelf"
    )
    if proved != exact["callsite_audit"]:
        raise CheckError("P3.05 inherited post-BL callsite audit changed")
    result["p303_callsite_audit"] = proved
    result["p303_offset_probe_rule"] = {
        "p300_epilogue_rejection_preserved": True,
        "immediate_post_bl_only": True,
        "w0_immediately_consumed": True,
        "fixed_module_receipt_shared_by_candidate_a_b": True,
        "hit_zero_distinct_from_rc_zero": True,
        "verified": True,
    }
    result["p305_folded_tail"] = exact["folded_tail"]
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
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii")
            + b"\n"
        )
        base.durable_create(base.resolve(base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        base.carrier.BuildError,
        base.boot_verify.BootVerifyError,
        parent.inherited.inherited.repro.CheckError,
        parent.inherited.inherited.postbuild_audit.AuditError,
        parent.inherited.callsite_audit.AuditError,
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
