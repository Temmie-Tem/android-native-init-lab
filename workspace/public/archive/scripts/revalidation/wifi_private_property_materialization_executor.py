#!/usr/bin/env python3
"""Approval-aware scaffold for private property namespace materialization."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v314-private-property-materialization-executor")
DEFAULT_V312 = Path("tmp/wifi/v312-private-property-runtime-layout/manifest.json")
DEFAULT_V313 = Path("tmp/wifi/v313-private-property-materialization-approval/manifest.json")
REQUIRED_APPROVAL_PHRASE = (
    "approve v314 private property namespace materialization only; "
    "no daemon start and no Wi-Fi bring-up"
)


@dataclass
class ExecutorCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


@dataclass
class PlannedStep:
    name: str
    command: str
    mutates_device: bool
    allowed_by_scope: bool
    executed: bool
    note: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v312-manifest", type=Path, default=DEFAULT_V312)
    parser.add_argument("--v313-manifest", type=Path, default=DEFAULT_V313)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--allow-device-mutation", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
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


def quote_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def layout_files(v312: dict[str, Any]) -> list[dict[str, Any]]:
    files = v312.get("files", [])
    return [item for item in files if isinstance(item, dict)]


def build_checks(args: argparse.Namespace,
                 v312: dict[str, Any],
                 v313: dict[str, Any]) -> list[ExecutorCheck]:
    files = layout_files(v312)
    phrase = str(v313.get("operator_approval_phrase") or REQUIRED_APPROVAL_PHRASE)
    phrase_ok = args.approval_phrase == phrase
    approval_flags_ok = args.allow_device_mutation and args.assume_yes and phrase_ok
    return [
        ExecutorCheck(
            "v312-layout",
            "pass" if v312.get("decision") == "private-property-layout-dryrun-ready" and bool(v312.get("pass")) else "blocked",
            "blocker",
            f"decision={v312.get('decision')} pass={v312.get('pass')} files={len(files)}",
            [str(v312.get("path", ""))],
        ),
        ExecutorCheck(
            "v313-approval-packet",
            "pass" if v313.get("decision") == "private-property-materialization-approval-ready" and bool(v313.get("pass")) else "blocked",
            "blocker",
            f"decision={v313.get('decision')} pass={v313.get('pass')}",
            [str(v313.get("path", ""))],
        ),
        ExecutorCheck(
            "approval-phrase",
            "pass" if phrase_ok else "needs-operator",
            "approval",
            "exact approval phrase matched" if phrase_ok else "exact v314 approval phrase not provided",
            [phrase],
        ),
        ExecutorCheck(
            "approval-flags",
            "pass" if approval_flags_ok else "needs-operator",
            "approval",
            f"allow_device_mutation={args.allow_device_mutation} assume_yes={args.assume_yes}",
            ["--allow-device-mutation", "--assume-yes", "--approval-phrase"],
        ),
        ExecutorCheck(
            "live-implementation",
            "blocked",
            "blocker" if args.command == "run" and approval_flags_ok else "info",
            "v314 provides a fail-closed scaffold only; live materialization code is intentionally not implemented in this step",
            ["no device command is executed by this tool"],
        ),
    ]


def build_planned_steps(v312: dict[str, Any]) -> list[PlannedStep]:
    files = layout_files(v312)
    file_names = [str(item.get("relative_path") or "") for item in files]
    return [
        PlannedStep(
            "read-current-native-state",
            quote_command(["python3", "scripts/revalidation/a90ctl.py", "--json", "version"]),
            False,
            True,
            False,
            "future live run must verify native control before any mutation",
        ),
        PlannedStep(
            "prepare-private-device-workdir",
            "bridge run mkdir /mnt/sdext/a90/private-property-v314",
            True,
            True,
            False,
            "private workspace only; no global /dev replacement",
        ),
        PlannedStep(
            "copy-layout-files",
            f"copy {len(files)} files: " + ", ".join(file_names[:6]),
            True,
            True,
            False,
            "future implementation must use checksum verification and private paths",
        ),
        PlannedStep(
            "materialize-private-namespace-only",
            "future helper enters private mount/runtime namespace and exposes generated /dev/__properties__ inside that namespace only",
            True,
            True,
            False,
            "no global bind mount and no property_service socket",
        ),
        PlannedStep(
            "verify-readonly-property-lookup",
            "future helper reads selected ro.* keys through bionic property API",
            False,
            True,
            False,
            "no setprop/property mutation",
        ),
        PlannedStep(
            "cleanup-private-workdir",
            "remove private workspace or reboot native init for cleanup",
            True,
            True,
            False,
            "rollback must be local to private namespace/workdir",
        ),
    ]


def decide(args: argparse.Namespace, checks: list[ExecutorCheck]) -> tuple[str, bool, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    approvals = [check.name for check in checks if check.severity == "approval" and check.status != "pass"]
    if blockers:
        if blockers == ["live-implementation"]:
            return "private-property-materialization-executor-live-not-implemented", False, "approval gates matched, but v314 intentionally does not execute live materialization"
        return "private-property-materialization-executor-blocked", False, "blocked checks: " + ", ".join(blockers)
    if args.command == "plan":
        return "private-property-materialization-executor-plan-ready", True, "execution plan generated without device mutation"
    if approvals:
        return "private-property-materialization-executor-approval-required", False, "missing approval gates: " + ", ".join(approvals)
    return "private-property-materialization-executor-live-not-implemented", False, "approval gates matched, but v314 intentionally does not execute live materialization"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v312 = load_json(args.v312_manifest)
    v313 = load_json(args.v313_manifest)
    checks = build_checks(args, v312, v313)
    decision, pass_ok, reason = decide(args, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": "v315 read-only live preflight before any materialization implementation" if decision.endswith("plan-ready") else "resolve blockers or provide exact approval for a future live implementation",
        "host": collect_host_metadata(),
        "inputs": {
            "v312": {"path": v312.get("path"), "present": bool(v312.get("present")), "decision": v312.get("decision"), "pass": v312.get("pass")},
            "v313": {"path": v313.get("path"), "present": bool(v313.get("present")), "decision": v313.get("decision"), "pass": v313.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "planned_steps": [asdict(step) for step in build_planned_steps(v312)],
        "required_approval_phrase": str(v313.get("operator_approval_phrase") or REQUIRED_APPROVAL_PHRASE),
        "blocked_actions": [
            "global /dev/__properties__ replacement",
            "global /dev/socket/property_service creation",
            "property mutation or setprop-like writes",
            "service-manager or hwservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
        "device_commands_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"][:3])] for item in manifest["checks"]]
    step_rows = [[item["name"], str(item["mutates_device"]), str(item["allowed_by_scope"]), str(item["executed"]), item["note"]] for item in manifest["planned_steps"]]
    return "\n".join([
        "# v314 Private Property Materialization Executor",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
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
        "## Planned Steps",
        "",
        markdown_table(["step", "mutates", "allowed", "executed", "note"], step_rows),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
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
