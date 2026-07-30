#!/usr/bin/env python3
"""Independently audit one deterministic P2.88 boot-only candidate."""

from __future__ import annotations

import argparse
from pathlib import Path

import s22plus_fyg8_p286_candidate_static_checker as base
import build_s22plus_fyg8_p288_candidate as candidate
import s22plus_fyg8_p288_build_repro_check as repro
import s22plus_fyg8_p288_candidate_contract as contract
import s22plus_fyg8_p288_e2_stock_closure as p288_closure
import s22plus_fyg8_p288_postbuild_linked_audit as postbuild_audit
import s22plus_fyg8_p288_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p288_candidate_static_checker_v1"
VERDICT = "PASS_P288_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/candidate-b"
)
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = base.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = repro.DEFAULT_BUILD_A
DEFAULT_BUILD_B = repro.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = repro.DEFAULT_NM
DEFAULT_OBJDUMP = repro.DEFAULT_OBJDUMP
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/"
    "static-check-result.json"
)
CheckError = base.CheckError


def _configure() -> None:
    candidate._configure()
    contract._configure()
    repro._configure()
    userspace._configure()
    base.candidate = candidate
    base.repro = repro
    base.contract = contract
    base.p286_closure = p288_closure
    base.userspace = userspace
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
    base.verify_repro = verify_repro


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def verify_repro(root: Path, args, exact_contract):  # noqa: ANN001, ANN201
    result, payload = base.read_json(
        base.resolve(root, args.repro_result),
        "P2.88 build reproducibility result",
        16 * 1024 * 1024,
    )
    check_args = argparse.Namespace(
        build_a=args.build_a,
        build_b=args.build_b,
        source=args.source,
        intent=args.intent,
        patch=args.patch,
        nm=args.nm,
        objdump=args.objdump,
    )
    try:
        fresh = postbuild_audit.check(check_args)
    except (postbuild_audit.AuditError, repro.CheckError) as exc:
        raise CheckError(str(exc)) from exc
    if (
        result != fresh
        or result.get("candidate_contract") != exact_contract
        or result.get("linked_audit", {})
        .get("postbuild_audit", {})
        .get("verified")
        is not True
    ):
        raise CheckError(
            "P2.88 reproducibility result differs from post-build verification"
        )
    return result, base.receipt(payload)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    return base.audit(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
