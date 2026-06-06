#!/usr/bin/env python3
"""V677 V676-residual private property runtime overlay dry-run.

This extends the V535 private `/dev/__properties__` model with the residual
property keys observed in the V676 V535-property Android userspace-order live
proof. It is host-only: it does not install files on the device, bind over
global `/dev/__properties__`, create property-service sockets, start daemons,
or bring Wi-Fi up.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v677-v676-residual-private-property-runtime")
DEFAULT_V676_MANIFEST = Path("tmp/wifi/v676-v535-property-android-order-orchestrated-live/manifest.json")
PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v676-manifest", type=Path, default=DEFAULT_V676_MANIFEST)
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


def residual_keys(v676: dict[str, Any]) -> tuple[list[str], dict[str, int], str]:
    arm_path = Path(str(((v676.get("arm_v676") or {}).get("manifest") or "")))
    helper_text = ""
    if arm_path.exists():
        arm = load_json(arm_path)
        helper_text = str((arm.get("live") or {}).get("helper_stdout_stderr") or "")
    counts = collections.Counter(PROPERTY_DENIAL_RE.findall(helper_text))
    if not counts:
        for key, count in (((v676.get("arm_v676") or {}).get("property_surface") or {}).get("property_denial_top") or []):
            counts[str(key)] = int(count)
    return list(counts.keys()), dict(counts), str(arm_path)


def fallback_values(keys: list[str]) -> dict[str, str]:
    values = {key: "" for key in keys}
    values.setdefault("ro.boot.product.hardware.sku", "")
    values.setdefault("ro.boot.product.vendor.sku", "")
    return values


def build_v677_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v676 = load_json(args.v676_manifest)
    keys, counts, arm_path = residual_keys(v676)
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

    observed = list(dict.fromkeys((manifest.get("rmt_storage_observed_keys") or []) + keys))
    mappings = {
        str(item.get("key")): item
        for item in manifest.get("mappings", [])
        if isinstance(item, dict) and item.get("key")
    }
    seeds = {
        str(item.get("key")): item
        for item in manifest.get("seeds", [])
        if isinstance(item, dict) and item.get("key")
    }
    missing_mapping = [key for key in keys if key not in mappings or mappings[key].get("status") != "pass"]
    missing_seed = [key for key in keys if key not in seeds]
    pass_ok = bool(manifest.get("pass")) and not missing_mapping and not missing_seed and bool(keys)

    manifest["decision"] = (
        "v677-v676-residual-private-property-runtime-ready"
        if pass_ok
        else "v677-v676-residual-private-property-runtime-blocked"
    )
    manifest["pass"] = pass_ok
    manifest["reason"] = (
        "V676 residual private property layout generated and roundtripped"
        if pass_ok
        else f"missing_mapping={missing_mapping} missing_seed={missing_seed} residual_keys={len(keys)}"
    )
    manifest["next_step"] = (
        "deploy under a versioned V677 property root and rerun V676-style Android userspace-order proof"
        if pass_ok
        else "fix V677 property mapping before live deploy"
    )
    model = manifest.setdefault("model", {})
    model["scope"] = "host-only V676 residual private /dev/__properties__ layout"
    model["v676_residual_key_count"] = len(keys)
    model["v676_residual_total_denials"] = sum(counts.values())
    manifest["cycle"] = "v677"
    manifest["inputs"]["v676"] = {
        "path": v676.get("path"),
        "present": bool(v676.get("present")),
        "decision": v676.get("decision"),
        "pass": v676.get("pass"),
        "arm_manifest": arm_path,
    }
    manifest["v676_residual_keys"] = keys
    manifest["v676_residual_counts"] = counts
    manifest["v676_missing_mapping"] = missing_mapping
    manifest["v676_missing_seed"] = missing_seed
    manifest["rmt_storage_observed_keys"] = observed
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    keys = manifest.get("v676_residual_keys") or []
    counts = manifest.get("v676_residual_counts") or {}
    seed_by_key = {
        item["key"]: item
        for item in manifest.get("seeds", [])
        if isinstance(item, dict) and item.get("key") in keys
    }
    mapping_by_key = {
        item["key"]: item
        for item in manifest.get("mappings", [])
        if isinstance(item, dict) and item.get("key") in keys
    }
    rows = [
        [
            key,
            str(counts.get(key, 0)),
            str((mapping_by_key.get(key) or {}).get("context", "")),
            str((mapping_by_key.get(key) or {}).get("prop_type", "")),
            str((seed_by_key.get(key) or {}).get("source", "")),
            "set" if (seed_by_key.get(key) or {}).get("value") else "empty",
        ]
        for key in keys
    ]
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest.get("checks", [])]
    return "\n".join([
        "# V677 V676-residual Private Property Runtime Overlay Dry-run",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_count: `{manifest['model']['property_count']}`",
        f"- context_count: `{manifest['model']['context_count']}`",
        f"- residual_key_count: `{manifest['model']['v676_residual_key_count']}`",
        f"- residual_total_denials: `{manifest['model']['v676_residual_total_denials']}`",
        "",
        "## V676 Residual Mappings",
        "",
        markdown_table(["key", "count", "context", "type", "seed_source", "value"], rows),
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
    manifest = build_v677_manifest(args, store)
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
