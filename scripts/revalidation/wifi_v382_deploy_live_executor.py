#!/usr/bin/env python3
"""Fail-closed executor for V382 helper deploy and service-manager live smoke.

This script sequences the already-validated V382 tools:

* final readiness gate
* helper v14 deploy
* service-manager property-runtime live runner
* V382 result router
* runtime-gap classifier when needed

Approved actions remain split: deploy and live start have separate exact
approval phrases. Without the relevant phrase and explicit flags, no bridge
command is executed by this wrapper.
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
from wifi_service_manager_start_only_approval_packet import APPROVAL_PHRASE as LIVE_APPROVAL_PHRASE


DEFAULT_OUT_DIR = Path("tmp/wifi/v382-deploy-live-executor")
DEPLOY_APPROVAL_PHRASE = "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up"
DEPLOY_APPROVAL_BLOCKER = "exact-v382-deploy-approval-phrase"
LIVE_APPROVAL_BLOCKER = "exact-v373-service-manager-approval-phrase"


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
    parser.add_argument("--timeout", type=int, default=360)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("deploy")
    subparsers.add_parser("live")
    subparsers.add_parser("full")
    return parser.parse_args()


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
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def deploy_approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.deploy_approval_phrase == DEPLOY_APPROVAL_PHRASE


def live_approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.live_approval_phrase == LIVE_APPROVAL_PHRASE


def readiness_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "readiness"


def deploy_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "deploy"


def live_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "live"


def live_preflight_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "live-preflight"


def route_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "route"


def classify_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "classify"


def readiness_command(store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_v382_final_readiness.py",
        "--out-dir",
        str(readiness_dir(store)),
        "check",
    ]


def deploy_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py",
        "--out-dir",
        str(deploy_dir(store)),
        "--approval-phrase",
        args.deploy_approval_phrase,
        "--apply",
        "--assume-yes",
        "run",
    ]


def live_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py",
        "--out-dir",
        str(live_dir(store)),
        "--approval-phrase",
        args.live_approval_phrase,
        "--apply",
        "--assume-yes",
        "run",
    ]


def live_preflight_command(store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py",
        "--out-dir",
        str(live_preflight_dir(store)),
        "preflight",
    ]


def route_command(store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py",
        "--out-dir",
        str(route_dir(store)),
        "--v376-manifest",
        str(live_dir(store) / "manifest.json"),
        "route",
    ]


def classify_command(store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py",
        "--out-dir",
        str(classify_dir(store)),
        "--v376-manifest",
        str(live_dir(store) / "manifest.json"),
        "classify",
    ]


def command_string(command: list[str]) -> str:
    return display_command(command)


def readiness_ok(store: EvidenceStore) -> bool:
    manifest = load_json(readiness_dir(store) / "manifest.json")
    return manifest.get("decision") == "v382-final-readiness-awaiting-deploy-approval" and bool(manifest.get("pass"))


def deploy_ok(store: EvidenceStore) -> bool:
    manifest = load_json(deploy_dir(store) / "manifest.json")
    return manifest.get("decision") == "execns-helper-v14-deploy-pass" and bool(manifest.get("pass"))


def live_ready_or_done(store: EvidenceStore) -> bool:
    manifest = load_json(live_dir(store) / "manifest.json")
    return bool(manifest.get("present")) and str(manifest.get("decision")).startswith("service-manager-start-only-live-")


def live_preflight_ok(store: EvidenceStore) -> bool:
    manifest = load_json(live_preflight_dir(store) / "manifest.json")
    return manifest.get("decision") == "service-manager-start-only-live-preflight-ready" and bool(manifest.get("pass"))


def route_pass(store: EvidenceStore) -> bool:
    manifest = load_json(route_dir(store) / "manifest.json")
    return bool(manifest.get("present")) and bool(manifest.get("pass"))


def route_blockers(store: EvidenceStore) -> list[str]:
    manifest = load_json(route_dir(store) / "manifest.json")
    blockers = manifest.get("remaining_blockers")
    if isinstance(blockers, list):
        return [str(item) for item in blockers]
    return []


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V382 Deploy Live Executor",
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
        "### Live",
        "",
        "```bash",
        manifest["planned_live_command"],
        "```",
        "",
    ])
    return "\n".join(lines)


def refusal_manifest(args: argparse.Namespace, store: EvidenceStore, blockers: list[str]) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "v382-deploy-live-executor-approval-required",
        "pass": True,
        "reason": "exact approval phrase and explicit flags are required for requested live action",
        "next_step": "provide exact approval phrase only if accepting the V382 handoff scope",
        "host": collect_host_metadata(),
        "steps": [],
        "remaining_blockers": blockers,
        "required_deploy_approval_phrase": DEPLOY_APPROVAL_PHRASE,
        "required_live_approval_phrase": LIVE_APPROVAL_PHRASE,
        "planned_deploy_command": command_string(deploy_command(args, store)),
        "planned_live_command": command_string(live_command(args, store)),
        "deploy_execution_approved": False,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


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
                live_preflight_executed: bool,
                live_executed: bool,
                device_mutated: bool,
                daemon_started: bool,
                wifi_started: bool) -> dict[str, Any]:
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
        "planned_live_preflight_command": command_string(live_preflight_command(store)),
        "planned_live_command": command_string(live_command(args, store)),
        "deploy_execution_approved": args.command in {"deploy", "full"} and deploy_approved(args),
        "live_execution_approved": args.command in {"live", "full"} and live_approved(args),
        "device_commands_executed": deploy_executed or live_preflight_executed or live_executed,
        "device_mutations": device_mutated,
        "daemon_start_executed": daemon_started,
        "wifi_bringup_executed": wifi_started,
        "explicitly_not_approved": [
            "Wi-Fi HAL start",
            "CNSS/diag start",
            "wificond/supplicant/hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def live_route_and_classify(args: argparse.Namespace, store: EvidenceStore, steps: list[StepResult]) -> tuple[str, bool, str, str, list[str]]:
    if live_ready_or_done(store):
        steps.append(execute_step(store, "result-router", route_command(store), args.timeout, execute=True))
    route = load_json(route_dir(store) / "manifest.json")
    if load_json(live_dir(store) / "manifest.json").get("decision") == "service-manager-start-only-live-runtime-gap":
        steps.append(execute_step(store, "runtime-gap-classifier", classify_command(store), args.timeout, execute=True))
    return (
        "pass" if route_pass(store) else "review",
        route_pass(store),
        f"route decision={route.get('decision')} pass={route.get('pass')}",
        str(route.get("next_step") or "inspect V382 route"),
        route_blockers(store),
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    blockers = requested_blockers(args)
    if blockers:
        return refusal_manifest(args, store, blockers)

    steps: list[StepResult] = []
    deploy_executed = False
    live_preflight_executed = False
    live_executed = False
    device_mutated = False
    daemon_started = False
    wifi_started = False

    if args.command in {"plan", "deploy", "full"}:
        steps.append(execute_step(store, "final-readiness", readiness_command(store), args.timeout, execute=True))
        if not readiness_ok(store):
            return base_result(
                args, store, steps,
                "v382-deploy-live-executor-readiness-blocked",
                False,
                "V382 final readiness did not pass",
                "inspect readiness manifest before deploy/live execution",
                ["v382-final-readiness"],
                deploy_executed, live_preflight_executed, live_executed,
                device_mutated, daemon_started, wifi_started,
            )

    if args.command == "plan":
        steps.append(execute_step(store, "deploy", deploy_command(args, store), args.timeout, execute=False))
        steps.append(execute_step(store, "live-preflight", live_preflight_command(store), args.timeout, execute=False))
        steps.append(execute_step(store, "live", live_command(args, store), args.timeout, execute=False))
        return base_result(
            args, store, steps,
            "v382-deploy-live-executor-plan-ready",
            True,
            "V382 final readiness passes; deploy/live remain approval-gated",
            "provide exact V382 deploy approval phrase only if accepting the approved scope",
            [DEPLOY_APPROVAL_BLOCKER, LIVE_APPROVAL_BLOCKER],
            deploy_executed, live_preflight_executed, live_executed,
            device_mutated, daemon_started, wifi_started,
        )

    if args.command in {"deploy", "full"}:
        steps.append(execute_step(store, "deploy", deploy_command(args, store), args.timeout, execute=True))
        deploy_executed = True
        device_mutated = True
        if not deploy_ok(store):
            return base_result(
                args, store, steps,
                "v382-deploy-live-executor-deploy-review",
                False,
                f"deploy decision={load_json(deploy_dir(store) / 'manifest.json').get('decision')}",
                "inspect deploy evidence before live execution",
                ["v382-deploy-review"],
                deploy_executed, live_preflight_executed, live_executed,
                device_mutated, daemon_started, wifi_started,
            )
        if args.command == "deploy":
            return base_result(
                args, store, steps,
                "v382-deploy-live-executor-deploy-pass",
                True,
                f"deploy decision={load_json(deploy_dir(store) / 'manifest.json').get('decision')}",
                "run V382 live after exact live approval phrase",
                [LIVE_APPROVAL_BLOCKER],
                deploy_executed, live_preflight_executed, live_executed,
                device_mutated, daemon_started, wifi_started,
            )

    steps.append(execute_step(store, "live-preflight", live_preflight_command(store), args.timeout, execute=True))
    live_preflight_executed = True
    if not live_preflight_ok(store):
        return base_result(
            args, store, steps,
            "v382-deploy-live-executor-live-preflight-blocked",
            False,
            f"live preflight decision={load_json(live_preflight_dir(store) / 'manifest.json').get('decision')}",
            "inspect live preflight evidence before live execution",
            ["v382-live-preflight"],
            deploy_executed, live_preflight_executed, live_executed,
            device_mutated, daemon_started, wifi_started,
        )

    steps.append(execute_step(store, "live", live_command(args, store), args.timeout, execute=True))
    live_executed = True
    device_mutated = True
    daemon_started = True
    route_label, pass_ok, reason, next_step, remaining = live_route_and_classify(args, store, steps)
    decision_prefix = "full" if args.command == "full" else "live"
    return base_result(
        args, store, steps,
        f"v382-deploy-live-executor-{decision_prefix}-{route_label}",
        pass_ok,
        reason,
        next_step,
        remaining,
        deploy_executed, live_preflight_executed, live_executed,
        device_mutated, daemon_started, wifi_started,
    )


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
    print(f"deploy_execution_approved: {manifest['deploy_execution_approved']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
