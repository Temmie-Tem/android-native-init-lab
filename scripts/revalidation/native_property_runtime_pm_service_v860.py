#!/usr/bin/env python3
"""V860 pm-service property superset runtime classifier.

This host-only classifier builds a single private `/dev/__properties__` layout
that preserves the V858 `pm-service`/`pm-proxy` keys and adds the V859 newly
exposed service-manager/log property keys.  When V677 evidence is present, its
broader V676 residual set is included as a regression guard.

It does not contact the device, install files, start daemons, scan/connect, or
bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_property_runtime_overlay_v535 as v535
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v860-pm-service-property-superset-runtime")
DEFAULT_V858_LAYOUT = Path("tmp/wifi/v858-pm-service-private-property-runtime/manifest.json")
DEFAULT_V859_REPLAY = Path("tmp/wifi/v859-pm-service-property-delta-replay-r2/manifest.json")
DEFAULT_V677_LAYOUT = Path("tmp/wifi/v677-v676-residual-private-property-runtime/manifest.json")
DEFAULT_V535_MANIFEST = Path("tmp/wifi/v535-rmt-storage-private-property-runtime/manifest.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v858-layout", type=Path, default=DEFAULT_V858_LAYOUT)
    parser.add_argument("--v859-replay", type=Path, default=DEFAULT_V859_REPLAY)
    parser.add_argument("--v677-layout", type=Path, default=DEFAULT_V677_LAYOUT)
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


def ordered_unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if item))


def fallback_values(keys: list[str]) -> dict[str, str]:
    values = {key: "" for key in keys}
    values.setdefault("ro.boot.product.hardware.sku", "")
    values.setdefault("ro.boot.product.vendor.sku", "")
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


def v859_new_keys(v859_replay: dict[str, Any]) -> tuple[list[str], dict[str, int]]:
    property_denials = ((v859_replay.get("analysis") or {}).get("property_denials") or {})
    keys = [str(key) for key in property_denials.get("new_after_v858") or []]
    counts = {
        str(key): int(value)
        for key, value in (property_denials.get("counts") or {}).items()
        if key in set(keys)
    }
    return keys, counts


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v858_layout = load_json(args.v858_layout)
    v859_replay = load_json(args.v859_replay)
    v677_layout = load_json(args.v677_layout)
    v535_manifest = load_json(args.v535_manifest)

    v858_keys = [str(key) for key in v858_layout.get("v857_residual_keys", [])]
    v859_keys, v859_counts = v859_new_keys(v859_replay)
    v677_keys = [str(key) for key in v677_layout.get("v676_residual_keys", [])] if v677_layout.get("present") else []
    superset_keys = ordered_unique(v858_keys + v859_keys + v677_keys)

    original_keys = v535.WIFI_COMPANION_OBSERVED_KEYS
    original_fallbacks = dict(v535.RMT_STORAGE_FALLBACK_VALUES)
    try:
        v535.WIFI_COMPANION_OBSERVED_KEYS = tuple(dict.fromkeys(original_keys + tuple(superset_keys)))
        v535.RMT_STORAGE_FALLBACK_VALUES.update(fallback_values(superset_keys))
        manifest = v535._with_rmt_keys(args, store)
    finally:
        v535.WIFI_COMPANION_OBSERVED_KEYS = original_keys
        v535.RMT_STORAGE_FALLBACK_VALUES.clear()
        v535.RMT_STORAGE_FALLBACK_VALUES.update(original_fallbacks)

    mappings = mapping_by_key(manifest)
    seeds = seed_by_key(manifest)
    old_v535_mappings = mapping_by_key(v535_manifest)
    v858_target_set = set(v858_keys)
    v859_new_set = set(v859_keys)
    v677_set = set(v677_keys)
    missing_mapping = [
        key
        for key in superset_keys
        if key not in mappings or mappings[key].get("status") != "pass"
    ]
    missing_seed = [key for key in superset_keys if key not in seeds]
    already_in_v535 = [
        key
        for key in superset_keys
        if key in old_v535_mappings and old_v535_mappings[key].get("status") == "pass"
    ]
    pass_ok = (
        bool(manifest.get("pass"))
        and bool(superset_keys)
        and not missing_mapping
        and not missing_seed
        and v858_layout.get("decision") == "v858-pm-service-private-property-runtime-ready"
        and v859_replay.get("decision") == "v859-v858-target-denials-removed-new-property-gap"
    )

    manifest["cycle"] = "v860"
    manifest["decision"] = (
        "v860-pm-service-property-superset-runtime-ready"
        if pass_ok
        else "v860-pm-service-property-superset-runtime-blocked"
    )
    manifest["pass"] = pass_ok
    manifest["reason"] = (
        "V858 target keys and V859 newly exposed property keys mapped into one private property runtime superset"
        if pass_ok
        else (
            f"v858_decision={v858_layout.get('decision')} v859_decision={v859_replay.get('decision')} "
            f"superset_keys={len(superset_keys)} missing_mapping={missing_mapping} missing_seed={missing_seed}"
        )
    )
    manifest["next_step"] = (
        "deploy the V860 superset delta and rerun bounded pm-service/pm-proxy start-only replay"
        if pass_ok
        else "fix V860 property mapping before any live deploy"
    )
    model = manifest.setdefault("model", {})
    model["scope"] = "host-only V858+V859+optional-V677 private /dev/__properties__ superset layout"
    model["v858_key_count"] = len(v858_keys)
    model["v859_new_key_count"] = len(v859_keys)
    model["v677_regression_key_count"] = len(v677_keys)
    model["v860_superset_key_count"] = len(superset_keys)
    manifest["inputs"]["v858_layout"] = {
        "path": v858_layout.get("path"),
        "present": bool(v858_layout.get("present")),
        "decision": v858_layout.get("decision"),
        "pass": bool(v858_layout.get("pass")),
    }
    manifest["inputs"]["v859_replay"] = {
        "path": v859_replay.get("path"),
        "present": bool(v859_replay.get("present")),
        "decision": v859_replay.get("decision"),
        "pass": bool(v859_replay.get("pass")),
    }
    manifest["inputs"]["v677_layout"] = {
        "path": v677_layout.get("path"),
        "present": bool(v677_layout.get("present")),
        "decision": v677_layout.get("decision"),
        "pass": bool(v677_layout.get("pass")),
    }
    manifest["inputs"]["v535"] = {
        "path": v535_manifest.get("path"),
        "present": bool(v535_manifest.get("present")),
        "decision": v535_manifest.get("decision"),
        "pass": bool(v535_manifest.get("pass")),
    }
    manifest["v858_target_keys"] = v858_keys
    manifest["v859_new_keys"] = v859_keys
    manifest["v859_new_counts"] = v859_counts
    manifest["v677_regression_keys"] = v677_keys
    manifest["v860_superset_keys"] = superset_keys
    manifest["v860_missing_mapping"] = missing_mapping
    manifest["v860_missing_seed"] = missing_seed
    manifest["v860_already_in_v535"] = already_in_v535
    manifest["v860_v859_keys_already_in_v677"] = [key for key in v859_keys if key in v677_set]
    manifest["v860_key_origins"] = {
        key: {
            "v858": key in v858_target_set,
            "v859": key in v859_new_set,
            "v677": key in v677_set,
        }
        for key in superset_keys
    }
    manifest["rmt_storage_observed_keys"] = ordered_unique(
        [str(key) for key in manifest.get("rmt_storage_observed_keys", [])] + superset_keys
    )
    manifest["pm_service_observed_keys"] = superset_keys
    manifest["blocked_actions"] = [
        "install generated layout on device outside the explicit V860 incremental deployer",
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
    mappings = mapping_by_key(manifest)
    seeds = seed_by_key(manifest)
    counts = manifest.get("v859_new_counts") or {}
    origin_lookup = manifest.get("v860_key_origins") or {}
    rows = []
    for key in manifest.get("v860_superset_keys") or []:
        origins = origin_lookup.get(key) or {}
        rows.append([
            key,
            "yes" if origins.get("v858") else "no",
            "yes" if origins.get("v859") else "no",
            "yes" if origins.get("v677") else "no",
            str(counts.get(key, "")),
            str((mappings.get(key) or {}).get("context", "")),
            str((mappings.get(key) or {}).get("prop_type", "")),
            str((seeds.get(key) or {}).get("source", "")),
        ])
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest.get("checks", [])]
    return "\n".join([
        "# V860 pm-service Property Superset Runtime",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_count: `{manifest['model']['property_count']}`",
        f"- context_count: `{manifest['model']['context_count']}`",
        f"- v858_key_count: `{manifest['model']['v858_key_count']}`",
        f"- v859_new_key_count: `{manifest['model']['v859_new_key_count']}`",
        f"- v677_regression_key_count: `{manifest['model']['v677_regression_key_count']}`",
        f"- v860_superset_key_count: `{manifest['model']['v860_superset_key_count']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Superset Mappings",
        "",
        markdown_table(["key", "v858", "v859", "v677", "v859_count", "context", "type", "seed_source"], rows),
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
    manifest = build_manifest(args, store)
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
