#!/usr/bin/env python3
"""Classify local tmp artifacts without moving or deleting them."""

from __future__ import annotations

import argparse
import json
import stat
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

from a90harness.evidence import (
    DOC_ARTIFACT_ROOT,
    REPO_ROOT,
    TMP_LOG_ROOT,
    WIFI_ARTIFACT_KINDS,
    WIFI_TMP_ROOT,
    write_private_json,
    write_public_json,
    write_public_text,
)


TMP_ROOT = REPO_ROOT / "tmp"
DEFAULT_JSON = DOC_ARTIFACT_ROOT / "tmp-artifact-inventory-summary.json"
DEFAULT_MD = DOC_ARTIFACT_ROOT / "TMP_ARTIFACT_INVENTORY_SUMMARY.md"
DEFAULT_FULL_JSON = TMP_LOG_ROOT / "archive" / "tmp-artifact-folder-catalog-full.json"
STRUCTURED_WIFI_ROOTS = set(WIFI_ARTIFACT_KINDS)
ROOT_TOOL_EVIDENCE_DIRS = {
    "cgroup-psi",
    "debug-observability",
    "diag",
    "diag-batch4-test",
    "kernel-capability",
    "kernel-config",
    "kerneldiag",
    "kernelinv",
    "netfilter",
    "pstore",
    "sensormap",
    "tracefs",
    "watchdog",
    "wififeas",
    "wifiinv",
}
WIFI_SURFACE_EVIDENCE_PREFIXES = (
    "device-check-",
    "final-state-",
    "wifi-native-cnss-sysfs-",
    "wifi-native-driver-surface-",
)
WIFI_PROBE_EVIDENCE_NAMES = {
    "arm64-wpa-pkg-probe",
    "cnss-debugdata",
    "deploy-speed-plan-check",
    "helper-sha-probe",
}
PRESERVE = "preserve"
PRUNE_BUILD_PRODUCTS = "prune-build-products"
COMPRESS_OR_ROTATE = "compress-or-rotate"
REVIEW = "review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print inventory JSON")
    parser.add_argument("--write-public", action="store_true", help="write docs/artifacts summaries")
    parser.add_argument("--top", type=int, default=20, help="top entries per section")
    parser.add_argument("--root", type=Path, default=TMP_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--include-full", action="store_true", help="include all classified top-level entries in JSON output")
    parser.add_argument("--write-full-private", action="store_true", help="write full classified catalog under tmp/logs/archive")
    parser.add_argument("--full-json-out", type=Path, default=DEFAULT_FULL_JSON)
    return parser.parse_args()


def path_size(path: Path) -> int:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return 0
    if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
        return info.st_size
    total = 0
    for child in path.rglob("*"):
        try:
            total += child.lstat().st_size
        except FileNotFoundError:
            pass
    return total


def modified_at(path: Path) -> str:
    try:
        timestamp = path.lstat().st_mtime
    except FileNotFoundError:
        timestamp = 0
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def direct_children(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.iterdir(), key=lambda item: str(item))


def classify_wifi_entry(path: Path) -> tuple[str, str]:
    name = path.name
    if name in STRUCTURED_WIFI_ROOTS:
        return f"wifi-structured-{name}", PRESERVE
    if name == ".wifi-test.env":
        return "wifi-private-local-config", PRESERVE
    if name.startswith("unpack-"):
        return "wifi-unpacked-build-product", PRUNE_BUILD_PRODUCTS
    if name.startswith("a90-ncm-transport-smoke"):
        return "wifi-benchmark", PRUNE_BUILD_PRODUCTS
    if name == "commit-verify":
        return "wifi-build-cache", PRUNE_BUILD_PRODUCTS
    if name.startswith("v2167-connect-dhcp-google-ping-handoff"):
        return "wifi-connect-evidence", PRESERVE
    if name.startswith(WIFI_SURFACE_EVIDENCE_PREFIXES) or name in WIFI_PROBE_EVIDENCE_NAMES:
        return "wifi-probe-evidence", PRESERVE
    if name.startswith("state-check-"):
        return "wifi-probe-evidence", PRESERVE
    if name.startswith((".last-", ".latest-")) or name.startswith(("latest-", "current-")):
        return "wifi-legacy-marker", PRESERVE
    if name.endswith((".objdump.txt", ".txt", ".json")):
        return "wifi-static-analysis", PRESERVE
    if name.startswith(("cnss_", "cnss-")):
        return "wifi-static-analysis", PRESERVE
    if "build" in name or "source" in name or "extract" in name or "cache" in name:
        return "wifi-build-cache", PRUNE_BUILD_PRODUCTS
    if "-test-boot" in name:
        return "wifi-test-boot-evidence", PRUNE_BUILD_PRODUCTS
    if "host-only" in name or "classifier" in name or "preflight" in name:
        return "wifi-host-analysis", PRESERVE
    if name.startswith("v"):
        return "wifi-run-evidence", PRESERVE
    return "wifi-other", REVIEW


def classify_tmp_entry(path: Path) -> tuple[str, str]:
    name = path.name
    if path == WIFI_TMP_ROOT:
        return "wifi-artifact-root", PRESERVE
    if path == TMP_LOG_ROOT:
        return "root-structured-log-root", PRESERVE
    if name in ROOT_TOOL_EVIDENCE_DIRS:
        return "root-tool-evidence", PRESERVE
    if name in {"xfer-http-test"}:
        return "root-benchmark", PRUNE_BUILD_PRODUCTS
    if name in {"worktree-cleanup", "unit"}:
        return "root-tool-evidence", PRESERVE
    if name.startswith("bridge-") and name.endswith(".log.gz"):
        return "root-bridge-log-compressed", PRESERVE
    if name.startswith("bridge-") and name.endswith(".log"):
        return "root-bridge-log", COMPRESS_OR_ROTATE
    if name.startswith("bridge-") and name.endswith(".pid"):
        return "root-bridge-runtime", PRUNE_BUILD_PRODUCTS
    if name.startswith("serial_tcp_bridge-") and name.endswith(".log"):
        return "root-bridge-log", COMPRESS_OR_ROTATE
    if name.startswith("wait-flash-") and name.endswith((".log", ".sh")):
        return "root-flash-helper-evidence", PRESERVE
    if name.startswith("mkbootimg_") and name.endswith(".args"):
        return "root-build-metadata", PRESERVE
    if name.endswith(".so"):
        return "root-vendor-library-extract", PRESERVE
    if name.startswith("a90_") and "_v" in name:
        return "root-build-product", PRUNE_BUILD_PRODUCTS
    if name.startswith("a90-") or name.startswith("v"):
        return "root-legacy-run-evidence", PRESERVE
    if name.startswith("current-") or name.endswith((".txt", ".json", ".out")):
        return "root-legacy-run-evidence", PRESERVE
    if name in {"validation", "verify", "security", "host", "source"}:
        return "root-tool-evidence", PRESERVE
    if name in {"inspect-v1571-ramdisk", "diag-src"}:
        return "root-build-inspection", PRUNE_BUILD_PRODUCTS
    return "root-other", REVIEW


def item(path: Path, category: str, action: str) -> dict[str, Any]:
    size = path_size(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        entry_type = "missing"
    else:
        if stat.S_ISDIR(info.st_mode):
            entry_type = "dir"
        elif stat.S_ISREG(info.st_mode):
            entry_type = "file"
        elif stat.S_ISLNK(info.st_mode):
            entry_type = "symlink"
        else:
            entry_type = "other"
    child_count = len(direct_children(path)) if path.is_dir() and not path.is_symlink() else 0
    return {
        "path": rel(path),
        "type": entry_type,
        "category": category,
        "recommended_action": action,
        "bytes": size,
        "mib": round(size / 1024 / 1024, 3),
        "children": child_count,
        "modified": modified_at(path),
    }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, dict[str, Any]] = {}
    actions: dict[str, dict[str, Any]] = {}
    for key_name, target in (("category", categories), ("recommended_action", actions)):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in items:
            grouped[str(entry[key_name])].append(entry)
        for key, entries in grouped.items():
            total = sum(int(entry["bytes"]) for entry in entries)
            target[key] = {
                "count": len(entries),
                "bytes": total,
                "mib": round(total / 1024 / 1024, 3),
            }
    return {"categories": categories, "recommended_actions": actions}


def build_inventory(root: Path, top: int, *, include_full: bool = False) -> dict[str, Any]:
    tmp_entries: list[dict[str, Any]] = []
    for path in direct_children(root):
        category, action = classify_tmp_entry(path)
        tmp_entries.append(item(path, category, action))

    wifi_entries: list[dict[str, Any]] = []
    for path in direct_children(WIFI_TMP_ROOT):
        category, action = classify_wifi_entry(path)
        wifi_entries.append(item(path, category, action))

    summary_entries = [entry for entry in tmp_entries if entry["path"] != rel(WIFI_TMP_ROOT)] + wifi_entries
    total_bytes = sum(int(entry["bytes"]) for entry in tmp_entries)
    inventory = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "root": rel(root),
        "tmp_total_bytes": total_bytes,
        "tmp_total_mib": round(total_bytes / 1024 / 1024, 3),
        "tmp_entries": len(tmp_entries),
        "wifi_entries": len(wifi_entries),
        "summary": summarize(summary_entries),
        "top_tmp_entries": sorted(tmp_entries, key=lambda entry: int(entry["bytes"]), reverse=True)[:top],
        "top_wifi_entries": sorted(wifi_entries, key=lambda entry: int(entry["bytes"]), reverse=True)[:top],
        "top_review_entries": sorted(
            [entry for entry in summary_entries if entry["recommended_action"] == REVIEW],
            key=lambda entry: int(entry["bytes"]),
            reverse=True,
        )[:top],
    }
    if include_full:
        inventory["tmp_entries_full"] = sorted(tmp_entries, key=lambda entry: str(entry["path"]))
        inventory["wifi_entries_full"] = sorted(wifi_entries, key=lambda entry: str(entry["path"]))
    return inventory


def render_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# Tmp Artifact Inventory Summary",
        "",
        f"- Generated: `{inventory['generated_at']}`",
        f"- Root: `{inventory['root']}`",
        f"- Tmp entries: `{inventory['tmp_entries']}`",
        f"- Wifi entries: `{inventory['wifi_entries']}`",
        f"- Tmp total: `{inventory['tmp_total_mib']} MiB`",
        "",
        "## Classification Taxonomy",
        "",
        "| Axis | Meaning | Default action |",
        "| --- | --- | --- |",
        "| `wifi-connect-evidence` / `wifi-run-evidence` / `wifi-host-analysis` | Evidence and run records | preserve |",
        "| `wifi-probe-evidence` / `wifi-static-analysis` | Small probe outputs, disassembly, marker/status files | preserve |",
        "| `wifi-private-local-config` | Local-only secret/config marker paths | preserve locally; do not copy contents |",
        "| `wifi-test-boot-evidence` | Mixed test-boot dirs; logs preserved, generated binaries pruneable | prune build products only |",
        "| `wifi-unpacked-build-product` | Reproducible unpacked kernel/ramdisk products | prune after explicit review |",
        "| `wifi-build-cache` | Build/extract/cache dirs | prune build products or cache after review |",
        "| `wifi-benchmark` | Transfer benchmark payloads | prune dummy payloads after summary |",
        "| `root-structured-log-root` | New top-level structured logs under `tmp/logs/` | preserve |",
        "| `root-tool-evidence` | Older tool outputs referenced by docs/scripts | preserve until indexed |",
        "| `root-bridge-log` | Large host bridge logs | compress or rotate |",
        "| `root-bridge-log-compressed` | Compressed host bridge logs | preserve |",
        "| `root-legacy-run-evidence` | Older root-level run records | preserve until indexed |",
        "",
        "## By Recommended Action",
        "",
        "| Action | Count | MiB |",
        "| --- | ---: | ---: |",
    ]
    for action, data in sorted(inventory["summary"]["recommended_actions"].items()):
        lines.append(f"| `{action}` | {data['count']} | {data['mib']} |")
    lines.extend(["", "## Top Tmp Entries", "", "| Path | Category | Action | MiB |", "| --- | --- | --- | ---: |"])
    for entry in inventory["top_tmp_entries"]:
        lines.append(
            f"| `{entry['path']}` | `{entry['category']}` | `{entry['recommended_action']}` | {entry['mib']} |"
        )
    lines.extend(["", "## Top Wifi Entries", "", "| Path | Category | Action | MiB |", "| --- | --- | --- | ---: |"])
    for entry in inventory["top_wifi_entries"]:
        lines.append(
            f"| `{entry['path']}` | `{entry['category']}` | `{entry['recommended_action']}` | {entry['mib']} |"
        )
    lines.extend(["", "## Top Review Entries", "", "| Path | Category | Action | MiB |", "| --- | --- | --- | ---: |"])
    for entry in inventory["top_review_entries"]:
        lines.append(
            f"| `{entry['path']}` | `{entry['category']}` | `{entry['recommended_action']}` | {entry['mib']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This is a metadata-only public summary; it does not copy raw logs, firmware, boot images, credentials, or private payloads.",
            "- Cleanup remains separate and dry-run first. This inventory is for classification and review.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    include_full = args.include_full or args.write_full_private
    inventory = build_inventory(args.root, args.top, include_full=include_full)
    if args.write_public:
        public_inventory = {key: value for key, value in inventory.items() if not key.endswith("_full")}
        write_public_json(args.json_out, public_inventory)
        write_public_text(args.md_out, render_markdown(inventory))
    if args.write_full_private:
        write_private_json(args.full_json_out, inventory)
    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.write_public:
        print(render_markdown(inventory), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
