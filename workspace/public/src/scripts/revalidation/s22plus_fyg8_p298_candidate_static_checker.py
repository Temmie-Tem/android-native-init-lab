#!/usr/bin/env python3
"""Independently audit one deterministic P2.98 boot-only candidate."""

from __future__ import annotations

import argparse
from contextvars import ContextVar
from pathlib import Path

import build_s22plus_fyg8_p298_candidate as candidate
import s22plus_fyg8_p286_candidate_static_checker as base
import s22plus_fyg8_p298_build_repro_check as repro
import s22plus_fyg8_p298_candidate_contract as contract
import s22plus_fyg8_p298_e2_stock_closure as p298_closure
import s22plus_fyg8_p298_identity_tiers as identity
import s22plus_fyg8_p298_postbuild_linked_audit as postbuild_audit
import s22plus_fyg8_p298_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p298_candidate_static_checker_v1"
VERDICT = "PASS_P298_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p298/candidate-b")
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
    "workspace/private/outputs/s22plus_fyg8_p298/static-check-result.json"
)
CheckError = base.CheckError
HISTORICAL_POSTBUILD_RESULT = {
    "sha256": "a7bfff7bdc82683999ef0d91349f20560b659ea703cb0542eeb37ca36a3ff997",
    "size": 71342,
}
HISTORICAL_QUALIFICATION = {
    "sha256": "f3533d20ef3edc5c4feaf410296492820138dcd2c56861ee81be02fca78b89eb",
    "size": 115141,
}
TIER2_REPAIR_PATHS = (
    Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_p298_e2_stock_closure.py"),
    Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_p298_candidate_static_checker.py"),
    Path("tests/test_s22plus_fyg8_p298_contract.py"),
)
_ACTIVE_TIER2_REPAIR: ContextVar[dict | None] = ContextVar(
    "p298_active_tier2_repair", default=None
)
_BASE_AUDIT = base.audit


def artifact_safety(exact_contract):  # noqa: ANN001, ANN201
    candidate._configure()
    return candidate.base.artifact_safety(exact_contract)


class _CandidateStaticView:
    artifact_safety = staticmethod(artifact_safety)

    def __getattr__(self, name: str):
        return getattr(candidate, name)


_CANDIDATE_STATIC_VIEW = _CandidateStaticView()


def _configure() -> None:
    candidate._configure()
    contract._configure()
    repro._configure()
    userspace._configure()
    base.candidate = _CANDIDATE_STATIC_VIEW
    base.repro = repro
    base.contract = contract
    base.p286_closure = p298_closure
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
    base.audit = audit


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def verify_repro(root: Path, args, exact_contract):  # noqa: ANN001, ANN201
    result, payload = base.read_json(
        base.resolve(root, args.repro_result),
        "P2.98 build reproducibility result",
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
    telemetry = (
        result.get("linked_audit", {})
        .get("postbuild_audit", {})
        .get("gadget_start_event_telemetry", {})
    )
    result_receipt = base.receipt(payload)
    if _is_historical_postbuild_result(payload):
        repair = _verify_historical_postbuild_repair(
            root, args, result, exact_contract
        )
        _ACTIVE_TIER2_REPAIR.set(repair)
        fresh = result
    else:
        try:
            fresh = postbuild_audit.check(check_args)
        except (postbuild_audit.AuditError, repro.CheckError) as exc:
            raise CheckError(str(exc)) from exc
        _ACTIVE_TIER2_REPAIR.set(None)
    if (
        result != fresh
        or result.get("candidate_contract") != exact_contract
        or telemetry.get("verified") is not True
        or telemetry.get("pair_adjacency", {}).get("verified") is not True
        or telemetry.get("delivery", {}).get("verified") is not True
        or telemetry.get("result_contract", {}).get("verified") is not True
    ):
        raise CheckError(
            "P2.98 reproducibility result differs from fresh verification"
        )
    return result, base.receipt(payload)


def _is_historical_postbuild_result(payload: bytes) -> bool:
    return base.receipt(payload) == HISTORICAL_POSTBUILD_RESULT


def _distinct_build_directories(root: Path, args) -> dict[str, Path]:  # noqa: ANN001
    directories = {
        "build_a": base.resolve(root, args.build_a),
        "build_b": base.resolve(root, args.build_b),
    }
    for name, directory in directories.items():
        if directory.is_symlink() or not directory.is_dir():
            raise CheckError(f"P2.98 historical {name} directory is indirect or missing")
    if (
        directories["build_a"].resolve() == directories["build_b"].resolve()
        or directories["build_a"].samefile(directories["build_b"])
    ):
        raise CheckError("P2.98 historical A/B build directories are not distinct")
    return directories


def _verify_historical_postbuild_repair(
    root: Path,
    args,
    result: dict,
    exact_contract: dict,
) -> dict:  # noqa: ANN001
    qualification = result.get("pre_lto_qualification", {})
    qualification_receipt = qualification.get("qualification", {})
    if (
        result.get("schema") != repro.SCHEMA
        or result.get("verdict") != repro.VERDICT
        or result.get("candidate_contract") != exact_contract
        or {
            name: qualification_receipt.get(name)
            for name in ("sha256", "size")
        }
        != HISTORICAL_QUALIFICATION
        or qualification.get("qualification_repo_path")
        != "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/qualification-v3.json"
        or result.get("linked_audit", {})
        .get("postbuild_audit", {})
        .get("verified")
        is not True
        or result.get("linked_audit", {}).get("verified") is not True
    ):
        raise CheckError("P2.98 historical postbuild repair header mismatch")
    expected_equal = set(repro.ARTIFACT_LIMITS) - {"build-result.json"}
    if (
        set(result.get("byte_identical_artifacts", {})) != expected_equal
        or any(
            value is not True
            for value in result["byte_identical_artifacts"].values()
        )
    ):
        raise CheckError("P2.98 historical A/B equality proof mismatch")

    artifact_receipts: dict[str, dict[str, dict[str, int | str]]] = {}
    directories = _distinct_build_directories(root, args)
    for result_key, directory in directories.items():
        expected = result.get(result_key, {}).get("artifacts", {})
        if set(expected) != set(repro.ARTIFACT_LIMITS):
            raise CheckError(
                f"P2.98 historical {result_key} artifact inventory mismatch"
            )
        actual = {}
        for name, limit in repro.ARTIFACT_LIMITS.items():
            data = base.stable_read(
                directory / name,
                f"P2.98 historical {result_key} {name}",
                limit,
            )
            actual[name] = base.receipt(data)
        if actual != expected:
            raise CheckError(
                f"P2.98 historical {result_key} artifact receipt mismatch"
            )
        artifact_receipts[result_key] = actual
    for name in repro.ARTIFACT_LIMITS:
        if (directories["build_a"] / name).samefile(
            directories["build_b"] / name
        ):
            raise CheckError(
                f"P2.98 historical A/B {name} artifacts share one inode"
            )
    for name in expected_equal:
        if (
            artifact_receipts["build_a"][name]
            != artifact_receipts["build_b"][name]
        ):
            raise CheckError(
                f"P2.98 historical A/B {name} bytes are not identical"
            )

    tier2 = set(identity.path_tiers()["tier2_qualification"])
    if any(path.as_posix() not in tier2 for path in TIER2_REPAIR_PATHS):
        raise CheckError("P2.98 repair path escaped Tier-2 qualification")
    repair_files = {}
    for path in TIER2_REPAIR_PATHS:
        data = base.stable_read(
            root / path, f"P2.98 Tier-2 repair {path.name}", 2 * 1024 * 1024
        )
        repair_files[path.as_posix()] = base.receipt(data)
    return {
        "schema": "s22plus_fyg8_p298_postbuild_tier2_repair_v1",
        "historical_postbuild_result": HISTORICAL_POSTBUILD_RESULT,
        "historical_pre_lto_qualification": HISTORICAL_QUALIFICATION,
        "a_b_artifacts_reopened": artifact_receipts,
        "a_b_artifact_inodes_distinct": True,
        "byte_identical_artifacts_reverified": sorted(expected_equal),
        "tier1_candidate_identity_changed": False,
        "tier2_repair_files": repair_files,
        "fresh_full_lto_claimed": False,
        "verified": True,
    }


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    token = _ACTIVE_TIER2_REPAIR.set(None)
    try:
        result = _BASE_AUDIT(args)
        repair = _ACTIVE_TIER2_REPAIR.get()
    finally:
        _ACTIVE_TIER2_REPAIR.reset(token)
    if repair is not None:
        result["build_repro"]["fresh_reverification"] = False
        result["build_repro"]["immutable_build_time_proof_revalidated"] = True
        result["build_repro"]["tier2_repair"] = repair
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
