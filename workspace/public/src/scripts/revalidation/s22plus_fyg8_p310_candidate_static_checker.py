#!/usr/bin/env python3
"""Independently audit one P3.10 Carrier v2 boot-only candidate."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator

import build_s22plus_fyg8_p310_candidate as candidate
import s22plus_fyg8_p286_candidate_static_checker as base
import s22plus_fyg8_p310_build_repro_check as repro
import s22plus_fyg8_p310_candidate_contract as contract
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p310_e2_stock_closure as p310_closure
import s22plus_fyg8_p310_postbuild_linked_audit as postbuild_audit
import s22plus_fyg8_p310_source_contract as source_contract
import s22plus_fyg8_p310_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p310_candidate_static_checker_v1"
VERDICT = "PASS_P310_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p310/candidate-b")
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
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p310/static-check-result.json")
CheckError = base.CheckError


def _json_document(value):  # noqa: ANN001, ANN201
    """Normalize an in-memory audit result to its persisted JSON shape."""
    try:
        return json.loads(
            json.dumps(
                value,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    except (TypeError, ValueError) as exc:
        raise CheckError("P3.10 fresh reproducibility result is not JSON") from exc


def artifact_safety(exact_contract):  # noqa: ANN001, ANN201
    candidate._configure()  # noqa: SLF001
    return candidate.artifact_safety(exact_contract)


class _CandidateStaticView:
    artifact_safety = staticmethod(artifact_safety)

    def __getattr__(self, name: str):
        return getattr(candidate, name)


_CANDIDATE_STATIC_VIEW = _CandidateStaticView()


@contextmanager
def rootfs_entrypoint_context(
    _closure_api, _exact_contract, userspace_payloads  # noqa: ANN001
) -> Iterator[None]:
    with p310_closure.exact_init_authority(userspace_payloads["init"]):
        yield


def _configure() -> None:
    candidate._configure()  # noqa: SLF001
    contract._configure()  # noqa: SLF001
    repro._configure()  # noqa: SLF001
    userspace._configure()  # noqa: SLF001
    base.candidate = _CANDIDATE_STATIC_VIEW
    base.repro = repro
    base.contract = contract
    base.p286_closure = p310_closure
    base.rootfs_entrypoint_context = rootfs_entrypoint_context
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
        "P3.10 build reproducibility result",
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
        fresh = _json_document(postbuild_audit.check(check_args))
    except (postbuild_audit.AuditError, repro.CheckError) as exc:
        raise CheckError(str(exc)) from exc
    linked = result.get("linked_audit", {}).get("postbuild_audit", {})
    if (
        result != fresh
        or result.get("candidate_contract") != exact_contract
        or linked.get("verified") is not True
        or linked.get("carrier_v2_linked_pair", {}).get("verified") is not True
        or linked.get("full_lto_p310_probe_callsites", {}).get("verified") is not True
        or linked.get("tracefs_abi_source_a_b", {}).get("verified") is not True
    ):
        raise CheckError("P3.10 reproducibility result differs from fresh verification")
    return result, base.receipt(payload)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    run_id = bytes.fromhex(result["candidate_contract"]["run_id"])
    try:
        implementation = source_contract.implementation_result(base.repo_root())
        reachable = source_contract.validate_reachable_records(run_id)
    except source_contract.SourceContractError as exc:
        raise CheckError(str(exc)) from exc
    if implementation.get("verified") is not True or reachable.get("verified") is not True:
        raise CheckError("P3.10 Carrier v2 source or reachable-record closure differs")
    result["p310_carrier"] = carrier.validate()
    result["p310_implementation"] = implementation
    result["p310_reachable_records"] = reachable
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
