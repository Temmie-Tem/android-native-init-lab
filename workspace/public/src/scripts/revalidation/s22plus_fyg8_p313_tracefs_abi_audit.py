#!/usr/bin/env python3
"""Validate P3.13 descriptors against the linked tracefs ABI authorities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p311_tracefs_abi_audit as inherited


SCHEMA = "s22plus_fyg8_p313_tracefs_abi_cross_authority_v1"
VERDICT = "PASS_P313_TRACEFS_ABI_AND_DESCRIPTOR_HOST_ONLY"
AuditError = inherited.AuditError

_ROLE = (
    b'{"role_qscratch", "p:p282/role_qscratch '
    b'dwc3_msm:dwc3_otg_start_peripheral+0x4cc rc=%x21:s32\\n", '
    b'"common_pid > 0"}'
)
_CYCLE = (
    b'{"cycle_qscratch", "p:p282/cycle_qscratch '
    b'dwc3_msm:dwc3_otg_start_peripheral+0x4cc rc=%x21:s32\\n", '
    b'"common_pid > 0"}'
)
_AUDIT_ALIAS = (
    b'{"p307_qscratch", "p:p282/p307_qscratch '
    b'dwc3_msm:dwc3_otg_start_peripheral+0x4cc rc=%x21:s32\\n", '
    b'"common_pid > 0"}'
)


def audit(root: Path, descriptor: bytes) -> dict[str, Any]:
    if (
        descriptor.count(_ROLE) != 1
        or descriptor.count(_CYCLE) != 1
        or b"p307_qscratch" in descriptor
        or b"%w21" in descriptor
    ):
        raise AuditError("P3.13 QSCRATCH descriptor inventory differs")
    # The inherited cross-authority validator's only historical-name
    # assumption is p307_qscratch.  Rename one actual row solely for that
    # validator; all grammar, symbol, offset, register and type bytes remain
    # unchanged.  The real two-row inventory is asserted above and below.
    adapted = descriptor.replace(_ROLE, _AUDIT_ALIAS, 1)
    result = inherited.audit(root, adapted)
    if (
        result.get("verified") is not True
        or result.get("inherited", {})
        .get("descriptor", {})
        .get("qscratch_trace_fetch_register")
        != "x21"
    ):
        raise AuditError("P3.13 inherited tracefs ABI result differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inherited": result,
        "qscratch": {
            "actual_events": ["role_qscratch", "cycle_qscratch"],
            "module_symbol_offset": "dwc3_msm:dwc3_otg_start_peripheral+0x4cc",
            "register": "x21",
            "fetch_type": "s32",
            "historical_name_adapter_changes_semantics": False,
            "verified": True,
        },
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--descriptor", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.descriptor if args.descriptor.is_absolute() else root / args.descriptor
    try:
        result = audit(root, path.read_bytes())
    except (AuditError, OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
