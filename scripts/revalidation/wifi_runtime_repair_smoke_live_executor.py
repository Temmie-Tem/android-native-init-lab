#!/usr/bin/env python3
"""Fail-closed executor for V366 bounded runtime repair smoke.

The executor refreshes the V369 approval packet and V370 result router, then
runs the approved V366 smoke or cleanup only when the exact approval phrase and
both mutation flags are supplied.  It never starts service-manager, Wi-Fi HAL,
or Wi-Fi scan/connect/link-up.
"""

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
from wifi_runtime_repair_smoke import APPROVAL_PHRASE


DEFAULT_OUT_DIR = Path("tmp/wifi/v371-runtime-repair-smoke-live-executor")
DEFAULT_LIVE_OUT_DIR = Path("tmp/wifi/v366-runtime-repair-smoke-live-approved")
DEFAULT_CLEANUP_OUT_DIR = Path("tmp/wifi/v366-runtime-repair-smoke-cleanup-approved")
APPROVAL_BLOCKER = "exact-v366-approval-phrase"


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
    parser.add_argument("--live-out-dir", type=Path, default=DEFAULT_LIVE_OUT_DIR)
    parser.add_argument("--cleanup-out-dir", type=Path, default=DEFAULT_CLEANUP_OUT_DIR)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--timeout", type=int, default=360)
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


def approved(args: argparse.Namespace) -> bool:
    return args.approval_phrase == APPROVAL_PHRASE and args.apply and args.assume_yes


def packet_dir(args: argparse.Namespace, store: EvidenceStore) -> Path:
    return store.run_dir / "packet"


def router_dir(store: EvidenceStore, label: str) -> Path:
    return store.run_dir / label


def packet_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_runtime_repair_smoke_approval_packet.py",
        "--out-dir",
        str(packet_dir(args, store)),
        "--live-out-dir",
        str(repo_path(args.live_out_dir)),
        "--cleanup-out-dir",
        str(repo_path(args.cleanup_out_dir)),
        "run",
    ]


def router_command(args: argparse.Namespace, store: EvidenceStore, label: str, smoke_manifest: Path) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_runtime_repair_smoke_result_router.py",
        "--out-dir",
        str(router_dir(store, label)),
        "--packet-manifest",
        str(packet_dir(args, store) / "manifest.json"),
        "--smoke-manifest",
        str(repo_path(smoke_manifest)),
        "--cleanup-manifest",
        str(repo_path(args.cleanup_out_dir / "manifest.json")),
        "route",
    ]


def packet_manifest_path(args: argparse.Namespace, store: EvidenceStore) -> Path:
    return packet_dir(args, store) / "manifest.json"


def approval_packet_ready(packet: dict[str, Any]) -> bool:
    return packet.get("decision") == "runtime-repair-smoke-approval-packet-ready" and bool(packet.get("pass"))


def packet_approval_command(packet: dict[str, Any]) -> str:
    return str(packet.get("approval_command") or "")


def packet_cleanup_command(packet: dict[str, Any]) -> str:
    return str(packet.get("cleanup_command") or "")


def route_manifest(store: EvidenceStore, label: str) -> dict[str, Any]:
    return load_json(router_dir(store, label) / "manifest.json")


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V371 Runtime Repair Smoke Live Executor",
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
        "## Live Command",
        "",
        "```bash",
        manifest.get("live_command", ""),
        "```",
        "",
        "## Cleanup Command",
        "",
        "```bash",
        manifest.get("cleanup_command", ""),
        "```",
        "",
    ])
    return "\n".join(lines)


def refusal_manifest(args: argparse.Namespace) -> dict[str, Any]:
    reason = "exact V366 approval phrase and mutation flags are required"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "runtime-repair-smoke-live-executor-approval-required",
        "pass": True,
        "reason": reason,
        "next_step": "provide exact V366 approval phrase only if accepting the V369 approval packet scope",
        "host": collect_host_metadata(),
        "steps": [],
        "approval_phrase": APPROVAL_PHRASE,
        "approval_supplied": False,
        "live_command": "",
        "cleanup_command": "",
        "router_decision": "not-run",
        "remaining_blockers": [APPROVAL_BLOCKER],
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command in {"run", "cleanup"} and not approved(args):
        return refusal_manifest(args)

    steps: list[StepResult] = []
    steps.append(execute_step(store, "approval-packet", packet_command(args, store), args.timeout, execute=True))
    packet = load_json(packet_manifest_path(args, store))
    packet_ok = approval_packet_ready(packet)
    live_command = packet_approval_command(packet)
    cleanup_command = packet_cleanup_command(packet)

    if not packet_ok:
        decision = "runtime-repair-smoke-live-executor-readiness-blocked"
        pass_ok = False
        reason = f"packet not ready: decision={packet.get('decision')} pass={packet.get('pass')}"
        next_step = "repair V369 approval packet before live smoke"
        remaining = ["v369-approval-packet"]
        router_decision = "not-run"
        device_executed = bool(steps)
        device_mutated = False
    elif args.command == "plan":
        steps.append(execute_step(store, "v366-live-smoke", shlex.split(live_command), args.timeout, execute=False))
        steps.append(execute_step(store, "v366-cleanup", shlex.split(cleanup_command), args.timeout, execute=False))
        steps.append(execute_step(store, "result-router", router_command(args, store, "router-plan", args.live_out_dir / "manifest.json"), args.timeout, execute=True))
        route = route_manifest(store, "router-plan")
        route_decision = str(route.get("decision") or "missing")
        if route_decision == "runtime-repair-smoke-router-awaiting-approval":
            decision = "runtime-repair-smoke-live-executor-plan-ready"
            next_step = "run executor with exact approval phrase only if accepting the V369 packet scope"
            remaining = [APPROVAL_BLOCKER]
        elif route_decision == "runtime-repair-smoke-router-service-runtime-next-ready":
            decision = "runtime-repair-smoke-live-executor-current-next-ready"
            next_step = "create service-manager start-only approval packet"
            remaining = ["service-manager-start-only-approval-packet"]
        else:
            decision = "runtime-repair-smoke-live-executor-plan-review"
            next_step = "inspect V366/V370 evidence before another live action"
            remaining = ["v366-live-smoke-review"]
        pass_ok = decision != "runtime-repair-smoke-live-executor-plan-review"
        reason = f"router decision={route.get('decision')} pass={route.get('pass')}"
        router_decision = route_decision
        device_executed = True
        device_mutated = False
    elif args.command == "run":
        steps.append(execute_step(store, "v366-live-smoke", shlex.split(live_command), args.timeout, execute=True))
        steps.append(execute_step(store, "result-router", router_command(args, store, "router-after-run", args.live_out_dir / "manifest.json"), args.timeout, execute=True))
        route = route_manifest(store, "router-after-run")
        route_decision = str(route.get("decision") or "missing")
        pass_ok = route_decision == "runtime-repair-smoke-router-service-runtime-next-ready" and bool(route.get("pass"))
        decision = "runtime-repair-smoke-live-executor-run-pass" if pass_ok else "runtime-repair-smoke-live-executor-run-needs-review"
        reason = f"router decision={route_decision} pass={route.get('pass')}"
        next_step = "create service-manager start-only approval packet" if pass_ok else "inspect V366 evidence and run approved cleanup if required"
        remaining = [] if pass_ok else ["v366-live-smoke-review"]
        router_decision = route_decision
        device_executed = True
        device_mutated = True
    else:
        steps.append(execute_step(store, "v366-cleanup", shlex.split(cleanup_command), args.timeout, execute=True))
        steps.append(execute_step(store, "result-router", router_command(args, store, "router-after-cleanup", args.cleanup_out_dir / "manifest.json"), args.timeout, execute=True))
        route = route_manifest(store, "router-after-cleanup")
        route_decision = str(route.get("decision") or "missing")
        cleanup_ok = steps[-2].ok and route_decision in {"runtime-repair-smoke-router-cleanup-done", "runtime-repair-smoke-router-awaiting-approval"}
        decision = "runtime-repair-smoke-live-executor-cleanup-pass" if cleanup_ok else "runtime-repair-smoke-live-executor-cleanup-review"
        pass_ok = cleanup_ok
        reason = f"cleanup rc={steps[-2].rc} router decision={route_decision}"
        next_step = "rerun V366 preflight/router before another live action" if cleanup_ok else "manual review required before further live action"
        remaining = [] if cleanup_ok else ["v366-cleanup-review"]
        router_decision = route_decision
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
        "approval_phrase": APPROVAL_PHRASE,
        "approval_supplied": approved(args),
        "packet_manifest": str(packet_manifest_path(args, store)),
        "live_manifest": str(repo_path(args.live_out_dir / "manifest.json")),
        "cleanup_manifest": str(repo_path(args.cleanup_out_dir / "manifest.json")),
        "live_command": live_command,
        "cleanup_command": cleanup_command,
        "router_decision": router_decision,
        "remaining_blockers": remaining,
        "live_execution_approved": bool(args.command in {"run", "cleanup"} and approved(args)),
        "device_commands_executed": device_executed,
        "device_mutations": device_mutated,
        "explicitly_not_approved": [
            "service-manager/HAL start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
        ],
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
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
