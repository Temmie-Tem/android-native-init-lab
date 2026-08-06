#!/usr/bin/env python3
"""Verify one exact P3.10 Carrier v2 candidate identity and patch."""

from __future__ import annotations

from pathlib import Path

import s22plus_fyg8_p286_candidate_contract as base
import s22plus_fyg8_p310_candidate_intent as intent
import s22plus_fyg8_p310_source_contract as p310


SCHEMA = p310.CONTRACT_SCHEMA
VERDICT = p310.CONTRACT_VERDICT
TARGET = intent.TARGET
DEFAULT_SOURCE = intent.DEFAULT_SOURCE
DEFAULT_INTENT = intent.DEFAULT_OUT / "candidate-intent.json"
DEFAULT_PATCH = intent.DEFAULT_OUT / "candidate.patch"
ContractError = base.ContractError
stable_read = base.stable_read


def _configure() -> None:
    intent._configure()
    intent.selector.select = intent._selector_select  # noqa: SLF001
    intent.selector.contract_ids = intent._selector_contract_ids  # noqa: SLF001
    base.intent = intent
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.DEFAULT_SOURCE = DEFAULT_SOURCE
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH


def verify(root: Path, source: Path, intent_path: Path, patch_path: Path):
    _configure()
    return base.verify(root, source, intent_path, patch_path)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
