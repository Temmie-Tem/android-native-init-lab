#!/usr/bin/env python3
"""Build the final host-only operator checklist for V317 live proof."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v350-v317-operator-checklist")
DEFAULT_V340 = Path("tmp/wifi/v340-v317-final-handoff-packet/manifest.json")
DEFAULT_V349 = Path("tmp/wifi/v349-v317-final-readiness/manifest.json")
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
EXPECTED_PRELIVE = "tmp/wifi/v336-v317-prelive-gate-audit/manifest.json"
EXPECTED_PREFLIGHT_OUT = "tmp/wifi/v317-private-property-namespace-proof-preflight"
EXPECTED_LIVE_OUT = "tmp/wifi/v317-private-property-namespace-proof"
EXPECTED_CLEANUP_OUT = "tmp/wifi/v317-private-property-namespace-proof-cleanup"
RUNNER = "scripts/revalidation/wifi_private_property_namespace_proof.py"
EXECUTOR = "scripts/revalidation/wifi_v317_live_executor.py"


@dataclass
class ChecklistCheck:
    name: str
    status: str
    detail: str
    evidence: str


@dataclass
class CommandView:
    name: str
    raw: str
    argv: list[str]
    script: str
    subcommand: str
    out_dir: str
    prelive_gate: str
    approval_phrase: str
    allow_device_mutation: bool
    assume_yes: bool


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v340-manifest", type=Path, default=DEFAULT_V340)
    parser.add_argument("--v349-manifest", type=Path, default=DEFAULT_V349)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def host_head(payload: dict[str, Any]) -> str:
    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    return str(host.get("git_head") or "")


def host_dirty(payload: dict[str, Any]) -> bool | None:
    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


def command_arg(argv: list[str], flag: str) -> str:
    try:
        index = argv.index(flag)
    except ValueError:
        return ""
    if index + 1 >= len(argv):
        return ""
    return argv[index + 1]


def command_view(name: str, raw: str) -> CommandView:
    argv = shlex.split(raw)
    script = argv[1] if len(argv) > 1 else ""
    return CommandView(
        name=name,
        raw=raw,
        argv=argv,
        script=script,
        subcommand=argv[-1] if argv else "",
        out_dir=command_arg(argv, "--out-dir"),
        prelive_gate=command_arg(argv, "--prelive-gate-manifest"),
        approval_phrase=command_arg(argv, "--approval-phrase"),
        allow_device_mutation="--allow-device-mutation" in argv,
        assume_yes="--assume-yes" in argv,
    )


def executor_command(subcommand: str) -> str:
    argv = [
        "python3",
        EXECUTOR,
        "--out-dir",
        "tmp/wifi/v351-v317-live-executor",
    ]
    if subcommand in {"run", "cleanup"}:
        argv.extend([
            "--approval-phrase",
            APPROVAL_PHRASE,
            "--allow-device-mutation",
            "--assume-yes",
        ])
    argv.append(subcommand)
    return " ".join(shlex.quote(item) for item in argv)


def check_command(view: CommandView, expected_subcommand: str, expected_out_dir: str) -> list[ChecklistCheck]:
    return [
        ChecklistCheck(
            f"{view.name}-runner",
            "pass" if view.script == RUNNER else "blocked",
            f"script={view.script}",
            "",
        ),
        ChecklistCheck(
            f"{view.name}-subcommand",
            "pass" if view.subcommand == expected_subcommand else "blocked",
            f"subcommand={view.subcommand}",
            "",
        ),
        ChecklistCheck(
            f"{view.name}-out-dir",
            "pass" if view.out_dir == expected_out_dir else "blocked",
            f"out_dir={view.out_dir}",
            "",
        ),
        ChecklistCheck(
            f"{view.name}-prelive-gate",
            "pass" if view.prelive_gate == EXPECTED_PRELIVE else "blocked",
            f"prelive_gate={view.prelive_gate}",
            "",
        ),
        ChecklistCheck(
            f"{view.name}-approval",
            "pass" if view.approval_phrase == APPROVAL_PHRASE and view.allow_device_mutation and view.assume_yes else "blocked",
            f"phrase_ok={view.approval_phrase == APPROVAL_PHRASE} allow_mutation={view.allow_device_mutation} assume_yes={view.assume_yes}",
            "",
        ),
    ]


def build_checks(v340: dict[str, Any], v349: dict[str, Any], current_head: str) -> tuple[list[ChecklistCheck], dict[str, CommandView]]:
    views = {
        "preflight": command_view("preflight", str(v340.get("preflight_command") or "")),
        "live": command_view("live", str(v340.get("live_command") or "")),
        "cleanup": command_view("cleanup", str(v340.get("cleanup_command") or "")),
    }
    host = collect_host_metadata()
    checks = [
        ChecklistCheck(
            "current-tree-clean",
            "pass" if host.get("git_head") == current_head and host.get("git_dirty") is False else "blocked",
            f"head={host.get('git_head')} current={current_head} dirty={host.get('git_dirty')}",
            "",
        ),
        ChecklistCheck(
            "v340-handoff-ready",
            "pass" if v340.get("present") and v340.get("decision") == "v317-handoff-awaiting-approval" and bool(v340.get("pass")) else "blocked",
            f"decision={v340.get('decision')} pass={v340.get('pass')}",
            str(v340.get("path") or ""),
        ),
        ChecklistCheck(
            "v340-current-clean-head",
            "pass" if host_head(v340) == current_head and host_dirty(v340) is False else "blocked",
            f"head={host_head(v340)} current={current_head} dirty={host_dirty(v340)}",
            str(v340.get("path") or ""),
        ),
        ChecklistCheck(
            "v340-blocker-only-approval",
            "pass" if v340.get("remaining_blockers") == ["exact-v317-approval-phrase"] else "blocked",
            f"remaining_blockers={v340.get('remaining_blockers')}",
            str(v340.get("path") or ""),
        ),
        ChecklistCheck(
            "v349-final-readiness",
            "pass" if v349.get("present") and v349.get("decision") == "v317-final-readiness-awaiting-approval" and bool(v349.get("pass")) else "blocked",
            f"decision={v349.get('decision')} pass={v349.get('pass')}",
            str(v349.get("path") or ""),
        ),
        ChecklistCheck(
            "v349-current-clean-head",
            "pass" if host_head(v349) == current_head and host_dirty(v349) is False else "blocked",
            f"head={host_head(v349)} current={current_head} dirty={host_dirty(v349)}",
            str(v349.get("path") or ""),
        ),
        ChecklistCheck(
            "v349-blocker-only-approval",
            "pass" if v349.get("remaining_blockers") == ["exact-v317-approval-phrase"] else "blocked",
            f"remaining_blockers={v349.get('remaining_blockers')}",
            str(v349.get("path") or ""),
        ),
        ChecklistCheck(
            "v349-no-device-action",
            "pass" if not bool(v349.get("device_commands_executed")) and not bool(v349.get("device_mutations")) else "blocked",
            f"device_commands_executed={v349.get('device_commands_executed')} device_mutations={v349.get('device_mutations')}",
            str(v349.get("path") or ""),
        ),
    ]
    checks.extend(check_command(views["preflight"], "preflight", EXPECTED_PREFLIGHT_OUT))
    checks.extend(check_command(views["live"], "run", EXPECTED_LIVE_OUT))
    checks.extend(check_command(views["cleanup"], "cleanup", EXPECTED_CLEANUP_OUT))
    out_dirs = {views[name].out_dir for name in ("preflight", "live", "cleanup")}
    checks.append(ChecklistCheck(
        "command-output-dirs-distinct",
        "pass" if len(out_dirs) == 3 and "" not in out_dirs else "blocked",
        f"out_dirs={sorted(out_dirs)}",
        "",
    ))
    return checks, views


def decide(checks: list[ChecklistCheck]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in checks if item.status != "pass"]
    if blocked:
        return (
            "v317-operator-checklist-blocked",
            False,
            "blocked checklist checks: " + ", ".join(blocked),
            "refresh V340/V349 evidence before requesting approval",
            blocked,
        )
    return (
        "v317-operator-checklist-ready",
        True,
        "operator checklist is current and only exact V317 approval remains",
        "execute live command only after exact approval phrase is provided",
        ["exact-v317-approval-phrase"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["detail"], item["evidence"]] for item in manifest["checks"]]
    return "\n".join([
        "# v350 V317 Operator Checklist",
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
        "## Required Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Execution Order After Approval",
        "",
        "1. Confirm the serial bridge is open and responsive.",
        "2. Re-run V349/V350 or run the V351 executor `plan` on a clean HEAD.",
        "3. Run the V351 executor `run` command exactly as generated.",
        "4. Use the executor-produced post-V317 router result to choose the next plan.",
        "5. Run the V351 executor `cleanup` command only if the live proof fails or manual rollback is needed.",
        "",
        "## Preferred Commands",
        "",
        "### V351 executor plan",
        "",
        "```bash",
        manifest["executor_plan_command"],
        "```",
        "",
        "### V351 executor run",
        "",
        "```bash",
        manifest["executor_run_command"],
        "```",
        "",
        "### V351 executor cleanup",
        "",
        "```bash",
        manifest["executor_cleanup_command"],
        "```",
        "",
        "## Internal Raw Commands",
        "",
        "These are kept for contract inspection. Prefer the V351 executor commands above.",
        "",
        "### Raw V317 live proof",
        "",
        "```bash",
        manifest["live_command"],
        "```",
        "",
        "### Raw V317 cleanup",
        "",
        "```bash",
        manifest["cleanup_command"],
        "```",
        "",
        "### Post-V317 router",
        "",
        "```bash",
        manifest["post_router_command"],
        "```",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "evidence"], rows),
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    host = collect_host_metadata()
    current_head = str(host.get("git_head") or "")
    v340 = load_json(args.v340_manifest)
    v349 = load_json(args.v349_manifest)
    checks, views = build_checks(v340, v349, current_head)
    decision, pass_ok, reason, next_step, blockers = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": host,
        "v340_manifest": str(repo_path(args.v340_manifest)),
        "v349_manifest": str(repo_path(args.v349_manifest)),
        "checks": [asdict(item) for item in checks],
        "remaining_blockers": blockers,
        "approval_phrase": APPROVAL_PHRASE,
        "final_readiness_command": "python3 scripts/revalidation/wifi_v317_final_readiness.py --out-dir tmp/wifi/v349-v317-final-readiness check",
        "executor_plan_command": executor_command("plan"),
        "executor_run_command": executor_command("run"),
        "executor_cleanup_command": executor_command("cleanup"),
        "preflight_command": views["preflight"].raw,
        "live_command": views["live"].raw,
        "cleanup_command": views["cleanup"].raw,
        "post_router_command": "python3 scripts/revalidation/wifi_post_v317_router.py --out-dir tmp/wifi/v333-post-v317-router route",
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "This checklist is host-only and does not execute V317.",
            "The live command remains approval-gated by the exact phrase.",
            "No daemon start or Wi-Fi bring-up is included in this checklist.",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("checklist.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
