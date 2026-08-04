#!/usr/bin/env python3
"""Build one candidate-bound P3.00 FYG8 kernel host-only."""

from __future__ import annotations

from pathlib import Path

import s22plus_fyg8_p286_build as base
import s22plus_fyg8_p300_candidate_contract as candidate_contract
import s22plus_fyg8_p300_source_contract as p300


SCHEMA = "s22plus_fyg8_p300_build_v1"
DEFAULT_RESULT_DIR = Path("workspace/private/outputs/s22plus_fyg8_p300/build-a")
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
P300_SOURCE_CONTRACT_ID = p300.CONTRACT_ID
P286_SOURCE_CONTRACT_ID = P300_SOURCE_CONTRACT_ID
P300_KERNEL_DEBUG_PATH_REPRODUCIBLE = base.P286_KERNEL_DEBUG_PATH_REPRODUCIBLE
P286_KERNEL_DEBUG_PATH_REPRODUCIBLE = P300_KERNEL_DEBUG_PATH_REPRODUCIBLE
QUALIFICATION_MODULES = {
    P300_SOURCE_CONTRACT_ID: (
        "s22plus_fyg8_p300_pre_lto_qualification",
        "p300_pre_lto_qualification",
        "P3.00",
    ),
}
BuildError = base.BuildError


def _configure() -> None:
    candidate_contract._configure()
    base.__file__ = __file__
    base.candidate_contract = candidate_contract
    base.p286 = p300
    base.SCHEMA = SCHEMA
    base.DEFAULT_RESULT_DIR = DEFAULT_RESULT_DIR
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH
    base.P286_SOURCE_CONTRACT_ID = P300_SOURCE_CONTRACT_ID
    base.P286_KERNEL_DEBUG_PATH_REPRODUCIBLE = P300_KERNEL_DEBUG_PATH_REPRODUCIBLE
    base.QUALIFICATION_MODULES = dict(QUALIFICATION_MODULES)


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def _configure_contract(args):  # noqa: ANN001, ANN201
    _configure()
    return base._configure_contract(args)  # noqa: SLF001


def parse_args():  # noqa: ANN201
    _configure()
    return base.parse_args()


def output_gate(work_tree: Path):  # noqa: ANN201
    _configure()
    return base.output_gate(work_tree)


def bind_engine():  # noqa: ANN201
    _configure()
    return base.bind_engine()


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
