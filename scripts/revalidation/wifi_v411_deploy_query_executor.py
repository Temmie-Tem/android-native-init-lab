#!/usr/bin/env python3
"""Fail-closed executor for V411 helper v27 deploy and binderized lshal query.

This sequences the V411 tools:

* helper v27 deploy wrapper
* binderized lshal registration-query preflight
* binderized lshal registration-query live runner

Deploy and live query remain separately approved.  Without exact V411 approval
phrases and explicit flags, this wrapper executes no bridge/device command.  It
never performs Wi-Fi scan/connect/link-up or Wi-Fi bring-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v411-deploy-query-executor")
DEPLOY_APPROVAL_PHRASE = "approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up"
LIVE_APPROVAL_PHRASE = "approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up"
DEPLOY_APPROVAL_BLOCKER = "exact-v411-deploy-approval-phrase"
LIVE_APPROVAL_BLOCKER = "exact-v411-binderized-lshal-live-approval-phrase"


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
    parser.add_argument("--deploy-approval-phrase", default="")
    parser.add_argument("--live-approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("deploy")
    subparsers.add_parser("live")
    subparsers.add_parser("full")
    return parser.parse_args()


def ensure_private_run_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        st = os.lstat(path)
        if not os.path.isdir(path) or os.path.islink(path):
            raise RuntimeError(f"refusing unsafe output path: {path}")
        os.chmod(path, 0o700)
    os.chmod(path, 0o700)


def display_command(command: list[str] | str) -> str:
    if isinstance(command, str):
        return command
    return " ".join(shlex.quote(part) for part in command)


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


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload["present"] = True
        payload["path"] = str(resolved)
        return payload
    return {"present": True, "path": str(resolved), "payload_type": type(payload).__name__}


def deploy_approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.deploy_approval_phrase == DEPLOY_APPROVAL_PHRASE


def live_approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.live_approval_phrase == LIVE_APPROVAL_PHRASE


def deploy_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "deploy"


def query_preflight_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "query-preflight"


def query_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "query"


def deploy_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py",
        "--out-dir",
        str(deploy_dir(store)),
        "--approval-phrase",
        args.deploy_approval_phrase,
        "--apply",
        "--assume-yes",
        "run",
    ]


def query_preflight_command(store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py",
        "--out-dir",
        str(query_preflight_dir(store)),
        "preflight",
    ]


def query_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py",
        "--out-dir",
        str(query_dir(store)),
        "--approval-phrase",
        args.live_approval_phrase,
        "--apply",
        "--assume-yes",
        "run",
    ]


def command_string(command: list[str]) -> str:
    return display_command(command)


def deploy_ok(store: EvidenceStore) -> bool:
    manifest = load_json(deploy_dir(store) / "manifest.json")
    return manifest.get("decision") == "execns-helper-v27-deploy-pass" and bool(manifest.get("pass"))


def query_preflight_ok(store: EvidenceStore) -> bool:
    manifest = load_json(query_preflight_dir(store) / "manifest.json")
    return manifest.get("decision") == "v411-hal-registration-query-preflight-ready" and bool(manifest.get("pass"))


def query_manifest(store: EvidenceStore) -> dict[str, Any]:
    return load_json(query_dir(store) / "manifest.json")


def requested_blockers(args: argparse.Namespace) -> list[str]:
    if args.command == "deploy" and not deploy_approved(args):
        return [DEPLOY_APPROVAL_BLOCKER]
    if args.command == "live" and not live_approved(args):
        return [LIVE_APPROVAL_BLOCKER]
    if args.command == "full":
        blockers = []
        if not deploy_approved(args):
            blockers.append(DEPLOY_APPROVAL_BLOCKER)
        if not live_approved(args):
            blockers.append(LIVE_APPROVAL_BLOCKER)
        return blockers
    return []


def base_result(args: argparse.Namespace,
                store: EvidenceStore,
                steps: list[StepResult],
                decision: str,
                pass_ok: bool,
                reason: str,
                next_step: str,
                remaining: list[str],
                deploy_executed: bool,
                query_preflight_executed: bool,
                query_executed: bool,
                device_mutated: bool,
                daemon_started: bool,
                wifi_hal_started: bool) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": [asdict(step) for step in steps],
        "remaining_blockers": remaining,
        "required_deploy_approval_phrase": DEPLOY_APPROVAL_PHRASE,
        "required_live_approval_phrase": LIVE_APPROVAL_PHRASE,
        "planned_deploy_command": command_string(deploy_command(args, store)),
        "planned_query_preflight_command": command_string(query_preflight_command(store)),
        "planned_query_command": command_string(query_command(args, store)),
        "deploy_execution_approved": args.command in {"deploy", "full"} and deploy_approved(args),
        "live_execution_approved": args.command in {"live", "full"} and live_approved(args),
        "device_commands_executed": deploy_executed or query_preflight_executed or query_executed,
        "device_mutations": device_mutated,
        "daemon_start_executed": daemon_started,
        "wifi_hal_start_executed": wifi_hal_started,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "wificond/supplicant/hostapd start",
            "CNSS lifecycle or diag daemon start",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V411 Deploy Query Executor",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- deploy_execution_approved: `{manifest['deploy_execution_approved']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Steps",
        "",
    ]
    for step in manifest["steps"]:
        lines.append(f"- {'OK' if step['ok'] else 'FAIL'} `{step['name']}` rc={step['rc']} skipped={step['skipped']} file=`{step['file']}`")
    lines.extend([
        "",
        "## Required Approval Phrases",
        "",
        f"- deploy: `{manifest['required_deploy_approval_phrase']}`",
        f"- live: `{manifest['required_live_approval_phrase']}`",
        "",
        "## Planned Commands",
        "",
        "### Deploy",
        "",
        "```bash",
        manifest["planned_deploy_command"],
        "```",
        "",
        "### Query Preflight",
        "",
        "```bash",
        manifest["planned_query_preflight_command"],
        "```",
        "",
        "### Query",
        "",
        "```bash",
        manifest["planned_query_command"],
        "```",
        "",
    ])
    return "\n".join(lines)


def refusal_manifest(args: argparse.Namespace, store: EvidenceStore, blockers: list[str]) -> dict[str, Any]:
    return base_result(
        args,
        store,
        [],
        "v411-deploy-query-executor-approval-required",
        True,
        "exact V411 approval phrase and explicit flags are required for requested live action",
        "provide exact V411 approval phrase only if accepting the scoped action",
        blockers,
        False,
        False,
        False,
        False,
        False,
        False,
    )


def query_result(args: argparse.Namespace, store: EvidenceStore, steps: list[StepResult], prefix: str) -> dict[str, Any]:
    query = query_manifest(store)
    decision = str(query.get("decision") or "v411-query-missing")
    pass_ok = bool(query.get("pass"))
    return base_result(
        args,
        store,
        steps,
        f"v411-deploy-query-executor-{prefix}-{decision}",
        pass_ok,
        f"query decision={query.get('decision')} pass={query.get('pass')}",
        str(query.get("next_step") or "inspect V411 query evidence"),
        [],
        args.command == "full",
        True,
        True,
        True,
        True,
        True,
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    blockers = requested_blockers(args)
    if blockers:
        return refusal_manifest(args, store, blockers)

    steps: list[StepResult] = []
    deploy_executed = False
    query_preflight_executed = False
    query_executed = False
    device_mutated = False
    daemon_started = False
    wifi_hal_started = False

    if args.command == "plan":
        steps.append(execute_step(store, "deploy", deploy_command(args, store), args.timeout, execute=False))
        steps.append(execute_step(store, "query-preflight", query_preflight_command(store), args.timeout, execute=False))
        steps.append(execute_step(store, "query", query_command(args, store), args.timeout, execute=False))
        return base_result(
            args, store, steps,
            "v411-deploy-query-executor-plan-ready",
            True,
            "plan-only; deploy/query remain approval-gated",
            "run V411 deploy with exact approval before binderized query live gate",
            [DEPLOY_APPROVAL_BLOCKER, LIVE_APPROVAL_BLOCKER],
            deploy_executed, query_preflight_executed, query_executed,
            device_mutated, daemon_started, wifi_hal_started,
        )

    if args.command in {"deploy", "full"}:
        steps.append(execute_step(store, "deploy", deploy_command(args, store), args.timeout, execute=True))
        deploy_executed = True
        device_mutated = True
        if not deploy_ok(store):
            return base_result(
                args, store, steps,
                "v411-deploy-query-executor-deploy-review",
                False,
                f"deploy decision={load_json(deploy_dir(store) / 'manifest.json').get('decision')}",
                "inspect deploy evidence before query preflight/live execution",
                ["v411-deploy-review"],
                deploy_executed, query_preflight_executed, query_executed,
                device_mutated, daemon_started, wifi_hal_started,
            )
        if args.command == "deploy":
            return base_result(
                args, store, steps,
                "v411-deploy-query-executor-deploy-pass",
                True,
                f"deploy decision={load_json(deploy_dir(store) / 'manifest.json').get('decision')}",
                "run V411 binderized query preflight, then exact live query approval if ready",
                [LIVE_APPROVAL_BLOCKER],
                deploy_executed, query_preflight_executed, query_executed,
                device_mutated, daemon_started, wifi_hal_started,
            )

    steps.append(execute_step(store, "query-preflight", query_preflight_command(store), args.timeout, execute=True))
    query_preflight_executed = True
    if not query_preflight_ok(store):
        return base_result(
            args, store, steps,
            "v411-deploy-query-executor-query-preflight-blocked",
            False,
            f"query preflight decision={load_json(query_preflight_dir(store) / 'manifest.json').get('decision')}",
            "inspect query preflight evidence before live query execution",
            ["v411-query-preflight"],
            deploy_executed, query_preflight_executed, query_executed,
            device_mutated, daemon_started, wifi_hal_started,
        )

    steps.append(execute_step(store, "query", query_command(args, store), args.timeout, execute=True))
    query_executed = True
    device_mutated = True
    daemon_started = True
    wifi_hal_started = True
    return query_result(args, store, steps, "full" if args.command == "full" else "live")


def main() -> int:
    args = parse_args()
    run_dir = repo_path(args.out_dir)
    ensure_private_run_dir(run_dir)
    store = EvidenceStore(run_dir)
    store.mkdir("steps")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"deploy_execution_approved: {manifest['deploy_execution_approved']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
