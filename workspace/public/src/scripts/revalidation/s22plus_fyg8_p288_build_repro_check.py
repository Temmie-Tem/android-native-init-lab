#!/usr/bin/env python3
"""Verify P2.88 Full-LTO A/B and gate A path leaks before B."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import s22plus_fyg8_p286_build_repro_check as base
import s22plus_fyg8_p288_build as build
import s22plus_fyg8_p288_candidate_contract as candidate_contract
import s22plus_fyg8_p288_source_contract as p288


SCHEMA = "s22plus_fyg8_p288_build_repro_check_v1"
VERDICT = (
    "PASS_P288_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY"
)
PATH_GATE_SCHEMA = "s22plus_fyg8_p288_full_lto_a_path_gate_v1"
PATH_GATE_VERDICT = "PASS_P288_FULL_LTO_A_PATH_LEAK_GATE_HOST_ONLY"
TARGET = candidate_contract.TARGET
P288_SOURCE_CONTRACT_ID = p288.CONTRACT_ID
P286_SOURCE_CONTRACT_ID = P288_SOURCE_CONTRACT_ID
P288_QUALIFICATION_MODULE = "s22plus_fyg8_p288_pre_lto_qualification"
P288_QUALIFICATION_PROVENANCE_KEY = "p288_pre_lto_qualification"
P286_QUALIFICATION_MODULE = P288_QUALIFICATION_MODULE
P286_QUALIFICATION_PROVENANCE_KEY = (
    P288_QUALIFICATION_PROVENANCE_KEY
)
DEFAULT_BUILD_A = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/artifacts-a"
)
DEFAULT_BUILD_B = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/artifacts-b"
)
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_NM = base.DEFAULT_NM
DEFAULT_OBJDUMP = base.DEFAULT_OBJDUMP
ARTIFACT_LIMITS = dict(base.ARTIFACT_LIMITS)
RANDOM_PRIVATE_PATH_PREFIX = base.RANDOM_PRIVATE_PATH_PREFIX
LINKED_VALIDATOR_ADAPTERS = {
    **base.LINKED_VALIDATOR_ADAPTERS,
    P288_SOURCE_CONTRACT_ID: "s22plus_fyg8_p288_linked_audit",
}
CheckError = base.CheckError


def _configure() -> None:
    candidate_contract._configure()
    build._configure()
    base.build = build
    base.candidate_contract = candidate_contract
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.P286_SOURCE_CONTRACT_ID = P288_SOURCE_CONTRACT_ID
    base.P286_QUALIFICATION_MODULE = P288_QUALIFICATION_MODULE
    base.P286_QUALIFICATION_PROVENANCE_KEY = (
        P288_QUALIFICATION_PROVENANCE_KEY
    )
    base.DEFAULT_BUILD_A = DEFAULT_BUILD_A
    base.DEFAULT_BUILD_B = DEFAULT_BUILD_B
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH
    base.DEFAULT_SOURCE = DEFAULT_SOURCE
    base.LINKED_VALIDATOR_ADAPTERS = dict(
        LINKED_VALIDATOR_ADAPTERS
    )


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def verify_p286_qualification_file(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    _configure()
    return base.verify_p286_qualification_file(*args, **kwargs)


def verify_p288_qualification_file(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return verify_p286_qualification_file(*args, **kwargs)


def _string_inventory(data: bytes) -> tuple[bytes, ...]:
    return tuple(
        match.group(0)
        for match in re.finditer(rb"[\x20-\x7e]{4,}", data)
    )


def _path_fingerprint(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def audit_a_path_leaks(directory: Path) -> dict[str, Any]:
    _configure()
    root = candidate_contract.intent.repo_root()
    selected = candidate_contract.intent.resolve(root, directory)
    if selected.is_symlink() or not selected.is_dir():
        raise CheckError(
            "P2.88 Full-LTO A directory is missing or indirect"
        )
    vmlinux = candidate_contract.stable_read(
        selected / "vmlinux",
        "P2.88 Full-LTO A vmlinux",
        ARTIFACT_LIMITS["vmlinux"],
    )
    image = candidate_contract.stable_read(
        selected / "Image",
        "P2.88 Full-LTO A Image",
        ARTIFACT_LIMITS["Image"],
    )
    strings = _string_inventory(vmlinux)
    clang_resource_paths = tuple(
        value
        for value in strings
        if value.startswith(b"/")
        and b"/lib/clang/" in value
        and b"/include" in value
    )
    stable_paths = tuple(
        value
        for value in clang_resource_paths
        if value.startswith(b"/private-repo/")
    )
    absolute_host_paths = tuple(
        value
        for value in clang_resource_paths
        if not value.startswith(b"/private-repo/")
    )
    random_counts = {
        "vmlinux": vmlinux.count(RANDOM_PRIVATE_PATH_PREFIX),
        "Image": image.count(RANDOM_PRIVATE_PATH_PREFIX),
    }
    if any(random_counts.values()):
        raise CheckError(
            "P2.88 Full-LTO A leaks a random private namespace"
        )
    if absolute_host_paths:
        raise CheckError(
            "P2.88 Full-LTO A leaks an absolute clang resource path"
        )
    if not stable_paths:
        raise CheckError(
            "P2.88 Full-LTO A lacks the mapped clang resource path"
        )
    return {
        "schema": PATH_GATE_SCHEMA,
        "verdict": PATH_GATE_VERDICT,
        "build_a": {
            "Image": candidate_contract.intent.receipt(image),
            "vmlinux": candidate_contract.intent.receipt(vmlinux),
        },
        "random_private_namespace_counts": random_counts,
        "absolute_host_clang_resource_path_count": 0,
        "mapped_clang_resource_path_count": len(stable_paths),
        "mapped_clang_resource_path_fingerprints": sorted(
            {_path_fingerprint(value) for value in stable_paths}
        ),
        "b_build_permitted": True,
        "verified": True,
        "safety": {
            "host_only": True,
            "kernel_built": True,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def check(args):  # noqa: ANN001, ANN201
    _configure()
    return base.check(args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--a-only-path-leak-gate", action="store_true"
    )
    parser.add_argument("--build-a", type=Path, default=DEFAULT_BUILD_A)
    parser.add_argument("--build-b", type=Path, default=DEFAULT_BUILD_B)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--nm", type=Path, default=DEFAULT_NM)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = (
            audit_a_path_leaks(args.build_a)
            if args.a_only_path_leak_gate
            else check(args)
        )
    except (
        CheckError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema": (
                        PATH_GATE_SCHEMA
                        if args.a_only_path_leak_gate
                        else SCHEMA
                    ),
                    "verdict": "FAIL_CLOSED",
                    "error": str(exc),
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
