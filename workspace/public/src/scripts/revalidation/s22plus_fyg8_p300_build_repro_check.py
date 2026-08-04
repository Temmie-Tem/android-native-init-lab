#!/usr/bin/env python3
"""Verify P3.00 Full-LTO A/B with the inherited path-leak gate."""

from __future__ import annotations

import json
from pathlib import Path

import s22plus_fyg8_p290_build_repro_check as base
import s22plus_fyg8_p300_build as build
import s22plus_fyg8_p300_candidate_contract as candidate_contract
import s22plus_fyg8_p300_linked_audit as linked_audit
import s22plus_fyg8_p300_source_contract as p300


SCHEMA = "s22plus_fyg8_p300_build_repro_check_v1"
VERDICT = "PASS_P300_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY"
PATH_GATE_SCHEMA = "s22plus_fyg8_p300_full_lto_a_path_gate_v1"
PATH_GATE_VERDICT = "PASS_P300_FULL_LTO_A_PATH_LEAK_GATE_HOST_ONLY"
TARGET = candidate_contract.TARGET
P300_SOURCE_CONTRACT_ID = p300.CONTRACT_ID
P286_SOURCE_CONTRACT_ID = P300_SOURCE_CONTRACT_ID
P300_QUALIFICATION_MODULE = "s22plus_fyg8_p300_pre_lto_qualification"
P300_QUALIFICATION_PROVENANCE_KEY = "p300_pre_lto_qualification"
P286_QUALIFICATION_MODULE = P300_QUALIFICATION_MODULE
P286_QUALIFICATION_PROVENANCE_KEY = P300_QUALIFICATION_PROVENANCE_KEY
DEFAULT_BUILD_A = Path("workspace/private/outputs/s22plus_fyg8_p300/artifacts-a")
DEFAULT_BUILD_B = Path("workspace/private/outputs/s22plus_fyg8_p300/artifacts-b")
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_NM = base.DEFAULT_NM
DEFAULT_OBJDUMP = base.DEFAULT_OBJDUMP
ARTIFACT_LIMITS = dict(base.ARTIFACT_LIMITS)
RANDOM_PRIVATE_PATH_PREFIX = base.RANDOM_PRIVATE_PATH_PREFIX
CLANG_RESOURCE_PATH_MARKERS = base.CLANG_RESOURCE_PATH_MARKERS
LINKED_VALIDATOR_ADAPTERS = {
    **base.LINKED_VALIDATOR_ADAPTERS,
    P300_SOURCE_CONTRACT_ID: "s22plus_fyg8_p300_postbuild_linked_audit",
}
CheckError = base.CheckError


def _configure() -> None:
    candidate_contract._configure()
    build._configure()
    base.build = build
    base.candidate_contract = candidate_contract
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.PATH_GATE_SCHEMA = PATH_GATE_SCHEMA
    base.PATH_GATE_VERDICT = PATH_GATE_VERDICT
    base.TARGET = TARGET
    base.P290_SOURCE_CONTRACT_ID = P300_SOURCE_CONTRACT_ID
    base.P286_SOURCE_CONTRACT_ID = P300_SOURCE_CONTRACT_ID
    base.P290_QUALIFICATION_MODULE = P300_QUALIFICATION_MODULE
    base.P290_QUALIFICATION_PROVENANCE_KEY = P300_QUALIFICATION_PROVENANCE_KEY
    base.P286_QUALIFICATION_MODULE = P300_QUALIFICATION_MODULE
    base.P286_QUALIFICATION_PROVENANCE_KEY = P300_QUALIFICATION_PROVENANCE_KEY
    base.DEFAULT_BUILD_A = DEFAULT_BUILD_A
    base.DEFAULT_BUILD_B = DEFAULT_BUILD_B
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH
    base.DEFAULT_SOURCE = DEFAULT_SOURCE
    base.LINKED_VALIDATOR_ADAPTERS = dict(LINKED_VALIDATOR_ADAPTERS)
    base._configure()  # noqa: SLF001


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def verify_p300_qualification_file(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    _configure()
    return base.base.verify_p286_qualification_file(*args, **kwargs)


def audit_a_path_leaks(directory: Path) -> dict:
    _configure()
    result = dict(base.audit_a_path_leaks(directory))
    result["schema"] = PATH_GATE_SCHEMA
    result["verdict"] = PATH_GATE_VERDICT
    return result


def check(args):  # noqa: ANN001, ANN201
    _configure()
    return base.check(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit_a_path_leaks(args.build_a) if args.a_only_path_leak_gate else check(args)
    except (
        CheckError,
        linked_audit.AuditError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema": PATH_GATE_SCHEMA if args.a_only_path_leak_gate else SCHEMA,
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
