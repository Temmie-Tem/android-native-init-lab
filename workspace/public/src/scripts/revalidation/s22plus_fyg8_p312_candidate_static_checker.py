#!/usr/bin/env python3
"""Independently audit one P3.12 fixed-P3.10-Image candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import build_s22plus_fyg8_p312_candidate as candidate
import s22plus_fyg8_p311_candidate_static_checker as inherited
import s22plus_fyg8_p312_candidate_contract as contract
import s22plus_fyg8_p312_e2_stock_closure as closure
import s22plus_fyg8_p312_overlay_contract as overlay
import s22plus_fyg8_p312_runtime_fixture as runtime_fixture
import s22plus_fyg8_p312_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p312_candidate_static_checker_v1"
VERDICT = "PASS_P312_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p312/candidate-b")
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
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p312/static-check-result.json")
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
    return getattr(inherited.base, name)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = inherited.base.audit(args)
    root = inherited.base.repo_root()
    exact = overlay.verify_intent(root, inherited.base.resolve(root, args.intent))
    fixture = runtime_fixture.audit(root)
    if fixture.get("verified") is not True:
        raise CheckError("P3.12 runtime fixtures differ")
    result.update({
        "p312_callsite_audit": exact["callsite_audit"],
        "p312_delayed_arm_qemu": exact["delayed_arm_qemu"],
        "p312_tracefs_abi": exact["tracefs_abi"],
        "p312_cross_gate_audit": exact["cross_gate_audit"],
        "p312_carrier_decoder_authority": exact["carrier_decoder_authority"],
        "p312_runtime_fixture": fixture,
        "p312_telemetry": exact["telemetry"],
        "p312_observer": exact["observer"],
    })
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return inherited.base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        args = inherited.base.parse_args(argv)
        result = audit(args)
        encoded = json.dumps(
            result, indent=2, sort_keys=True, allow_nan=False
        ).encode("ascii") + b"\n"
        inherited.base.durable_create(
            inherited.base.resolve(inherited.base.repo_root(), args.out), encoded
        )
    except (
        CheckError,
        candidate.BuildError,
        inherited.base.carrier.BuildError,
        inherited.base.boot_verify.BootVerifyError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        inherited.base.e1_static.CheckError,
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
