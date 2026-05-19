#!/usr/bin/env python3
"""Generate a host-only readiness packet for the V317 live proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v331-v317-live-readiness-packet")
DEFAULT_V330 = Path("tmp/wifi/v330-evidence-freshness-audit/manifest.json")
DEFAULT_V327 = Path("tmp/wifi/v327-private-property-approval-refresh/manifest.json")
DEFAULT_V328_PLAN = Path("tmp/wifi/v328-v317-runner-plan/manifest.json")
DEFAULT_V328_REFUSE = Path("tmp/wifi/v328-v317-runner-refuse/manifest.json")
DEFAULT_RUNNER = Path("scripts/revalidation/wifi_private_property_namespace_proof.py")


@dataclass
class ReadinessCheck:
    name: str
    status: str
    detail: str
    evidence: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v330-manifest", type=Path, default=DEFAULT_V330)
    parser.add_argument("--v327-manifest", type=Path, default=DEFAULT_V327)
    parser.add_argument("--v328-plan-manifest", type=Path, default=DEFAULT_V328_PLAN)
    parser.add_argument("--v328-refuse-manifest", type=Path, default=DEFAULT_V328_REFUSE)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--live-out-dir", type=Path, default=Path("tmp/wifi/v317-private-property-namespace-proof"))
    parser.add_argument("--cleanup-out-dir", type=Path, default=Path("tmp/wifi/v317-private-property-namespace-proof-cleanup"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("packet")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def shell_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in argv)


def build_command(args: argparse.Namespace, approval_phrase: str, subcommand: str, out_dir: Path) -> list[str]:
    return [
        "python3",
        str(args.runner),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--approval-phrase",
        approval_phrase,
        "--allow-device-mutation",
        "--assume-yes",
        subcommand,
    ]


def build_checks(v330: dict[str, Any],
                 v327: dict[str, Any],
                 v328_plan: dict[str, Any],
                 v328_refuse: dict[str, Any],
                 approval_phrase: str) -> list[ReadinessCheck]:
    v330_ok = (
        v330.get("present")
        and v330.get("decision") == "wifi-evidence-freshness-clean"
        and bool(v330.get("pass"))
        and not bool(v330.get("device_commands_executed"))
        and not bool(v330.get("device_mutations"))
    )
    v327_ok = (
        v327.get("present")
        and v327.get("decision") == "private-property-approval-refresh-ready"
        and bool(v327.get("pass"))
        and v327.get("approval_phrase") == approval_phrase
        and not bool(v327.get("live_execution_approved"))
        and not bool(v327.get("device_commands_executed"))
        and not bool(v327.get("device_mutations"))
    )
    v328_plan_ok = (
        v328_plan.get("present")
        and v328_plan.get("decision") == "private-property-namespace-proof-plan-ready"
        and bool(v328_plan.get("pass"))
        and v328_plan.get("operator_approval_phrase") == approval_phrase
        and not bool(v328_plan.get("device_commands_executed"))
        and not bool(v328_plan.get("device_mutations"))
    )
    v328_refuse_ok = (
        v328_refuse.get("present")
        and v328_refuse.get("decision") == "private-property-namespace-proof-approval-required"
        and not bool(v328_refuse.get("pass"))
        and v328_refuse.get("operator_approval_phrase") == approval_phrase
        and not bool(v328_refuse.get("device_commands_executed"))
        and not bool(v328_refuse.get("device_mutations"))
    )
    return [
        ReadinessCheck(
            "v330-freshness",
            "pass" if v330_ok else "blocked",
            f"decision={v330.get('decision')} pass={v330.get('pass')}",
            str(v330.get("path", "")),
        ),
        ReadinessCheck(
            "v327-approval-packet",
            "pass" if v327_ok else "blocked",
            f"decision={v327.get('decision')} pass={v327.get('pass')} live_execution_approved={v327.get('live_execution_approved')}",
            str(v327.get("path", "")),
        ),
        ReadinessCheck(
            "v328-plan",
            "pass" if v328_plan_ok else "blocked",
            f"decision={v328_plan.get('decision')} pass={v328_plan.get('pass')}",
            str(v328_plan.get("path", "")),
        ),
        ReadinessCheck(
            "v328-refusal",
            "pass" if v328_refuse_ok else "blocked",
            f"decision={v328_refuse.get('decision')} pass={v328_refuse.get('pass')}",
            str(v328_refuse.get("path", "")),
        ),
    ]


def decide(checks: list[ReadinessCheck]) -> tuple[str, bool, str, str]:
    blocked = [check.name for check in checks if check.status != "pass"]
    if blocked:
        return (
            "v317-live-readiness-packet-blocked",
            False,
            "blocked checks: " + ", ".join(blocked),
            "rerun prerequisite host-only evidence before asking for live approval",
        )
    return (
        "v317-live-readiness-packet-ready",
        True,
        "approved command packet is ready; live execution still requires the operator to provide the exact phrase",
        "wait for the exact V317 approval phrase before running the generated command",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v330 = load_json(args.v330_manifest)
    v327 = load_json(args.v327_manifest)
    v328_plan = load_json(args.v328_plan_manifest)
    v328_refuse = load_json(args.v328_refuse_manifest)
    approval_phrase = str(v327.get("approval_phrase") or v328_plan.get("operator_approval_phrase") or "")
    checks = build_checks(v330, v327, v328_plan, v328_refuse, approval_phrase)
    decision, pass_ok, reason, next_step = decide(checks)
    run_argv = build_command(args, approval_phrase, "run", args.live_out_dir)
    cleanup_argv = build_command(args, approval_phrase, "cleanup", args.cleanup_out_dir)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "approval_phrase": approval_phrase,
        "live_command": shell_command(run_argv),
        "cleanup_command": shell_command(cleanup_argv),
        "approved_scope": [
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
        ],
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_packet(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["detail"], item["evidence"]] for item in manifest["checks"]]
    return "\n".join([
        "# v331 V317 Live Readiness Packet",
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
        markdown_table(["name", "status", "detail", "evidence"], rows),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Command To Run After Approval",
        "",
        "```bash",
        manifest["live_command"],
        "```",
        "",
        "## Cleanup Command If Needed",
        "",
        "```bash",
        manifest["cleanup_command"],
        "```",
        "",
        "## Approved Scope",
        "",
        "\n".join(f"- {item}" for item in manifest["approved_scope"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- {item}" for item in manifest["explicitly_not_approved"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("readiness-packet.md", render_packet(manifest))
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
