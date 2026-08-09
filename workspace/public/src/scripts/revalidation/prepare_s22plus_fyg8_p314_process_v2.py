#!/usr/bin/env python3
"""Promote one checked P3.14 candidate into Process-v2 evidence."""

from __future__ import annotations

from pathlib import Path

import prepare_s22plus_fyg8_p234_process_v2 as base
import s22plus_fyg8_p313_e2_stock_closure as e2_closure_selector
import s22plus_fyg8_p314_candidate_static_checker as static_checker


SCHEMA = "s22plus_fyg8_p314_process_v2_promotion_v1"
VERDICT = base.VERDICT
TARGET = static_checker.TARGET
DEFAULT_STATIC = static_checker.DEFAULT_OUT
DEFAULT_CANDIDATE_AP = static_checker.DEFAULT_CANDIDATE / "odin4/AP.tar.md5"
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p314/process-v2")


def _configure() -> None:
    static_checker._configure()  # noqa: SLF001
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
