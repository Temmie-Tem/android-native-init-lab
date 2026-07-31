#!/usr/bin/env python3
"""Register-independent linked audit interface for P2.94 telemetry."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p292_linked_audit as inherited
import s22plus_fyg8_p294_source_contract as p294


ADAPTER_ID = "s22plus-fyg8-p294-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p294.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p294_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p294.LINKED_VALIDATOR_SYMBOLS
AuditError = inherited.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = inherited.require_gnu_aarch64_tools


def linked_table_storage_bytes(logical_tables: dict[str, bytes]) -> dict[str, bytes]:
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
    result = dict(
        inherited.audit_linked_validator(
            disassembly, calls, symbol_addresses
        )
    )
    missing = sorted(
        symbol
        for symbol in (
            "s22_p294_dwc3_state_snapshot",
            "s22_p294_wrapper_vbus_snapshot",
        )
        if symbol not in disassembly or symbol not in symbol_addresses
    )
    if missing:
        raise AuditError(f"P2.94 linked telemetry symbols are missing: {missing}")
    result["audit_adapter"] = ADAPTER_ID
    result["telemetry_symbols"] = {
        "symbols": [
            "s22_p294_dwc3_state_snapshot",
            "s22_p294_wrapper_vbus_snapshot",
        ],
        "full_lto_retained": True,
        "verified": True,
    }
    result["accept_to_resume_pending_postbuild"] = True
    return result
