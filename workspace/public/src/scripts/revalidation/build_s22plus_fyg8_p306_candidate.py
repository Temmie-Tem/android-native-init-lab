#!/usr/bin/env python3
"""Build a P3.06 fixed-Image candidate with passive IPC telemetry."""

from __future__ import annotations

from pathlib import Path

import build_s22plus_fyg8_p304_candidate as parent
import s22plus_fyg8_p306_candidate_contract as candidate_contract
import s22plus_fyg8_p306_overlay_contract as contract
import s22plus_fyg8_p306_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p306_candidate_artifact_result_v1"
VERDICT = "PASS_P306_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = contract.TARGET
P286_SOURCE_CONTRACT_ID = contract.PARENT_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = contract.PARENT_IMAGE
DEFAULT_REPRO_RESULT = contract.PARENT_REPRO_RESULT
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = parent.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = parent.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = parent.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = parent.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p306/candidate-a")
BOOT_SIZE = parent.BOOT_SIZE
KERNEL_START = parent.KERNEL_START
KERNEL_END = parent.KERNEL_END
BuildError = parent.BuildError
receipt = parent.receipt


def verify_repro_result(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    value = parent.verify_repro_result(*args, **kwargs)
    value.pop("kernel_rebuilt_for_p304", None)
    value["kernel_rebuilt_for_p306"] = False
    return value


def artifact_safety(exact_contract: dict) -> dict:
    result = parent.artifact_safety(exact_contract)
    result.pop("p304_kernel_rebuild", None)
    result.pop("p304_full_lto_ab", None)
    result.update({
        "p306_kernel_rebuild": False,
        "p306_full_lto_ab": False,
        "ipc_observer": exact_contract["observer"],
    })
    return result


def _configure() -> None:
    parent._configure()
    base = parent.base
    base.candidate_contract = candidate_contract
    base.userspace = userspace
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.P286_SOURCE_CONTRACT_ID = P286_SOURCE_CONTRACT_ID
    base.DEFAULT_IMAGE = DEFAULT_IMAGE
    base.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    base.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    base.DEFAULT_OUT = DEFAULT_OUT
    base.verify_repro_result = verify_repro_result
    base.artifact_safety = artifact_safety


def build_candidate(args):  # noqa: ANN001, ANN201
    _configure()
    return parent.base.build_candidate(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return parent.base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return parent.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
