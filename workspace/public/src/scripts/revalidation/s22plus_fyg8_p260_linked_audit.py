#!/usr/bin/env python3
"""CFG-aware linked audit adapter for the P2.60 source contract."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import s22plus_fyg8_p234_build_repro_check as repro
import s22plus_fyg8_p253_linked_audit as p253
import s22plus_fyg8_p260_source_contract as p260


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = "s22plus-fyg8-p260-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p260.CONTRACT_ID

AuditError = p253.AuditError
SourceContractError = AuditError


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    return p253.audit_linked_validator(
        disassembly,
        calls,
        symbol_addresses,
        source_contract_module=p260,
        adapter_id=ADAPTER_ID,
    )


def check(args) -> dict[str, Any]:
    result = repro.check(args)
    linked = result.get("linked_audit")
    if (
        not isinstance(linked, dict)
        or linked.get("audit_adapter") != ADAPTER_ID
        or linked.get("source_contract_validator", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.60 linked validator adapter was not applied")
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
