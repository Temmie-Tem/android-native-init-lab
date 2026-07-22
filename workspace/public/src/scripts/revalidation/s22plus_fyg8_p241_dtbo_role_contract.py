#!/usr/bin/env python3
"""Validate the pinned FYG8 DTBO USB-role contract without expanded DTS files."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p241_dtbo_role_contract_v1"
VERDICT = "PASS_P241_FYG8_DTBO_ROLE_CONTRACT_HOST_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
DEFAULT_DTBO = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/dtbo.img"
)
EXPECTED_DTBO_SHA256 = (
    "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
)
EXPECTED_ENTRY_COUNT = 11
EXPECTED_ENTRY_MANIFEST_SHA256 = (
    "16c732ccedd27bc31fdcce510003c26aefd89a8a79dbe61a9828373acb5085c2"
)

DT_TABLE_MAGIC = 0xD7B7AB1E
FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class FdtNode:
    path: str
    properties: dict[str, bytes]


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise ContractError("repository root not found")


def stable_read(path: Path, limit: int = 16 * 1024 * 1024) -> bytes:
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise ContractError(f"DTBO is unavailable, indirect, or outside bound: {path}")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(data) != before.st_size:
        raise ContractError("DTBO changed while reading")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_DTBO_SHA256:
        raise ContractError(f"DTBO SHA256 mismatch: {digest}")
    return data


def align4(value: int) -> int:
    return (value + 3) & ~3


def cstring(data: bytes, start: int, end: int, label: str) -> tuple[str, int]:
    stop = data.find(b"\0", start, end)
    if stop < 0:
        raise ContractError(f"unterminated {label}")
    try:
        text = data[start:stop].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError(f"non-ASCII {label}") from exc
    return text, align4(stop + 1)


def parse_fdt(blob: bytes) -> tuple[FdtNode, ...]:
    if len(blob) < 40:
        raise ContractError("FDT header truncated")
    header = struct.unpack_from(">10I", blob, 0)
    (
        magic,
        total_size,
        struct_offset,
        strings_offset,
        reserve_offset,
        version,
        last_compatible,
        _boot_cpu,
        strings_size,
        struct_size,
    ) = header
    if (
        magic != FDT_MAGIC
        or total_size != len(blob)
        or version < 17
        or last_compatible > version
        or reserve_offset < 40
        or struct_offset + struct_size > total_size
        or strings_offset + strings_size > total_size
    ):
        raise ContractError("FDT header contract mismatch")
    strings = blob[strings_offset : strings_offset + strings_size]
    cursor = struct_offset
    struct_end = struct_offset + struct_size
    stack: list[str] = []
    nodes: list[FdtNode] = []
    current: dict[str, bytes] | None = None
    saw_end = False
    while cursor + 4 <= struct_end:
        token = struct.unpack_from(">I", blob, cursor)[0]
        cursor += 4
        if token == FDT_BEGIN_NODE:
            name, cursor = cstring(blob, cursor, struct_end, "FDT node name")
            stack.append(name)
            path = "/" + "/".join(value for value in stack if value)
            current = {}
            nodes.append(FdtNode(path or "/", current))
        elif token == FDT_END_NODE:
            if not stack:
                raise ContractError("FDT node stack underflow")
            stack.pop()
            current = nodes[-1].properties if nodes and stack else None
            if stack:
                parent_path = "/" + "/".join(value for value in stack if value)
                parent = next(
                    (node for node in reversed(nodes) if node.path == (parent_path or "/")),
                    None,
                )
                current = parent.properties if parent is not None else None
        elif token == FDT_PROP:
            if current is None or cursor + 8 > struct_end:
                raise ContractError("FDT property outside a node")
            length, name_offset = struct.unpack_from(">II", blob, cursor)
            cursor += 8
            if name_offset >= len(strings) or cursor + length > struct_end:
                raise ContractError("FDT property bounds mismatch")
            name, _ = cstring(strings, name_offset, len(strings), "FDT property name")
            if name in current:
                raise ContractError(f"duplicate FDT property: {name}")
            current[name] = blob[cursor : cursor + length]
            cursor = align4(cursor + length)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            saw_end = True
            break
        else:
            raise ContractError(f"unknown FDT structure token: {token}")
    if not saw_end or stack:
        raise ContractError("FDT structure did not terminate cleanly")
    return tuple(nodes)


def parse_dtbo(data: bytes) -> tuple[dict[str, Any], ...]:
    if len(data) < 32:
        raise ContractError("DTBO table header truncated")
    (
        magic,
        total_size,
        header_size,
        entry_size,
        entry_count,
        entries_offset,
        page_size,
        version,
    ) = struct.unpack_from(">8I", data, 0)
    if (
        magic != DT_TABLE_MAGIC
        or total_size > len(data)
        or header_size != 32
        or entry_size != 32
        or entry_count != EXPECTED_ENTRY_COUNT
        or entries_offset != header_size
        or page_size != 4096
        or version != 0
        or entries_offset + entry_count * entry_size > len(data)
    ):
        raise ContractError("DTBO table header contract mismatch")
    rows: list[dict[str, Any]] = []
    intervals: list[tuple[int, int]] = []
    for index in range(entry_count):
        entry = struct.unpack_from(">8I", data, entries_offset + index * entry_size)
        dt_size, dt_offset, entry_id, revision, *custom = entry
        if dt_size < 40 or dt_offset < entries_offset + entry_count * entry_size:
            raise ContractError(f"DTBO entry {index} has invalid bounds")
        end = dt_offset + dt_size
        if end > total_size or any(dt_offset < prior_end and start < end for start, prior_end in intervals):
            raise ContractError(f"DTBO entry {index} overlaps or escapes the image")
        intervals.append((dt_offset, end))
        blob = data[dt_offset:end]
        nodes = parse_fdt(blob)
        rows.append(
            {
                "index": index,
                "offset": dt_offset,
                "size": dt_size,
                "id": entry_id,
                "revision": revision,
                "custom": custom,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "nodes": nodes,
            }
        )
    return tuple(rows)


def string_list(value: bytes) -> tuple[str, ...]:
    if not value or value[-1] != 0:
        raise ContractError("FDT string-list property is not NUL terminated")
    try:
        return tuple(item.decode("ascii") for item in value[:-1].split(b"\0"))
    except UnicodeDecodeError as exc:
        raise ContractError("FDT string-list property is not ASCII") from exc


def inspect_entry(row: dict[str, Any]) -> dict[str, Any]:
    nodes: tuple[FdtNode, ...] = row["nodes"]
    by_path = {node.path: node for node in nodes}
    parent = next(
        (
            node
            for path, node in by_path.items()
            if path.endswith("/fragment@23/__overlay__")
        ),
        None,
    )
    child = next(
        (
            node
            for path, node in by_path.items()
            if path.endswith("/fragment@23/__overlay__/dwc3@a600000")
        ),
        None,
    )
    compatible = [
        value
        for node in nodes
        if "compatible" in node.properties
        for value in string_list(node.properties["compatible"])
    ]
    fixups = next((node for node in nodes if node.path == "/__fixups__"), None)
    ucsi = () if fixups is None or "ucsi" not in fixups.properties else string_list(
        fixups.properties["ucsi"]
    )
    extcon_count = sum("extcon" in node.properties for node in nodes)
    role_switch_default_mode_count = sum(
        "role-switch-default-mode" in node.properties for node in nodes
    )
    checks = {
        "parent_role_switch": parent is not None
        and parent.properties.get("usb-role-switch") == b"",
        "child_role_switch": child is not None
        and child.properties.get("usb-role-switch") == b"",
        "child_otg_mode": child is not None
        and child.properties.get("dr_mode") == b"otg\0",
        "max77705_mfd": "maxim,max77705" in compatible,
        "max77705_pdic": "maxim,max77705_pdic" in compatible,
        "pd_role_swap": any(
            "support_pd_role_swap" in node.properties for node in nodes
        ),
        "samsung_usb_notifier": "samsung,usb-notifier" in compatible,
        "ucsi_fixup": any("/fragment@24:target:0" in value for value in ucsi),
        "no_extcon_property": extcon_count == 0,
        "no_role_switch_default_mode": role_switch_default_mode_count == 0,
    }
    if not all(checks.values()):
        raise ContractError(f"DTBO entry {row['index']} USB role mismatch: {checks}")
    return {
        "index": row["index"],
        "offset": row["offset"],
        "size": row["size"],
        "id": row["id"],
        "revision": row["revision"],
        "custom": row["custom"],
        "sha256": row["sha256"],
        "node_count": len(nodes),
        "checks": checks,
    }


def manifest_sha(entries: tuple[dict[str, Any], ...]) -> str:
    lines = [
        f"{row['index']}\t{row['offset']}\t{row['size']}\t{row['sha256']}\n"
        for row in entries
    ]
    return hashlib.sha256("".join(lines).encode("ascii")).hexdigest()


def build_result(dtbo_path: Path = DEFAULT_DTBO) -> dict[str, Any]:
    root = repo_root()
    path = dtbo_path if dtbo_path.is_absolute() else root / dtbo_path
    data = stable_read(path)
    parsed = parse_dtbo(data)
    inspected = tuple(inspect_entry(row) for row in parsed)
    manifest = manifest_sha(inspected)
    if EXPECTED_ENTRY_MANIFEST_SHA256 and manifest != EXPECTED_ENTRY_MANIFEST_SHA256:
        raise ContractError(f"DTBO entry manifest mismatch: {manifest}")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "dtbo": {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()},
        "entry_count": len(inspected),
        "entry_manifest_sha256": manifest,
        "entries": list(inspected),
        "common_topology": {
            "parent_role_switch": True,
            "child_role_switch": True,
            "child_dr_mode": "otg",
            "max77705_pdic": True,
            "samsung_usb_notifier": True,
            "ucsi_fixup": True,
            "explicit_extcon_property": False,
            "explicit_role_switch_default_mode": False,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "image_built": False,
            "flash": False,
        },
    }


def main() -> int:
    try:
        result = build_result()
    except (ContractError, OSError) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
