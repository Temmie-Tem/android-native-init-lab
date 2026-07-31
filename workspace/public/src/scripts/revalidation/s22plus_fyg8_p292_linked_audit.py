#!/usr/bin/env python3
"""Register-independent linked audit interface for the P2.92 contract."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p290_linked_audit as inherited
import s22plus_fyg8_p292_source_contract as p292


ADAPTER_ID = "s22plus-fyg8-p292-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p292.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p292_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p292.LINKED_VALIDATOR_SYMBOLS
AuditError = inherited.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = inherited.require_gnu_aarch64_tools


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
    result = dict(
        inherited.audit_linked_validator(
            disassembly, calls, symbol_addresses
        )
    )
    result["audit_adapter"] = ADAPTER_ID
    result["accept_to_resume_pending_postbuild"] = True
    return result
