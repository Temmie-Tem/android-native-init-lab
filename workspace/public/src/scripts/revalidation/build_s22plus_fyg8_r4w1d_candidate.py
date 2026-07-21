#!/usr/bin/env python3
"""Build the host-only FYG8 R4W1-D retained-PID1 witness candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_s22plus_fyg8_r4w1b_candidate as engine  # noqa: E402
import s22plus_fyg8_r4w1d_witness_contract as contract  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1d_candidate_build_v1"
VERDICT = "PASS_R4W1D_CANDIDATE_BUILT_HOST_ONLY"
TARGET = contract.TARGET
RUNG = "R4W1-D"
CARRIER_SHA256 = contract.CARRIER_BOOT_SHA256
IMAGE_SHA256 = "bb768461a55a8ed4b36b4e5777e12e37953fa76fa3703b332b4273d653cbdcd9"
REPRO_RESULT_SIZE = 319_637
REPRO_RESULT_SHA256 = "6abde754a7411168bfd7bd42878efd9d743cd9cace86b113fbfb79294a6f5a60"
REPRO_SCHEMA = "s22plus_fyg8_r4w1d_repro_check_v1"
REPRO_VERDICT = "PASS_R4W1D_CLEAN_REPRODUCIBILITY"
MARKER = contract.PROOF.encode("ascii")
MARKER_FAMILY = contract.PROOF_FAMILY.encode("ascii")

DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate/reproduction-a"
)
DEFAULT_CARRIER = contract.DEFAULT_CARRIER_BOOT
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate_inputs/Image"
)
DEFAULT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_static_repro_20260721/"
    "repro/result.json"
)
DEFAULT_LZ4 = engine.DEFAULT_LZ4
DEFAULT_ODIN = engine.DEFAULT_ODIN

BuildError = engine.BuildError


@contextmanager
def _bind_engine_contract() -> Iterator[None]:
    replacements: dict[str, Any] = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "TARGET": TARGET,
        "RUNG": RUNG,
        "CARRIER_SHA256": CARRIER_SHA256,
        "IMAGE_SHA256": IMAGE_SHA256,
        "REPRO_RESULT_SIZE": REPRO_RESULT_SIZE,
        "REPRO_RESULT_SHA256": REPRO_RESULT_SHA256,
        "REPRO_SCHEMA": REPRO_SCHEMA,
        "REPRO_VERDICT": REPRO_VERDICT,
        "CARRIER_LABEL": "R4W1-C watchdog carrier",
        "IMAGE_LABEL": "R4W1-D Image",
        "REPRO_LABEL": "R4W1-D reproduction result",
        "CARRIER_INPUT_KEY": "r4w1c_watchdog_carrier",
        "IMAGE_INPUT_KEY": "r4w1d_image",
        "REPRO_INPUT_KEY": "r4w1d_reproduction_result",
        "MARKER_ID": contract.MARKER_ID,
        "MARKER": MARKER,
        "MARKER_FAMILY": MARKER_FAMILY,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(engine, name, value)


def verify_reproduction_result(encoded: bytes) -> dict[str, Any]:
    with _bind_engine_contract():
        return engine.verify_reproduction_result(encoded)


def build_candidate_bytes(carrier: bytes, image: bytes) -> tuple[bytes, dict[str, Any]]:
    with _bind_engine_contract():
        return engine.build_candidate_bytes(carrier, image)


def build(args: argparse.Namespace) -> dict[str, Any]:
    with _bind_engine_contract():
        return engine.build(args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        manifest = build(parse_args(argv))
    except (BuildError, engine.boot_slice.BootSliceError, OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": manifest["verdict"],
                "boot_sha256": manifest["outputs"]["boot_img"]["sha256"],
                "ap_sha256": manifest["outputs"]["ap_tar_md5"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
