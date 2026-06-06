#!/usr/bin/env python3
"""Host-only serializer/parser proof for Android property_info and prop_area."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_bytes


DEFAULT_OUT_DIR = Path("tmp/wifi/v310-property-serializer-proof")
DEFAULT_SEED = Path("tmp/wifi/v301-property-shim-seed-android/seed.json")
DEFAULT_V309 = Path("tmp/wifi/v309-property-format-source-probe/manifest.json")
UINT32_MAX = 0xFFFFFFFF
PROP_VALUE_MAX = 92
PROP_AREA_SIZE = 128 * 1024
PROP_AREA_MAGIC = 0x504F5250
PROP_AREA_VERSION = 0xFC6ED0AB
PROP_AREA_HEADER_SIZE = 128
PROP_BT_FIXED_SIZE = 20
PROP_INFO_FIXED_SIZE = 96
PROPERTY_INFO_HEADER_SIZE = 24
MODEL_CONTEXT = "u:object_r:default_prop:s0"
MODEL_TYPE = "string"


@dataclass
class ProofOutput:
    name: str
    path: str
    bytes: int
    sha256: str


@dataclass
class RoundTripCheck:
    name: str
    status: str
    detail: str
    evidence: list[str]


@dataclass
class SeedProperty:
    key: str
    value: str


class Arena:
    def __init__(self) -> None:
        self.data = bytearray()

    @staticmethod
    def align4(value: int) -> int:
        return (value + 3) & ~3

    def allocate(self, size: int) -> int:
        offset = len(self.data)
        self.data.extend(b"\x00" * self.align4(size))
        return offset

    def write_at(self, offset: int, payload: bytes) -> None:
        self.data[offset:offset + len(payload)] = payload

    def write_u32(self, offset: int, value: int) -> None:
        self.write_at(offset, struct.pack("<I", value))

    def read_u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, offset)[0]

    def allocate_object(self, fmt: str, values: tuple[int, ...]) -> int:
        payload = struct.pack(fmt, *values)
        offset = self.allocate(len(payload))
        self.write_at(offset, payload)
        return offset

    def allocate_u32_array(self, values: list[int]) -> int:
        offset = self.allocate(len(values) * 4)
        for index, value in enumerate(values):
            self.write_u32(offset + index * 4, value)
        return offset

    def allocate_string(self, value: str) -> int:
        payload = value.encode("utf-8") + b"\x00"
        offset = self.allocate(len(payload))
        self.write_at(offset, payload)
        return offset


class PropertyInfoNode:
    def __init__(self, name: str) -> None:
        self.name = name
        self.children: dict[str, PropertyInfoNode] = {}
        self.exact_matches: dict[str, tuple[int, int]] = {}

    def add(self, property_name: str, context_index: int, type_index: int) -> None:
        parts = property_name.split(".")
        node = self
        for part in parts[:-1]:
            node = node.children.setdefault(part, PropertyInfoNode(part))
        node.exact_matches[parts[-1]] = (context_index, type_index)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--v309-manifest", type=Path, default=DEFAULT_V309)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def selected_properties(seed: dict[str, Any]) -> list[SeedProperty]:
    properties: list[SeedProperty] = []
    for entry in seed.get("entries", []):
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "")
        value = str(entry.get("value") or "")
        if entry.get("state") == "ready" and key.startswith("ro.") and value:
            properties.append(SeedProperty(key, value))
    return properties


def serialize_strings(arena: Arena, values: list[str]) -> int:
    sorted_values = sorted(set(values))
    start = arena.allocate(4)
    arena.write_u32(start, len(sorted_values))
    array_offset = arena.allocate_u32_array([0] * len(sorted_values))
    for index, value in enumerate(sorted_values):
        string_offset = arena.allocate_string(value)
        arena.write_u32(array_offset + index * 4, string_offset)
    return start


def serialize_property_info(properties: list[SeedProperty],
                            context: str,
                            prop_type: str) -> bytes:
    arena = Arena()
    header_offset = arena.allocate(PROPERTY_INFO_HEADER_SIZE)
    contexts = [context]
    types = [prop_type]
    context_index = sorted(contexts).index(context)
    type_index = sorted(types).index(prop_type)

    contexts_offset = len(arena.data)
    serialize_strings(arena, contexts)
    types_offset = len(arena.data)
    serialize_strings(arena, types)
    root = PropertyInfoNode("")
    for prop in properties:
        root.add(prop.key, context_index, type_index)

    root_offset = write_property_info_node(arena, root)
    size = len(arena.data)
    arena.write_at(
        header_offset,
        struct.pack("<IIIIII", 1, 1, size, contexts_offset, types_offset, root_offset),
    )
    return bytes(arena.data)


def write_property_entry(arena: Arena, name: str, context_index: int, type_index: int) -> int:
    name_offset = arena.allocate_string(name)
    return arena.allocate_object("<IIII", (name_offset, len(name), context_index, type_index))


def write_property_info_node(arena: Arena, node: PropertyInfoNode) -> int:
    node_offset = arena.allocate(28)
    property_entry = write_property_entry(arena, node.name, UINT32_MAX, UINT32_MAX)

    child_offsets: list[int] = []
    for child in sorted(node.children.values(), key=lambda item: item.name):
        child_offsets.append(write_property_info_node(arena, child))

    exact_offsets: list[int] = []
    for name, (context_index, type_index) in sorted(node.exact_matches.items()):
        exact_offsets.append(write_property_entry(arena, name, context_index, type_index))

    children_offset = arena.allocate_u32_array(child_offsets)
    prefix_offset = arena.allocate_u32_array([])
    exact_offset = arena.allocate_u32_array(exact_offsets)
    arena.write_at(
        node_offset,
        struct.pack(
            "<IIIIIII",
            property_entry,
            len(child_offsets),
            children_offset,
            0,
            prefix_offset,
            len(exact_offsets),
            exact_offset,
        ),
    )
    return node_offset


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_c_string(data: bytes, offset: int) -> str:
    end = data.index(0, offset)
    return data[offset:end].decode("utf-8")


def parse_string_table(data: bytes, offset: int) -> list[str]:
    count = read_u32(data, offset)
    array_offset = offset + 4
    return [read_c_string(data, read_u32(data, array_offset + index * 4)) for index in range(count)]


def parse_property_entry(data: bytes, offset: int) -> tuple[str, int, int]:
    name_offset, _namelen, context_index, type_index = struct.unpack_from("<IIII", data, offset)
    return read_c_string(data, name_offset), context_index, type_index


def find_property_info(data: bytes, property_name: str) -> tuple[str | None, str | None]:
    current_version, minimum_version, size, contexts_offset, types_offset, root_offset = struct.unpack_from("<IIIIII", data, 0)
    if current_version != 1 or minimum_version > 1 or size != len(data):
        raise ValueError("invalid property_info header")
    contexts = parse_string_table(data, contexts_offset)
    types = parse_string_table(data, types_offset)
    context_index = UINT32_MAX
    type_index = UINT32_MAX
    remaining = property_name
    node_offset = root_offset

    while True:
        property_entry, child_count, children_offset, _prefix_count, _prefix_offset, exact_count, exact_offset = struct.unpack_from("<IIIIIII", data, node_offset)
        _node_name, node_context, node_type = parse_property_entry(data, property_entry)
        if node_context != UINT32_MAX:
            context_index = node_context
        if node_type != UINT32_MAX:
            type_index = node_type
        if "." not in remaining:
            break
        token, remaining = remaining.split(".", 1)
        next_node = 0
        for index in range(child_count):
            child_offset = read_u32(data, children_offset + index * 4)
            child_entry = read_u32(data, child_offset)
            child_name, _child_context, _child_type = parse_property_entry(data, child_entry)
            if child_name == token:
                next_node = child_offset
                break
        if next_node == 0:
            break
        node_offset = next_node

    _property_entry, _child_count, _children_offset, _prefix_count, _prefix_offset, exact_count, exact_offset = struct.unpack_from("<IIIIIII", data, node_offset)
    for index in range(exact_count):
        entry_offset = read_u32(data, exact_offset + index * 4)
        exact_name, exact_context, exact_type = parse_property_entry(data, entry_offset)
        if exact_name == remaining:
            if exact_context != UINT32_MAX:
                context_index = exact_context
            if exact_type != UINT32_MAX:
                type_index = exact_type
            break
    context = None if context_index == UINT32_MAX else contexts[context_index]
    prop_type = None if type_index == UINT32_MAX else types[type_index]
    return context, prop_type


class PropAreaBuilder:
    def __init__(self) -> None:
        self.data = bytearray(PROP_AREA_SIZE)
        self.bytes_used = PROP_BT_FIXED_SIZE + PROP_VALUE_MAX
        self.write_header()

    @staticmethod
    def align4(value: int) -> int:
        return (value + 3) & ~3

    def data_abs(self, offset: int) -> int:
        return PROP_AREA_HEADER_SIZE + offset

    def write_header(self) -> None:
        struct.pack_into(
            "<IIII28I",
            self.data,
            0,
            self.bytes_used,
            0,
            PROP_AREA_MAGIC,
            PROP_AREA_VERSION,
            *([0] * 28),
        )

    def read_u32_rel(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, self.data_abs(offset))[0]

    def write_u32_rel(self, offset: int, value: int) -> None:
        struct.pack_into("<I", self.data, self.data_abs(offset), value)

    def allocate(self, size: int) -> int:
        offset = self.bytes_used
        aligned = self.align4(size)
        if PROP_AREA_HEADER_SIZE + offset + aligned > PROP_AREA_SIZE:
            raise ValueError("property area overflow")
        self.bytes_used += aligned
        self.write_header()
        return offset

    def node_name(self, offset: int) -> str:
        namelen = self.read_u32_rel(offset)
        start = self.data_abs(offset + PROP_BT_FIXED_SIZE)
        return self.data[start:start + namelen].decode("utf-8")

    @staticmethod
    def cmp_prop_name(one: str, two: str) -> int:
        if len(one) < len(two):
            return -1
        if len(one) > len(two):
            return 1
        if one < two:
            return -1
        if one > two:
            return 1
        return 0

    def create_node(self, name: str) -> int:
        encoded = name.encode("utf-8")
        offset = self.allocate(PROP_BT_FIXED_SIZE + len(encoded) + 1)
        self.write_u32_rel(offset, len(encoded))
        start = self.data_abs(offset + PROP_BT_FIXED_SIZE)
        self.data[start:start + len(encoded)] = encoded
        return offset

    def find_or_create_sibling(self, root_offset: int, name: str) -> int:
        current = root_offset
        while True:
            current_name = self.node_name(current)
            if name == current_name:
                return current
            field = 8 if self.cmp_prop_name(name, current_name) < 0 else 12
            next_offset = self.read_u32_rel(current + field)
            if next_offset != 0:
                current = next_offset
                continue
            new_offset = self.create_node(name)
            self.write_u32_rel(current + field, new_offset)
            return new_offset

    def child_for_token(self, current_offset: int, token: str) -> int:
        children_field = current_offset + 16
        child_root = self.read_u32_rel(children_field)
        if child_root == 0:
            child_root = self.create_node(token)
            self.write_u32_rel(children_field, child_root)
            return child_root
        return self.find_or_create_sibling(child_root, token)

    def create_prop_info(self, name: str, value: str) -> int:
        encoded_name = name.encode("utf-8")
        encoded_value = value.encode("utf-8")
        if len(encoded_value) >= PROP_VALUE_MAX:
            raise ValueError(f"long property values are out of v310 scope: {name}")
        offset = self.allocate(PROP_INFO_FIXED_SIZE + len(encoded_name) + 1)
        self.write_u32_rel(offset, len(encoded_value) << 24)
        value_start = self.data_abs(offset + 4)
        self.data[value_start:value_start + len(encoded_value)] = encoded_value
        name_start = self.data_abs(offset + PROP_INFO_FIXED_SIZE)
        self.data[name_start:name_start + len(encoded_name)] = encoded_name
        return offset

    def add(self, name: str, value: str) -> None:
        current = 0
        for token in name.split("."):
            current = self.child_for_token(current, token)
        prop_offset = self.create_prop_info(name, value)
        self.write_u32_rel(current + 4, prop_offset)

    def bytes(self) -> bytes:
        return bytes(self.data)


def find_property_in_area(data: bytes, property_name: str) -> str | None:
    bytes_used, _serial, magic, version = struct.unpack_from("<IIII", data, 0)
    if magic != PROP_AREA_MAGIC or version != PROP_AREA_VERSION:
        raise ValueError("invalid prop_area header")
    if bytes_used > PROP_AREA_SIZE - PROP_AREA_HEADER_SIZE:
        raise ValueError("invalid prop_area bytes_used")

    def read_rel(offset: int) -> int:
        return struct.unpack_from("<I", data, PROP_AREA_HEADER_SIZE + offset)[0]

    def node_name(offset: int) -> str:
        namelen = read_rel(offset)
        start = PROP_AREA_HEADER_SIZE + offset + PROP_BT_FIXED_SIZE
        return data[start:start + namelen].decode("utf-8")

    def cmp_prop_name(one: str, two: str) -> int:
        if len(one) < len(two):
            return -1
        if len(one) > len(two):
            return 1
        if one < two:
            return -1
        if one > two:
            return 1
        return 0

    def find_sibling(root_offset: int, name: str) -> int:
        current = root_offset
        while current != 0:
            current_name = node_name(current)
            if name == current_name:
                return current
            current = read_rel(current + (8 if cmp_prop_name(name, current_name) < 0 else 12))
        return 0

    current = 0
    for token in property_name.split("."):
        child_root = read_rel(current + 16)
        current = find_sibling(child_root, token)
        if current == 0:
            return None
    prop_offset = read_rel(current + 4)
    if prop_offset == 0:
        return None
    serial = read_rel(prop_offset)
    value_len = serial >> 24
    start = PROP_AREA_HEADER_SIZE + prop_offset + 4
    return data[start:start + value_len].decode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_output(store: EvidenceStore, relative_path: str, data: bytes) -> ProofOutput:
    path = store.path(relative_path)
    write_private_bytes(path, data)
    return ProofOutput(relative_path, str(path), len(data), sha256_hex(data))


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    seed = load_json(args.seed)
    v309 = load_json(args.v309_manifest)
    properties = selected_properties(seed)
    property_info = serialize_property_info(properties, MODEL_CONTEXT, MODEL_TYPE)
    area_builder = PropAreaBuilder()
    for prop in properties:
        area_builder.add(prop.key, prop.value)
    property_area = area_builder.bytes()
    serial_area = PropAreaBuilder().bytes()

    outputs = [
        write_output(store, "layout/property_info", property_info),
        write_output(store, f"layout/{MODEL_CONTEXT}", property_area),
        write_output(store, "layout/properties_serial", serial_area),
    ]

    checks: list[RoundTripCheck] = []
    for prop in properties:
        context, prop_type = find_property_info(property_info, prop.key)
        value = find_property_in_area(property_area, prop.key)
        checks.append(RoundTripCheck(
            prop.key,
            "pass" if context == MODEL_CONTEXT and prop_type == MODEL_TYPE and value == prop.value else "fail",
            f"context={context} type={prop_type} value={value}",
            [prop.value],
        ))

    header_current, header_minimum, header_size, contexts_offset, types_offset, root_offset = struct.unpack_from("<IIIIII", property_info, 0)
    area_bytes_used, _area_serial, area_magic, area_version = struct.unpack_from("<IIII", property_area, 0)
    checks.append(RoundTripCheck(
        "property-info-header",
        "pass" if header_current == 1 and header_minimum == 1 and header_size == len(property_info) and contexts_offset > 0 and types_offset > contexts_offset and root_offset > types_offset else "fail",
        f"current={header_current} minimum={header_minimum} size={header_size} contexts_offset={contexts_offset} types_offset={types_offset} root_offset={root_offset}",
        [],
    ))
    checks.append(RoundTripCheck(
        "prop-area-header",
        "pass" if area_magic == PROP_AREA_MAGIC and area_version == PROP_AREA_VERSION and area_bytes_used > PROP_BT_FIXED_SIZE + PROP_VALUE_MAX else "fail",
        f"magic=0x{area_magic:08x} version=0x{area_version:08x} bytes_used={area_bytes_used}",
        [],
    ))
    checks.append(RoundTripCheck(
        "v309-prerequisite",
        "pass" if v309.get("decision") == "property-format-source-map-ready" else "warn",
        f"v309_decision={v309.get('decision')}",
        [str(v309.get("path", ""))],
    ))
    pass_ok = bool(properties) and all(check.status == "pass" for check in checks if check.name != "v309-prerequisite")
    decision = "property-serializer-proof-ready" if pass_ok else "property-serializer-proof-blocked"
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": "host-only property_info and prop_area roundtrip passed" if pass_ok else "serializer/parser roundtrip failed",
        "next_step": "v311 context-aware property_contexts mapping proof",
        "host": collect_host_metadata(),
        "inputs": {
            "seed": {"path": seed.get("path"), "present": bool(seed.get("present")), "schema": seed.get("schema"), "policy": seed.get("policy")},
            "v309": {"path": v309.get("path"), "present": bool(v309.get("present")), "decision": v309.get("decision"), "pass": v309.get("pass")},
        },
        "model": {
            "scope": "host-only serializer/parser compatibility proof",
            "context": MODEL_CONTEXT,
            "type": MODEL_TYPE,
            "runtime_files_created": False,
            "device_commands_executed": False,
            "property_count": len(properties),
            "limits": {
                "PROP_VALUE_MAX": PROP_VALUE_MAX,
                "PROP_AREA_MAGIC": f"0x{PROP_AREA_MAGIC:08x}",
                "PROP_AREA_VERSION": f"0x{PROP_AREA_VERSION:08x}",
                "PROP_AREA_SIZE": PROP_AREA_SIZE,
            },
        },
        "properties": [asdict(prop) for prop in properties],
        "outputs": [asdict(output) for output in outputs],
        "checks": [asdict(check) for check in checks],
        "blocked_actions": [
            "create global /dev/__properties__",
            "create /dev/socket/property_service",
            "install generated files on device",
            "start service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    output_rows = [[item["name"], str(item["bytes"]), item["sha256"][:16]] for item in manifest["outputs"]]
    check_rows = [[item["name"], item["status"], item["detail"], "<br>".join(item["evidence"])] for item in manifest["checks"]]
    property_rows = [[item["key"], item["value"]] for item in manifest["properties"]]
    return "\n".join([
        "# v310 Property Serializer Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- model_context: `{manifest['model']['context']}`",
        "",
        "## Properties",
        "",
        markdown_table(["key", "value"], property_rows),
        "",
        "## Outputs",
        "",
        markdown_table(["name", "bytes", "sha256"], output_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "evidence"], check_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
