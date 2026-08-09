#!/usr/bin/env python3
"""Validate P3.11 descriptors against source and linked tracefs ABI."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import Any

import s22plus_fyg8_p309_tracefs_abi_audit as inherited
import s22plus_fyg8_p311_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p311_tracefs_abi_cross_authority_v1"
VERDICT = "PASS_P311_TRACEFS_ABI_AND_EARLY_DESCRIPTOR_HOST_ONLY"
AuditError = inherited.AuditError


def _early_rows(descriptor: bytes) -> list[dict[str, str]]:
    text = descriptor.decode("ascii")
    entries = inherited._initializer_entries(  # noqa: SLF001
        text,
        "static const struct p282_event_descriptor p311_early_events[] =",
    )
    rows: list[dict[str, str]] = []
    for entry in entries:
        strings = re.findall(r'"(?:\\.|[^"\\])*"', entry)
        residue = re.sub(r'"(?:\\.|[^"\\])*"', '""', entry)
        if len(strings) != 3 or not re.fullmatch(
            r"\{\s*\"\"\s*,\s*\"\"\s*,\s*\"\"\s*\}", residue, re.S
        ):
            raise AuditError("P3.11 early descriptor row grammar differs")
        name, definition, filter_value = (
            ast.literal_eval(value) for value in strings
        )
        rows.append({"name": name, "definition": definition, "filter": filter_value})
    return rows


def _validate_early(root: Path, descriptor: bytes, inherited_result: dict[str, Any]) -> dict[str, Any]:
    rows = _early_rows(descriptor)
    expected = [
        {"name": event.name, "definition": event.definition, "filter": event.filter}
        for event in spec.EARLY_EVENTS
    ]
    if rows != expected:
        raise AuditError("P3.11 early descriptor inventory differs from SoT")
    registers = set(
        inherited.extract_source_registers(
            inherited._read_regular(root / inherited.PTRACE, "P3.11 ptrace source")  # noqa: SLF001
        )
    )
    fetch_types = set(
        inherited.extract_source_types(
            inherited._read_regular(root / inherited.TRACE_PROBE, "P3.11 trace type source")  # noqa: SLF001
        )
    )
    names = inherited_result["authority"]["names"]
    for row in rows:
        match = re.fullmatch(
            r"(p|r\d*):([A-Za-z_][A-Za-z0-9_]*)/"
            r"([A-Za-z_][A-Za-z0-9_]*)\s+\S+(?:\s+(.*))?\n",
            row["definition"],
        )
        if match is None:
            raise AuditError(f"P3.11 probe grammar differs: {row['name']}")
        kind, group, event, arguments = match.groups()
        if (
            group != "p282"
            or event != row["name"]
            or len(group) > names["group_max"]
            or len(event) > names["event_max"]
            or row["filter"] != "common_pid >= 0"
        ):
            raise AuditError(f"P3.11 group/event/filter differs: {row['name']}")
        for argument in (arguments or "").split():
            _alias, expression = argument.split("=", 1)
            value, fetch_type = expression.rsplit(":", 1)
            if fetch_type not in fetch_types:
                raise AuditError(f"P3.11 fetch type differs: {row['name']}")
            if value == "$retval":
                if not kind.startswith("r"):
                    raise AuditError(f"P3.11 retval is not on kretprobe: {row['name']}")
            else:
                match_register = re.fullmatch(r"%([A-Za-z_][A-Za-z0-9_]*)", value)
                if match_register is None or match_register.group(1) not in registers:
                    raise AuditError(f"P3.11 register differs: {row['name']}")
                if kind.startswith("r"):
                    raise AuditError(f"P3.11 return probe uses entry register: {row['name']}")
    return {
        "event_count": len(rows),
        "group": "p282",
        "filters": ["common_pid >= 0"],
        "probe_kind_retval_consistent": True,
        "source_and_linked_abi_inherited": True,
        "verified": True,
    }


def audit(root: Path, descriptor: bytes) -> dict[str, Any]:
    base_result = inherited.audit(root, descriptor)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inherited": base_result,
        "early": _validate_early(root, descriptor, base_result),
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
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
