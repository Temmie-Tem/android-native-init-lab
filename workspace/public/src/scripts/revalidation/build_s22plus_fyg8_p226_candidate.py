#!/usr/bin/env python3
"""Construct the P2.26 boot-only AP with the reusable P2.21 core."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p221_candidate as engine  # noqa: E402
import s22plus_fyg8_p225_build_artifact_contract as artifact  # noqa: E402


SCHEMA = "s22plus_fyg8_p226_candidate_artifact_result_v1"
VERDICT = "PASS_P226_CANDIDATE_ARTIFACTS_BUILT_HOST_ONLY"
DEFAULT_IMAGE = Path("workspace/private/outputs/s22plus_fyg8_p225_build/artifacts/Image")
DEFAULT_VMLINUX = Path(
    "workspace/private/outputs/s22plus_fyg8_p225_build/artifacts/vmlinux"
)
DEFAULT_CONFIG = Path("workspace/private/outputs/s22plus_fyg8_p225_build/artifacts/.config")
DEFAULT_BUILD_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p225_build/artifacts/build-result.json"
)
DEFAULT_CARRIER = engine.DEFAULT_CARRIER
DEFAULT_LZ4 = engine.DEFAULT_LZ4
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p226_candidate/artifacts")

BOOT_SIZE = engine.BOOT_SIZE
KERNEL_START = engine.KERNEL_START
KERNEL_END = engine.KERNEL_END
E0_CARRIER_SIZE = engine.E0_CARRIER_SIZE
E0_CARRIER_SHA256 = engine.E0_CARRIER_SHA256
BuildError = engine.BuildError
repo_root = engine.repo_root
resolve = engine.resolve
replace_kernel = engine.replace_kernel


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements: dict[str, Any] = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "DEFAULT_IMAGE": DEFAULT_IMAGE,
        "DEFAULT_VMLINUX": DEFAULT_VMLINUX,
        "DEFAULT_CONFIG": DEFAULT_CONFIG,
        "DEFAULT_BUILD_RESULT": DEFAULT_BUILD_RESULT,
        "DEFAULT_CARRIER": DEFAULT_CARRIER,
        "DEFAULT_LZ4": DEFAULT_LZ4,
        "DEFAULT_OUT": DEFAULT_OUT,
        "artifact": artifact,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(engine, name, value)


def parse_args(argv: list[str] | None = None):
    with bind_engine():
        return engine.parse_args(argv)


def build(args) -> dict[str, Any]:
    with bind_engine():
        return engine.build(args)


def main(argv: list[str] | None = None) -> int:
    with bind_engine():
        return engine.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
