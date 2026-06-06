#!/usr/bin/env python3
"""Build a host-only private /dev/__properties__ layout dry-run."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_bytes
from wifi_property_context_mapping_proof import PropertyMapping, serialize_mapped_property_info
from wifi_property_serializer_proof import PropAreaBuilder, SeedProperty, find_property_in_area, find_property_info


DEFAULT_OUT_DIR = Path("tmp/wifi/v312-private-property-runtime-layout")
DEFAULT_V311 = Path("tmp/wifi/v311-property-context-mapping-proof/manifest.json")
PROP_ROOT = Path("layout/dev/__properties__")


@dataclass
class LayoutFile:
    role: str
    relative_path: str
    bytes: int
    sha256: str


@dataclass
class LayoutCheck:
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
    parser.add_argument("--v311-manifest", type=Path, default=DEFAULT_V311)
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


def mapping_from_manifest(item: dict[str, Any]) -> PropertyMapping:
    return PropertyMapping(
        key=str(item.get("key") or ""),
        value=str(item.get("value") or ""),
        context=str(item.get("context") or "") or None,
        prop_type=str(item.get("prop_type") or "") or None,
        match_kind=str(item.get("match_kind") or ""),
        source=str(item.get("source") or ""),
        line_number=int(item.get("line_number") or 0),
        rule=str(item.get("rule") or ""),
        status=str(item.get("status") or "fail"),
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_layout_file(store: EvidenceStore, role: str, relative_path: Path, data: bytes) -> LayoutFile:
    path = store.path(str(relative_path))
    ensure_private_dir(path.parent)
    write_private_bytes(path, data)
    return LayoutFile(role, str(relative_path), len(data), sha256_hex(data))


def safe_context_filename(context: str) -> bool:
    return bool(context) and "/" not in context and "\x00" not in context and context.startswith("u:object_r:") and context.endswith(":s0")


def build_prop_area(properties: list[SeedProperty]) -> bytes:
    builder = PropAreaBuilder()
    for prop in properties:
        builder.add(prop.key, prop.value)
    return builder.bytes()


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v311 = load_json(args.v311_manifest)
    mappings = [mapping_from_manifest(item) for item in v311.get("mappings", []) if isinstance(item, dict)]
    ready_mappings = [mapping for mapping in mappings if mapping.status == "pass" and mapping.context and mapping.prop_type]
    property_info = serialize_mapped_property_info(ready_mappings)
    files: list[LayoutFile] = []
    files.append(write_layout_file(store, "property_info", PROP_ROOT / "property_info", property_info))
    files.append(write_layout_file(store, "properties_serial", PROP_ROOT / "properties_serial", build_prop_area([])))

    by_context: dict[str, list[SeedProperty]] = defaultdict(list)
    type_by_key = {mapping.key: mapping.prop_type for mapping in ready_mappings}
    for mapping in ready_mappings:
        by_context[str(mapping.context)].append(SeedProperty(mapping.key, mapping.value))
    for context, properties in sorted(by_context.items()):
        files.append(write_layout_file(store, "context_prop_area", PROP_ROOT / context, build_prop_area(properties)))

    checks: list[LayoutCheck] = []
    checks.append(LayoutCheck(
        "v311-prerequisite",
        "pass" if v311.get("decision") == "property-context-mapping-ready" else "warn",
        "warning" if v311.get("decision") != "property-context-mapping-ready" else "info",
        f"v311_decision={v311.get('decision')}",
        [str(v311.get("path", ""))],
        "refresh v311 before packaging layout",
    ))
    unsafe_contexts = [context for context in by_context if not safe_context_filename(context)]
    checks.append(LayoutCheck(
        "context-filenames",
        "pass" if not unsafe_contexts else "blocked",
        "blocker" if unsafe_contexts else "info",
        "all context names are single path components" if not unsafe_contexts else "unsafe contexts: " + ", ".join(unsafe_contexts),
        sorted(by_context),
        "do not create host/device layout until context filenames are safe",
    ))

    roundtrip_failures: list[str] = []
    for mapping in ready_mappings:
        context, prop_type = find_property_info(property_info, mapping.key)
        if context != mapping.context or prop_type != type_by_key[mapping.key]:
            roundtrip_failures.append(f"{mapping.key}:property_info")
            continue
        context_file = store.path(str(PROP_ROOT / str(mapping.context)))
        value = find_property_in_area(context_file.read_bytes(), mapping.key)
        if value != mapping.value:
            roundtrip_failures.append(f"{mapping.key}:prop_area")
    checks.append(LayoutCheck(
        "layout-roundtrip",
        "pass" if not roundtrip_failures and ready_mappings else "blocked",
        "blocker" if roundtrip_failures or not ready_mappings else "info",
        f"properties={len(ready_mappings)} contexts={len(by_context)}",
        roundtrip_failures,
        "fix layout builder before runtime materialization planning",
    ))
    checks.append(LayoutCheck(
        "runtime-safety-gate",
        "pass",
        "info",
        "v312 writes only private host evidence under tmp/wifi",
        [],
        "next live stage requires a separate approval packet",
    ))
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    pass_ok = not blockers
    return {
        "generated_at": now_iso(),
        "decision": "private-property-layout-dryrun-ready" if pass_ok else "private-property-layout-dryrun-blocked",
        "pass": pass_ok,
        "reason": "private property runtime layout generated and roundtripped on host" if pass_ok else "blocked checks: " + ", ".join(blockers),
        "next_step": "v313 private property runtime materialization approval packet",
        "host": collect_host_metadata(),
        "inputs": {
            "v311": {"path": v311.get("path"), "present": bool(v311.get("present")), "decision": v311.get("decision"), "pass": v311.get("pass")},
        },
        "model": {
            "scope": "host-only private /dev/__properties__ layout dry-run",
            "device_commands_executed": False,
            "runtime_files_installed": False,
            "property_count": len(ready_mappings),
            "context_count": len(by_context),
            "layout_root": str(PROP_ROOT),
        },
        "mappings": [asdict(mapping) for mapping in ready_mappings],
        "files": [asdict(file) for file in files],
        "checks": [asdict(check) for check in checks],
        "blocked_actions": [
            "push or install generated layout on device",
            "bind mount generated layout over /dev/__properties__",
            "create /dev/socket/property_service",
            "start service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    file_rows = [[item["role"], item["relative_path"], str(item["bytes"]), item["sha256"][:16]] for item in manifest["files"]]
    mapping_rows = [[item["key"], item["context"], item["prop_type"], item["value"]] for item in manifest["mappings"]]
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"][:4])] for item in manifest["checks"]]
    return "\n".join([
        "# v312 Private Property Runtime Layout Dry-run",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Mappings",
        "",
        markdown_table(["key", "context", "type", "value"], mapping_rows),
        "",
        "## Files",
        "",
        markdown_table(["role", "relative_path", "bytes", "sha256"], file_rows),
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
