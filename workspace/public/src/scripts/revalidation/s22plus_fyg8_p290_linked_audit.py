#!/usr/bin/env python3
"""Register-independent linked audit interface for the P2.90 contract."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p288_linked_audit as inherited
import s22plus_fyg8_p290_source_contract as p290


ADAPTER_ID = "s22plus-fyg8-p290-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p290.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p290_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p290.LINKED_VALIDATOR_SYMBOLS
AuditError = inherited.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = inherited.require_gnu_aarch64_tools


def _validate_tables(logical_tables: dict[str, bytes]) -> None:
    expected = p290.linked_table_bytes()
    if (
        not isinstance(logical_tables, dict)
        or logical_tables != expected
        or any(
            not isinstance(value, bytes)
            for value in logical_tables.values()
        )
    ):
        raise AuditError("P2.90 logical linked table set is invalid")


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
        raise AuditError("P2.90 physical linked table bytes differ")
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
            f"P2.90 linked call edge is not exact: {caller}->{callee}"
        )


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    _symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    """Prove call topology here; semantics are closed by host exhaustive."""

    required = (
        "s22_fyg8_e1_expected_item",
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_p290_tuple_allowed",
        "s22_fyg8_e1_write",
    )
    if any(
        not isinstance(disassembly.get(name), str) for name in required
    ):
        raise AuditError("P2.90 linked validator evidence is incomplete")
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
        "s22_fyg8_p290_tuple_allowed",
    )
    return {
        "audit_adapter": ADAPTER_ID,
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "detail_calls_tuple_validator": True,
        "writer_guard": cfg_audit._audit_writer_guard(  # noqa: SLF001
            disassembly["s22_fyg8_e1_write"]
        ),
        "register_specific_validator_patterns_used": False,
        "validator_semantics_pending_host_exhaustive": True,
        "verified": False,
    }
