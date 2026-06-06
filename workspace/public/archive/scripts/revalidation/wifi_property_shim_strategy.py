#!/usr/bin/env python3
"""Host-side strategy model for Android property shim planning."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v296-property-shim-strategy")
DEFAULT_V295_MANIFEST = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json")
REQUIRED_RUNTIME_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)
SERVICE_MANAGER_HINT_KEYS = (
    "ro.debuggable",
    "ro.secure",
    "ro.build.version.sdk",
    "ro.vndk.version",
    "ro.product.first_api_level",
    "ro.vendor.build.version.sdk",
)


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(v295: dict[str, Any]) -> tuple[list[Check], dict[str, Any]]:
    checks: list[Check] = []
    snapshot = v295.get("snapshot", {}) if isinstance(v295.get("snapshot"), dict) else {}
    required = snapshot.get("required", {}) if isinstance(snapshot.get("required"), dict) else {}
    required_present = [key for key in REQUIRED_RUNTIME_KEYS if required.get(key)]
    required_missing = [key for key in REQUIRED_RUNTIME_KEYS if not required.get(key)]
    property_count = int(snapshot.get("property_count", 0) or 0)
    context_count = int(snapshot.get("context_line_count", 0) or 0)
    wifi_count = int(snapshot.get("wifi_property_count", 0) or 0)
    props_sample = snapshot.get("wifi_properties_sample", {})

    add_check(
        checks,
        "v295-snapshot-input",
        "present" if v295.get("decision") == "property-snapshot-model-ready" else "missing",
        "info" if v295.get("decision") == "property-snapshot-model-ready" else "blocker",
        f"decision={v295.get('decision', 'missing')}",
        "refresh v295 if property snapshot changed",
    )
    add_check(
        checks,
        "static-property-volume",
        "present" if property_count >= 20 else "partial",
        "info" if property_count >= 20 else "warning",
        f"property_count={property_count}",
        "static properties can seed a lookup table but not a live runtime",
    )
    add_check(
        checks,
        "property-context-volume",
        "present" if context_count >= 20 else "partial",
        "info" if context_count >= 20 else "warning",
        f"context_line_count={context_count}",
        "contexts are available for labels/type planning",
    )
    add_check(
        checks,
        "required-runtime-baseline",
        "partial" if required_missing else "present",
        "warning" if required_missing else "info",
        f"present={len(required_present)}/{len(REQUIRED_RUNTIME_KEYS)} missing={','.join(required_missing) or '-'}",
        "capture Android-boot getprop before synthesizing runtime values" if required_missing else "static baseline may be enough for a dry-run model",
    )
    add_check(
        checks,
        "wifi-property-hints",
        "present" if wifi_count > 0 else "absent",
        "info" if wifi_count > 0 else "warning",
        f"wifi_property_count={wifi_count}",
        "Wi-Fi hints are not service-manager readiness",
    )
    hint_present = [key for key in SERVICE_MANAGER_HINT_KEYS if key in required or key in props_sample]
    model = {
        "property_count": property_count,
        "context_line_count": context_count,
        "wifi_property_count": wifi_count,
        "required_present": required_present,
        "required_missing": required_missing,
        "service_manager_hint_keys_seen": hint_present,
        "recommendation": (
            "android-boot-property-capture"
            if required_missing
            else "static-readonly-shim-design"
        ),
        "blocked_actions": [
            "create /dev/__properties__",
            "create /dev/socket/property_service",
            "start servicemanager",
            "start hwservicemanager",
            "start Wi-Fi HAL or wificond",
        ],
    }
    return checks, model


def choose_decision(v295: dict[str, Any], checks: list[Check], model: dict[str, Any]) -> tuple[str, bool, str]:
    if not v295.get("present") or v295.get("decision") != "property-snapshot-model-ready":
        return "property-shim-input-missing", False, "v295 snapshot manifest missing or not ready"
    if model["required_missing"]:
        return "property-shim-strategy-capture-needed", True, "static snapshot missing selected runtime baseline keys"
    return "property-shim-static-minimal-candidate", True, "static snapshot has selected runtime baseline keys"


def render_summary(manifest: dict[str, Any], checks: list[Check], model: dict[str, Any]) -> str:
    rows = [[check.name, check.status, check.severity, check.detail, check.next_step] for check in checks]
    return "\n".join(
        [
            "# v296 Property Shim Strategy Model",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            f"- recommendation: `{model['recommendation']}`",
            "",
            "## Model",
            "",
            f"- property_count: `{model['property_count']}`",
            f"- context_line_count: `{model['context_line_count']}`",
            f"- wifi_property_count: `{model['wifi_property_count']}`",
            f"- required_present: `{', '.join(model['required_present']) or '-'}`",
            f"- required_missing: `{', '.join(model['required_missing']) or '-'}`",
            "",
            "## Checks",
            "",
            markdown_table(["check", "status", "severity", "detail", "next"], rows),
            "",
            "## Blocked Actions",
            "",
            *[f"- {item}" for item in model["blocked_actions"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v295 = load_manifest(args.v295_manifest)
    checks, model = build_checks(v295)
    decision, pass_ok, reason = choose_decision(v295, checks, model)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "v295_manifest": {
            "path": str(repo_path(args.v295_manifest)),
            "present": bool(v295.get("present")),
            "decision": v295.get("decision"),
        },
        "host": collect_host_metadata(),
        "model": model,
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_json("model.json", model)
    store.write_json("checks.json", {"checks": [asdict(check) for check in checks]})
    store.write_text("summary.md", render_summary(manifest, checks, model))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
