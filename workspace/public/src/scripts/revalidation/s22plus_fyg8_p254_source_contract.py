#!/usr/bin/env python3
"""Versioned P2.54 source contract binding the P2.53 proof adapters."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p254_e1_decoder as decoder


CONTRACT_ID = "s22plus-fyg8-p254-e2-proof-bound-v1"
PROFILE = p252.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P254-E2-PROOF-BOUND-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p254_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p254_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P254_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p254_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P254_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P254_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P254_PROOF_BOUND_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P254-PROOF-BOUND-SOURCE-CHECK-V1"
).digest()[:16]

GENERATED_KEYS = p252.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p252.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p254_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p254_e2_runtime.c",
    "plan_header": "s22plus_fyg8_p244_e2_plan.h",
}
COMMON_SOURCE_PATHS = dict(p252.COMMON_SOURCE_PATHS)
COMMON_SOURCE_PATHS["p252_source_contract"] = COMMON_SOURCE_PATHS.pop(
    "source_contract"
)
COMMON_SOURCE_PATHS["p252_decoder_adapter"] = COMMON_SOURCE_PATHS.pop(
    "decoder_adapter"
)
COMMON_SOURCE_PATHS["p245_stock_closure_adapter"] = COMMON_SOURCE_PATHS.pop(
    "stock_closure_adapter"
)
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p254_source_contract.py"
        ),
        "decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p254_e1_decoder.py"
        ),
        "linked_validator_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p253_linked_audit.py"
        ),
        "stock_closure_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p253_e2_stock_closure.py"
        ),
        "linked_adapter_dispatch": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p234_build_repro_check.py"
        ),
        "candidate_repro_enforcement": Path(
            "workspace/public/src/scripts/revalidation/"
            "build_s22plus_fyg8_p234_candidate.py"
        ),
    }
)
SOURCE_KEYS = frozenset((*GENERATED_KEYS, *COMMON_SOURCE_PATHS))
STAGE_SEQUENCE = p252.STAGE_SEQUENCE
REACHABLE_VARIANTS = p252.REACHABLE_VARIANTS


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P254 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=p252.P252.terminal_stage,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p252.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P254


def generate(root: Path | None = None) -> dict[str, bytes]:
    return p252.generate(root)


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.54 source {name}"
        )
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.54 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def implementation_result(root: Path) -> dict[str, Any]:
    first = source_bytes(root)
    second = source_bytes(root)
    if first != second:
        raise SourceContractError("P2.54 source inventory is not deterministic")
    try:
        base = p252.implementation_result(root)
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc
    linked = first["linked_validator_adapter"]
    stock = first["stock_closure_adapter"]
    dispatch = first["linked_adapter_dispatch"]
    enforcement = first["candidate_repro_enforcement"]
    required_linked = (
        b'ADAPTER_ID = "s22plus-fyg8-p253-linked-audit-v2"',
        f'EXPECTED_SOURCE_CONTRACT_ID = "{CONTRACT_ID}"'.encode("ascii"),
        b"guard_dominates_retained_flushes",
        b"guard_dominates_retained_stores",
        b"failure_path_returns_negative",
    )
    required_stock = (
        f'P254_CONTRACT_ID = "{CONTRACT_ID}"'.encode("ascii"),
        b"isolated_legacy = _load_isolated_legacy()",
        b"P2.52 stock closure is not proof-bound",
    )
    if any(token not in linked for token in required_linked):
        raise SourceContractError("P2.54 linked adapter identity drifted")
    if any(token not in stock for token in required_stock):
        raise SourceContractError("P2.54 stock closure identity drifted")
    if (
        CONTRACT_ID.encode("ascii") not in dispatch
        or b"s22plus_fyg8_p253_linked_audit" not in dispatch
        or b"linked validator adapter is required" not in dispatch
    ):
        raise SourceContractError("P2.54 linked adapter dispatch drifted")
    if (
        CONTRACT_ID.encode("ascii") not in enforcement
        or b"P2.54 linked audit adapter mismatch" not in enforcement
    ):
        raise SourceContractError("P2.54 candidate enforcement drifted")
    if (
        b"legacy.EXPECTED_ELF_ENTRYPOINTS =" in stock
        or b"_ENTRYPOINT_LOCK" in stock
    ):
        raise SourceContractError("P2.54 stock closure mutates legacy globals")
    return {
        "schema": "s22plus_fyg8_p254_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": base["generated"],
        "p252_runtime_semantics": base["generated_semantics"],
        "p252_path_map": base["path_map"],
        "p252_descriptor": base["descriptor"],
        "proof_adapters": {
            name: receipt(first[name])
            for name in (
                "linked_validator_adapter",
                "stock_closure_adapter",
            )
        },
        "proof_limit": (
            "classifier detail is a bounded settled-snapshot pointer, "
            "not a permanent root-cause verdict"
        ),
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    try:
        result = dict(p252.validate_reachable_records(run_id))
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc
    result["decoder_policy_id"] = decoder.POLICY_ID
    return result


def linked_table_bytes() -> dict[str, bytes]:
    return p252.linked_table_bytes()


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    try:
        return p252.audit_linked_tables(actual)
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


LINKED_VALIDATOR_SYMBOLS = p252.LINKED_VALIDATOR_SYMBOLS


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        p252.SourceContractError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
