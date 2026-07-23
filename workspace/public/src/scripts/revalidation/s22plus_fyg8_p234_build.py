#!/usr/bin/env python3
"""Build one candidate-bound FYG8 E1 kernel host-only."""

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

import s22plus_fyg8_p233_e1_static_checker as p233  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_r4w1d_build as engine  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_build_v1"
DEFAULT_RESULT_DIR = Path("workspace/private/outputs/s22plus_fyg8_p234/build-a")
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
BASE_OUTPUT_GATE = engine.witness_output_gate

CONFIG = "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE"
LONG_FAMILY = b"S22E1L1|"
UNSAT_FAMILY = b"S22E1U1|"
REQUEST_MAGIC = b"S22Q"
INERT_REJECTION_FAMILIES = (
    b"[[S22P1U|",
    b"S22UNS1|",
)
HISTORICAL_FAMILIES = (
    b"[[S22P1E|",
    b"[[S22P1D|",
    b"[[S22R4W1B|",
    b"[[S22R4W1|",
)
HISTORICAL_CONFIGS = (
    "CONFIG_S22PLUS_FYG8_PID1_SAME_RING_DISCRIMINATOR",
    "CONFIG_S22PLUS_FYG8_PID1_USERSPACE_PROOF",
    "CONFIG_S22PLUS_FYG8_RUNTIME_CHECKPOINT",
    "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS",
    "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS",
)
PRIVATE_REPO_DEBUG_MAP = (
    "KBUILD_AFLAGS += -fdebug-prefix-map="
    "$(realpath $(abs_srctree)/../../..)=/private-repo\n"
    "KBUILD_CFLAGS += -fdebug-prefix-map="
    "$(realpath $(abs_srctree)/../../..)=/private-repo\n"
)
P234_KERNEL_DEBUG_PATH_REPRODUCIBLE = (
    engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE + PRIVATE_REPO_DEBUG_MAP
)


class BuildError(ValueError):
    pass


class _ContractAdapter:
    CONFIG = CONFIG
    VERDICT = candidate_contract.VERDICT
    DEFAULT_PATCH = DEFAULT_PATCH
    PATCH_SHA256 = ""
    BASE_FILES: dict[str, str] = {}
    PATCHED_FILES: dict[str, str] = {}
    CheckError = candidate_contract.ContractError
    _bound_result: dict[str, Any] | None = None
    _intent_path: Path | None = None

    @classmethod
    def bind(cls, result: dict[str, Any], intent_path: Path) -> None:
        if result.get("verdict") != cls.VERDICT or result.get("verified") is not True:
            raise BuildError("P2.34 candidate contract did not verify")
        cls.PATCH_SHA256 = result["patch"]["sha256"]
        cls.BASE_FILES = dict(result["base_files"])
        cls.PATCHED_FILES = dict(result["patched_files"])
        cls._bound_result = result
        cls._intent_path = intent_path

    @classmethod
    def run_check(
        cls,
        work_tree: Path,
        patch: Path,
        intent_path: Path,
        _unused_carrier_boot: Path,
        _unused_carrier_init: Path,
    ) -> dict[str, Any]:
        root = candidate_contract.intent.repo_root()
        result = candidate_contract.verify(
            root,
            work_tree,
            intent_path,
            patch,
        )
        if cls._bound_result is None or cls._intent_path is None:
            raise BuildError("P2.34 candidate contract was not bound before build")
        if (
            result["run_id"] != cls._bound_result["run_id"]
            or result["patch"] != cls._bound_result["patch"]
            or intent_path != cls._intent_path
        ):
            raise BuildError("P2.34 candidate contract changed after argument binding")
        return result


def _configure_contract(args: argparse.Namespace) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    paths = (args.work_tree, args.intent, args.patch)
    if any(path.is_absolute() for path in paths):
        raise BuildError("P2.34 build inputs must be repository-relative")
    intent_path = candidate_contract.intent.resolve(root, args.intent)
    result = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, args.work_tree),
        intent_path,
        candidate_contract.intent.resolve(root, args.patch),
    )
    _ContractAdapter.bind(result, intent_path)
    return result


def _bound_identity() -> tuple[bytes, bytes, list[str]]:
    result = _ContractAdapter._bound_result
    if result is None:
        raise BuildError("P2.34 output gate has no bound candidate identity")
    run_id = result["run_id"].encode("ascii")
    unsat_tag = result["unsat_tag_hex"].encode("ascii")
    return run_id, unsat_tag, list(result["config_lines"])


def output_gate(work_tree: Path) -> dict[str, Any]:
    result = BASE_OUTPUT_GATE(work_tree)
    if not result.get("image_path") or not result.get("vmlinux_path"):
        return result
    image = Path(result["image_path"]).read_bytes()
    vmlinux = Path(result["vmlinux_path"]).read_bytes()
    config_path = (
        work_tree / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    )
    config_lines = config_path.read_text(encoding="utf-8").splitlines()
    run_id, unsat_tag, expected_config = _bound_identity()
    bound = _ContractAdapter._bound_result
    if bound is None:
        raise BuildError("candidate identity disappeared before output gate")
    profile = bound["profile"]
    source_check_run_id = candidate_contract.intent.source_check_run_id(profile)
    binaries = {"image": image, "vmlinux": vmlinux}
    identity_counts = {
        name: {
            "long_family": data.count(LONG_FAMILY),
            "unsat_family": data.count(UNSAT_FAMILY),
            "request_magic": data.count(REQUEST_MAGIC),
            "run_id_hex": data.count(run_id),
            "unsat_tag_hex": data.count(unsat_tag),
            "model_run_id": data.count(
                candidate_contract.intent.decoder.model.model_run_id(profile).hex().encode(
                    "ascii"
                )
            ),
            "source_check_run_id": data.count(
                source_check_run_id.hex().encode("ascii")
            ),
        }
        for name, data in binaries.items()
    }
    exact_config_counts = {
        line: config_lines.count(line) for line in expected_config
    }
    historical_config_enable_counts = {
        name: config_lines.count(f"{name}=y") for name in HISTORICAL_CONFIGS
    }
    inert_rejection_family_counts = {
        family.decode("ascii"): {
            name: data.count(family) for name, data in binaries.items()
        }
        for family in INERT_REJECTION_FAMILIES
    }
    result.update(
        {
            "candidate_run_id": run_id.decode("ascii"),
            "candidate_unsat_tag": unsat_tag.decode("ascii"),
            "candidate_binary_counts": identity_counts,
            "candidate_config_counts": exact_config_counts,
            "historical_config_enable_counts": historical_config_enable_counts,
            "inert_rejection_family_counts": inert_rejection_family_counts,
        }
    )
    result["verified"] = (
        result.get("verified") is True
        and all(
            row
            == {
                "long_family": 1,
                "unsat_family": 1,
                "request_magic": 1,
                "run_id_hex": 1,
                "unsat_tag_hex": 1,
                "model_run_id": 0,
                "source_check_run_id": 0,
            }
            for row in identity_counts.values()
        )
        and all(count == 1 for count in exact_config_counts.values())
        and all(count == 0 for count in historical_config_enable_counts.values())
        and all(
            row == {"image": 1, "vmlinux": 1}
            for row in inert_rejection_family_counts.values()
        )
    )
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
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    args = parser.parse_args()
    args.inherited_result = args.intent
    args.carrier_boot = args.patch
    args.carrier_init = args.patch
    _configure_contract(args)
    return args


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "EXECUTION_SCRIPT": Path(__file__),
        "DEFAULT_RESULT_DIR": DEFAULT_RESULT_DIR,
        "contract": _ContractAdapter,
        "PROOF_BYTES": LONG_FAMILY,
        "PROOF_FAMILY": LONG_FAMILY,
        "HISTORICAL_FAMILIES": HISTORICAL_FAMILIES,
        "HISTORICAL_CONFIGS": HISTORICAL_CONFIGS,
        "CONTRACT_RESULT_KEY": "p234_candidate_contract",
        "BUILD_PASS_KEY": "p234_build_pass",
        "witness_output_gate": output_gate,
        "parse_args": parse_args,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    previous_kernel_debug = engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE = (
            P234_KERNEL_DEBUG_PATH_REPRODUCIBLE
        )
        yield
    finally:
        engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE = previous_kernel_debug
        for name, value in previous.items():
            setattr(engine, name, value)


def main() -> int:
    with bind_engine():
        return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
