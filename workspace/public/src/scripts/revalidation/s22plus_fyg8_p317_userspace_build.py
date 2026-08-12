#!/usr/bin/env python3
"""Build P3.17 userspace twice against the fixed P3.10 Image."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile

import s22plus_fyg8_p286_userspace_build as base
import s22plus_fyg8_p310_candidate_contract as p310_contract
import s22plus_fyg8_p317_candidate_contract as candidate_contract
import s22plus_fyg8_p317_overlay_contract as contract


SCHEMA = "s22plus_fyg8_p317_userspace_build_v1"
VERDICT = contract.USERSPACE_VERDICT
TARGET = contract.TARGET
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p317/userspace")
COMPILE_FLAGS = base.COMPILE_FLAGS
BuildError = base.BuildError


class _P317SourceModule:
    MODULE_PLAN_COUNT = 69

    def __init__(self, parent_module) -> None:  # noqa: ANN001
        self._parent_module = parent_module

    def __getattr__(self, name: str):  # noqa: ANN204
        return getattr(self._parent_module, name)


def verdict_for_profile(profile: str, source_contract_id: str | None = None) -> str:
    if profile != contract.PROFILE or source_contract_id != contract.PARENT_SOURCE_CONTRACT_ID:
        raise BuildError("P3.17 userspace profile/source contract differs")
    return VERDICT


def _configure_base() -> None:
    p310_contract._configure()  # noqa: SLF001
    base.candidate_contract = p310_contract


def _compile(root: Path, directory: Path, exact: dict, materialized: Path, tools: dict[str, str]) -> dict:
    _configure_base()
    original_selected = base._selected  # noqa: SLF001

    def p317_selected(source_contract_id: str, profile: str):  # noqa: ANN202
        selected = original_selected(source_contract_id, profile)
        return replace(selected, module=_P317SourceModule(selected.module))

    base._selected = p317_selected  # noqa: SLF001
    try:
        return base._compile_once(  # noqa: SLF001
            root, directory, bytes.fromhex(exact["run_id"]), tools,
            exact["profile"], contract.PARENT_SOURCE_CONTRACT_ID, materialized,
        )
    finally:
        base._selected = original_selected  # noqa: SLF001


def _source_contract(exact: dict) -> dict:
    return {
        "userspace_overlay_contract_id": contract.CONTRACT_ID,
        "parent_source_contract_id": contract.PARENT_SOURCE_CONTRACT_ID,
        **{
            key: exact[key]
            for key in (
                "source_receipts", "generated_artifacts", "fixed_image",
                "max77705_surface_gate", "executability_gates",
                "runtime_fixture", "late_loader_lifecycle", "envelope_fixture",
                "process_v2_adapter_fixture", "sidecar_positive_control",
                "telemetry", "observer", "packaging_requirements",
            )
        },
        "verified": True,
    }


def build_userspace(args: argparse.Namespace) -> dict:
    root = candidate_contract.intent.repo_root()
    output = candidate_contract.intent.resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"P3.17 userspace output exists: {output}")
    exact = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, args.source),
        candidate_contract.intent.resolve(root, args.intent),
        candidate_contract.intent.resolve(root, args.patch),
    )
    materialized = candidate_contract.intent.resolve(root, args.intent).parent / "materialized-sources"
    _configure_base()
    tools = base.require_tools()
    builds = []
    metadata = []
    for label in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"s22-p317-userspace-{label}-") as name:
            directory = Path(name)
            result = _compile(root, directory, exact, materialized, tools)
            metadata.append(result)
            builds.append({
                "init": (directory / "init").read_bytes(),
                "child": (directory / "s22-e1-child").read_bytes(),
            })
    if builds[0] != builds[1] or metadata[0] != metadata[1]:
        raise BuildError("P3.17 userspace two-build reproducibility mismatch")
    result = {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "candidate_contract": exact,
        "source_contract": _source_contract(exact),
        "run_id": exact["run_id"],
        "profile": exact["profile"],
        "compile_flags": list(COMPILE_FLAGS),
        "outputs": metadata[0],
        "two_build_byte_identical": True,
        "module_plan_count": 69,
        "late_diagnostic_payload_count": 1,
        "telemetry": exact["telemetry"],
        "observer": exact["observer"],
        "safety": {
            "host_only": True, "kernel_built": False,
            "full_lto_ab_required": False, "fixed_p310_image": True,
            "early_stock_module_count": 69,
            "diagnostic_absent_from_early_plan": True,
            "module_binaries_injected": 0, "boot_image_created": False,
            "candidate_packaged": False, "device_contact": False,
            "live_authorized": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as name:
        staging = Path(name)
        (staging / "init").write_bytes(builds[0]["init"])
        (staging / "s22-e1-child").write_bytes(builds[0]["child"])
        (staging / "init").chmod(0o755)
        (staging / "s22-e1-child").chmod(0o755)
        (staging / "userspace-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="ascii",
        )
        os.replace(staging, output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    try:
        result = build_userspace(args)
    except (
        BuildError, candidate_contract.ContractError,
        candidate_contract.intent.IntentError, subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
