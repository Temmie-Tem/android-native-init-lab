#!/usr/bin/env python3
"""Generate refreshed v317 private-property live approval packet."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v327-private-property-approval-refresh")
DEFAULT_V317_PLAN = Path("tmp/wifi/v317-private-property-namespace-proof-current-plan/manifest.json")
DEFAULT_CHAIN_AUDIT = Path("tmp/wifi/v326-private-property-chain-audit/manifest.json")
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class RefreshCheck:
    name: str
    status: str
    detail: str
    evidence: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v317-plan-manifest", type=Path, default=DEFAULT_V317_PLAN)
    parser.add_argument("--chain-audit-manifest", type=Path, default=DEFAULT_CHAIN_AUDIT)
    parser.add_argument("--v323-audit-manifest", type=Path, dest="chain_audit_manifest", help=argparse.SUPPRESS)
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


def build_checks(v317: dict[str, Any], chain_audit: dict[str, Any]) -> list[RefreshCheck]:
    transfer = v317.get("transfer_estimate") if isinstance(v317.get("transfer_estimate"), dict) else {}
    v317_ok = (
        v317.get("present") and
        v317.get("decision") == "private-property-namespace-proof-plan-ready" and
        bool(v317.get("pass")) and
        transfer.get("status") == "pass"
    )
    chain_audit_ok = (
        chain_audit.get("present") and
        chain_audit.get("decision") == "private-property-chain-blocked-v317-missing" and
        bool(chain_audit.get("audit_pass")) and
        not bool(chain_audit.get("chain_ready"))
    )
    return [
        RefreshCheck(
            "v317-current-plan",
            "pass" if v317_ok else "blocked",
            f"decision={v317.get('decision')} pass={v317.get('pass')} transfer_status={transfer.get('status')}",
            str(v317.get("path", "")),
        ),
        RefreshCheck(
            "chain-audit",
            "pass" if chain_audit_ok else "blocked",
            f"decision={chain_audit.get('decision')} audit_pass={chain_audit.get('audit_pass')} chain_ready={chain_audit.get('chain_ready')}",
            str(chain_audit.get("path", "")),
        ),
    ]


def decide(checks: list[RefreshCheck]) -> tuple[str, bool, str, str]:
    blocked = [check.name for check in checks if check.status != "pass"]
    if blocked:
        return (
            "private-property-approval-refresh-blocked",
            False,
            "blocked checks: " + ", ".join(blocked),
            "repair local evidence before asking for live approval",
        )
    return (
        "private-property-approval-refresh-ready",
        True,
        "refreshed approval packet is ready; live execution is still not approved",
        "operator may provide the exact phrase only if they accept the listed live boundary",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v317 = load_json(args.v317_plan_manifest)
    chain_audit = load_json(args.chain_audit_manifest)
    checks = build_checks(v317, chain_audit)
    decision, pass_ok, reason, next_step = decide(checks)
    transfer = v317.get("transfer_estimate") if isinstance(v317.get("transfer_estimate"), dict) else {}
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "transfer_estimate": transfer,
        "chain_audit_decision": chain_audit.get("decision"),
        "chain_audit_path": chain_audit.get("path"),
        "live_execution_approved": False,
        "approval_phrase": APPROVAL_PHRASE,
        "approved_scope_after_phrase": [
            "create /mnt/sdext/a90/private-property-v317 private workdir only",
            "copy v312 generated property layout files into that private workdir only",
            "verify size and SHA-256 of copied files",
            "run private namespace proof/cleanup bounded to that workdir",
        ],
        "explicitly_not_approved": [
            "global /dev/__properties__ replacement or bind mount",
            "global /dev/socket/property_service creation",
            "property mutation or setprop-like writes",
            "service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, module load/unload, firmware mutation, or partition write",
            "NCM/tcpctl transfer for this v317 proof",
        ],
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_packet(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["detail"], item["evidence"]] for item in manifest["checks"]]
    transfer_rows = [[key, str(value)] for key, value in sorted(manifest["transfer_estimate"].items())]
    return "\n".join([
        "# Refreshed Private Property Live Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "evidence"], check_rows),
        "",
        "## Transfer Estimate",
        "",
        markdown_table(["field", "value"], transfer_rows),
        "",
        "## Approved Scope After Exact Phrase",
        "",
        "\n".join(f"- {item}" for item in manifest["approved_scope_after_phrase"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- {item}" for item in manifest["explicitly_not_approved"]),
        "",
        "## Required Exact Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("approval-packet.md", render_packet(manifest))
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"approval_phrase: {manifest['approval_phrase']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
