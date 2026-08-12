#!/usr/bin/env python3
"""Independently reconstruct and audit the reproducible P3.17 candidate."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
from typing import Iterator

import build_s22plus_fyg8_p317_candidate as candidate
import s22plus_fyg8_p316_candidate_static_checker as base
import s22plus_fyg8_p316_sidecar_positive_control as sidecar_control
import s22plus_fyg8_p317_candidate_contract as contract
import s22plus_fyg8_p317_e2_stock_closure as closure
import s22plus_fyg8_p317_lifecycle_audit as lifecycle
import s22plus_fyg8_p317_overlay_contract as overlay
import s22plus_fyg8_p317_qualification_closure as qualification
import s22plus_fyg8_p317_runtime_fixture as runtime_fixture
import s22plus_fyg8_p317_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p317_candidate_static_checker_v1"
VERDICT = "PASS_P317_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
EXPECTED_MODULE_PLAN_COUNT = 69
RESULT_PREFIX = "p317"
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = qualification.DEFAULT_CANDIDATE_B
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = base.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_DIAGNOSTIC = candidate.DEFAULT_DIAGNOSTIC
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_QUALIFICATION = qualification.DEFAULT_OUT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p317/static-check-result.json")
CheckError = base.CheckError
ARTIFACT_LIMITS = base.ARTIFACT_LIMITS
repo_root = contract.intent.repo_root
stable_read = base.stable_read
resolve = base.resolve


@contextmanager
def _configured() -> Iterator[None]:
    names = (
        "candidate", "contract", "closure", "lifecycle", "overlay",
        "qualification", "runtime_fixture", "sidecar_control", "userspace",
        "SCHEMA", "VERDICT", "TARGET", "EXPECTED_MODULE_PLAN_COUNT",
        "RESULT_PREFIX", "DEFAULT_CANDIDATE", "DEFAULT_CANDIDATE_B",
        "DEFAULT_IMAGE", "DEFAULT_REPRO_RESULT", "DEFAULT_USERSPACE",
        "DEFAULT_BASE_BOOT", "DEFAULT_VENDOR_RAMDISK", "DEFAULT_VENDOR_BOOT",
        "DEFAULT_LZ4", "DEFAULT_MAGISKBOOT", "DEFAULT_DIAGNOSTIC",
        "DEFAULT_SOURCE", "DEFAULT_INTENT", "DEFAULT_PATCH",
        "DEFAULT_QUALIFICATION", "DEFAULT_OUT",
    )
    values = {name: globals()[name] for name in names}
    previous = {name: getattr(base, name) for name in names}
    for name, value in values.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def audit(args):  # noqa: ANN001, ANN201
    with _configured():
        result = base.audit(args)
    exact = result["candidate_contract"]
    result["p317_envelope_fixture"] = exact["envelope_fixture"]
    result["p317_executability_fixed_point"] = exact[
        "executability_gates"
    ]["fixed_point"]["value"]
    return result


def parse_args(argv: list[str] | None = None):
    with _configured():
        return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = audit(args)
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n"
        base.base.durable_create(resolve(contract.intent.repo_root(), args.out), encoded)
    except (
        CheckError, candidate.BuildError, qualification.QualificationError,
        contract.ContractError, contract.intent.IntentError,
        overlay.OverlayContractError, closure.ClosureError,
        subprocess.TimeoutExpired, OSError, ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
