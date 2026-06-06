#!/usr/bin/env python3
"""V471 extended private property runtime overlay dry-run.

This builds a host-only `/dev/__properties__` layout that covers the V470
Wi-Fi/runtime property gap. It does not install files on the device, bind over
global `/dev/__properties__`, start daemons, or bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_bytes
from wifi_private_property_layout_dryrun import build_prop_area, safe_context_filename
from wifi_property_context_mapping_proof import (
    ContextRule,
    PropertyMapping,
    capture_files,
    map_property,
    parse_context_file,
    serialize_mapped_property_info,
)
from wifi_property_serializer_proof import SeedProperty, find_property_in_area, find_property_info


DEFAULT_OUT_DIR = Path("tmp/wifi/v471-extended-private-property-runtime")
DEFAULT_V295 = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json")
DEFAULT_V470 = Path("tmp/wifi/v470-native-property-gap-20260521-013907/property-analysis.json")
DEFAULT_ANDROID_GETPROP = Path("tmp/wifi/v297-android-property-capture-android/commands/all-getprop.txt")
PROP_ROOT = Path("layout/dev/__properties__")

CORE_KEYS = (
    "ro.build.version.sdk",
    "ro.build.version.release",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
    "ro.property_service.version",
    "sys.boot_completed",
    "dev.bootcomplete",
    "wifi.interface",
    "wlan.driver.status",
    "init.svc.servicemanager",
    "init.svc.hwservicemanager",
    "init.svc.vendor.wifi_hal_ext",
    "init.svc.vendor.wifi_hal_legacy",
    "init.svc.vendor.wifi_hal",
    "init.svc.wificond",
    "init.svc.wpa_supplicant",
    "init.svc.cnss-daemon",
    "init.svc.cnss_diag",
)

LOADER_CONTEXT_KEYS = (
    "ro.debuggable",
    "debug.ld.app.getprop",
    "arm64.memtag.process.getprop",
    "ro.vndk.version",
    "debug.fdsan",
    "libc.debug.pthread.lock_owner",
    "libc.debug.malloc.options",
    "libc.debug.hooks.enable",
    "heapprofd.enable",
    "ro.vendor.redirect_socket_calls",
)

RUNTIME_OBSERVED_KEYS = (
    "arm64.memtag.process.cnss-daemon",
    "arm64.memtag.process.hwservicemanager",
    "arm64.memtag.process.lshal",
    "arm64.memtag.process.servicemanager",
    "arm64.memtag.process.sh",
    "arm64.memtag.process.vendor.samsung.hardware.wifi@2.0-service",
    "debug.enable",
    "debug.atrace.app_number",
    "debug.atrace.tags.enableflags",
    "debug.ld.app.cnss-daemon",
    "debug.ld.app.hwservicemanager",
    "debug.ld.app.lshal",
    "debug.ld.app.servicemanager",
    "debug.ld.app.sh",
    "debug.ld.app.vendor.samsung.hardware.wifi@2.0-service",
    "hwservicemanager.ready",
    "log.tag",
    "log.tag.CLD80211",
    "log.tag.cutils-trace",
    "log.tag.HidlServiceManagement",
    "log.tag.ProcessState",
    "log.tag.SELinux",
    "log.tag.cnss-daemon",
    "log.tag.hw-ProcessState",
    "log.tag.hwservicemanager",
    "log.tag.liblog",
    "log.tag.libmdmdetect",
    "log.tag.lshal",
    "log.tag.servicemanager",
    "log.tag.vendor.samsung.hardware.wifi@2.0-service",
    "net.redirect_socket_calls.hooked",
    "persist.log.level",
    "persist.log.tag",
    "persist.log.tag.CLD80211",
    "persist.log.tag.cutils-trace",
    "persist.log.tag.HidlServiceManagement",
    "persist.log.tag.ProcessState",
    "persist.log.tag.SELinux",
    "persist.log.tag.cnss-daemon",
    "persist.log.tag.hw-ProcessState",
    "persist.log.tag.hwservicemanager",
    "persist.log.tag.liblog",
    "persist.log.tag.libmdmdetect",
    "persist.log.tag.lshal",
    "persist.log.tag.servicemanager",
    "persist.log.tag.vendor.samsung.hardware.wifi@2.0-service",
    "persist.vendor.cnss-daemon.debug_level",
    "persist.vendor.cnss-daemon.kmsg_logging",
    "ro.build.version.codename",
    "ro.vendor.extension_library",
    "sys.perf.boostopt",
)

FALLBACK_VALUES = {
    "ro.build.version.sdk": "31",
    "ro.build.version.release": "",
    "ro.product.name": "r3qks",
    "ro.hardware": "qcom",
    "ro.vendor.build.version.sdk": "30",
    "ro.property_service.version": "2",
    "sys.boot_completed": "1",
    "dev.bootcomplete": "1",
    "wifi.interface": "wlan0",
    "wlan.driver.status": "ok",
    "init.svc.servicemanager": "running",
    "init.svc.hwservicemanager": "running",
    "init.svc.vendor.wifi_hal_ext": "running",
    "init.svc.vendor.wifi_hal_legacy": "running",
    "init.svc.vendor.wifi_hal": "",
    "init.svc.wificond": "running",
    "init.svc.wpa_supplicant": "",
    "init.svc.cnss-daemon": "running",
    "init.svc.cnss_diag": "running",
    "ro.debuggable": "0",
    "debug.ld.app.getprop": "",
    "arm64.memtag.process.getprop": "",
    "ro.vndk.version": "30",
    "debug.fdsan": "",
    "libc.debug.pthread.lock_owner": "",
    "libc.debug.malloc.options": "",
    "libc.debug.hooks.enable": "",
    "heapprofd.enable": "",
    "ro.vendor.redirect_socket_calls": "true",
    "hwservicemanager.ready": "true",
    "net.redirect_socket_calls.hooked": "false",
}
FALLBACK_VALUES.update({key: "" for key in RUNTIME_OBSERVED_KEYS if key not in FALLBACK_VALUES})


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


@dataclass
class SeedRecord:
    key: str
    value: str
    source: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295)
    parser.add_argument("--v470-analysis", type=Path, default=DEFAULT_V470)
    parser.add_argument("--android-getprop", type=Path, default=DEFAULT_ANDROID_GETPROP)
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


def parse_android_getprop(path: Path) -> dict[str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    values: dict[str, str] = {}
    pattern = re.compile(r"^\[([^\]]+)\]: \[(.*)\]$")
    for line in resolved.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return values


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_layout_file(store: EvidenceStore, role: str, relative_path: Path, data: bytes) -> LayoutFile:
    path = store.path(str(relative_path))
    ensure_private_dir(path.parent)
    write_private_bytes(path, data)
    return LayoutFile(role, str(relative_path), len(data), sha256_hex(data))


def selected_keys(v470: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for key in CORE_KEYS + LOADER_CONTEXT_KEYS + RUNTIME_OBSERVED_KEYS:
        if key not in keys:
            keys.append(key)
    for row in v470.get("rows", []):
        if isinstance(row, dict):
            key = str(row.get("key") or "")
            if key and key not in keys:
                keys.append(key)
    return keys


def build_seed_records(keys: list[str], android_values: dict[str, str]) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    for key in keys:
        if key in android_values:
            records.append(SeedRecord(key, android_values[key], "android-getprop"))
        elif key in FALLBACK_VALUES:
            source = "fallback-empty" if FALLBACK_VALUES[key] == "" else "fallback-static"
            if key in ("wifi.interface", "wlan.driver.status"):
                source = "vendor-init-inferred"
            records.append(SeedRecord(key, FALLBACK_VALUES[key], source))
        else:
            records.append(SeedRecord(key, "", "fallback-empty"))
    return records


def build_rules(v295: dict[str, Any]) -> list[ContextRule]:
    rules: list[ContextRule] = []
    for name, path in capture_files(v295):
        rules.extend(parse_context_file(name, path))
    return rules


def build_checks(v295: dict[str, Any],
                 v470: dict[str, Any],
                 rules: list[ContextRule],
                 mappings: list[PropertyMapping],
                 roundtrip_failures: list[str],
                 unsafe_contexts: list[str]) -> list[LayoutCheck]:
    missing = [mapping.key for mapping in mappings if mapping.status != "pass"]
    v470_empty = v470.get("empty_stdout_keys") if isinstance(v470.get("empty_stdout_keys"), list) else []
    return [
        LayoutCheck(
            "v295-context-input",
            "pass" if v295.get("decision") == "property-snapshot-model-ready" else "warn",
            "warning" if v295.get("decision") != "property-snapshot-model-ready" else "info",
            f"decision={v295.get('decision')} pass={v295.get('pass')} rules={len(rules)}",
            [str(v295.get("path", ""))],
            "refresh property_contexts capture if mapping rules are stale",
        ),
        LayoutCheck(
            "v470-gap-input",
            "pass" if v470.get("decision") == "v470-property-context-gap-confirmed" else "warn",
            "warning" if v470.get("decision") != "v470-property-context-gap-confirmed" else "info",
            f"decision={v470.get('decision')} empty_stdout_keys={len(v470_empty)}",
            [str(v470.get("path", ""))],
            "refresh V470 property lookup analysis before live overlay deployment",
        ),
        LayoutCheck(
            "selected-key-mapping",
            "pass" if not missing else "blocked",
            "blocker" if missing else "info",
            f"mapped={len(mappings) - len(missing)} missing={len(missing)}",
            missing[:8],
            "capture missing property_contexts before runtime packaging",
        ),
        LayoutCheck(
            "context-filenames",
            "pass" if not unsafe_contexts else "blocked",
            "blocker" if unsafe_contexts else "info",
            "all context names are safe single components" if not unsafe_contexts else "unsafe contexts: " + ", ".join(unsafe_contexts),
            unsafe_contexts[:8],
            "do not package unsafe context filenames",
        ),
        LayoutCheck(
            "layout-roundtrip",
            "pass" if not roundtrip_failures else "blocked",
            "blocker" if roundtrip_failures else "info",
            f"failures={len(roundtrip_failures)}",
            roundtrip_failures[:12],
            "fix property_info/prop_area generation before live deployment",
        ),
        LayoutCheck(
            "runtime-safety-gate",
            "pass",
            "info",
            "host-only layout generation; no device mutation or daemon start",
            [],
            "deploy under a versioned private property root only after a separate live gate",
        ),
    ]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v295 = load_json(args.v295_manifest)
    v470 = load_json(args.v470_analysis)
    android_values = parse_android_getprop(args.android_getprop)
    seeds = build_seed_records(selected_keys(v470), android_values)
    rules = build_rules(v295)
    mappings = [map_property(SeedProperty(seed.key, seed.value), rules) for seed in seeds]
    property_info = serialize_mapped_property_info(mappings)

    files: list[LayoutFile] = []
    files.append(write_layout_file(store, "property_info", PROP_ROOT / "property_info", property_info))
    files.append(write_layout_file(store, "properties_serial", PROP_ROOT / "properties_serial", build_prop_area([])))

    by_context: dict[str, list[SeedProperty]] = defaultdict(list)
    value_by_key = {seed.key: seed.value for seed in seeds}
    for mapping in mappings:
        if mapping.status == "pass" and mapping.context:
            by_context[mapping.context].append(SeedProperty(mapping.key, value_by_key[mapping.key]))
    for context, properties in sorted(by_context.items()):
        files.append(write_layout_file(store, "context_prop_area", PROP_ROOT / context, build_prop_area(properties)))

    roundtrip_failures: list[str] = []
    type_by_key = {mapping.key: mapping.prop_type for mapping in mappings}
    context_by_key = {mapping.key: mapping.context for mapping in mappings}
    for seed in seeds:
        context, prop_type = find_property_info(property_info, seed.key)
        if context != context_by_key.get(seed.key) or prop_type != type_by_key.get(seed.key):
            roundtrip_failures.append(f"{seed.key}:property_info")
            continue
        if not context:
            roundtrip_failures.append(f"{seed.key}:missing-context")
            continue
        context_file = store.path(str(PROP_ROOT / context))
        value = find_property_in_area(context_file.read_bytes(), seed.key)
        if value != seed.value:
            roundtrip_failures.append(f"{seed.key}:prop_area")

    unsafe_contexts = [context for context in by_context if not safe_context_filename(context)]
    checks = build_checks(v295, v470, rules, mappings, roundtrip_failures, unsafe_contexts)
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    pass_ok = not blockers
    return {
        "generated_at": now_iso(),
        "decision": "v471-extended-private-property-runtime-ready" if pass_ok else "v471-extended-private-property-runtime-blocked",
        "pass": pass_ok,
        "reason": "extended private property layout generated and roundtripped" if pass_ok else "blocked checks: " + ", ".join(blockers),
        "next_step": "deploy under /mnt/sdext/a90/private-property-v317/v471 and rerun property lookup plus Samsung registration proof",
        "host": collect_host_metadata(),
        "inputs": {
            "v295": {"path": v295.get("path"), "present": bool(v295.get("present")), "decision": v295.get("decision"), "pass": v295.get("pass")},
            "v470": {"path": v470.get("path"), "present": bool(v470.get("present")), "decision": v470.get("decision")},
            "android_getprop": str(repo_path(args.android_getprop)),
        },
        "model": {
            "scope": "host-only extended private /dev/__properties__ layout",
            "device_commands_executed": False,
            "runtime_files_installed": False,
            "property_count": len(seeds),
            "context_count": len(by_context),
            "layout_root": str(PROP_ROOT),
        },
        "seeds": [asdict(seed) for seed in seeds],
        "mappings": [asdict(mapping) for mapping in mappings],
        "files": [asdict(file) for file in files],
        "checks": [asdict(check) for check in checks],
        "blocked_actions": [
            "install generated layout on device",
            "bind mount generated layout over global /dev/__properties__",
            "create /dev/socket/property_service",
            "property mutation or setprop-like writes",
            "start service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    seed_rows = [[item["key"], item["value"], item["source"]] for item in manifest["seeds"]]
    mapping_rows = [
        [item["key"], item["context"], item["prop_type"], item["match_kind"], f"{item['source']}:{item['line_number']}"]
        for item in manifest["mappings"]
    ]
    file_rows = [[item["role"], item["relative_path"], str(item["bytes"]), item["sha256"][:16]] for item in manifest["files"]]
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"][:4])] for item in manifest["checks"]]
    return "\n".join([
        "# V471 Extended Private Property Runtime Overlay Dry-run",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Seeds",
        "",
        markdown_table(["key", "value", "source"], seed_rows),
        "",
        "## Mappings",
        "",
        markdown_table(["key", "context", "type", "match", "source"], mapping_rows),
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
