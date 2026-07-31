#!/usr/bin/env python3
"""P2.92 post-build proof with accept-to-resume closure."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p290_postbuild_linked_audit as inherited
import s22plus_fyg8_p292_accept_to_resume as closure
import s22plus_fyg8_p292_build_repro_check as repro
import s22plus_fyg8_p292_linked_audit as linked
import s22plus_fyg8_p292_source_contract as p292


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = linked.ADAPTER_ID
IMPLEMENTATION_ID = (
    "s22plus-fyg8-p292-linked-data-and-accept-to-resume-v1"
)
EXPECTED_SOURCE_CONTRACT_ID = p292.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p292_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = linked.LINKED_VALIDATOR_SYMBOLS
LINKED_DATA_SYMBOLS = inherited.LINKED_DATA_SYMBOLS
HOST_GENERATIONS = len(p292.spec.POSITIONS) + 1
PAIR_DOMAIN_SIZE = inherited.PAIR_DOMAIN_SIZE
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p292.spec.POSITIONS)
HOST_OUTPUT = (
    f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n"
).encode("ascii")
AuditError = linked.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = linked.require_gnu_aarch64_tools
linked_table_storage_bytes = linked.linked_table_storage_bytes
normalize_linked_table_storage = linked.normalize_linked_table_storage


def _prune_noreturn_successors(
    instructions,  # noqa: ANN001
    successors: dict[int, tuple[int, ...]],
) -> tuple[dict[int, tuple[int, ...]], tuple[int, ...]]:
    result = dict(successors)
    calls = tuple(
        instruction.address
        for instruction in instructions
        if cfg_audit._call_target(instruction) == "__stack_chk_fail"  # noqa: SLF001
    )
    if len(calls) > 1:
        raise AuditError(
            "P2.92 linked writer has multiple stack-check failure calls"
        )
    for address in calls:
        result[address] = ()
    return result, calls


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    writer = disassembly.get("s22_fyg8_e1_write")
    if not isinstance(writer, str):
        raise AuditError("P2.92 linked writer evidence is missing")
    instructions = cfg_audit._instructions(writer)  # noqa: SLF001
    _successors, noreturn_calls = _prune_noreturn_successors(
        instructions,
        cfg_audit._successors(instructions),  # noqa: SLF001
    )
    if len(noreturn_calls) != 1:
        raise AuditError(
            "P2.92 linked writer stack-check failure call is missing"
        )

    original_successors = cfg_audit._successors  # noqa: SLF001

    def corrected_successors(candidate_instructions):  # noqa: ANN001, ANN202
        return _prune_noreturn_successors(
            candidate_instructions,
            original_successors(candidate_instructions),
        )[0]

    cfg_audit._successors = corrected_successors  # noqa: SLF001
    try:
        result = dict(
            linked.audit_linked_validator(
                disassembly, calls, symbol_addresses
            )
        )
    finally:
        cfg_audit._successors = original_successors  # noqa: SLF001
    result["writer_guard"]["noreturn_call_fallthroughs_pruned"] = len(
        noreturn_calls
    )
    result["writer_guard"]["noreturn_call_target"] = "__stack_chk_fail"
    return result


def _configure() -> None:
    repro._configure()
    inherited.repro = repro
    inherited.linked = linked
    inherited.p290 = p292
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.ADAPTER_ID = ADAPTER_ID
    inherited.IMPLEMENTATION_ID = IMPLEMENTATION_ID
    inherited.EXPECTED_SOURCE_CONTRACT_ID = EXPECTED_SOURCE_CONTRACT_ID
    inherited.ADAPTER_MODULE = ADAPTER_MODULE
    inherited.LINKED_VALIDATOR_SYMBOLS = LINKED_VALIDATOR_SYMBOLS
    inherited.LINKED_DATA_SYMBOLS = LINKED_DATA_SYMBOLS
    inherited.HOST_GENERATIONS = HOST_GENERATIONS
    inherited.HOST_CASE_COUNT = HOST_CASE_COUNT
    inherited.HOST_ACCEPT_COUNT = HOST_ACCEPT_COUNT
    inherited.HOST_OUTPUT = HOST_OUTPUT


def check(args):  # noqa: ANN001, ANN201
    _configure()
    result = inherited.check(args)
    root = repro.candidate_contract.intent.repo_root()
    proof = closure.run_closure(root)
    if (
        proof.get("verdict") != closure.VERDICT
        or proof.get("accept_to_resume_closure", {}).get(
            "closure_case_count"
        )
        != 171
        or proof.get("accept_to_resume_sequence_walk", {}).get(
            "snapshot_count"
        )
        != 214
        or proof.get("checkpoint_errno_observability", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.92 accept-to-resume postbuild closure differs")
    linked_result = result["linked_audit"]
    linked_result["postbuild_audit"]["accept_to_resume"] = {
        "closure_case_count": 171,
        "sequence_walk_snapshots": 214,
        "exact_old_generation_88_resumed": True,
        "errno_observable": True,
        "verified": True,
    }
    linked_result["source_contract_validator"][
        "accept_to_resume_pending_postbuild"
    ] = False
    return result


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        result = check(repro.parse_args(argv))
    except (
        AuditError,
        repro.CheckError,
        repro.candidate_contract.ContractError,
        repro.candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
