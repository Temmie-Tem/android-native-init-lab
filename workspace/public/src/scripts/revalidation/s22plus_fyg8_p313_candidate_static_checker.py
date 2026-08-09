#!/usr/bin/env python3
"""Independently audit one P3.13 fixed-P3.10-Image candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import build_s22plus_fyg8_p313_candidate as candidate
import s22plus_fyg8_p312_candidate_static_checker as inherited
import s22plus_fyg8_p313_candidate_contract as contract
import s22plus_fyg8_p313_e2_stock_closure as closure
import s22plus_fyg8_p313_overlay_contract as overlay
import s22plus_fyg8_p313_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_p313_runtime_fixture as runtime_fixture
import s22plus_fyg8_p313_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p313_candidate_static_checker_v1"
VERDICT = "PASS_P313_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p313/candidate-b")
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
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p313/static-check-result.json")
CheckError = inherited.CheckError


def _configure() -> None:
    inherited.candidate = candidate
    inherited.contract = contract
    inherited.closure = closure
    inherited.overlay = overlay
    inherited.runtime_fixture = runtime_fixture
    inherited.userspace = userspace
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    inherited.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    inherited.DEFAULT_IMAGE = DEFAULT_IMAGE
    inherited.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    inherited.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    inherited.DEFAULT_BASE_BOOT = DEFAULT_BASE_BOOT
    inherited.DEFAULT_VENDOR_RAMDISK = DEFAULT_VENDOR_RAMDISK
    inherited.DEFAULT_VENDOR_BOOT = DEFAULT_VENDOR_BOOT
    inherited.DEFAULT_LZ4 = DEFAULT_LZ4
    inherited.DEFAULT_MAGISKBOOT = DEFAULT_MAGISKBOOT
    inherited.DEFAULT_SOURCE = DEFAULT_SOURCE
    inherited.DEFAULT_INTENT = DEFAULT_INTENT
    inherited.DEFAULT_PATCH = DEFAULT_PATCH
    inherited.DEFAULT_OUT = DEFAULT_OUT
    inherited._configure()  # noqa: SLF001


def __getattr__(name: str):
    _configure()
    return getattr(inherited.inherited.base, name)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = inherited.inherited.base.audit(args)
    root = inherited.inherited.base.repo_root()
    exact = overlay.verify_intent(root, inherited.inherited.base.resolve(root, args.intent))
    fixture = runtime_fixture.audit(root)
    adapter = adapter_fixture.audit(root)
    if fixture.get("verified") is not True:
        raise CheckError("P3.13 runtime fixtures differ")
    result.update({
        "p313_tracefs_abi": exact["tracefs_abi"],
        "p313_cross_gate_audit": exact["cross_gate_audit"],
        "p313_runtime_fixture": fixture,
        "p313_process_v2_adapter_fixture": adapter,
        "p313_hazard_closure": exact["hazard_closure"],
        "p313_telemetry": exact["telemetry"],
        "p313_observer": exact["observer"],
    })
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return inherited.inherited.base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        args = inherited.inherited.base.parse_args(argv)
        result = audit(args)
        encoded = json.dumps(
            result, indent=2, sort_keys=True, allow_nan=False
        ).encode("ascii") + b"\n"
        inherited.inherited.base.durable_create(
            inherited.inherited.base.resolve(inherited.inherited.base.repo_root(), args.out),
            encoded,
        )
    except (
        CheckError,
        candidate.BuildError,
        inherited.inherited.base.carrier.BuildError,
        inherited.inherited.base.boot_verify.BootVerifyError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        inherited.inherited.base.e1_static.CheckError,
        closure.ClosureError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
