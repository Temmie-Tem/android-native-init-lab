#!/usr/bin/env python3
"""Build a read-only property shim seed model from static and Android baselines."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v301-property-shim-seed")
DEFAULT_V295_MANIFEST = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json")
DEFAULT_V297_MANIFEST = Path("tmp/wifi/v297-android-property-capture-android/manifest.json")
DEFAULT_V298_MANIFEST = Path("tmp/wifi/v298-property-baseline-compare-android/manifest.json")
REQUIRED_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)


@dataclass
class SeedEntry:
    key: str
    value: str
    source: str
    state: str
    reason: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295_MANIFEST)
    parser.add_argument("--v297-manifest", type=Path, default=DEFAULT_V297_MANIFEST)
    parser.add_argument("--v298-manifest", type=Path, default=DEFAULT_V298_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def safe_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def required_from_v295(manifest: dict[str, Any]) -> dict[str, str]:
    snapshot = manifest.get("snapshot", {}) if isinstance(manifest.get("snapshot"), dict) else {}
    required = snapshot.get("required", {}) if isinstance(snapshot.get("required"), dict) else {}
    return {key: safe_value(required.get(key, "")) for key in REQUIRED_KEYS}


def required_from_v297(manifest: dict[str, Any]) -> dict[str, str]:
    required = manifest.get("required", {}) if isinstance(manifest.get("required"), dict) else {}
    return {key: safe_value(required.get(key, "")) for key in REQUIRED_KEYS}


def build_seed(static_required: dict[str, str], android_required: dict[str, str]) -> list[SeedEntry]:
    entries: list[SeedEntry] = []
    for key in REQUIRED_KEYS:
        android_value = android_required.get(key, "")
        static_value = static_required.get(key, "")
        if android_value:
            if static_value and static_value == android_value:
                entries.append(SeedEntry(key, android_value, "static+android-match", "ready", "static and Android values match"))
            else:
                entries.append(SeedEntry(key, android_value, "android-capture", "ready", "Android runtime capture is authoritative"))
        elif static_value:
            entries.append(SeedEntry(key, static_value, "static-only", "blocked", "static value exists but Android runtime capture is missing"))
        else:
            entries.append(SeedEntry(key, "", "missing", "blocked", "required key missing from static and Android evidence"))
    return entries


def decide(v295: dict[str, Any], v297: dict[str, Any], v298: dict[str, Any], seed: list[SeedEntry]) -> tuple[str, bool, str]:
    if not v295.get("present") or not v297.get("present") or not v298.get("present"):
        return "property-shim-seed-input-missing", False, "one or more input manifests are missing"
    if v297.get("decision") == "android-property-capture-waiting-for-android" or v298.get("decision") == "property-baseline-compare-waiting-for-android":
        return "property-shim-seed-waiting-for-android", True, "Android property capture is not available yet"
    if v297.get("decision") != "android-property-capture-pass" or v298.get("decision") != "property-baseline-compare-ready":
        return "property-shim-seed-blocked-missing-required", False, f"input decisions are v297={v297.get('decision')} v298={v298.get('decision')}"
    blocked = [entry.key for entry in seed if entry.state != "ready"]
    if blocked:
        return "property-shim-seed-blocked-missing-required", False, "blocked required keys: " + ", ".join(blocked)
    return "property-shim-seed-ready", True, "all selected seed keys have Android-backed values"


def render_seed(seed: list[SeedEntry]) -> dict[str, Any]:
    return {
        "schema": "a90-property-shim-seed-v1",
        "policy": "read-only-model-only",
        "entries": [asdict(entry) for entry in seed],
        "blocked_actions": [
            "create /dev/__properties__",
            "create /dev/socket/property_service",
            "start servicemanager",
            "start hwservicemanager",
            "start Wi-Fi HAL or wificond",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def build_manifest(v295: dict[str, Any], v297: dict[str, Any], v298: dict[str, Any]) -> dict[str, Any]:
    static_required = required_from_v295(v295)
    android_required = required_from_v297(v297)
    seed = build_seed(static_required, android_required)
    decision, pass_ok, reason = decide(v295, v297, v298, seed)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "inputs": {
            "v295": {
                "path": v295.get("path"),
                "present": bool(v295.get("present")),
                "decision": v295.get("decision"),
            },
            "v297": {
                "path": v297.get("path"),
                "present": bool(v297.get("present")),
                "decision": v297.get("decision"),
            },
            "v298": {
                "path": v298.get("path"),
                "present": bool(v298.get("present")),
                "decision": v298.get("decision"),
            },
        },
        "required_static": static_required,
        "required_android": android_required,
        "seed": render_seed(seed),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    input_rows = [
        ["v295", str(manifest["inputs"]["v295"]["present"]), str(manifest["inputs"]["v295"]["decision"]), str(manifest["inputs"]["v295"]["path"])],
        ["v297", str(manifest["inputs"]["v297"]["present"]), str(manifest["inputs"]["v297"]["decision"]), str(manifest["inputs"]["v297"]["path"])],
        ["v298", str(manifest["inputs"]["v298"]["present"]), str(manifest["inputs"]["v298"]["decision"]), str(manifest["inputs"]["v298"]["path"])],
    ]
    seed_rows = [
        [entry["key"], entry["state"], entry["source"], "<set>" if entry["value"] else "missing", entry["reason"]]
        for entry in manifest["seed"]["entries"]
    ]
    return "\n".join(
        [
            "# v301 Property Shim Seed",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "present", "decision", "path"], input_rows),
            "",
            "## Seed Entries",
            "",
            markdown_table(["key", "state", "source", "value", "reason"], seed_rows),
            "",
            "## Blocked Actions",
            "",
            *[f"- {item}" for item in manifest["seed"]["blocked_actions"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v295 = load_manifest(args.v295_manifest)
    v297 = load_manifest(args.v297_manifest)
    v298 = load_manifest(args.v298_manifest)
    manifest = build_manifest(v295, v297, v298)
    store.write_json("manifest.json", manifest)
    store.write_json("seed.json", manifest["seed"])
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
