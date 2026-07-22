#!/usr/bin/env python3
"""Build the reviewed FYG8 P2.19 same-ring kernel host-only."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p219_same_ring_contract as contract  # noqa: E402
import s22plus_fyg8_r4w1d_build as engine  # noqa: E402


SCHEMA = "s22plus_fyg8_p221_build_v1"
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_p221_build/build"
)
BASE_OUTPUT_GATE = engine.witness_output_gate


class _ContractAdapter:
    CONFIG = contract.CONFIG
    VERDICT = contract.VERDICT
    DEFAULT_PATCH = contract.DEFAULT_PATCH
    PATCH_SHA256 = contract.PATCH_SHA256
    BASE_FILES = contract.shared.BASE_FILES
    PATCHED_FILES = contract.PATCHED_FILES
    CheckError = contract.CheckError

    @staticmethod
    def run_check(
        work_tree: Path,
        patch: Path,
        _unused_inherited: Path,
        _unused_carrier_boot: Path,
        _unused_carrier_init: Path,
    ) -> dict[str, Any]:
        return contract.run(work_tree, patch)


def output_gate(work_tree: Path) -> dict[str, Any]:
    result = BASE_OUTPUT_GATE(work_tree)
    if not result.get("image_path") or not result.get("vmlinux_path"):
        return result
    image = Path(result["image_path"]).read_bytes()
    vmlinux = Path(result["vmlinux_path"]).read_bytes()
    counts = {
        "image_userspace_count": image.count(contract.USERSPACE_PROOF),
        "vmlinux_userspace_count": vmlinux.count(contract.USERSPACE_PROOF),
        "image_unsat_count": image.count(contract.UNSAT_PROOF),
        "vmlinux_unsat_count": vmlinux.count(contract.UNSAT_PROOF),
        "image_long_family_count": image.count(contract.decoder.ENTRY_FAMILY),
        "vmlinux_long_family_count": vmlinux.count(contract.decoder.ENTRY_FAMILY),
        "image_unsat_family_count": image.count(contract.decoder.UNSAT_FAMILY),
        "vmlinux_unsat_family_count": vmlinux.count(contract.decoder.UNSAT_FAMILY),
        "image_old_e0_entry_count": image.count(contract.OLD_E0_ENTRY_PROOF),
        "vmlinux_old_e0_entry_count": vmlinux.count(contract.OLD_E0_ENTRY_PROOF),
        "image_old_e0_userspace_count": image.count(
            contract.OLD_E0_USERSPACE_PROOF
        ),
        "vmlinux_old_e0_userspace_count": vmlinux.count(
            contract.OLD_E0_USERSPACE_PROOF
        ),
    }
    result.update(counts)
    result["verified"] = result.get("verified") is True and counts == {
        "image_userspace_count": 1,
        "vmlinux_userspace_count": 1,
        "image_unsat_count": 1,
        "vmlinux_unsat_count": 1,
        "image_long_family_count": 2,
        "vmlinux_long_family_count": 2,
        "image_unsat_family_count": 1,
        "vmlinux_unsat_family_count": 1,
        "image_old_e0_entry_count": 0,
        "vmlinux_old_e0_entry_count": 0,
        "image_old_e0_userspace_count": 0,
        "vmlinux_old_e0_userspace_count": 0,
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "build"), default="preflight")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--work-tree", type=Path, default=engine.base.DEFAULT_WORK_TREE)
    parser.add_argument("--clang-repo", type=Path, default=engine.base.DEFAULT_CLANG_REPO)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--base-archive", type=Path, default=engine.base.DEFAULT_BASE_ARCHIVE)
    parser.add_argument("--delta-archive", type=Path, default=engine.base.DEFAULT_DELTA_ARCHIVE)
    parser.add_argument("--overlay-audit", type=Path, default=engine.base.DEFAULT_OVERLAY_AUDIT)
    parser.add_argument("--stock-baseline", type=Path, default=engine.base.DEFAULT_STOCK_BASELINE)
    parser.add_argument("--patch", type=Path, default=contract.DEFAULT_PATCH)
    args = parser.parse_args()
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
        "PROOF_BYTES": contract.ENTRY_PROOF,
        # The inherited gate must count the exact ENTRY once.  P2.21 adds the
        # shared long-family and UNSAT cardinality checks above.
        "PROOF_FAMILY": contract.ENTRY_PROOF,
        "HISTORICAL_FAMILIES": (
            b"[[S22P1E|",
            b"[[S22P1D|",
            b"[[S22R4W1B|",
            b"[[S22R4W1|",
            contract.OLD_E0_ENTRY_PROOF,
            contract.OLD_E0_USERSPACE_PROOF,
        ),
        "HISTORICAL_CONFIGS": (
            "CONFIG_S22PLUS_FYG8_PID1_USERSPACE_PROOF",
            "CONFIG_S22PLUS_FYG8_RUNTIME_CHECKPOINT",
            "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS",
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS",
        ),
        "CONTRACT_RESULT_KEY": "p219_same_ring_contract",
        "BUILD_PASS_KEY": "p221_build_pass",
        "witness_output_gate": output_gate,
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
