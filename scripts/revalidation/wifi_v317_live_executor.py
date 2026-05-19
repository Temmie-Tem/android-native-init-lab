#!/usr/bin/env python3
"""Fail-closed executor wrapper for V317 minimal live proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v351-v317-live-executor")
DEFAULT_V350 = Path("tmp/wifi/v350-v317-operator-checklist/manifest.json")
DEFAULT_V317 = Path("tmp/wifi/v317-private-property-namespace-proof/manifest.json")
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class StepResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    skipped: bool
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v350-manifest", type=Path, default=DEFAULT_V350)
    parser.add_argument("--v317-manifest", type=Path, default=DEFAULT_V317)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--allow-device-mutation", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    subparsers.add_parser("cleanup")
    return parser.parse_args()


def display_command(command: list[str] | str) -> str:
    if isinstance(command, str):
        return command
    return " ".join(shlex.quote(part) for part in command)


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path(Path(".")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - executor evidence preserves failure details
        return None, "", str(exc), time.monotonic() - started


def write_step(store: EvidenceStore,
               name: str,
               command: list[str] | str,
               text: str,
               error: str,
               rc: int | None,
               duration: float,
               skipped: bool = False,
               ok_override: bool | None = None) -> StepResult:
    body = "\n".join([
        f"$ {display_command(command)}",
        text.rstrip() if text else error.rstrip(),
        f"rc={rc}",
        "",
    ])
    path = store.write_text(f"steps/{name}.txt", body)
    ok = ok_override if ok_override is not None else rc == 0
    return StepResult(name, display_command(command), bool(ok), rc, duration, str(path.relative_to(store.run_dir)), skipped, error)


def execute_step(store: EvidenceStore,
                 name: str,
                 command: list[str],
                 timeout: int,
                 execute: bool) -> StepResult:
    if not execute:
        return write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    rc, text, error, duration = run_process(command, timeout)
    return write_step(store, name, command, text, error, rc, duration)


def refresh_commands() -> list[tuple[str, list[str]]]:
    return [
        (
            "v349-final-readiness",
            [
                "python3",
                "scripts/revalidation/wifi_v317_final_readiness.py",
                "--out-dir",
                "tmp/wifi/v349-v317-final-readiness",
                "check",
            ],
        ),
        (
            "v350-operator-checklist",
            [
                "python3",
                "scripts/revalidation/wifi_v317_operator_checklist.py",
                "--out-dir",
                "tmp/wifi/v350-v317-operator-checklist",
                "build",
            ],
        ),
    ]


def approved(args: argparse.Namespace) -> bool:
    return args.approval_phrase == APPROVAL_PHRASE and args.allow_device_mutation and args.assume_yes


def validate_v350(v350: dict[str, Any]) -> tuple[bool, str]:
    host = collect_host_metadata()
    if not v350.get("present"):
        return False, "v350 manifest missing"
    if v350.get("decision") != "v317-operator-checklist-ready" or not bool(v350.get("pass")):
        return False, f"v350 not ready: decision={v350.get('decision')} pass={v350.get('pass')}"
    if v350.get("remaining_blockers") != ["exact-v317-approval-phrase"]:
        return False, f"unexpected blockers: {v350.get('remaining_blockers')}"
    v350_host = v350.get("host") if isinstance(v350.get("host"), dict) else {}
    if v350_host.get("git_head") != host.get("git_head") or v350_host.get("git_dirty") is not False or host.get("git_dirty") is not False:
        return False, f"stale/dirty v350: v350_head={v350_host.get('git_head')} current={host.get('git_head')} v350_dirty={v350_host.get('git_dirty')} current_dirty={host.get('git_dirty')}"
    return True, "v350 ready"


def live_result_ok(v317: dict[str, Any]) -> bool:
    return v317.get("present") and v317.get("decision") == "private-property-namespace-proof-pass" and bool(v317.get("pass"))


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# v351 V317 Live Executor",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Steps",
        "",
    ]
    for step in manifest["steps"]:
        lines.append(f"- {'OK' if step['ok'] else 'FAIL'} `{step['name']}` rc={step['rc']} skipped={step['skipped']} file=`{step['file']}`")
    lines.extend([
        "",
        "## Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Commands",
        "",
        "### Live",
        "",
        "```bash",
        manifest["live_command"],
        "```",
        "",
        "### Cleanup",
        "",
        "```bash",
        manifest["cleanup_command"],
        "```",
        "",
    ])
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[StepResult] = []
    approval_ok = approved(args)
    if args.command in {"run", "cleanup"} and not approval_ok:
        reason = "exact V317 approval phrase and mutation flags are required"
        v350 = load_json(args.v350_manifest)
        return {
            "generated_at": now_iso(),
            "command": args.command,
            "decision": "v317-live-executor-approval-required",
            "pass": False,
            "reason": reason,
            "next_step": "provide exact V317 approval phrase only if accepting the V350 checklist scope",
            "host": collect_host_metadata(),
            "steps": [],
            "v350_manifest": str(repo_path(args.v350_manifest)),
            "v317_manifest": str(repo_path(args.v317_manifest)),
            "v350_decision": v350.get("decision"),
            "approval_phrase": APPROVAL_PHRASE,
            "live_command": str(v350.get("live_command") or ""),
            "cleanup_command": str(v350.get("cleanup_command") or ""),
            "post_router_command": str(v350.get("post_router_command") or ""),
            "live_execution_approved": False,
            "device_commands_executed": False,
            "device_mutations": False,
        }

    for name, command in refresh_commands():
        steps.append(execute_step(store, name, command, args.timeout, execute=True))
    v350 = load_json(args.v350_manifest)
    v350_ok, v350_reason = validate_v350(v350)
    live_command = str(v350.get("live_command") or "")
    cleanup_command = str(v350.get("cleanup_command") or "")
    post_router_command = str(v350.get("post_router_command") or "")

    if not v350_ok:
        decision = "v317-live-executor-readiness-blocked"
        pass_ok = False
        reason = v350_reason
        next_step = "repair V349/V350 readiness before V317 live proof"
        device_executed = False
        device_mutated = False
    elif args.command == "plan":
        steps.append(execute_step(store, "v317-live-proof", shlex.split(live_command), args.timeout, execute=False))
        steps.append(execute_step(store, "v317-cleanup", shlex.split(cleanup_command), args.timeout, execute=False))
        decision = "v317-live-executor-plan-ready"
        pass_ok = True
        reason = "V350 checklist is current; live proof remains approval-gated"
        next_step = "run executor with exact approval phrase only if accepting the approved scope"
        device_executed = False
        device_mutated = False
    elif args.command == "run":
        steps.append(execute_step(store, "v317-live-proof", shlex.split(live_command), args.timeout, execute=True))
        steps.append(execute_step(store, "post-v317-router", shlex.split(post_router_command), args.timeout, execute=True))
        v317 = load_json(args.v317_manifest)
        pass_ok = live_result_ok(v317)
        decision = "v317-live-executor-run-pass" if pass_ok else "v317-live-executor-run-needs-review"
        reason = f"v317 decision={v317.get('decision')} pass={v317.get('pass')}"
        next_step = "run V320 plan via router recommendation" if pass_ok else "inspect V317 evidence and run cleanup if required"
        device_executed = True
        device_mutated = True
    else:
        steps.append(execute_step(store, "v317-cleanup", shlex.split(cleanup_command), args.timeout, execute=True))
        steps.append(execute_step(store, "post-v317-router", shlex.split(post_router_command), args.timeout, execute=True))
        cleanup_ok = steps[-2].ok
        decision = "v317-live-executor-cleanup-pass" if cleanup_ok else "v317-live-executor-cleanup-failed"
        pass_ok = cleanup_ok
        reason = f"cleanup rc={steps[-2].rc}"
        next_step = "rerun V349/V350 readiness before another V317 attempt" if cleanup_ok else "manual review required before further live action"
        device_executed = True
        device_mutated = True

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": [asdict(step) for step in steps],
        "v350_manifest": str(repo_path(args.v350_manifest)),
        "v317_manifest": str(repo_path(args.v317_manifest)),
        "approval_phrase": APPROVAL_PHRASE,
        "approval_supplied": approval_ok,
        "live_command": live_command,
        "cleanup_command": cleanup_command,
        "post_router_command": post_router_command,
        "live_execution_approved": bool(args.command in {"run", "cleanup"} and approval_ok),
        "device_commands_executed": device_executed,
        "device_mutations": device_mutated,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("steps")
    manifest = build_manifest(args, store)
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
