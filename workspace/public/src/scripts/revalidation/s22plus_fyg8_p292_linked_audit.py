#!/usr/bin/env python3
"""Register-independent linked audit interface for the P2.92 contract."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p290_linked_audit as inherited
import s22plus_fyg8_p292_source_contract as p292


ADAPTER_ID = "s22plus-fyg8-p292-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p292.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p292_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p292.LINKED_VALIDATOR_SYMBOLS
AuditError = inherited.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = inherited.require_gnu_aarch64_tools


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


def linked_table_storage_bytes(
    logical_tables: dict[str, bytes],
) -> dict[str, bytes]:
    return inherited.linked_table_storage_bytes(logical_tables)


def normalize_linked_table_storage(
    actual_storage: dict[str, bytes],
    logical_tables: dict[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    return inherited.normalize_linked_table_storage(
        actual_storage, logical_tables
    )


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
            inherited.audit_linked_validator(
                disassembly, calls, symbol_addresses
            )
        )
    finally:
        cfg_audit._successors = original_successors  # noqa: SLF001
    result["writer_guard"]["noreturn_call_fallthroughs_pruned"] = len(
        noreturn_calls
    )
    result["writer_guard"]["noreturn_call_target"] = "__stack_chk_fail"
    result.update(
        {
            "audit_adapter": ADAPTER_ID,
            "accept_to_resume_pending_postbuild": True,
        }
    )
    return result
