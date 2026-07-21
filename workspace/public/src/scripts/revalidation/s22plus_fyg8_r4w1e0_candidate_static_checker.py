#!/usr/bin/env python3
"""Independently audit one host-only FYG8 R4W1-E0 candidate."""

from __future__ import annotations

import argparse
import hashlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_r4w1e0_candidate as contract  # noqa: E402
import s22plus_fyg8_r4w1e_e1_candidate_static_checker as engine  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1e0_candidate_static_checker_v1"
VERDICT = "PASS_R4W1E0_OFFLINE_CANDIDATE_STATIC_CONTRACT"
CANDIDATE_SCHEMA = contract.SCHEMA
RUN_MANIFEST_SCHEMA = contract.RUN_MANIFEST_SCHEMA
CANDIDATE_VERDICT = contract.VERDICT
RUNG = contract.RUNG
DEFAULT_CANDIDATE = contract.DEFAULT_OUT
DEFAULT_IMAGE = contract.DEFAULT_IMAGE
DEFAULT_KERNEL_RESULT = contract.DEFAULT_KERNEL_RESULT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_candidate/"
    "static-check-result.json"
)


def verify_kernel_result(
    data: bytes, image_receipt: dict[str, Any]
) -> dict[str, Any]:
    return contract.verify_kernel_result_common(
        data, image_receipt, engine.CheckError
    )


def verify_run_manifest(
    data: bytes,
    *,
    image_receipt: dict[str, Any],
    kernel_result_receipt: dict[str, Any],
    fixed_receipts: dict[str, Any],
    source_receipts: dict[str, Any],
    actual_tool_receipts: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bytes]:
    return contract.verify_run_manifest_common(
        data,
        image_receipt=image_receipt,
        kernel_result_receipt=kernel_result_receipt,
        fixed_receipts=fixed_receipts,
        source_receipts=source_receipts,
        actual_tool_receipts=actual_tool_receipts,
        error=engine.CheckError,
    )


def classify_image(image: bytes) -> dict[str, Any]:
    try:
        return contract.classify_image(image)
    except contract.engine.BuildError as exc:
        raise engine.CheckError(str(exc)) from exc


def verify_candidate_run_binding(
    binding: Any, run_encoded: bytes, run_id: bytes
) -> None:
    try:
        expected = contract.candidate_run_binding(run_encoded, run_id)
    except contract.engine.BuildError as exc:
        raise engine.CheckError(str(exc)) from exc
    if binding != expected:
        raise engine.CheckError("R4W1-E0 candidate run binding mismatch")


def run_binding_evidence(run_encoded: bytes, run_id: bytes) -> dict[str, Any]:
    if run_id != contract.proof.PROBE_ID:
        raise engine.CheckError("R4W1-E0 static result run ID mismatch")
    return {
        "run_id": run_id.hex(),
        "canonical_manifest_size": len(run_encoded),
        "canonical_manifest_sha256": hashlib.sha256(run_encoded).hexdigest(),
        "fixed_probe_id": True,
        "clean_baseline_required": True,
        "verified": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--kernel-result", type=Path, default=DEFAULT_KERNEL_RESULT)
    parser.add_argument("--base-boot", type=Path, default=engine.DEFAULT_BASE_BOOT)
    parser.add_argument(
        "--vendor-ramdisk", type=Path, default=engine.DEFAULT_VENDOR_RAMDISK
    )
    parser.add_argument("--vendor-boot", type=Path, default=engine.DEFAULT_VENDOR_BOOT)
    parser.add_argument("--lz4", type=Path, default=engine.DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=engine.DEFAULT_MAGISKBOOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "CANDIDATE_SCHEMA": CANDIDATE_SCHEMA,
        "RUN_MANIFEST_SCHEMA": RUN_MANIFEST_SCHEMA,
        "CANDIDATE_VERDICT": CANDIDATE_VERDICT,
        "TARGET": contract.proof.TARGET,
        "RUNG": RUNG,
        "DEFAULT_CANDIDATE": DEFAULT_CANDIDATE,
        "DEFAULT_IMAGE": DEFAULT_IMAGE,
        "DEFAULT_KERNEL_RESULT": DEFAULT_KERNEL_RESULT,
        "DEFAULT_OUT": DEFAULT_OUT,
        "build_artifact": contract.artifact,
        "checkpoint": contract.checkpoint,
        "e1": contract.runtime,
        "verify_kernel_result": verify_kernel_result,
        "verify_run_manifest": verify_run_manifest,
        "classify_image": classify_image,
        "verify_candidate_run_binding": verify_candidate_run_binding,
        "run_binding_evidence": run_binding_evidence,
        "parse_args": parse_args,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(engine, name, value)


def main(argv: list[str] | None = None) -> int:
    with bind_engine():
        return engine.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
