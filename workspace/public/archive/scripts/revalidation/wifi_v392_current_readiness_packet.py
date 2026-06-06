#!/usr/bin/env python3
"""Build a current V392 approval-readiness packet from safe evidence.

This is host-only. It reads existing preflight/no-approval/router manifests,
emits the exact approved command sequence, and never opens the serial bridge or
mutates the device.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v395-v392-current-readiness-packet")
DEPLOY_APPROVAL_PHRASE = "approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up"
LIVE_APPROVAL_PHRASE = "approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up"


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--deploy-preflight", type=Path, required=False)
    parser.add_argument("--live-preflight", type=Path, required=False)
    parser.add_argument("--executor-manifest", type=Path, required=False)
    parser.add_argument("--router-manifest", type=Path, required=False)
    parser.add_argument("--version-json", type=Path, required=False)
    parser.add_argument("--status-json", type=Path, required=False)
    parser.add_argument("--selftest-json", type=Path, required=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("packet")
    subparsers.add_parser("regression")
    return parser.parse_args()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": ""}
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("checks")
    return value if isinstance(value, list) else []


def check_named(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in checks(manifest):
        if check.get("name") == name:
            return check
    return {}


def check_status(manifest: dict[str, Any], name: str) -> str:
    return str(check_named(manifest, name).get("status") or "missing")


def no_action(manifest: dict[str, Any]) -> bool:
    return not any(
        bool(manifest.get(key))
        for key in ("device_commands_executed", "device_mutations", "daemon_start_executed", "wifi_bringup_executed")
    )


def no_mutating_action(manifest: dict[str, Any]) -> bool:
    return not any(
        bool(manifest.get(key))
        for key in ("device_mutations", "daemon_start_executed", "wifi_bringup_executed")
    )


def manifest_ref(manifest: dict[str, Any]) -> str:
    return str(manifest.get("path") or "")


def add_check(checks_list: list[ReadinessCheck],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: str = "",
              next_step: str = "") -> None:
    checks_list.append(ReadinessCheck(name, status, severity, detail, evidence, next_step))


def device_json_ok(payload: dict[str, Any], label: str) -> tuple[bool, str]:
    if not payload.get("present"):
        return False, "missing"
    rc = payload.get("rc")
    status = payload.get("status")
    return rc == 0 and status == "ok", f"rc={rc} status={status}"


def shell_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def approved_executor_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_v392_deploy_live_executor.py",
        "--out-dir",
        "tmp/wifi/v392-approved-full-$(date +%Y%m%d-%H%M%S)",
        "--deploy-approval-phrase",
        DEPLOY_APPROVAL_PHRASE,
        "--live-approval-phrase",
        LIVE_APPROVAL_PHRASE,
        "--apply",
        "--assume-yes",
        "full",
    ])


def post_live_router_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_v392_post_live_router.py",
        "--out-dir",
        "tmp/wifi/v394-post-v392-route-$(date +%Y%m%d-%H%M%S)",
        "--executor-manifest",
        "tmp/wifi/<v392-approved-full-run>/manifest.json",
        "route",
    ])


def build_checks(deploy: dict[str, Any],
                 live: dict[str, Any],
                 executor: dict[str, Any],
                 router: dict[str, Any],
                 version: dict[str, Any],
                 status: dict[str, Any],
                 selftest: dict[str, Any]) -> list[ReadinessCheck]:
    result: list[ReadinessCheck] = []

    deploy_expected = (
        deploy.get("present")
        and deploy.get("decision") == "execns-helper-v21-deploy-blocked"
        and check_status(deploy, "remote-helper-v21") == "needs-deploy"
        and check_status(deploy, "approval-gate") == "needs-operator"
        and no_mutating_action(deploy)
    )
    add_check(
        result,
        "deploy-preflight",
        "pass" if deploy_expected else "blocked",
        "blocker",
        f"decision={deploy.get('decision')} remote-helper-v21={check_status(deploy, 'remote-helper-v21')} approval={check_status(deploy, 'approval-gate')}",
        manifest_ref(deploy),
        "expected state before V392 deploy is remote helper v20 plus exact deploy approval pending",
    )

    live_expected = (
        live.get("present")
        and live.get("decision") == "service-manager-start-only-live-blocked"
        and check_status(live, "helper-v21") == "blocked"
        and check_status(live, "approval-gate") == "needs-operator"
        and no_mutating_action(live)
    )
    add_check(
        result,
        "live-preflight",
        "pass" if live_expected else "blocked",
        "blocker",
        f"decision={live.get('decision')} helper-v21={check_status(live, 'helper-v21')} approval={check_status(live, 'approval-gate')}",
        manifest_ref(live),
        "expected state before V392 live is helper-v21 deploy pending plus exact live approval pending",
    )

    executor_expected = (
        executor.get("present")
        and executor.get("decision") == "v392-deploy-live-executor-approval-required"
        and bool(executor.get("pass"))
        and no_action(executor)
    )
    add_check(
        result,
        "noapproval-executor",
        "pass" if executor_expected else "blocked",
        "blocker",
        f"decision={executor.get('decision')} pass={executor.get('pass')}",
        manifest_ref(executor),
        "executor must fail closed without exact approval",
    )

    router_expected = (
        router.get("present")
        and router.get("decision") == "v392-post-live-router-awaiting-approval"
        and bool(router.get("pass"))
        and no_action(router)
    )
    add_check(
        result,
        "post-live-router",
        "pass" if router_expected else "blocked",
        "blocker",
        f"decision={router.get('decision')} pass={router.get('pass')}",
        manifest_ref(router),
        "router should point to V392 exact-approved deploy/live",
    )

    for label, payload in (("version", version), ("status", status), ("selftest", selftest)):
        ok, detail = device_json_ok(payload, label)
        add_check(
            result,
            f"readonly-{label}",
            "pass" if ok else "warn",
            "warning",
            detail,
            manifest_ref(payload),
            "refresh read-only device health if stale or missing",
        )

    return result


def decide(checks_list: list[ReadinessCheck]) -> tuple[str, bool, str, str, list[str]]:
    blockers = [check.name for check in checks_list if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return (
            "v392-current-readiness-blocked",
            False,
            "blocking readiness checks failed: " + ", ".join(blockers),
            "refresh failed evidence before requesting V392 live approval",
            blockers,
        )
    return (
        "v392-current-readiness-ready-for-approval",
        True,
        "V392 is fail-closed without approval and current preflights are in the expected pre-deploy state",
        "operator may run exact-approved V392 deploy/live executor; Wi-Fi HAL/start/scan/connect remains blocked",
        ["exact-v392-deploy-approval-phrase", "exact-v392-backchain-capture-live-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace,
                   deploy: dict[str, Any],
                   live: dict[str, Any],
                   executor: dict[str, Any],
                   router: dict[str, Any],
                   version: dict[str, Any],
                   status: dict[str, Any],
                   selftest: dict[str, Any]) -> dict[str, Any]:
    readiness_checks = build_checks(deploy, live, executor, router, version, status, selftest)
    decision, pass_ok, reason, next_step, blockers = decide(readiness_checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in readiness_checks],
        "remaining_blockers": blockers,
        "approval_phrases": {
            "deploy": DEPLOY_APPROVAL_PHRASE,
            "live": LIVE_APPROVAL_PHRASE,
        },
        "recommended_commands": [
            approved_executor_command(),
            post_live_router_command(),
        ],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["evidence"]]
        for check in manifest["checks"]
    ]
    lines = [
        "# V395 V392 Current Readiness Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], rows),
        "",
        "## Recommended Commands",
        "",
    ]
    for command in manifest["recommended_commands"]:
        lines.extend(["```bash", command, "```", ""])
    return "\n".join(lines)


def synthetic_manifest(decision: str,
                       pass_value: bool = True,
                       present: bool = True,
                       fields: dict[str, Any] | None = None,
                       check_values: dict[str, str] | None = None) -> dict[str, Any]:
    payload = {
        "present": present,
        "path": "/synthetic/manifest.json" if present else "",
        "decision": decision,
        "pass": pass_value,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "checks": [{"name": name, "status": status} for name, status in (check_values or {}).items()],
    }
    if fields:
        payload.update(fields)
    return payload


def synthetic_device() -> dict[str, Any]:
    return {"present": True, "path": "/synthetic/device.json", "rc": 0, "status": "ok"}


def regression_manifest(args: argparse.Namespace) -> dict[str, Any]:
    ok_deploy = synthetic_manifest(
        "execns-helper-v21-deploy-blocked",
        False,
        check_values={"remote-helper-v21": "needs-deploy", "approval-gate": "needs-operator"},
    )
    ok_live = synthetic_manifest(
        "service-manager-start-only-live-blocked",
        False,
        check_values={"helper-v21": "blocked", "approval-gate": "needs-operator"},
    )
    ok_executor = synthetic_manifest("v392-deploy-live-executor-approval-required", True)
    ok_router = synthetic_manifest("v392-post-live-router-awaiting-approval", True)
    device = synthetic_device()
    ready = build_manifest(args, ok_deploy, ok_live, ok_executor, ok_router, device, device, device)
    bad_executor = build_manifest(
        args,
        ok_deploy,
        ok_live,
        synthetic_manifest("v392-deploy-live-executor-approval-required", True, fields={"wifi_bringup_executed": True}),
        ok_router,
        device,
        device,
        device,
    )
    missing_deploy = build_manifest(args, {"present": False, "path": ""}, ok_live, ok_executor, ok_router, device, device, device)
    cases = [
        {
            "name": "ready",
            "decision": ready["decision"],
            "expected": "v392-current-readiness-ready-for-approval",
            "pass": ready["pass"],
            "expected_pass": True,
        },
        {
            "name": "executor-wifi-scope",
            "decision": bad_executor["decision"],
            "expected": "v392-current-readiness-blocked",
            "pass": bad_executor["pass"],
            "expected_pass": False,
        },
        {
            "name": "missing-deploy",
            "decision": missing_deploy["decision"],
            "expected": "v392-current-readiness-blocked",
            "pass": missing_deploy["pass"],
            "expected_pass": False,
        },
    ]
    failed = [
        case["name"]
        for case in cases
        if case["decision"] != case["expected"] or case["pass"] != case["expected_pass"]
    ]
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "v392-current-readiness-regression-pass" if not failed else "v392-current-readiness-regression-failed",
        "pass": not failed,
        "reason": "all readiness cases passed" if not failed else "failed cases: " + ", ".join(failed),
        "next_step": "build packet from current V392 safe evidence",
        "host": collect_host_metadata(),
        "cases": cases,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_regression_summary(manifest: dict[str, Any]) -> str:
    rows = [[case["name"], case["decision"], case["expected"], case["pass"], case["expected_pass"]] for case in manifest["cases"]]
    return "\n".join([
        "# V395 V392 Current Readiness Packet Regression",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        "",
        markdown_table(["name", "decision", "expected", "pass", "expected_pass"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "regression":
        manifest = regression_manifest(args)
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_regression_summary(manifest))
    else:
        manifest = build_manifest(
            args,
            load_json(args.deploy_preflight),
            load_json(args.live_preflight),
            load_json(args.executor_manifest),
            load_json(args.router_manifest),
            load_json(args.version_json),
            load_json(args.status_json),
            load_json(args.selftest_json),
        )
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
