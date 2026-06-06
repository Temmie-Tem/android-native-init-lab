#!/usr/bin/env python3
"""Generate an approval packet for future private property materialization."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v313-private-property-materialization-approval")
DEFAULT_V312 = Path("tmp/wifi/v312-private-property-runtime-layout/manifest.json")


@dataclass
class ApprovalCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v312-manifest", type=Path, default=DEFAULT_V312)
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


def build_checks(v312: dict[str, Any]) -> list[ApprovalCheck]:
    files = v312.get("files", [])
    return [
        ApprovalCheck(
            "v312-layout",
            "pass" if v312.get("decision") == "private-property-layout-dryrun-ready" else "blocked",
            "blocker" if v312.get("decision") != "private-property-layout-dryrun-ready" else "info",
            f"v312_decision={v312.get('decision')}",
            [str(v312.get("path", ""))],
        ),
        ApprovalCheck(
            "layout-files",
            "pass" if len(files) >= 5 else "blocked",
            "blocker" if len(files) < 5 else "info",
            f"files={len(files)}",
            [str(item.get("relative_path")) for item in files if isinstance(item, dict)],
        ),
        ApprovalCheck(
            "runtime-scope",
            "needs-operator",
            "approval",
            "future materialization would create or expose property runtime files in a private namespace",
            ["requires explicit approval before any device mutation"],
        ),
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v312 = load_json(args.v312_manifest)
    checks = build_checks(v312)
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    pass_ok = not blockers
    return {
        "generated_at": now_iso(),
        "decision": "private-property-materialization-approval-ready" if pass_ok else "private-property-materialization-approval-blocked",
        "pass": pass_ok,
        "reason": "approval packet is ready; live materialization still requires explicit operator approval" if pass_ok else "blocked checks: " + ", ".join(blockers),
        "next_step": "v314 approved private namespace materialization executor",
        "host": collect_host_metadata(),
        "inputs": {
            "v312": {"path": v312.get("path"), "present": bool(v312.get("present")), "decision": v312.get("decision"), "pass": v312.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "proposed_scope": [
            "copy v312 generated files to a private device working directory only",
            "materialize property files only inside a private mount/runtime namespace if supported",
            "verify read-only property lookup with a minimal test helper only",
            "remove private files or reboot native init for cleanup",
        ],
        "explicitly_not_approved_by_this_packet": [
            "global /dev/__properties__ replacement",
            "global /dev/socket/property_service creation",
            "service-manager or hwservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
        "operator_approval_phrase": "approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up",
    }


def render_approval_text(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"][:4])] for item in manifest["checks"]]
    return "\n".join([
        "# v313 Private Property Materialization Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], check_rows),
        "",
        "## Proposed Scope",
        "",
        "\n".join(f"- {item}" for item in manifest["proposed_scope"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved_by_this_packet"]),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['operator_approval_phrase']}`",
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("approval-packet.md", render_approval_text(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"approval_phrase: {manifest['operator_approval_phrase']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
