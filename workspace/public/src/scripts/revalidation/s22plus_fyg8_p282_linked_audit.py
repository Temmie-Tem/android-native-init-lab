#!/usr/bin/env python3
"""GNU AArch64 linked-audit adapter for the exact P2.82 contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import s22plus_fyg8_p234_build_repro_check as repro
import s22plus_fyg8_p253_linked_audit as p253
import s22plus_fyg8_p282_source_contract as p282


if __name__ == "__main__":
    sys.modules.setdefault(
        "s22plus_fyg8_p282_linked_audit", sys.modules[__name__]
    )


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = "s22plus-fyg8-p282-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p282.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p282_linked_audit"

AuditError = p253.AuditError
SourceContractError = AuditError

P282_INHERITED_DETAIL_TABLE = "s22_fyg8_p282_inherited_role_details"
P282_DETAIL_TABLE = "s22_fyg8_p282_details"
P282_DETAIL_LOGICAL_STRIDE = 4
P282_DETAIL_STORAGE_STRIDE = 4

P282_VALIDATOR_FUNCTIONS = (
    "s22_fyg8_p282_detail_allowed",
    "s22_fyg8_p282_tuple_allowed",
)
LINKED_VALIDATOR_SYMBOLS = tuple(
    dict.fromkeys((*p282.LINKED_VALIDATOR_SYMBOLS, *P282_VALIDATOR_FUNCTIONS))
)

_P282_LINKED_TABLE_BYTES = p282.linked_table_bytes


@dataclass(frozen=True)
class TableLayout:
    entry_count: int
    logical_stride: int = P282_DETAIL_LOGICAL_STRIDE
    physical_stride: int = P282_DETAIL_STORAGE_STRIDE

    @property
    def logical_size(self) -> int:
        return self.entry_count * self.logical_stride

    @property
    def physical_size(self) -> int:
        return self.entry_count * self.physical_stride


P282_TABLE_LAYOUTS = {
    P282_INHERITED_DETAIL_TABLE: TableLayout(
        len(p282.INHERITED_ROLE_DETAILS)
    ),
    P282_DETAIL_TABLE: TableLayout(len(p282.spec.DIAGNOSTIC_DETAILS)),
}


def _validate_logical_tables(logical_tables: dict[str, bytes]) -> None:
    expected = _P282_LINKED_TABLE_BYTES()
    if (
        not isinstance(logical_tables, dict)
        or set(logical_tables) != set(expected)
        or any(not isinstance(data, bytes) for data in logical_tables.values())
    ):
        raise AuditError("P2.82 logical linked table set is invalid")
    for name, layout in P282_TABLE_LAYOUTS.items():
        if len(logical_tables[name]) != layout.logical_size:
            raise AuditError(f"P2.82 logical table shape is invalid: {name}")


def _physical_table_bytes(data: bytes, layout: TableLayout) -> bytes:
    if layout.physical_stride < layout.logical_stride:
        raise AuditError("P2.82 physical table stride is smaller than logical")
    if len(data) != layout.logical_size:
        raise AuditError("P2.82 logical table size differs from its layout")
    padding = b"\0" * (layout.physical_stride - layout.logical_stride)
    return b"".join(
        data[offset : offset + layout.logical_stride] + padding
        for offset in range(0, len(data), layout.logical_stride)
    )


def linked_table_storage_bytes(
    logical_tables: dict[str, bytes],
) -> dict[str, bytes]:
    _validate_logical_tables(logical_tables)
    result = dict(logical_tables)
    for name, layout in P282_TABLE_LAYOUTS.items():
        result[name] = _physical_table_bytes(logical_tables[name], layout)
    return result


def normalize_linked_table_storage(
    actual_storage: dict[str, bytes],
    logical_tables: dict[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    _validate_logical_tables(logical_tables)
    expected_storage = linked_table_storage_bytes(logical_tables)
    if (
        not isinstance(actual_storage, dict)
        or set(actual_storage) != set(expected_storage)
        or any(not isinstance(data, bytes) for data in actual_storage.values())
    ):
        raise AuditError("P2.82 physical linked table set is invalid")

    normalized = dict(actual_storage)
    layouts: dict[str, dict[str, Any]] = {}
    for name, layout in P282_TABLE_LAYOUTS.items():
        actual = actual_storage[name]
        expected = expected_storage[name]
        if len(actual) != layout.physical_size:
            raise AuditError(f"P2.82 physical table size differs: {name}")
        logical_parts: list[bytes] = []
        for offset in range(0, len(actual), layout.physical_stride):
            entry = actual[offset : offset + layout.physical_stride]
            tail = entry[layout.logical_stride :]
            if any(tail):
                raise AuditError(
                    f"P2.82 physical table padding is nonzero: {name}"
                )
            logical_parts.append(entry[: layout.logical_stride])
        if actual != expected:
            raise AuditError(f"P2.82 physical table bytes differ: {name}")
        normalized[name] = b"".join(logical_parts)
        layouts[name] = {
            "entry_count": layout.entry_count,
            "logical_stride": layout.logical_stride,
            "physical_stride": layout.physical_stride,
            "physical_equals_logical": (
                layout.logical_stride == layout.physical_stride
            ),
            "zero_tail_padding_verified": True,
            "physical_bytes_verified": True,
        }

    for name in set(expected_storage) - set(P282_TABLE_LAYOUTS):
        if actual_storage[name] != logical_tables[name]:
            raise AuditError(f"P2.82 linked table bytes differ: {name}")
    if normalized != logical_tables:
        raise AuditError("P2.82 normalized linked tables differ")
    return normalized, {
        "tables": layouts,
        "p280_style_tail_padding_absent": True,
        "physical_bytes_verified": True,
        "verified": True,
    }


def _require_load(
    disassembly: dict[str, str],
    symbol_addresses: dict[str, int],
    function: str,
    table: str,
    size: int,
    width: str,
) -> list[dict[str, Any]]:
    text = disassembly.get(function)
    address = symbol_addresses.get(table)
    if not isinstance(text, str) or not isinstance(address, int):
        raise AuditError(
            f"P2.82 linked table evidence is incomplete: {function}/{table}"
        )
    loads = p253._table_loads(text, address, size, width)
    if not loads:
        raise AuditError(
            f"P2.82 linked validator does not load exact table: {table}"
        )
    return loads


def _immediates(disassembly: str) -> frozenset[int]:
    values: set[int] = set()
    for token in re.findall(
        r"#\s*(-?(?:0x[0-9a-fA-F]+|\d+))\b", disassembly
    ):
        try:
            values.add(int(token, 0))
        except ValueError:
            pass
    return frozenset(values)


def _audit_tuple_dispatch(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
) -> dict[str, Any]:
    dispatcher_calls = calls.get("s22_fyg8_e1_detail_allowed")
    tuple_text = disassembly.get("s22_fyg8_p282_tuple_allowed")
    if (
        not isinstance(dispatcher_calls, list)
        or dispatcher_calls.count("s22_fyg8_p282_detail_allowed") != 1
        or dispatcher_calls.count("s22_fyg8_p282_tuple_allowed") != 1
        or not isinstance(tuple_text, str)
    ):
        raise AuditError("P2.82 linked exact-detail dispatch is incomplete")
    immediates = _immediates(tuple_text)
    tuple_span = p282.spec.TUPLE_LAST - p282.spec.TUPLE_FIRST
    if (
        p282.spec.FINAL_STAGE not in immediates
        or p282.spec.TUPLE_FIRST not in immediates
        or not (
            p282.spec.TUPLE_LAST in immediates or tuple_span in immediates
        )
    ):
        raise AuditError("P2.82 linked tuple range dispatch differs")
    return {
        "detail_helper_call_count": 1,
        "tuple_helper_call_count": 1,
        "final_stage": f"0x{p282.spec.FINAL_STAGE:02x}",
        "tuple_first": f"0x{p282.spec.TUPLE_FIRST:03x}",
        "tuple_last": f"0x{p282.spec.TUPLE_LAST:03x}",
        "tuple_count": p282.spec.TUPLE_COUNT,
        "range_dispatch_verified": True,
    }


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    result = p253.audit_linked_validator(
        disassembly,
        calls,
        symbol_addresses,
        source_contract_module=p282,
        adapter_id=ADAPTER_ID,
    )
    logical = _P282_LINKED_TABLE_BYTES()
    storage = linked_table_storage_bytes(logical)

    extra_loads = {
        "sequence": _require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_e2_sequence",
            len(storage["s22_fyg8_e2_sequence"]),
            "byte",
        ),
        "kinds": _require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_e2_kinds",
            len(storage["s22_fyg8_e2_kinds"]),
            "byte",
        ),
        "inherited_role_details": _require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_p282_detail_allowed",
            P282_INHERITED_DETAIL_TABLE,
            len(storage[P282_INHERITED_DETAIL_TABLE]),
            "halfword",
        ),
        "p282_details": _require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_p282_detail_allowed",
            P282_DETAIL_TABLE,
            len(storage[P282_DETAIL_TABLE]),
            "halfword",
        ),
    }
    tuple_dispatch = _audit_tuple_dispatch(disassembly, calls)
    return {
        **result,
        "p282_generated_sequence_loaded": True,
        "p282_generated_items_loaded": True,
        "p282_generated_kinds_loaded": True,
        "p282_inherited_role_details_loaded": True,
        "p282_exact_c_details_loaded": True,
        "p282_exact_c_detail_count": len(p282.spec.DIAGNOSTIC_DETAILS),
        "p282_inherited_role_detail_count": len(
            p282.INHERITED_ROLE_DETAILS
        ),
        "p282_generated_step_count": len(p282.spec.STEPS),
        "p282_extra_table_loads": extra_loads,
        "p282_tuple_dispatch": tuple_dispatch,
        "verified": True,
    }


def _tool_version(path: Path, label: str) -> str:
    if path.name.startswith("llvm-"):
        raise AuditError(f"LLVM {label} is forbidden for P2.82 linked audit")
    completed = subprocess.run(
        [str(path), "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=10,
    )
    output = completed.stdout
    first_line = output.splitlines()[0] if output.splitlines() else ""
    if (
        completed.returncode != 0
        or "llvm" in output.lower()
        or "gnu" not in output.lower()
        or label not in first_line.lower()
        or not path.name.startswith("aarch64-linux-gnu-")
    ):
        raise AuditError(
            f"P2.82 linked audit requires GNU AArch64 {label}"
        )
    return first_line


def require_gnu_aarch64_tools(args) -> dict[str, str]:
    nm = getattr(args, "nm", None)
    objdump = getattr(args, "objdump", None)
    if not isinstance(nm, Path) or not isinstance(objdump, Path):
        raise AuditError("P2.82 GNU linked-audit tools are missing")
    return {
        "nm": _tool_version(nm, "nm"),
        "objdump": _tool_version(objdump, "objdump"),
    }


def check(args) -> dict[str, Any]:
    tool_identity = require_gnu_aarch64_tools(args)
    previous_adapter = repro.LINKED_VALIDATOR_ADAPTERS.get(
        EXPECTED_SOURCE_CONTRACT_ID
    )
    if previous_adapter not in {None, ADAPTER_MODULE}:
        raise AuditError("P2.82 linked adapter registry conflicts")
    repro.LINKED_VALIDATOR_ADAPTERS[EXPECTED_SOURCE_CONTRACT_ID] = (
        ADAPTER_MODULE
    )
    try:
        result = repro.check(args)
    finally:
        if previous_adapter is None:
            repro.LINKED_VALIDATOR_ADAPTERS.pop(
                EXPECTED_SOURCE_CONTRACT_ID, None
            )
        else:
            repro.LINKED_VALIDATOR_ADAPTERS[
                EXPECTED_SOURCE_CONTRACT_ID
            ] = previous_adapter
    linked = result.get("linked_audit")
    if (
        not isinstance(linked, dict)
        or linked.get("audit_adapter") != ADAPTER_ID
        or linked.get("source_contract_semantics", {}).get("verified")
        is not True
        or linked.get("source_contract_validator", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.82 linked validator adapter was not applied")
    result["linked_audit"]["gnu_aarch64_tools"] = tool_identity
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
