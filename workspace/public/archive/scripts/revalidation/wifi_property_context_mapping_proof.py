#!/usr/bin/env python3
"""Map Android-backed seed properties through captured property_contexts."""

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
from wifi_property_serializer_proof import (
    Arena,
    PropertyInfoNode,
    SeedProperty,
    find_property_info,
    selected_properties,
    write_property_info_node,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v311-property-context-mapping-proof")
DEFAULT_SEED = Path("tmp/wifi/v301-property-shim-seed-android/seed.json")
DEFAULT_V295 = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json")
DEFAULT_V310 = Path("tmp/wifi/v310-property-serializer-proof/manifest.json")
UINT32_MAX = 0xFFFFFFFF


@dataclass
class ContextRule:
    source: str
    line_number: int
    name: str
    context: str
    exact: bool
    prop_type: str
    raw: str


@dataclass
class PropertyMapping:
    key: str
    value: str
    context: str | None
    prop_type: str | None
    match_kind: str
    source: str
    line_number: int
    rule: str
    status: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295)
    parser.add_argument("--v310-manifest", type=Path, default=DEFAULT_V310)
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


def capture_files(v295: dict[str, Any]) -> list[tuple[str, Path]]:
    manifest_path = Path(str(v295.get("path", "")))
    if not manifest_path:
        return []
    files: list[tuple[str, Path]] = []
    for capture in v295.get("captures", []):
        if not isinstance(capture, dict):
            continue
        name = str(capture.get("name") or "")
        rel = str(capture.get("file") or "")
        if not name.startswith("cat-context-") or not rel:
            continue
        path = manifest_path.parent / rel
        if path.exists():
            files.append((name, path))
    return files


def parse_context_file(name: str, path: Path) -> list[ContextRule]:
    rules: list[ContextRule] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        prop_name = parts[0]
        context = parts[1]
        exact = len(parts) >= 3 and parts[2] == "exact"
        prop_type = "string"
        if exact and len(parts) >= 4:
            prop_type = parts[3]
        elif not exact and len(parts) >= 3:
            prop_type = parts[2]
        rules.append(ContextRule(name, line_number, prop_name, context, exact, prop_type, stripped))
    return rules


def rule_matches(rule: ContextRule, key: str) -> bool:
    if rule.exact:
        return key == rule.name
    return key.startswith(rule.name)


def map_property(prop: SeedProperty, rules: list[ContextRule]) -> PropertyMapping:
    exact_matches = [rule for rule in rules if rule.exact and rule_matches(rule, prop.key)]
    if exact_matches:
        rule = exact_matches[-1]
        return PropertyMapping(prop.key, prop.value, rule.context, rule.prop_type, "exact", rule.source, rule.line_number, rule.raw, "pass")
    prefix_matches = [rule for rule in rules if not rule.exact and rule_matches(rule, prop.key)]
    if prefix_matches:
        prefix_matches.sort(key=lambda item: len(item.name))
        rule = prefix_matches[-1]
        return PropertyMapping(prop.key, prop.value, rule.context, rule.prop_type, "prefix", rule.source, rule.line_number, rule.raw, "pass")
    return PropertyMapping(prop.key, prop.value, None, None, "missing", "", 0, "", "fail")


def serialize_mapped_property_info(mappings: list[PropertyMapping]) -> bytes:
    contexts = sorted({mapping.context for mapping in mappings if mapping.context})
    types = sorted({mapping.prop_type for mapping in mappings if mapping.prop_type})
    context_index = {context: index for index, context in enumerate(contexts)}
    type_index = {prop_type: index for index, prop_type in enumerate(types)}
    arena = Arena()
    header_offset = arena.allocate(24)
    contexts_offset = len(arena.data)
    serialize_string_table(arena, contexts)
    types_offset = len(arena.data)
    serialize_string_table(arena, types)
    root = PropertyInfoNode("")
    for mapping in mappings:
        if mapping.context is None or mapping.prop_type is None:
            continue
        root.add(mapping.key, context_index[mapping.context], type_index[mapping.prop_type])
    root_offset = write_property_info_node(arena, root)
    size = len(arena.data)
    arena.write_at(header_offset, struct.pack("<IIIIII", 1, 1, size, contexts_offset, types_offset, root_offset))
    return bytes(arena.data)


def serialize_string_table(arena: Arena, values: list[str]) -> None:
    arena.write_u32(arena.allocate(4), len(values))
    array_offset = arena.allocate_u32_array([0] * len(values))
    for index, value in enumerate(values):
        arena.write_u32(array_offset + index * 4, arena.allocate_string(value))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_binary(store: EvidenceStore, relative_path: str, data: bytes) -> dict[str, Any]:
    path = store.path(relative_path)
    write_private_bytes(path, data)
    return {"name": relative_path, "path": str(path), "bytes": len(data), "sha256": sha256_hex(data)}


def build_checks(v295: dict[str, Any],
                 v310: dict[str, Any],
                 rules: list[ContextRule],
                 mappings: list[PropertyMapping],
                 roundtrip_ok: bool) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check(
        "v295-context-input",
        "pass" if v295.get("decision") == "property-snapshot-model-ready" else "warn",
        "warning" if v295.get("decision") != "property-snapshot-model-ready" else "info",
        f"v295_decision={v295.get('decision')}",
        [str(v295.get("path", ""))],
        "refresh property snapshot if context evidence is stale",
    ))
    checks.append(Check(
        "v310-prerequisite",
        "pass" if v310.get("decision") == "property-serializer-proof-ready" else "warn",
        "warning" if v310.get("decision") != "property-serializer-proof-ready" else "info",
        f"v310_decision={v310.get('decision')}",
        [str(v310.get("path", ""))],
        "refresh v310 serializer proof if binary format model changed",
    ))
    checks.append(Check(
        "context-rules",
        "pass" if len(rules) >= 100 else "blocked",
        "blocker" if len(rules) < 100 else "info",
        f"rules={len(rules)}",
        sorted({rule.source for rule in rules}),
        "capture full property_contexts before mapping",
    ))
    missing = [mapping.key for mapping in mappings if mapping.status != "pass"]
    checks.append(Check(
        "selected-key-mapping",
        "pass" if not missing else "blocked",
        "blocker" if missing else "info",
        "all selected seed keys mapped" if not missing else "missing: " + ", ".join(missing),
        [mapping.rule for mapping in mappings if mapping.status == "pass"],
        "capture missing vendor/product property context files" if missing else "",
    ))
    checks.append(Check(
        "mapped-property-info-roundtrip",
        "pass" if roundtrip_ok else "blocked",
        "blocker" if not roundtrip_ok else "info",
        "context-aware property_info roundtrip passed" if roundtrip_ok else "roundtrip mismatch",
        [f"{mapping.key}->{mapping.context}/{mapping.prop_type}" for mapping in mappings],
        "fix mapped property_info serializer before runtime package modeling",
    ))
    checks.append(Check(
        "runtime-safety-gate",
        "pass",
        "info",
        "v311 uses captured files and writes only host evidence artifacts",
        [],
        "do not install generated property files without a later explicit runtime gate",
    ))
    return checks


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    seed = load_json(args.seed)
    v295 = load_json(args.v295_manifest)
    v310 = load_json(args.v310_manifest)
    properties = selected_properties(seed)
    files = capture_files(v295)
    rules: list[ContextRule] = []
    for name, path in files:
        rules.extend(parse_context_file(name, path))
    mappings = [map_property(prop, rules) for prop in properties]
    property_info = serialize_mapped_property_info(mappings)
    output = write_binary(store, "layout/property_info_context_mapped", property_info)
    roundtrip_ok = True
    for mapping in mappings:
        context, prop_type = find_property_info(property_info, mapping.key)
        if context != mapping.context or prop_type != mapping.prop_type:
            roundtrip_ok = False
    checks = build_checks(v295, v310, rules, mappings, roundtrip_ok)
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    pass_ok = not blockers
    return {
        "generated_at": now_iso(),
        "decision": "property-context-mapping-ready" if pass_ok else "property-context-mapping-blocked",
        "pass": pass_ok,
        "reason": "selected seed keys map through captured property_contexts" if pass_ok else "blocked checks: " + ", ".join(blockers),
        "next_step": "v312 private property runtime layout package dry-run",
        "host": collect_host_metadata(),
        "inputs": {
            "seed": {"path": seed.get("path"), "present": bool(seed.get("present")), "schema": seed.get("schema")},
            "v295": {"path": v295.get("path"), "present": bool(v295.get("present")), "decision": v295.get("decision"), "pass": v295.get("pass")},
            "v310": {"path": v310.get("path"), "present": bool(v310.get("present")), "decision": v310.get("decision"), "pass": v310.get("pass")},
        },
        "model": {
            "scope": "host-only context-aware mapping proof",
            "device_commands_executed": False,
            "runtime_files_created": False,
            "context_rule_count": len(rules),
            "context_file_count": len(files),
        },
        "mappings": [asdict(mapping) for mapping in mappings],
        "outputs": [output],
        "checks": [asdict(check) for check in checks],
        "blocked_actions": [
            "install generated property_info on device",
            "create global /dev/__properties__",
            "create /dev/socket/property_service",
            "start service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    mapping_rows = [
        [item["key"], item["context"], item["prop_type"], item["match_kind"], f"{item['source']}:{item['line_number']}"]
        for item in manifest["mappings"]
    ]
    check_rows = [
        [item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"][:4])]
        for item in manifest["checks"]
    ]
    output_rows = [[item["name"], str(item["bytes"]), item["sha256"][:16]] for item in manifest["outputs"]]
    return "\n".join([
        "# v311 Property Context Mapping Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Mappings",
        "",
        markdown_table(["key", "context", "type", "match", "source"], mapping_rows),
        "",
        "## Outputs",
        "",
        markdown_table(["name", "bytes", "sha256"], output_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], check_rows),
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
