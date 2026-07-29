#!/usr/bin/env python3
"""Build one candidate-bound FYG8 E1 kernel host-only."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p286_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p286_source_contract as p286  # noqa: E402
import s22plus_fyg8_p280_pre_lto_qualification as p280_qualification  # noqa: E402
import s22plus_fyg8_r4w1d_build as engine  # noqa: E402


SCHEMA = "s22plus_fyg8_p286_build_v1"
DEFAULT_RESULT_DIR = Path("workspace/private/outputs/s22plus_fyg8_p286/build-a")
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
BASE_OUTPUT_GATE = engine.witness_output_gate
BASE_PREFLIGHT = engine.base.preflight

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
P286_KERNEL_DEBUG_PATH_REPRODUCIBLE = (
    engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE + PRIVATE_REPO_DEBUG_MAP
)
P282_SOURCE_CONTRACT_ID = (
    "s22plus-fyg8-p282-prebind-child-reinit-decision-v1"
)
P284_SOURCE_CONTRACT_ID = "s22plus-fyg8-p284-sysfs-ingestion-correction-v1"
P286_SOURCE_CONTRACT_ID = p286.CONTRACT_ID
QUALIFICATION_MODULES = {
    p280_qualification.p280.CONTRACT_ID: (
        "s22plus_fyg8_p280_pre_lto_qualification",
        "p280_pre_lto_qualification",
        "P2.80",
    ),
    P282_SOURCE_CONTRACT_ID: (
        "s22plus_fyg8_p282_pre_lto_qualification",
        "p282_pre_lto_qualification",
        "P2.82",
    ),
    P284_SOURCE_CONTRACT_ID: (
        "s22plus_fyg8_p284_pre_lto_qualification",
        "p284_pre_lto_qualification",
        "P2.84",
    ),
    P286_SOURCE_CONTRACT_ID: (
        "s22plus_fyg8_p286_pre_lto_qualification",
        "p286_pre_lto_qualification",
        "P2.86",
    ),
}


class BuildError(ValueError):
    pass


def _qualification_module(
    source_contract_id: str, module_name: str
) -> Any:
    try:
        qualification = (
            p280_qualification
            if module_name == p280_qualification.__name__
            else importlib.import_module(module_name)
        )
    except ImportError as exc:
        raise BuildError(
            f"qualification module unavailable for {source_contract_id}"
        ) from exc
    if (
        not callable(getattr(qualification, "verify_receipt", None))
        or not isinstance(
            getattr(qualification, "QualificationError", None), type
        )
    ):
        raise BuildError(
            f"qualification module interface mismatch for {source_contract_id}"
        )
    return qualification


_bound_pre_lto_qualification: dict[str, Any] | None = None
_bound_pre_lto_provenance_key: str | None = None
_active_base_preflight = BASE_PREFLIGHT


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
        source_contract_id = result.get("source_contract_id")
        if source_contract_id is None:
            expected_schema = candidate_contract.SCHEMA
            expected_verdict = candidate_contract.VERDICT
        else:
            selected = candidate_contract.intent.selected_source_contract(
                source_contract_id, result.get("profile")
            )
            expected_schema = selected.contract_schema
            expected_verdict = selected.contract_verdict
        if (
            result.get("schema") != expected_schema
            or result.get("verdict") != expected_verdict
            or result.get("verified") is not True
        ):
            raise BuildError("P2.86 candidate contract did not verify")
        cls.VERDICT = expected_verdict
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
    global _bound_pre_lto_qualification, _bound_pre_lto_provenance_key

    root = candidate_contract.intent.repo_root()
    paths = (args.work_tree, args.intent, args.patch)
    if any(path.is_absolute() for path in paths):
        raise BuildError("P2.86 build inputs must be repository-relative")
    intent_path = candidate_contract.intent.resolve(root, args.intent)
    result = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, args.work_tree),
        intent_path,
        candidate_contract.intent.resolve(root, args.patch),
    )
    _ContractAdapter.bind(result, intent_path)
    _bound_pre_lto_qualification = None
    _bound_pre_lto_provenance_key = None
    source_contract_id = result.get("source_contract_id")
    selection = QUALIFICATION_MODULES.get(source_contract_id)
    if selection is not None:
        module_name, provenance_key, label = selection
        qualification_path = getattr(args, "pre_lto_qualification", None)
        if qualification_path is None:
            raise BuildError(
                f"{label} build requires --pre-lto-qualification"
            )
        if qualification_path.is_absolute():
            raise BuildError(
                f"{label} pre-LTO qualification must be repository-relative"
            )
        qualification = _qualification_module(
            source_contract_id, module_name
        )
        qualification_contract = next(
            (
                getattr(candidate, "CONTRACT_ID")
                for name in ("p286", "p284", "p282", "p280")
                if (
                    (candidate := getattr(qualification, name, None))
                    is not None
                    and hasattr(candidate, "CONTRACT_ID")
                )
            ),
            None,
        )
        if qualification_contract != source_contract_id:
            raise BuildError(
                f"{label} qualification module contract mismatch"
            )
        try:
            _bound_pre_lto_qualification = (
                qualification.verify_receipt(
                    candidate_contract.intent.resolve(
                        root, qualification_path
                    ),
                    result,
                    intent_path=intent_path,
                    patch_path=candidate_contract.intent.resolve(
                        root, args.patch
                    ),
                )
            )
        except qualification.QualificationError as exc:
            raise BuildError(str(exc)) from exc
        if (
            _bound_pre_lto_qualification.get("source_contract_id")
            != source_contract_id
            or _bound_pre_lto_qualification.get("run_id")
            != result.get("run_id")
        ):
            raise BuildError(f"{label} qualification identity mismatch")
        _bound_pre_lto_provenance_key = provenance_key
    return result


def qualified_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    result = _active_base_preflight(*args, **kwargs)
    bound = _ContractAdapter._bound_result
    if bound is not None and bound.get("source_contract_id") in QUALIFICATION_MODULES:
        _module_name, expected_key, label = QUALIFICATION_MODULES[
            bound["source_contract_id"]
        ]
        bound_key = _bound_pre_lto_provenance_key
        if (
            bound_key is None
            and bound["source_contract_id"]
            == p280_qualification.p280.CONTRACT_ID
        ):
            bound_key = expected_key
        if (
            _bound_pre_lto_qualification is None
            or bound_key != expected_key
            or _bound_pre_lto_qualification.get("verified") is not True
        ):
            raise BuildError(f"{label} pre-LTO qualification is not bound")
        result["build_allowed"] = (
            result.get("build_allowed") is True
            and _bound_pre_lto_qualification["build_allowed"] is True
        )
        provenance = result.setdefault("provenance", {})
        provenance[expected_key] = _bound_pre_lto_qualification
    return result


def _bound_identity() -> tuple[bytes, bytes, list[str]]:
    result = _ContractAdapter._bound_result
    if result is None:
        raise BuildError("P2.86 output gate has no bound candidate identity")
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
    source_check_run_id = candidate_contract.intent.source_check_run_id(
        profile, bound.get("source_contract_id")
    )
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
    parser.add_argument("--pre-lto-qualification", type=Path)
    args = parser.parse_args()
    args.inherited_result = args.intent
    args.carrier_boot = args.patch
    args.carrier_init = args.patch
    _configure_contract(args)
    return args


@contextmanager
def bind_engine() -> Iterator[None]:
    global _active_base_preflight

    replacements = {
        "SCHEMA": SCHEMA,
        "EXECUTION_SCRIPT": Path(__file__),
        "DEFAULT_RESULT_DIR": DEFAULT_RESULT_DIR,
        "contract": _ContractAdapter,
        "PROOF_BYTES": LONG_FAMILY,
        "PROOF_FAMILY": LONG_FAMILY,
        "HISTORICAL_FAMILIES": HISTORICAL_FAMILIES,
        "HISTORICAL_CONFIGS": HISTORICAL_CONFIGS,
        "CONTRACT_RESULT_KEY": "p286_candidate_contract",
        "BUILD_PASS_KEY": "p286_build_pass",
        "witness_output_gate": output_gate,
        "parse_args": parse_args,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    previous_kernel_debug = engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE
    previous_preflight = engine.base.preflight
    previous_active_preflight = _active_base_preflight
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE = (
            P286_KERNEL_DEBUG_PATH_REPRODUCIBLE
        )
        _active_base_preflight = (
            BASE_PREFLIGHT
            if previous_preflight is qualified_preflight
            else previous_preflight
        )
        engine.base.preflight = qualified_preflight
        yield
    finally:
        engine.base.preflight = previous_preflight
        _active_base_preflight = previous_active_preflight
        engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE = previous_kernel_debug
        for name, value in previous.items():
            setattr(engine, name, value)


def main() -> int:
    with bind_engine():
        return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
