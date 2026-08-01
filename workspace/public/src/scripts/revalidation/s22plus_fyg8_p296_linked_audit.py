#!/usr/bin/env python3
"""Register-independent linked audit interface for P2.96 telemetry."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p292_linked_audit as inherited
import s22plus_fyg8_p296_source_contract as p296


ADAPTER_ID = "s22plus-fyg8-p296-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p296.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p296_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p296.LINKED_VALIDATOR_SYMBOLS
AuditError = inherited.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = inherited.require_gnu_aarch64_tools


def _validate_tables(logical_tables: dict[str, bytes]) -> None:
    expected = p296.linked_table_bytes()
    if (
        not isinstance(logical_tables, dict)
        or logical_tables != expected
        or any(not isinstance(value, bytes) for value in logical_tables.values())
    ):
        raise AuditError("P2.96 logical linked table set is invalid")


def linked_table_storage_bytes(logical_tables: dict[str, bytes]) -> dict[str, bytes]:
    _validate_tables(logical_tables)
    return dict(logical_tables)


def normalize_linked_table_storage(
    actual_storage: dict[str, bytes],
    logical_tables: dict[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    _validate_tables(logical_tables)
    if actual_storage != logical_tables:
        raise AuditError("P2.96 physical linked table bytes differ")
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


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    result = dict(
        inherited.audit_linked_validator(disassembly, calls, symbol_addresses)
    )
    symbol = "s22_p294_dwc3_state_snapshot"
    if symbol not in disassembly or symbol not in symbol_addresses:
        raise AuditError("P2.96 built-in telemetry symbol is missing")
    if "s22_p294_wrapper_vbus_snapshot" in disassembly:
        raise AuditError("P2.96 external-module telemetry symbol is unexpected")
    result["audit_adapter"] = ADAPTER_ID
    result["telemetry_symbols"] = {
        "symbols": [symbol],
        "external_module_symbols": [],
        "full_lto_retained": True,
        "verified": True,
    }
    result["accept_to_resume_pending_postbuild"] = True
    return result
