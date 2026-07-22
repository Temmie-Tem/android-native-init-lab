#!/usr/bin/env python3
"""Audit the P2.26 candidate through the reusable P2.21 checker core."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p226_candidate as candidate  # noqa: E402
import s22plus_fyg8_p221_candidate_static_checker as engine  # noqa: E402
import s22plus_fyg8_p225_build_artifact_contract as artifact  # noqa: E402


SCHEMA = "s22plus_fyg8_p226_candidate_static_checker_v1"
VERDICT = "PASS_P226_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_VMLINUX = candidate.DEFAULT_VMLINUX
DEFAULT_CONFIG = candidate.DEFAULT_CONFIG
DEFAULT_BUILD_RESULT = candidate.DEFAULT_BUILD_RESULT
DEFAULT_CARRIER = candidate.DEFAULT_CARRIER
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = engine.DEFAULT_MAGISKBOOT
DEFAULT_VENDOR_BOOT = engine.DEFAULT_VENDOR_BOOT
DEFAULT_INIT = engine.DEFAULT_INIT
DEFAULT_RUNTIME_RECEIPT = engine.DEFAULT_RUNTIME_RECEIPT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p226_candidate/static-check-result.json"
)
CheckError = engine.CheckError


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements: dict[str, Any] = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "DEFAULT_CANDIDATE": DEFAULT_CANDIDATE,
        "DEFAULT_IMAGE": DEFAULT_IMAGE,
        "DEFAULT_VMLINUX": DEFAULT_VMLINUX,
        "DEFAULT_CONFIG": DEFAULT_CONFIG,
        "DEFAULT_BUILD_RESULT": DEFAULT_BUILD_RESULT,
        "DEFAULT_CARRIER": DEFAULT_CARRIER,
        "DEFAULT_LZ4": DEFAULT_LZ4,
        "DEFAULT_MAGISKBOOT": DEFAULT_MAGISKBOOT,
        "DEFAULT_VENDOR_BOOT": DEFAULT_VENDOR_BOOT,
        "DEFAULT_INIT": DEFAULT_INIT,
        "DEFAULT_RUNTIME_RECEIPT": DEFAULT_RUNTIME_RECEIPT,
        "DEFAULT_OUT": DEFAULT_OUT,
        "candidate": candidate,
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


def audit(args) -> dict[str, Any]:
    with bind_engine():
        return engine.audit(args)


def main(argv: list[str] | None = None) -> int:
    with bind_engine():
        return engine.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
