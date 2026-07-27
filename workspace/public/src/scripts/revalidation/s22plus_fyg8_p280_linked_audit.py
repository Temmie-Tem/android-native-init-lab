#!/usr/bin/env python3
"""CFG-aware linked audit adapter for the P2.80 source contract."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import s22plus_fyg8_p234_build_repro_check as repro
import s22plus_fyg8_p253_linked_audit as p253
import s22plus_fyg8_p280_source_contract as p280


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = "s22plus-fyg8-p280-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p280.CONTRACT_ID

AuditError = p253.AuditError
SourceContractError = AuditError
LINKED_VALIDATOR_SYMBOLS = ("s22_fyg8_p280_detail_allowed",)


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
    expected_table = p280.linked_table_bytes().get(
        "s22_fyg8_p280_details"
    )
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
        len(expected_table),
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
    result = repro.check(args)
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
