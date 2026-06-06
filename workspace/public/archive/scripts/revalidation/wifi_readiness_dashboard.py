#!/usr/bin/env python3
"""Build a host-only Wi-Fi readiness dashboard from existing evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v329-wifi-readiness-dashboard")
V317_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class EvidenceItem:
    name: str
    path: str
    present: bool
    decision: str
    status: str
    detail: str
    action: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
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


def latest_manifest(pattern: str) -> Path | None:
    matches = sorted(repo_path(Path("tmp/wifi")).glob(pattern))
    return matches[-1] if matches else None


def manifest_text(manifest: dict[str, Any], key: str) -> str:
    value = manifest.get(key)
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def item_from_manifest(name: str,
                       path: Path | None,
                       expected_decisions: set[str],
                       *,
                       action: str,
                       status_override: str | None = None) -> EvidenceItem:
    if path is None:
        return EvidenceItem(name, "", False, "missing", "missing", "missing evidence", action)
    manifest = load_manifest(path)
    decision = manifest_text(manifest, "decision")
    pass_value = manifest.get("pass")
    if pass_value is None:
        pass_value = manifest.get("audit_pass")
    if status_override is not None:
        status = status_override
    elif not manifest.get("present"):
        status = "missing"
    elif bool(pass_value) and decision in expected_decisions:
        status = "pass"
    elif bool(pass_value):
        status = "review"
    else:
        status = "blocked"
    detail = manifest_text(manifest, "reason") or manifest_text(manifest, "next_step") or f"pass={pass_value}"
    return EvidenceItem(
        name=name,
        path=str(manifest.get("path", "")),
        present=bool(manifest.get("present")),
        decision=decision or "missing",
        status=status,
        detail=detail,
        action=action,
    )


def build_items() -> list[EvidenceItem]:
    return [
        item_from_manifest(
            "native-baseline",
            Path("tmp/wifi/v203-baseline/manifest.json"),
            {"no-go"},
            action="historical baseline: Android-side assets existed but native kernel-facing gates were absent",
            status_override="blocked",
        ),
        item_from_manifest(
            "vendor-assets",
            Path("tmp/wifi/v209-vendor-ro-mount-probe/manifest.json"),
            {"vendor-assets-visible"},
            action="vendor assets are available read-only; keep using ro,noload evidence path",
        ),
        item_from_manifest(
            "icnss-start-delta",
            latest_manifest("v283-icnss-wlfw-start-delta-live-*/manifest.json"),
            {"icnss-wlfw-start-no-readiness-delta"},
            action="do not repeat blind cnss-daemon start-only; use blocker model",
            status_override="blocked",
        ),
        item_from_manifest(
            "icnss-focused-delta",
            latest_manifest("v285-icnss-qca6390-during-start-live-*/manifest.json"),
            {"icnss-qca6390-focused-no-during-delta"},
            action="same start-only path shows no useful WLAN/wiphy delta",
            status_override="blocked",
        ),
        item_from_manifest(
            "service-order-model",
            Path("tmp/wifi/v287-wifi-service-order-replay-model/manifest.json"),
            {"wifi-service-order-replay-model-ready"},
            action="HAL/framework path requires Binder/property prerequisites before execution",
        ),
        item_from_manifest(
            "binder-open",
            Path("tmp/wifi/v292-binder-open-smoke-live-20260519-141358/manifest.json"),
            {"binder-open-only-smoke-pass"},
            action="Binder device open blocker cleared, but service-manager is still not ready",
        ),
        item_from_manifest(
            "service-manager-prereq",
            Path("tmp/wifi/v293-service-manager-prereq-live-20260519-141752/manifest.json"),
            {"service-manager-prereq-blockers-mapped"},
            action="blocked by service-manager process/runtime property requirements",
            status_override="blocked",
        ),
        item_from_manifest(
            "android-property-capture",
            Path("tmp/wifi/v297-android-property-capture-android/manifest.json"),
            {"android-property-capture-pass"},
            action="Android-backed property seed is available",
        ),
        item_from_manifest(
            "property-layout",
            Path("tmp/wifi/v312-private-property-runtime-layout/manifest.json"),
            {"private-property-layout-dryrun-ready"},
            action="private property layout is ready host-side",
        ),
        item_from_manifest(
            "private-property-chain",
            Path("tmp/wifi/v326-private-property-chain-audit/manifest.json"),
            {"private-property-chain-blocked-v317-missing"},
            action="next live blocker is exact V317 approval and PASS evidence",
            status_override="blocked",
        ),
        item_from_manifest(
            "approval-refresh",
            Path("tmp/wifi/v327-private-property-approval-refresh/manifest.json"),
            {"private-property-approval-refresh-ready"},
            action="approval packet ready but not approved",
        ),
        item_from_manifest(
            "v317-runner-plan",
            Path("tmp/wifi/v328-v317-runner-plan/manifest.json"),
            {"private-property-namespace-proof-plan-ready"},
            action="runner plan is ready and host-only",
        ),
        item_from_manifest(
            "v317-runner-refusal",
            Path("tmp/wifi/v328-v317-runner-refuse/manifest.json"),
            {"private-property-namespace-proof-approval-required"},
            action="run without exact approval fails closed",
            status_override="blocked",
        ),
    ]


def decide(items: list[EvidenceItem]) -> tuple[str, bool, str, str]:
    missing = [item.name for item in items if item.status == "missing"]
    if missing:
        return (
            "wifi-readiness-dashboard-incomplete",
            False,
            "missing required evidence: " + ", ".join(missing),
            "regenerate missing host-only/read-only evidence before live Wi-Fi work",
        )
    return (
        "wifi-readiness-dashboard-ready-blocked-by-v317",
        True,
        "dashboard built; current live path is blocked by V317 private property proof approval",
        f"provide exact phrase only if proceeding: {V317_APPROVAL_PHRASE}",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    items = build_items()
    decision, pass_ok, reason, next_step = decide(items)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "items": [asdict(item) for item in items],
        "required_approval_phrase": V317_APPROVAL_PHRASE,
        "safe_without_approval": [
            "host-only evidence aggregation",
            "read-only device inventory",
            "static source/helper build checks",
        ],
        "blocked_without_approval": [
            "V317 private property namespace live proof",
            "V320 private property lookup live proof",
            "Wi-Fi daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, module load/unload, firmware mutation, or partition write",
        ],
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [item["name"], item["status"], item["decision"], item["action"], item["path"]]
        for item in manifest["items"]
    ]
    return "\n".join([
        "# v329 Wi-Fi Readiness Dashboard",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Track Status",
        "",
        markdown_table(["track", "status", "decision", "action", "evidence"], rows),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Blocked Without Approval",
        "",
        "\n".join(f"- {item}" for item in manifest["blocked_without_approval"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
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
