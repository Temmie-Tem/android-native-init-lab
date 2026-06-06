#!/usr/bin/env python3
"""Compare static native property snapshot with Android-boot property capture."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v298-property-baseline-compare")
DEFAULT_V295_MANIFEST = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json")
DEFAULT_V297_MANIFEST = Path("tmp/wifi/v297-android-property-capture-android/manifest.json")
REQUIRED_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)


@dataclass
class PropertyCompare:
    key: str
    static_state: str
    android_state: str
    static_value: str
    android_value: str
    same: bool
    implication: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295_MANIFEST)
    parser.add_argument("--v297-manifest", type=Path, default=DEFAULT_V297_MANIFEST)
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


def state(value: Any) -> str:
    return "present" if isinstance(value, str) and value != "" else "missing"


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


def compare_required(static_required: dict[str, str], android_required: dict[str, str]) -> list[PropertyCompare]:
    rows: list[PropertyCompare] = []
    for key in REQUIRED_KEYS:
        static_value = static_required.get(key, "")
        android_value = android_required.get(key, "")
        static_state = state(static_value)
        android_state = state(android_value)
        if android_state == "missing":
            implication = "block shim design until Android capture provides this key"
        elif static_state == "missing":
            implication = "candidate shim value must come from Android capture"
        elif static_value == android_value:
            implication = "static value matches Android capture"
        else:
            implication = "static value differs from Android capture; prefer Android value"
        rows.append(
            PropertyCompare(
                key=key,
                static_state=static_state,
                android_state=android_state,
                static_value=static_value,
                android_value=android_value,
                same=static_state == "present" and android_state == "present" and static_value == android_value,
                implication=implication,
            )
        )
    return rows


def decide(v295: dict[str, Any], v297: dict[str, Any], comparisons: list[PropertyCompare]) -> tuple[str, bool, str]:
    if not v295.get("present") or v295.get("decision") != "property-snapshot-model-ready":
        return "property-baseline-compare-static-missing", False, "v295 static property snapshot is missing or not ready"
    if not v297.get("present") or v297.get("decision") == "android-property-capture-waiting-for-android":
        return "property-baseline-compare-waiting-for-android", True, "Android property capture is not available yet"
    if v297.get("decision") != "android-property-capture-pass":
        return "property-baseline-compare-android-incomplete", False, f"v297 decision is {v297.get('decision', 'missing')}"
    missing_android = [row.key for row in comparisons if row.android_state == "missing"]
    if missing_android:
        return "property-baseline-compare-android-incomplete", False, "Android capture is missing required keys: " + ", ".join(missing_android)
    return "property-baseline-compare-ready", True, "Android baseline can seed next read-only property shim design"


def build_model(v295: dict[str, Any], v297: dict[str, Any]) -> dict[str, Any]:
    static_required = required_from_v295(v295)
    android_required = required_from_v297(v297)
    comparisons = compare_required(static_required, android_required)
    decision, pass_ok, reason = decide(v295, v297, comparisons)
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
                "adb_state": v297.get("adb_state"),
            },
        },
        "counts": {
            "static_property_count": v295.get("snapshot", {}).get("property_count") if isinstance(v295.get("snapshot"), dict) else None,
            "static_wifi_property_count": v295.get("snapshot", {}).get("wifi_property_count") if isinstance(v295.get("snapshot"), dict) else None,
            "android_property_count": v297.get("property_count"),
            "android_wifi_related_property_count": v297.get("wifi_related_property_count"),
        },
        "required_static": static_required,
        "required_android": android_required,
        "comparisons": [asdict(row) for row in comparisons],
        "blocked_actions": [
            "create /dev/__properties__",
            "create /dev/socket/property_service",
            "start servicemanager",
            "start hwservicemanager",
            "start Wi-Fi HAL or wificond",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["key"],
            item["static_state"],
            item["android_state"],
            "<same>" if item["same"] else "<diff-or-missing>",
            item["implication"],
        ]
        for item in manifest["comparisons"]
    ]
    input_rows = [
        ["v295", str(manifest["inputs"]["v295"]["present"]), str(manifest["inputs"]["v295"]["decision"]), str(manifest["inputs"]["v295"]["path"])],
        ["v297", str(manifest["inputs"]["v297"]["present"]), str(manifest["inputs"]["v297"]["decision"]), str(manifest["inputs"]["v297"]["path"])],
    ]
    return "\n".join(
        [
            "# v298 Property Baseline Compare",
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
            "## Required Property Comparison",
            "",
            markdown_table(["key", "static", "android", "state", "implication"], rows),
            "",
            "## Blocked Actions",
            "",
            *[f"- {item}" for item in manifest["blocked_actions"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v295 = load_manifest(args.v295_manifest)
    v297 = load_manifest(args.v297_manifest)
    manifest = build_model(v295, v297)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
