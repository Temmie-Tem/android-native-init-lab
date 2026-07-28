#!/usr/bin/env python3
"""GNU AArch64 linked-audit adapter for the exact P2.84 contract."""

from __future__ import annotations

from contextlib import contextmanager
import sys

from s22plus_fyg8_p282_linked_audit import *  # noqa: F403
import s22plus_fyg8_p282_linked_audit as p282_audit
import s22plus_fyg8_p284_source_contract as p284


ADAPTER_ID = "s22plus-fyg8-p284-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p284.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p284_linked_audit"
LINKED_VALIDATOR_SYMBOLS = tuple(
    dict.fromkeys(
        (
            *p284.LINKED_VALIDATOR_SYMBOLS,
            *p282_audit.P282_VALIDATOR_FUNCTIONS,
        )
    )
)


@contextmanager
def _p284_adapter():
    previous = {
        "ADAPTER_ID": p282_audit.ADAPTER_ID,
        "EXPECTED_SOURCE_CONTRACT_ID": (
            p282_audit.EXPECTED_SOURCE_CONTRACT_ID
        ),
        "ADAPTER_MODULE": p282_audit.ADAPTER_MODULE,
        "p282": p282_audit.p282,
        "_P282_LINKED_TABLE_BYTES": p282_audit._P282_LINKED_TABLE_BYTES,
    }
    p282_audit.ADAPTER_ID = ADAPTER_ID
    p282_audit.EXPECTED_SOURCE_CONTRACT_ID = EXPECTED_SOURCE_CONTRACT_ID
    p282_audit.ADAPTER_MODULE = ADAPTER_MODULE
    p282_audit.p282 = p284
    p282_audit._P282_LINKED_TABLE_BYTES = p284.linked_table_bytes
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(p282_audit, name, value)


def audit_linked_validator(disassembly, calls, symbol_addresses):
    with _p284_adapter():
        return p282_audit.audit_linked_validator(
            disassembly, calls, symbol_addresses
        )


def check(args):
    with _p284_adapter():
        return p282_audit.check(args)


def main(argv: list[str] | None = None) -> int:
    with _p284_adapter():
        return p282_audit.main(argv)


if __name__ == "__main__":
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
