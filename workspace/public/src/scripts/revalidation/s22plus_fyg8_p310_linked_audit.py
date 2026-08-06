#!/usr/bin/env python3
"""P3.10 linked audit adapter for unchanged DWC3 callsites."""

from __future__ import annotations

import s22plus_fyg8_p300_linked_audit as parent
import s22plus_fyg8_p310_source_contract as p310


ADAPTER_ID = "s22plus-fyg8-p310-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p310.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p310_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p310.LINKED_VALIDATOR_SYMBOLS
CALLSITE_AUDIT_SYMBOLS = parent.CALLSITE_AUDIT_SYMBOLS
AuditError = parent.AuditError
require_gnu_aarch64_tools = parent.require_gnu_aarch64_tools
linked_table_storage_bytes = parent.linked_table_storage_bytes
normalize_linked_table_storage = parent.normalize_linked_table_storage
audit_gadget_start_callsites = parent.audit_gadget_start_callsites
audit_gadget_start_callsite_pair = parent.audit_gadget_start_callsite_pair


def audit_linked_validator(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    result = dict(parent.audit_linked_validator(*args, **kwargs))
    result["audit_adapter"] = ADAPTER_ID
    return result
