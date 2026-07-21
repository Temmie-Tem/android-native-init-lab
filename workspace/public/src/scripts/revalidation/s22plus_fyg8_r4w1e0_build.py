#!/usr/bin/env python3
"""Build the FYG8 R4W1-E0 two-state PID 1 proof kernel host-only."""

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
import s22plus_fyg8_r4w1e0_pid1_userspace_proof as proof  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1e0_build_v1"
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_build/build"
)
BASE_OUTPUT_GATE = engine.witness_output_gate


class _ContractAdapter:
    CONFIG = proof.CONFIG
    VERDICT = proof.VERDICT
    DEFAULT_PATCH = proof.DEFAULT_PATCH
    PATCH_SHA256 = proof.PATCH_SHA256
    BASE_FILES = proof.shared.BASE_FILES
    PATCHED_FILES = proof.PATCHED_FILES

    @staticmethod
    def run_check(
        work_tree: Path,
        patch: Path,
        _unused_inherited: Path,
        runtime_receipt: Path,
        init: Path,
    ) -> dict[str, Any]:
        return proof.run(work_tree, patch, init, runtime_receipt)


def output_gate(work_tree: Path) -> dict[str, Any]:
    result = BASE_OUTPUT_GATE(work_tree)
    if not result.get("image_path") or not result.get("vmlinux_path"):
        return result
    image = Path(result["image_path"]).read_bytes()
    vmlinux = Path(result["vmlinux_path"]).read_bytes()
    result.update(
        {
            "image_userspace_proof_count": image.count(proof.USERSPACE_PROOF),
            "vmlinux_userspace_proof_count": vmlinux.count(proof.USERSPACE_PROOF),
            "image_shared_family_count": image.count(proof.PROOF_FAMILY),
            "vmlinux_shared_family_count": vmlinux.count(proof.PROOF_FAMILY),
        }
    )
    result["verified"] = result["verified"] and all(
        (
            result["image_userspace_proof_count"] == 1,
            result["vmlinux_userspace_proof_count"] == 1,
            result["image_shared_family_count"] == 2,
            result["vmlinux_shared_family_count"] == 2,
        )
    )
    return result


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
    parser.add_argument("--patch", type=Path, default=proof.DEFAULT_PATCH)
    parser.add_argument("--init", type=Path, default=proof.DEFAULT_INIT)
    parser.add_argument(
        "--runtime-receipt", type=Path, default=proof.DEFAULT_RUNTIME_RECEIPT
    )
    args = parser.parse_args()
    args.inherited_result = args.patch
    args.carrier_boot = args.runtime_receipt
    args.carrier_init = args.init
    return args


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "EXECUTION_SCRIPT": Path(__file__),
        "DEFAULT_RESULT_DIR": DEFAULT_RESULT_DIR,
        "contract": _ContractAdapter,
        "PROOF_BYTES": proof.ENTRY_PROOF,
        "PROOF_FAMILY": proof.ENTRY_PROOF,
        "HISTORICAL_FAMILIES": (
            b"[[S22P1E|",
            b"[[S22P1D|",
            b"[[S22R4W1B|",
            b"[[S22R4W1|",
        ),
        "HISTORICAL_CONFIGS": (
            "CONFIG_S22PLUS_FYG8_RUNTIME_CHECKPOINT",
            "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS",
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS",
        ),
        "CONTRACT_RESULT_KEY": "r4w1e0_pid1_userspace_proof_contract",
        "BUILD_PASS_KEY": "r4w1e0_build_pass",
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
