#!/usr/bin/env python3
"""Build the FYG8 R4W1-E runtime-checkpoint kernel host-only."""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_r4w1d_build as engine  # noqa: E402
import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1e_build_v1"
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_build/build"
)


class _ContractAdapter:
    CONFIG = checkpoint.CONFIG
    VERDICT = checkpoint.VERDICT
    DEFAULT_PATCH = checkpoint.DEFAULT_PATCH
    PATCH_SHA256 = checkpoint.PATCH_SHA256
    BASE_FILES = checkpoint.BASE_FILES
    PATCHED_FILES = checkpoint.PATCHED_FILES

    @staticmethod
    def run_check(
        work_tree: Path,
        patch: Path,
        _unused_inherited: Path,
        _unused_carrier_boot: Path,
        _unused_carrier_init: Path,
    ) -> dict[str, Any]:
        return checkpoint.run_check(work_tree, patch)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "build"), default="preflight")
    parser.add_argument("--jobs", type=int, default=min(__import__("os").cpu_count() or 1, 8))
    parser.add_argument("--work-tree", type=Path, default=engine.base.DEFAULT_WORK_TREE)
    parser.add_argument("--clang-repo", type=Path, default=engine.base.DEFAULT_CLANG_REPO)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--base-archive", type=Path, default=engine.base.DEFAULT_BASE_ARCHIVE)
    parser.add_argument("--delta-archive", type=Path, default=engine.base.DEFAULT_DELTA_ARCHIVE)
    parser.add_argument("--overlay-audit", type=Path, default=engine.base.DEFAULT_OVERLAY_AUDIT)
    parser.add_argument("--stock-baseline", type=Path, default=engine.base.DEFAULT_STOCK_BASELINE)
    parser.add_argument("--patch", type=Path, default=checkpoint.DEFAULT_PATCH)
    args = parser.parse_args()
    # The shared D engine has three legacy contract-only path fields. The E
    # adapter does not consume them, but keeps them repo-relative for the
    # engine's namespace/path gate.
    args.inherited_result = args.patch
    args.carrier_boot = args.patch
    args.carrier_init = args.patch
    return args


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "EXECUTION_SCRIPT": Path(__file__),
        "DEFAULT_RESULT_DIR": DEFAULT_RESULT_DIR,
        "contract": _ContractAdapter,
        "PROOF_BYTES": checkpoint.ENTRY_PROOF,
        "PROOF_FAMILY": checkpoint.ENTRY_FAMILY,
        "HISTORICAL_FAMILIES": (
            b"[[S22P1D|",
            b"[[S22R4W1B|",
            b"[[S22R4W1|",
        ),
        "HISTORICAL_CONFIGS": (
            "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS",
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS",
        ),
        "CONTRACT_RESULT_KEY": "r4w1e_checkpoint_contract",
        "BUILD_PASS_KEY": "r4w1e_build_pass",
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


def main() -> int:
    with bind_engine():
        return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
