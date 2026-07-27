#!/usr/bin/env python3
"""CFG-aware linked audit adapter for the P2.80 source contract."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import s22plus_fyg8_p234_build_repro_check as repro
import s22plus_fyg8_p253_linked_audit as p253
import s22plus_fyg8_p280_source_contract as p280


if __name__ == "__main__":
    sys.modules.setdefault(
        "s22plus_fyg8_p280_linked_audit", sys.modules[__name__]
    )


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = "s22plus-fyg8-p280-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p280.CONTRACT_ID

AuditError = p253.AuditError
SourceContractError = AuditError
LINKED_VALIDATOR_SYMBOLS = ("s22_fyg8_p280_detail_allowed",)
P280_DETAIL_TABLE = "s22_fyg8_p280_details"
P280_DETAIL_LOGICAL_STRIDE = 5
P280_DETAIL_STORAGE_STRIDE = 6
_P280_LINKED_TABLE_BYTES = p280.linked_table_bytes
_P280_AUDIT_LINKED_TABLES = p280.audit_linked_tables


def linked_table_storage_bytes(
    logical_tables: dict[str, bytes],
) -> dict[str, bytes]:
    if (
        not isinstance(logical_tables, dict)
        or P280_DETAIL_TABLE not in logical_tables
        or set(logical_tables) != set(_P280_LINKED_TABLE_BYTES())
        or any(not isinstance(data, bytes) for data in logical_tables.values())
    ):
        raise AuditError("P2.80 logical linked table set is invalid")
    logical = logical_tables[P280_DETAIL_TABLE]
    if (
        not logical
        or len(logical) % P280_DETAIL_LOGICAL_STRIDE != 0
        or len(logical) // P280_DETAIL_LOGICAL_STRIDE
        != len(p280.spec.DIAGNOSTIC_DETAILS)
    ):
        raise AuditError("P2.80 logical detail table shape is invalid")
    physical = b"".join(
        logical[offset : offset + P280_DETAIL_LOGICAL_STRIDE] + b"\0"
        for offset in range(0, len(logical), P280_DETAIL_LOGICAL_STRIDE)
    )
    return {**logical_tables, P280_DETAIL_TABLE: physical}


def normalize_linked_table_storage(
    actual_storage: dict[str, bytes],
    logical_tables: dict[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    expected_storage = linked_table_storage_bytes(logical_tables)
    if (
        not isinstance(actual_storage, dict)
        or set(actual_storage) != set(expected_storage)
        or any(not isinstance(data, bytes) for data in actual_storage.values())
    ):
        raise AuditError("P2.80 physical linked table set is invalid")
    actual = actual_storage[P280_DETAIL_TABLE]
    expected = expected_storage[P280_DETAIL_TABLE]
    if len(actual) != len(expected):
        raise AuditError("P2.80 physical detail table size differs")
    for offset in range(
        P280_DETAIL_LOGICAL_STRIDE,
        len(actual),
        P280_DETAIL_STORAGE_STRIDE,
    ):
        if actual[offset] != 0:
            raise AuditError("P2.80 physical detail table padding is nonzero")
    if actual != expected:
        raise AuditError("P2.80 physical detail table bytes differ")
    normalized_detail = b"".join(
        actual[offset : offset + P280_DETAIL_LOGICAL_STRIDE]
        for offset in range(0, len(actual), P280_DETAIL_STORAGE_STRIDE)
    )
    normalized = {**actual_storage, P280_DETAIL_TABLE: normalized_detail}
    if normalized != logical_tables:
        raise AuditError("P2.80 normalized detail table differs")
    return normalized, {
        "table": P280_DETAIL_TABLE,
        "entry_count": len(actual) // P280_DETAIL_STORAGE_STRIDE,
        "logical_stride": P280_DETAIL_LOGICAL_STRIDE,
        "physical_stride": P280_DETAIL_STORAGE_STRIDE,
        "zero_tail_padding_verified": True,
        "physical_bytes_verified": True,
        "verified": True,
    }


def _audit_physical_linked_tables(
    actual_storage: dict[str, bytes],
) -> dict[str, Any]:
    logical_tables = _P280_LINKED_TABLE_BYTES()
    normalized, evidence = normalize_linked_table_storage(
        actual_storage, logical_tables
    )
    physical_table_builder = p280.linked_table_bytes
    p280.linked_table_bytes = _P280_LINKED_TABLE_BYTES
    try:
        result = _P280_AUDIT_LINKED_TABLES(normalized)
    finally:
        p280.linked_table_bytes = physical_table_builder
    result["physical_storage_layout"] = evidence
    return result


def _audit_linked_with_physical_tables(
    original_audit,
    *args,
    **kwargs,
) -> dict[str, Any]:
    original_table_builder = p280.linked_table_bytes
    original_table_auditor = p280.audit_linked_tables
    if (
        original_table_builder is not _P280_LINKED_TABLE_BYTES
        or original_table_auditor is not _P280_AUDIT_LINKED_TABLES
    ):
        raise AuditError("P2.80 linked source contract was already adapted")
    p280.linked_table_bytes = lambda: linked_table_storage_bytes(
        _P280_LINKED_TABLE_BYTES()
    )
    p280.audit_linked_tables = _audit_physical_linked_tables
    try:
        return original_audit(*args, **kwargs)
    finally:
        p280.linked_table_bytes = original_table_builder
        p280.audit_linked_tables = original_table_auditor


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    result = p253.audit_linked_validator(
        disassembly,
        calls,
        symbol_addresses,
        source_contract_module=p280,
        adapter_id=ADAPTER_ID,
    )
    detail_calls = calls.get("s22_fyg8_e1_detail_allowed")
    detail_disassembly = disassembly.get("s22_fyg8_p280_detail_allowed")
    table_address = symbol_addresses.get("s22_fyg8_p280_details")
    expected_tables = _P280_LINKED_TABLE_BYTES()
    expected_table = expected_tables.get(P280_DETAIL_TABLE)
    if (
        not isinstance(detail_calls, list)
        or "s22_fyg8_p280_detail_allowed" not in detail_calls
        or not isinstance(detail_disassembly, str)
        or not isinstance(table_address, int)
        or not isinstance(expected_table, bytes)
    ):
        raise AuditError("P2.80 linked detail evidence is incomplete")
    table_loads = p253._table_loads(
        detail_disassembly,
        table_address,
        len(linked_table_storage_bytes(expected_tables)[P280_DETAIL_TABLE]),
        "halfword",
    )
    if not table_loads:
        raise AuditError("P2.80 linked validator does not load its detail table")
    return {
        **result,
        "p280_detail_validator_called": True,
        "p280_detail_validator_loads_exact_table": True,
        "p280_detail_table_loads": table_loads,
        "verified": True,
    }


def check(args) -> dict[str, Any]:
    original_audit = repro.audit_linked
    if getattr(original_audit, "__module__", None) != repro.__name__:
        raise AuditError("P2.80 linked audit entrypoint was already adapted")
    repro.audit_linked = lambda *call_args, **call_kwargs: (
        _audit_linked_with_physical_tables(
            original_audit, *call_args, **call_kwargs
        )
    )
    try:
        result = repro.check(args)
    finally:
        repro.audit_linked = original_audit
    linked = result.get("linked_audit")
    if (
        not isinstance(linked, dict)
        or linked.get("audit_adapter") != ADAPTER_ID
        or linked.get("source_contract_validator", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.80 linked validator adapter was not applied")
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
    raise SystemExit(main())
