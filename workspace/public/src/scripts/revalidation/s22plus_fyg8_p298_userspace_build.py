#!/usr/bin/env python3
"""Build the exact P2.98 userspace reproducibly."""

from __future__ import annotations

from pathlib import Path

import s22plus_fyg8_p286_userspace_build as base
import s22plus_fyg8_p298_candidate_contract as candidate_contract
import s22plus_fyg8_p298_source_contract as p298


SCHEMA = "s22plus_fyg8_p298_userspace_build_v1"
VERDICT = p298.USERSPACE_VERDICT
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p298/userspace")
BuildError = base.BuildError


def _configure() -> None:
    candidate_contract._configure()
    base.candidate_contract = candidate_contract
    base.p286 = p298
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH
    base.DEFAULT_SOURCE = DEFAULT_SOURCE
    base.DEFAULT_OUT = DEFAULT_OUT


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def verdict_for_profile(profile: str, source_contract_id: str | None = None) -> str:
    _configure()
    return base.verdict_for_profile(profile, source_contract_id)


def build_userspace(args):  # noqa: ANN001, ANN201
    _configure()
    return base.build_userspace(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
