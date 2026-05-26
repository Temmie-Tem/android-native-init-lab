#!/usr/bin/env python3
"""V1077 deploy/check-only proof for the PM-service uprobe helper."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly")
DEFAULT_V1076_MANIFEST = Path("tmp/wifi/v1076-pm-service-uprobe-helper-build/manifest.json")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1076-pm-service-uprobe-helper-build/a90_pm_service_uprobe_counter-aarch64-static")
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_pm_service_uprobe_counter"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_TCPCTL = Path("scripts/revalidation/tcpctl_host.py")
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TCP_PORT = 2325
HELPER_MARKER = "a90_pm_service_uprobe_counter v1076"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1076-manifest", type=Path, default=DEFAULT_V1076_MANIFEST)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--tcpctl", type=Path, default=DEFAULT_TCPCTL)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--transfer-port", type=int, default=18084)
    parser.add_argument("--expect-sha256", default="")
    parser.add_argument("--run", action="store_true", help="Execute deploy/check-only instead of plan-only.")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def run_host(command: list[str], output_file: Path, timeout: float = 180.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=repo_path(Path(".")),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        write_private_text(output_file, result.stdout)
        return {
            "command": [str(item) for item in command],
            "rc": result.returncode,
            "timeout": False,
            "output_file": str(output_file),
            "output_tail": result.stdout[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        write_private_text(output_file, output + "\n[TIMEOUT]\n")
        return {
            "command": [str(item) for item in command],
            "rc": None,
            "timeout": True,
            "output_file": str(output_file),
            "output_tail": (output + "\n[TIMEOUT]\n")[-2000:],
        }


def tcpctl_base(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        str(repo_path(args.tcpctl)),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port),
        "--toybox",
        args.toybox,
    ]


def helper_output_ok(text: str) -> bool:
    return (
        HELPER_MARKER in text and
        "result=check-only" in text and
        "tracefs_write_attempted=0" in text and
        "attach_attempted=0" in text and
        "child_command_attempted=0" in text and
        "OK" in text
    )


def run_deploy_check(args: argparse.Namespace, store: EvidenceStore, local_sha: str) -> dict[str, Any]:
    logs = store.mkdir("logs")
    base = tcpctl_base(args)
    steps: dict[str, Any] = {}
    steps["tcpctl_ping"] = run_host(base + ["ping"], logs / "tcpctl-ping.txt", timeout=30.0)
    steps["install"] = run_host(
        base + [
            "--device-binary",
            args.remote_helper,
            "install",
            "--local-binary",
            str(repo_path(args.local_helper)),
            "--transfer-port",
            str(args.transfer_port),
            "--transfer-timeout",
            "120",
            "--transfer-delay",
            "0.5",
        ],
        logs / "install.txt",
        timeout=180.0,
    )
    steps["remote_sha"] = run_host(
        base + ["run", args.toybox, "sha256sum", args.remote_helper],
        logs / "remote-sha.txt",
        timeout=45.0,
    )
    steps["check_only"] = run_host(
        base + ["run", args.remote_helper, "--check-only"],
        logs / "check-only.txt",
        timeout=45.0,
    )
    steps["default_no_args"] = run_host(
        base + ["run", args.remote_helper],
        logs / "default-no-args.txt",
        timeout=45.0,
    )
    steps["netservice_status"] = run_host(
        ["python3", "scripts/revalidation/a90ctl.py", "netservice", "status"],
        logs / "netservice-status.txt",
        timeout=30.0,
    )
    steps["selftest"] = run_host(
        ["python3", "scripts/revalidation/a90ctl.py", "selftest"],
        logs / "selftest.txt",
        timeout=30.0,
    )
    remote_sha_ok = steps["remote_sha"]["rc"] == 0 and local_sha in steps["remote_sha"].get("output_tail", "")
    check_only_ok = steps["check_only"]["rc"] == 0 and helper_output_ok(steps["check_only"].get("output_tail", ""))
    default_ok = steps["default_no_args"]["rc"] == 0 and helper_output_ok(steps["default_no_args"].get("output_tail", ""))
    return {
        "steps": steps,
        "remote_sha_ok": remote_sha_ok,
        "check_only_ok": check_only_ok,
        "default_ok": default_ok,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    analysis = manifest["analysis"]
    add_check(
        checks,
        "v1076-input",
        "pass" if analysis["v1076"]["decision"] == "v1076-pm-service-uprobe-helper-build-pass" and analysis["v1076"]["pass"] else "blocked",
        "blocker",
        f"decision={analysis['v1076']['decision']} pass={analysis['v1076']['pass']}",
        "complete V1076 build before deploy",
    )
    add_check(
        checks,
        "local-helper",
        "pass" if analysis["local_helper_exists"] else "blocked",
        "blocker",
        f"exists={analysis['local_helper_exists']} sha={analysis['local_sha256']}",
        "rebuild V1076 helper artifact",
    )
    if not manifest["run_requested"]:
        add_check(checks, "plan-only", "pass", "info", "no deploy or device command executed", "rerun V1077 with --run")
        return checks
    deploy = analysis.get("deploy") or {}
    steps = deploy.get("steps") or {}
    add_check(checks, "tcpctl-ping", "pass" if steps.get("tcpctl_ping", {}).get("rc") == 0 else "blocked", "blocker", f"rc={steps.get('tcpctl_ping', {}).get('rc')}", "restore NCM/tcpctl before deploy")
    add_check(checks, "install", "pass" if steps.get("install", {}).get("rc") == 0 else "blocked", "blocker", f"rc={steps.get('install', {}).get('rc')}", "inspect install transcript")
    add_check(checks, "remote-sha", "pass" if deploy.get("remote_sha_ok") else "blocked", "blocker", f"ok={deploy.get('remote_sha_ok')}", "redeploy helper until sha matches")
    add_check(checks, "check-only", "pass" if deploy.get("check_only_ok") else "blocked", "blocker", f"ok={deploy.get('check_only_ok')}", "inspect check-only output")
    add_check(checks, "default-no-args", "pass" if deploy.get("default_ok") else "blocked", "blocker", f"ok={deploy.get('default_ok')}", "ensure default mode remains no-attach")
    add_check(checks, "selftest", "pass" if steps.get("selftest", {}).get("rc") == 0 and "fail=0" in steps.get("selftest", {}).get("output_tail", "") else "blocked", "blocker", f"rc={steps.get('selftest', {}).get('rc')}", "recover native health before live attach")
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(manifest: dict[str, Any], checks: list[Check]) -> tuple[str, bool, str, str]:
    if not manifest["run_requested"]:
        return (
            "v1077-pm-service-uprobe-helper-deploy-plan-ready",
            True,
            "plan-only; no deploy, tracefs write, BPF attach, child command, or Wi-Fi action executed",
            "rerun V1077 with --run to deploy and verify check-only modes",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v1077-pm-service-uprobe-helper-deploy-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "repair deploy/check-only blocker before live attach",
        )
    return (
        "v1077-pm-service-uprobe-helper-deploy-checkonly-pass",
        True,
        "helper deployed over NCM and both check-only/default modes proved no tracefs write or BPF attach",
        "V1078 can run a bounded tracefs mount/register/attach cleanup proof around PM observer",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    table = ["| name | status | severity | detail | next |", "| --- | --- | --- | --- | --- |"]
    table.extend("| " + " | ".join(str(item) for item in row) + " |" for row in rows)
    return "\n".join([
        "# V1077 PM Service Uprobe Helper Deploy Check-only",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- run_requested: `{manifest['run_requested']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- remote_helper: `{manifest['remote_helper']}`",
        f"- local_sha256: `{manifest['analysis']['local_sha256']}`",
        f"- deploy_executed: `{manifest['deploy_executed']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        f"- child_command_executed: `{manifest['child_command_executed']}`",
        f"- wifi_action_executed: `{manifest['wifi_action_executed']}`",
        "",
        "## Checks",
        "",
        *table,
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1076 = load_json(args.v1076_manifest)
    local_helper = repo_path(args.local_helper)
    local_sha = sha256(local_helper) if local_helper.exists() else ""
    expected_sha = args.expect_sha256 or str(v1076.get("analysis", {}).get("build", {}).get("output_sha256", ""))
    analysis: dict[str, Any] = {
        "v1076": {
            "manifest": str(repo_path(args.v1076_manifest)),
            "decision": v1076.get("decision", ""),
            "pass": bool(v1076.get("pass")),
        },
        "local_helper": str(local_helper),
        "local_helper_exists": local_helper.exists(),
        "local_sha256": local_sha,
        "expected_sha256": expected_sha,
        "deploy": {},
    }
    manifest: dict[str, Any] = {
        "cycle": "v1077",
        "generated_at": now_iso(),
        "run_requested": bool(args.run),
        "remote_helper": args.remote_helper,
        "analysis": analysis,
        "deploy_executed": False,
        "device_commands_executed": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "child_command_executed": False,
        "pm_actor_executed": False,
        "service_manager_executed": False,
        "wifi_action_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    if args.run and local_helper.exists() and local_sha == expected_sha:
        analysis["deploy"] = run_deploy_check(args, store, local_sha)
        manifest["deploy_executed"] = True
        manifest["device_commands_executed"] = True
    checks = build_checks(manifest)
    decision, passed, reason, next_step = decide(manifest, checks)
    manifest.update({
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": [asdict(check) for check in checks],
    })
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.path('manifest.json')}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
