#!/usr/bin/env python3
"""Generate an approval packet for minimal private property live proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v316-private-property-live-approval")
DEFAULT_V314 = Path("tmp/wifi/v314-private-property-materialization-executor/manifest.json")
DEFAULT_V315 = Path("tmp/wifi/v315-private-property-live-preflight/manifest.json")
APPROVAL_PHRASE = (
    "approve v317 minimal private property namespace proof only; "
    "no daemon start and no Wi-Fi bring-up"
)


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
    parser.add_argument("--v314-manifest", type=Path, default=DEFAULT_V314)
    parser.add_argument("--v315-manifest", type=Path, default=DEFAULT_V315)
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


def build_checks(v314: dict[str, Any], v315: dict[str, Any]) -> list[ApprovalCheck]:
    return [
        ApprovalCheck(
            "v314-executor-plan",
            "pass" if v314.get("decision") == "private-property-materialization-executor-plan-ready" and bool(v314.get("pass")) else "blocked",
            "blocker",
            f"decision={v314.get('decision')} pass={v314.get('pass')}",
            [str(v314.get("path", ""))],
        ),
        ApprovalCheck(
            "v315-live-preflight",
            "pass" if v315.get("decision") == "private-property-live-preflight-ready" and bool(v315.get("pass")) else "blocked",
            "blocker",
            f"decision={v315.get('decision')} pass={v315.get('pass')}",
            [str(v315.get("path", ""))],
        ),
        ApprovalCheck(
            "mutation-boundary",
            "needs-operator",
            "approval",
            "next proof may create a private device workdir and copy generated property files",
            ["requires exact approval phrase"],
        ),
    ]


def decide(checks: list[ApprovalCheck]) -> tuple[str, bool, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "private-property-live-approval-blocked", False, "blocked checks: " + ", ".join(blockers)
    return "private-property-live-approval-ready", True, "approval packet is ready; live proof still requires explicit operator approval"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v314 = load_json(args.v314_manifest)
    v315 = load_json(args.v315_manifest)
    checks = build_checks(v314, v315)
    decision, pass_ok, reason = decide(checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": "v317 minimal private property namespace proof after explicit approval",
        "host": collect_host_metadata(),
        "inputs": {
            "v314": {"path": v314.get("path"), "present": bool(v314.get("present")), "decision": v314.get("decision"), "pass": v314.get("pass")},
            "v315": {"path": v315.get("path"), "present": bool(v315.get("present")), "decision": v315.get("decision"), "pass": v315.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "approved_scope_after_phrase": [
            "create a versioned private workdir under /mnt/sdext/a90 only",
            "copy v312 generated property layout files into that private workdir only",
            "verify copied file SHA-256 values",
            "run at most a minimal static verification helper in a private namespace",
            "remove the private workdir or require native reboot for cleanup",
        ],
        "explicitly_not_approved": [
            "global /dev/__properties__ replacement",
            "global bind mount over /dev/__properties__",
            "global /dev/socket/property_service creation",
            "property mutation or setprop-like writes",
            "service-manager or hwservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
        "operator_approval_phrase": APPROVAL_PHRASE,
        "device_commands_executed": False,
    }


def render_packet(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"])] for item in manifest["checks"]]
    return "\n".join([
        "# v316 Private Property Live Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], check_rows),
        "",
        "## Approved Scope After Phrase",
        "",
        "\n".join(f"- {item}" for item in manifest["approved_scope_after_phrase"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved"]),
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
    store.write_text("approval-packet.md", render_packet(manifest))
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"approval_phrase: {manifest['operator_approval_phrase']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
