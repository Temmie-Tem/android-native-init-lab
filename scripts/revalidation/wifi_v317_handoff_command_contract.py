#!/usr/bin/env python3
"""Host-only contract checks for V317 handoff commands."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v348-v317-handoff-command-contract")
DEFAULT_V340 = Path("tmp/wifi/v340-v317-final-handoff-packet/manifest.json")
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
RUNNER = "scripts/revalidation/wifi_private_property_namespace_proof.py"
PRELIVE_GATE = "tmp/wifi/v336-v317-prelive-gate-audit/manifest.json"
PREFLIGHT_OUT_DIR = "tmp/wifi/v317-private-property-namespace-proof-preflight"
LIVE_OUT_DIR = "tmp/wifi/v317-private-property-namespace-proof"
CLEANUP_OUT_DIR = "tmp/wifi/v317-private-property-namespace-proof-cleanup"


@dataclass
class CommandView:
    name: str
    raw: str
    argv: list[str]
    script: str | None
    subcommand: str | None
    out_dir: str | None
    prelive_gate: str | None
    approval_phrase: str | None
    has_allow_device_mutation: bool
    has_assume_yes: bool


@dataclass
class ContractCheck:
    name: str
    status: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v340-manifest", type=Path, default=DEFAULT_V340)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def command_arg(argv: list[str], name: str) -> str | None:
    for index, item in enumerate(argv[:-1]):
        if item == name:
            return argv[index + 1]
    return None


def command_view(name: str, raw: str) -> CommandView:
    argv = shlex.split(raw) if raw else []
    script = None
    for item in argv:
        if item.endswith("wifi_private_property_namespace_proof.py"):
            script = item
            break
    subcommand = argv[-1] if argv else None
    return CommandView(
        name=name,
        raw=raw,
        argv=argv,
        script=script,
        subcommand=subcommand,
        out_dir=command_arg(argv, "--out-dir"),
        prelive_gate=command_arg(argv, "--prelive-gate-manifest"),
        approval_phrase=command_arg(argv, "--approval-phrase"),
        has_allow_device_mutation="--allow-device-mutation" in argv,
        has_assume_yes="--assume-yes" in argv,
    )


def check_command(view: CommandView, expected_subcommand: str, expected_out_dir: str) -> list[ContractCheck]:
    return [
        ContractCheck(
            f"{view.name}-script",
            "pass" if view.script == RUNNER else "blocked",
            f"script={view.script} expected={RUNNER}",
        ),
        ContractCheck(
            f"{view.name}-subcommand",
            "pass" if view.subcommand == expected_subcommand else "blocked",
            f"subcommand={view.subcommand} expected={expected_subcommand}",
        ),
        ContractCheck(
            f"{view.name}-out-dir",
            "pass" if view.out_dir == expected_out_dir else "blocked",
            f"out_dir={view.out_dir} expected={expected_out_dir}",
        ),
        ContractCheck(
            f"{view.name}-prelive-gate",
            "pass" if view.prelive_gate == PRELIVE_GATE else "blocked",
            f"prelive_gate={view.prelive_gate} expected={PRELIVE_GATE}",
        ),
        ContractCheck(
            f"{view.name}-approval-phrase",
            "pass" if view.approval_phrase == APPROVAL_PHRASE else "blocked",
            "approval phrase matches exact V317 phrase",
        ),
        ContractCheck(
            f"{view.name}-approval-flags",
            "pass" if view.has_allow_device_mutation and view.has_assume_yes else "blocked",
            f"allow_device_mutation={view.has_allow_device_mutation} assume_yes={view.has_assume_yes}",
        ),
    ]


def build_checks(v340: dict[str, Any], views: dict[str, CommandView]) -> list[ContractCheck]:
    checks: list[ContractCheck] = [
        ContractCheck(
            "v340-ready",
            "pass" if v340.get("present") and v340.get("decision") == "v317-handoff-awaiting-approval" and bool(v340.get("pass")) else "blocked",
            f"decision={v340.get('decision')} pass={v340.get('pass')}",
        ),
        ContractCheck(
            "v340-no-device-execution",
            "pass" if not bool(v340.get("device_commands_executed")) and not bool(v340.get("device_mutations")) else "blocked",
            f"device_commands_executed={v340.get('device_commands_executed')} device_mutations={v340.get('device_mutations')}",
        ),
        ContractCheck(
            "remaining-blocker",
            "pass" if v340.get("remaining_blockers") == ["exact-v317-approval-phrase"] else "blocked",
            f"remaining_blockers={v340.get('remaining_blockers')}",
        ),
    ]
    checks.extend(check_command(views["preflight"], "preflight", PREFLIGHT_OUT_DIR))
    checks.extend(check_command(views["live"], "run", LIVE_OUT_DIR))
    checks.extend(check_command(views["cleanup"], "cleanup", CLEANUP_OUT_DIR))
    out_dirs = {views[name].out_dir for name in ("preflight", "live", "cleanup")}
    checks.append(ContractCheck(
        "out-dirs-distinct",
        "pass" if out_dirs == {PREFLIGHT_OUT_DIR, LIVE_OUT_DIR, CLEANUP_OUT_DIR} else "blocked",
        f"out_dirs={sorted(str(item) for item in out_dirs)}",
    ))
    return checks


def decide(checks: list[ContractCheck]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in checks if item.status != "pass"]
    if blocked:
        return (
            "v317-handoff-command-contract-blocked",
            False,
            "blocked checks: " + ", ".join(blocked),
            "repair V340 handoff command contract before V317 live proof",
            blocked,
        )
    return (
        "v317-handoff-command-contract-pass",
        True,
        "V340 preflight/live/cleanup command contract is safe and isolated",
        "V317 live proof remains blocked by exact approval phrase",
        ["exact-v317-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v340 = load_json(args.v340_manifest)
    views = {
        "preflight": command_view("preflight", str(v340.get("preflight_command") or "")),
        "live": command_view("live", str(v340.get("live_command") or "")),
        "cleanup": command_view("cleanup", str(v340.get("cleanup_command") or "")),
    }
    checks = build_checks(v340, views)
    decision, pass_ok, reason, next_step, blockers = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v340_manifest": str(repo_path(args.v340_manifest)),
        "views": {name: asdict(view) for name, view in views.items()},
        "checks": [asdict(item) for item in checks],
        "remaining_blockers": blockers,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["detail"]] for item in manifest["checks"]]
    return "\n".join([
        "# v348 V317 Handoff Command Contract",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Remaining Blockers",
        "",
        "\n".join(f"- `{item}`" for item in manifest["remaining_blockers"]) or "- none",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
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
