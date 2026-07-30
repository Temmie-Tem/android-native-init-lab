#!/usr/bin/env python3
"""GNU AArch64 linked audit for the exact P2.88 pair contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import s22plus_fyg8_p234_build_repro_check as repro
import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p282_linked_audit as p282_audit
import s22plus_fyg8_p288_source_contract as p288


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = "s22plus-fyg8-p288-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p288.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p288_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p288.LINKED_VALIDATOR_SYMBOLS

AuditError = cfg_audit.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = p282_audit.require_gnu_aarch64_tools


def _validate_tables(logical_tables: dict[str, bytes]) -> None:
    expected = p288.linked_table_bytes()
    if (
        not isinstance(logical_tables, dict)
        or logical_tables != expected
        or any(not isinstance(value, bytes) for value in logical_tables.values())
    ):
        raise AuditError("P2.88 logical linked table set is invalid")


def linked_table_storage_bytes(
    logical_tables: dict[str, bytes],
) -> dict[str, bytes]:
    _validate_tables(logical_tables)
    return dict(logical_tables)


def normalize_linked_table_storage(
    actual_storage: dict[str, bytes],
    logical_tables: dict[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    _validate_tables(logical_tables)
    if actual_storage != logical_tables:
        raise AuditError("P2.88 physical linked table bytes differ")
    return dict(actual_storage), {
        name: {
            "entry_count": len(data),
            "logical_stride": 1,
            "physical_stride": 1,
            "physical_equals_logical": True,
            "zero_tail_padding_verified": True,
            "physical_bytes_verified": True,
        }
        for name, data in sorted(logical_tables.items())
    }


def _require_call(
    calls: dict[str, list[str]], caller: str, callee: str
) -> None:
    row = calls.get(caller)
    if not isinstance(row, list) or row.count(callee) != 1:
        raise AuditError(
            f"P2.88 linked call edge is not exact: {caller}->{callee}"
        )


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    required = (
        "s22_fyg8_e1_expected_item",
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_p288_tuple_allowed",
        "s22_fyg8_e1_write",
    )
    if any(not isinstance(disassembly.get(name), str) for name in required):
        raise AuditError("P2.88 linked validator evidence is incomplete")
    _require_call(
        calls, "s22_fyg8_e1_write", "s22_fyg8_e1_request_allowed"
    )
    _require_call(
        calls,
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_expected_item",
    )
    _require_call(
        calls,
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
    )
    _require_call(
        calls,
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_p288_tuple_allowed",
    )

    expected = p288.linked_table_bytes()
    loads = {
        "sequence": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_request_allowed",
            "s22_fyg8_e2_sequence",
            len(expected["s22_fyg8_e2_sequence"]),
            "byte",
        ),
        "items": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_expected_item",
            "s22_fyg8_e2_items",
            len(expected["s22_fyg8_e2_items"]),
            "byte",
        ),
        "kinds": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_e2_kinds",
            len(expected["s22_fyg8_e2_kinds"]),
            "byte",
        ),
        "exact_rule_bytes": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_p288_detail_rules",
            len(expected["s22_fyg8_p288_detail_rules"]),
            "byte",
        ),
        "exact_rule_halfwords": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_p288_detail_rules",
            len(expected["s22_fyg8_p288_detail_rules"]),
            "halfword",
        ),
    }
    tuple_immediates = p282_audit._immediates(
        disassembly["s22_fyg8_p288_tuple_allowed"]
    )
    tuple_span = p288.spec.TUPLE_LAST - p288.spec.TUPLE_FIRST
    if (
        p288.spec.ordinal_for_position(p288.spec.FINAL_STAGE, 1)
        not in tuple_immediates
        or p288.spec.TUPLE_FIRST not in tuple_immediates
        or not (
            p288.spec.TUPLE_LAST in tuple_immediates
            or tuple_span in tuple_immediates
        )
    ):
        raise AuditError("P2.88 linked tuple range dispatch differs")
    writer_guard = cfg_audit._audit_writer_guard(
        disassembly["s22_fyg8_e1_write"]
    )
    return {
        "audit_adapter": ADAPTER_ID,
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "detail_calls_tuple_validator": True,
        "pair_tables_loaded": loads,
        "exact_rule_count": len(p288.spec.exact_detail_rules()),
        "tuple_range_verified": True,
        "writer_guard": writer_guard,
        "verified": True,
    }


def check(args) -> dict[str, Any]:  # noqa: ANN001
    tool_identity = p282_audit.require_gnu_aarch64_tools(args)
    previous = repro.LINKED_VALIDATOR_ADAPTERS.get(
        EXPECTED_SOURCE_CONTRACT_ID
    )
    if previous not in {None, ADAPTER_MODULE}:
        raise AuditError("P2.88 linked adapter registry conflicts")
    repro.LINKED_VALIDATOR_ADAPTERS[EXPECTED_SOURCE_CONTRACT_ID] = (
        ADAPTER_MODULE
    )
    try:
        result = repro.check(args)
    finally:
        if previous is None:
            repro.LINKED_VALIDATOR_ADAPTERS.pop(
                EXPECTED_SOURCE_CONTRACT_ID, None
            )
        else:
            repro.LINKED_VALIDATOR_ADAPTERS[
                EXPECTED_SOURCE_CONTRACT_ID
            ] = previous
    linked = result.get("linked_audit")
    if (
        not isinstance(linked, dict)
        or linked.get("audit_adapter") != ADAPTER_ID
        or linked.get("source_contract_semantics", {}).get("verified")
        is not True
        or linked.get("source_contract_validator", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.88 linked validator adapter was not applied")
    linked["gnu_aarch64_tools"] = tool_identity
    return result


def main(argv: list[str] | None = None) -> int:
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
