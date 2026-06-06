#!/usr/bin/env python3
"""V858 pm-service/private property context delta classifier.

This host-only classifier extends the V535 private `/dev/__properties__` model
with the `pm-service`/`pm-proxy` property keys observed in V857.  It does not
contact the device, install files, start daemons, scan/connect, or bring Wi-Fi
up.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from typing import Any

import native_property_runtime_overlay_v535 as v535
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v858-pm-service-private-property-runtime")
DEFAULT_V857_MANIFEST = Path("tmp/wifi/v857-pm-service-property-contract-start-only/manifest.json")
DEFAULT_V535_MANIFEST = Path("tmp/wifi/v535-rmt-storage-private-property-runtime/manifest.json")
PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v857-manifest", type=Path, default=DEFAULT_V857_MANIFEST)
    parser.add_argument("--v535-manifest", type=Path, default=DEFAULT_V535_MANIFEST)
    parser.add_argument("--v295-manifest", type=Path, default=v535.DEFAULT_V295)
    parser.add_argument("--v470-analysis", type=Path, default=v535.DEFAULT_V470)
    parser.add_argument("--android-getprop", type=Path, default=v535.DEFAULT_ANDROID_GETPROP)
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


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def v857_evidence_text(v857_manifest: dict[str, Any]) -> tuple[str, str]:
    out_dir = Path(str(v857_manifest.get("out_dir") or ""))
    if not out_dir:
        return "", ""
    evidence_path = out_dir / "native" / "pm-service-property-contract-start-only.txt"
    return read_text(evidence_path), str(evidence_path)


def observed_denials(v857_manifest: dict[str, Any]) -> tuple[list[str], dict[str, int], str]:
    text, source = v857_evidence_text(v857_manifest)
    counts = collections.Counter(PROPERTY_DENIAL_RE.findall(text))
    if not counts:
        report = read_text(Path("docs/reports/NATIVE_INIT_V857_PM_SERVICE_PROPERTY_CONTRACT_2026-05-25.md"))
        counts.update(PROPERTY_DENIAL_RE.findall(report))
        source = "docs/reports/NATIVE_INIT_V857_PM_SERVICE_PROPERTY_CONTRACT_2026-05-25.md"
    return list(counts.keys()), dict(counts), source


def fallback_values(keys: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for key in keys:
        values[key] = ""
    return values


def mapping_by_key(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("key")): item
        for item in manifest.get("mappings", [])
        if isinstance(item, dict) and item.get("key")
    }


def seed_by_key(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("key")): item
        for item in manifest.get("seeds", [])
        if isinstance(item, dict) and item.get("key")
    }


def build_v858_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v857 = load_json(args.v857_manifest)
    v535_manifest = load_json(args.v535_manifest)
    keys, counts, source = observed_denials(v857)
    original_keys = v535.WIFI_COMPANION_OBSERVED_KEYS
    original_fallbacks = dict(v535.RMT_STORAGE_FALLBACK_VALUES)
    try:
        v535.WIFI_COMPANION_OBSERVED_KEYS = tuple(dict.fromkeys(original_keys + tuple(keys)))
        v535.RMT_STORAGE_FALLBACK_VALUES.update(fallback_values(keys))
        manifest = v535._with_rmt_keys(args, store)
    finally:
        v535.WIFI_COMPANION_OBSERVED_KEYS = original_keys
        v535.RMT_STORAGE_FALLBACK_VALUES.clear()
        v535.RMT_STORAGE_FALLBACK_VALUES.update(original_fallbacks)

    mappings = mapping_by_key(manifest)
    seeds = seed_by_key(manifest)
    old_mappings = mapping_by_key(v535_manifest)
    missing_mapping = [key for key in keys if key not in mappings or mappings[key].get("status") != "pass"]
    missing_seed = [key for key in keys if key not in seeds]
    already_in_v535 = [key for key in keys if key in old_mappings and old_mappings[key].get("status") == "pass"]
    newly_covered = [key for key in keys if key in mappings and key not in already_in_v535]
    pass_ok = (
        bool(manifest.get("pass"))
        and bool(keys)
        and not missing_mapping
        and not missing_seed
        and bool(v857.get("pass"))
    )

    manifest["cycle"] = "v858"
    manifest["decision"] = (
        "v858-pm-service-private-property-runtime-ready"
        if pass_ok
        else "v858-pm-service-private-property-runtime-blocked"
    )
    manifest["pass"] = pass_ok
    manifest["reason"] = (
        "V857 pm-service/pm-proxy property denials mapped into a private property runtime layout"
        if pass_ok
        else (
            f"v857_pass={bool(v857.get('pass'))} residual_keys={len(keys)} "
            f"missing_mapping={missing_mapping} missing_seed={missing_seed}"
        )
    )
    manifest["next_step"] = (
        "deploy the V858 property delta and rerun pm-service property-contract start-only with the same hard gates"
        if pass_ok
        else "fix V858 property mapping before any live replay"
    )
    model = manifest.setdefault("model", {})
    model["scope"] = "host-only V857 pm-service/pm-proxy residual private /dev/__properties__ layout"
    model["v857_residual_key_count"] = len(keys)
    model["v857_residual_total_denials"] = sum(counts.values())
    manifest["inputs"]["v857"] = {
        "path": v857.get("path"),
        "present": bool(v857.get("present")),
        "decision": v857.get("decision"),
        "pass": bool(v857.get("pass")),
        "evidence_source": source,
    }
    manifest["inputs"]["v535"] = {
        "path": v535_manifest.get("path"),
        "present": bool(v535_manifest.get("present")),
        "decision": v535_manifest.get("decision"),
        "pass": bool(v535_manifest.get("pass")),
    }
    manifest["v857_residual_keys"] = keys
    manifest["v857_residual_counts"] = counts
    manifest["v857_missing_mapping"] = missing_mapping
    manifest["v857_missing_seed"] = missing_seed
    manifest["v857_already_in_v535"] = already_in_v535
    manifest["v857_newly_covered"] = newly_covered
    manifest["pm_service_observed_keys"] = list(dict.fromkeys((manifest.get("rmt_storage_observed_keys") or []) + keys))
    manifest["blocked_actions"] = [
        "install generated layout on device",
        "bind mount generated layout over global /dev/__properties__",
        "create global or persistent /dev/socket/property_service",
        "property mutation or setprop-like writes",
        "start mdm_helper, ks, service-manager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image or partition write",
    ]
    manifest["device_commands_executed"] = False
    manifest["device_mutations"] = False
    manifest["daemon_start_executed"] = False
    manifest["wifi_hal_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    keys = manifest.get("v857_residual_keys") or []
    counts = manifest.get("v857_residual_counts") or {}
    seed_lookup = seed_by_key(manifest)
    mapping_lookup = mapping_by_key(manifest)
    rows = [
        [
            key,
            str(counts.get(key, 0)),
            str((mapping_lookup.get(key) or {}).get("context", "")),
            str((mapping_lookup.get(key) or {}).get("prop_type", "")),
            str((mapping_lookup.get(key) or {}).get("match_kind", "")),
            str((seed_lookup.get(key) or {}).get("source", "")),
            "yes" if key in set(manifest.get("v857_newly_covered") or []) else "no",
        ]
        for key in keys
    ]
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest.get("checks", [])]
    return "\n".join([
        "# V858 pm-service Private Property Runtime Delta",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_count: `{manifest['model']['property_count']}`",
        f"- context_count: `{manifest['model']['context_count']}`",
        f"- residual_key_count: `{manifest['model']['v857_residual_key_count']}`",
        f"- residual_total_denials: `{manifest['model']['v857_residual_total_denials']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## V857 Residual Mappings",
        "",
        markdown_table(["key", "count", "context", "type", "match", "seed_source", "new"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], check_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_v858_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
