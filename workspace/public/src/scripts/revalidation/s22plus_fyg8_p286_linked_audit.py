#!/usr/bin/env python3
"""GNU AArch64 linked-audit adapter for the exact P2.86 contract."""

from __future__ import annotations

from contextlib import contextmanager
import sys

from s22plus_fyg8_p282_linked_audit import *  # noqa: F403
import s22plus_fyg8_p282_linked_audit as p282_audit
import s22plus_fyg8_p286_source_contract as p286


ADAPTER_ID = "s22plus-fyg8-p286-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p286.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p286_linked_audit"
LINKED_VALIDATOR_SYMBOLS = tuple(
    dict.fromkeys(
        (
            *p286.LINKED_VALIDATOR_SYMBOLS,
            *p282_audit.P282_VALIDATOR_FUNCTIONS,
        )
    )
)
P286_TABLE_LAYOUTS = {
    **p282_audit.P282_TABLE_LAYOUTS,
    p282_audit.P282_DETAIL_TABLE: p282_audit.TableLayout(
        len(p286.spec.DIAGNOSTIC_DETAILS)
    ),
}
P282_TABLE_LAYOUTS = P286_TABLE_LAYOUTS


@contextmanager
def _p286_adapter():
    previous = {
        "ADAPTER_ID": p282_audit.ADAPTER_ID,
        "EXPECTED_SOURCE_CONTRACT_ID": (
            p282_audit.EXPECTED_SOURCE_CONTRACT_ID
        ),
        "ADAPTER_MODULE": p282_audit.ADAPTER_MODULE,
        "p282": p282_audit.p282,
        "_P282_LINKED_TABLE_BYTES": p282_audit._P282_LINKED_TABLE_BYTES,
        "P282_TABLE_LAYOUTS": p282_audit.P282_TABLE_LAYOUTS,
    }
    p282_audit.ADAPTER_ID = ADAPTER_ID
    p282_audit.EXPECTED_SOURCE_CONTRACT_ID = EXPECTED_SOURCE_CONTRACT_ID
    p282_audit.ADAPTER_MODULE = ADAPTER_MODULE
    p282_audit.p282 = p286
    p282_audit._P282_LINKED_TABLE_BYTES = p286.linked_table_bytes
    p282_audit.P282_TABLE_LAYOUTS = P286_TABLE_LAYOUTS
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(p282_audit, name, value)


def linked_table_storage_bytes(logical_tables):
    with _p286_adapter():
        return p282_audit.linked_table_storage_bytes(logical_tables)


def normalize_linked_table_storage(actual_storage, logical_tables):
    with _p286_adapter():
        return p282_audit.normalize_linked_table_storage(
            actual_storage, logical_tables
        )


def audit_linked_validator(disassembly, calls, symbol_addresses):
    with _p286_adapter():
        return p282_audit.audit_linked_validator(
            disassembly, calls, symbol_addresses
        )


def check(args):
    with _p286_adapter():
        return p282_audit.check(args)


def main(argv: list[str] | None = None) -> int:
    with _p286_adapter():
        return p282_audit.main(argv)


if __name__ == "__main__":
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
