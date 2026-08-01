#!/usr/bin/env python3
"""Promote one independently checked P2.96 candidate into offline evidence."""

from __future__ import annotations

from pathlib import Path

import prepare_s22plus_fyg8_p234_process_v2 as base
import s22plus_fyg8_p296_candidate_static_checker as static_checker
import s22plus_fyg8_p296_e2_stock_closure as e2_closure_selector


SCHEMA = "s22plus_fyg8_p296_process_v2_promotion_v1"
VERDICT = base.VERDICT
TARGET = static_checker.TARGET
DEFAULT_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p296/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_p296/"
    "candidate-a/odin4/AP.tar.md5"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p296/process-v2"
)


def _configure() -> None:
    static_checker._configure()
    base.static_checker = static_checker
    base.e2_closure_selector = e2_closure_selector
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.DEFAULT_STATIC = DEFAULT_STATIC
    base.DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_AP
    base.DEFAULT_OUT = DEFAULT_OUT


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
