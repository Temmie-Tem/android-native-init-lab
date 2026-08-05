#!/usr/bin/env python3
"""Build P3.03 userspace twice against the fixed P3.00 kernel Image."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

import s22plus_fyg8_p286_userspace_build as base
import s22plus_fyg8_p303_candidate_contract as candidate_contract
import s22plus_fyg8_p303_overlay_contract as contract


SCHEMA = "s22plus_fyg8_p303_userspace_build_v1"
VERDICT = contract.USERSPACE_VERDICT
TARGET = contract.TARGET
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p303/userspace")
COMPILE_FLAGS = base.COMPILE_FLAGS
BuildError = base.BuildError


def verdict_for_profile(
    profile: str, source_contract_id: str | None = None
) -> str:
    if (
        profile != contract.PROFILE
        or source_contract_id != contract.PARENT_SOURCE_CONTRACT_ID
    ):
        raise BuildError("unsupported P3.03 userspace profile or parent contract")
    return VERDICT


def _compile(
    root: Path,
    directory: Path,
    exact: dict,
    materialized: Path,
    tools: dict[str, str],
) -> dict:
    return base._compile_once(  # noqa: SLF001
        root,
        directory,
        bytes.fromhex(exact["run_id"]),
        tools,
        exact["profile"],
        contract.PARENT_SOURCE_CONTRACT_ID,
        materialized,
    )


def build_userspace(args: argparse.Namespace) -> dict:
    root = candidate_contract.intent.repo_root()
    output = candidate_contract.intent.resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"P3.03 userspace output exists: {output}")
    exact = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, args.source),
        candidate_contract.intent.resolve(root, args.intent),
        candidate_contract.intent.resolve(root, args.patch),
    )
    materialized = (
        candidate_contract.intent.resolve(root, args.intent).parent
        / "materialized-sources"
    )
    tools = base.require_tools()
    builds = []
    metadata = []
    for label in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"s22-p303-userspace-{label}-") as name:
            directory = Path(name)
            result = _compile(root, directory, exact, materialized, tools)
            metadata.append(result)
            builds.append(
                {
                    "init": (directory / "init").read_bytes(),
                    "child": (directory / "s22-e1-child").read_bytes(),
                }
            )
    if builds[0] != builds[1] or metadata[0] != metadata[1]:
        raise BuildError("P3.03 userspace two-build reproducibility mismatch")
    result = {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "candidate_contract": exact,
        "source_contract": {
            "userspace_overlay_contract_id": contract.CONTRACT_ID,
            "parent_overlay_contract_id": contract.PARENT_OVERLAY_CONTRACT_ID,
            "parent_source_contract_id": contract.PARENT_SOURCE_CONTRACT_ID,
            "source_receipts": exact["source_receipts"],
            "generated_artifacts": exact["generated_artifacts"],
            "fixed_image": exact["fixed_image"],
            "callsite_audit": exact["callsite_audit"],
            "telemetry": exact["telemetry"],
            "verified": True,
        },
        "run_id": exact["run_id"],
        "profile": exact["profile"],
        "compile_flags": list(COMPILE_FLAGS),
        "outputs": metadata[0],
        "two_build_byte_identical": True,
        "callsite_descriptor_a_b_identical": True,
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "full_lto_ab_required": False,
            "fixed_p300_image": True,
            "module_binaries_injected": 0,
            "boot_image_created": False,
            "candidate_packaged": False,
            "device_contact": False,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_userspace(parse_args(argv))
    except (
        BuildError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
