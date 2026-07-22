#!/usr/bin/env python3
"""Promote the checked P2.26 candidate with the reusable P2.22 core."""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_s22plus_fyg8_p222_process_v2 as engine  # noqa: E402


SCHEMA = "s22plus_fyg8_p227_process_v2_promotion_v1"
VERDICT = "PASS_P227_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION"
P226_SCHEMA = "s22plus_fyg8_p226_candidate_static_checker_v1"
P226_VERDICT = "PASS_P226_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
P226_STATIC_SIZE = 11_203
P226_STATIC_SHA256 = (
    "3dbabd3fd9e411eb425a66accb2d0f589f3ce69862d13e481f2ca0095702aa69"
)
DEFAULT_P226_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p226_candidate/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_p226_candidate/"
    "artifacts/odin4/AP.tar.md5"
)
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p227_process_v2")
CANDIDATE_AP = {
    "path": str(DEFAULT_CANDIDATE_AP),
    "size": 27_064_361,
    "sha256": "aad4cf6bb572e228b81a1c8f441ecc50c021e3350935a349c58ed83ba4c2c44f",
}
PromotionError = engine.PromotionError
receipt = engine.receipt
canonical = engine.canonical
stable_read = engine.stable_read


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--p226-static",
        dest="p221_static",
        type=Path,
        default=DEFAULT_P226_STATIC,
    )
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements: dict[str, Any] = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "P221_SCHEMA": P226_SCHEMA,
        "P221_VERDICT": P226_VERDICT,
        "P221_STATIC_SIZE": P226_STATIC_SIZE,
        "P221_STATIC_SHA256": P226_STATIC_SHA256,
        "DEFAULT_P221_STATIC": DEFAULT_P226_STATIC,
        "DEFAULT_CANDIDATE_AP": DEFAULT_CANDIDATE_AP,
        "DEFAULT_OUT": DEFAULT_OUT,
        "CANDIDATE_AP": CANDIDATE_AP,
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


def derive(result: dict[str, Any], candidate_ap: dict[str, Any]):
    with bind_engine():
        return engine.derive(result, candidate_ap)


def main(argv: list[str] | None = None) -> int:
    with bind_engine():
        return engine.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
