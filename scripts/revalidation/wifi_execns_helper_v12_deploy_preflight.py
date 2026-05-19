#!/usr/bin/env python3
"""Fail-closed V375 execns helper v12 deploy/preflight executor.

This tool separates deployment mechanics from service-manager execution:

* plan: no bridge/device command
* preflight: read-only local/native/NCM checks
* run: deploys only with the exact V375 phrase and explicit apply flags

Even approved run only installs/verifies /cache/bin/a90_android_execns_probe and
reruns the V373 service-manager start-only preflight.  It does not start Android
service-manager processes and it does not bring up Wi-Fi.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v375-execns-helper-v12-deploy-preflight")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe")
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER_SHA256 = "fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918"
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TRANSFER_PORT = 18084
HELPER_MARKER = "a90_android_execns_probe v12"
SERVICE_MODE_TOKEN = "service-manager-start-only"
APPROVAL_PHRASE = (
    "approve v375 deploy execns helper v12 only; "
    "no daemon start and no Wi-Fi bring-up"
)
V373_SCRIPT = Path("scripts/revalidation/wifi_service_manager_start_only_smoke.py")
TCPCTL_SCRIPT = Path("scripts/revalidation/tcpctl_host.py")
MANAGER_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("netservice-status", ["netservice", "status"], 10.0),
    ("stat-helper", ["stat", DEFAULT_REMOTE_HELPER], 10.0),
    ("sha-helper", ["run", DEFAULT_TOYBOX, "sha256sum", DEFAULT_REMOTE_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_REMOTE_HELPER], 10.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
)


@dataclass
class StepResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], *, timeout: float = 30.0) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def capture_command(args: argparse.Namespace, store: EvidenceStore, name: str,
                    command: list[str], timeout: float) -> StepResult:
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return StepResult(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def run_read_only_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[StepResult]:
    store.mkdir("native")
    steps = []
    for name, command, timeout in READ_ONLY_COMMANDS:
        command = [args.remote_helper if item == DEFAULT_REMOTE_HELPER else item for item in command]
        command = [args.toybox if item == DEFAULT_TOYBOX else item for item in command]
        steps.append(capture_command(args, store, name, command, timeout))
    return steps


def capture_text(store: EvidenceStore, steps: list[StepResult], name: str) -> str:
    for step in steps:
        if step.name != name:
            continue
        path = store.path(step.file)
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[StepResult], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "strings_marker": False,
        "strings_service_mode": False,
        "file_output": "",
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    rc, file_output = run_host(["file", str(path)], timeout=10)
    info["file_output"] = file_output.strip() if rc == 0 else file_output.strip()
    rc, strings_output = run_host(["strings", str(path)], timeout=10)
    if rc == 0:
        info["strings_marker"] = HELPER_MARKER in strings_output
        info["strings_service_mode"] = SERVICE_MODE_TOKEN in strings_output
    return info


def run_host_ping(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    rc, output = run_host(["ping", "-c", "3", "-W", "2", args.device_ip], timeout=12)
    store.write_text("host/ping-device.txt", output)
    return {"rc": rc, "ok": rc == 0, "file": "host/ping-device.txt"}


def build_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[StepResult],
                 local: dict[str, Any], ping: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    version = capture_text(store, steps, "version")
    status = capture_text(store, steps, "status")
    selftest = capture_text(store, steps, "selftest")
    helper_usage = capture_text(store, steps, "helper-usage")
    helper_sha = capture_text(store, steps, "sha-helper")
    ps = capture_text(store, steps, "ps")
    netdev = capture_text(store, steps, "proc-net-dev")
    managers = [line.strip() for line in ps.splitlines() if MANAGER_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]
    remote_sha_match = args.helper_sha256 in helper_sha
    remote_has_mode = SERVICE_MODE_TOKEN in helper_usage and HELPER_MARKER in helper_usage

    add_check(
        checks,
        "local-helper-v12",
        "pass" if local["exists"] and local["sha256"] == args.helper_sha256 and local["strings_marker"] and local["strings_service_mode"] else "blocked",
        "blocker",
        f"exists={local['exists']} sha={local['sha256'] or 'missing'} marker={local['strings_marker']} service_mode={local['strings_service_mode']}",
        [local["path"]],
        "rebuild V374 helper before deploy",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no bridge or host network command executed", [], "run preflight next")
        return checks
    add_check(
        checks,
        "native-version",
        "pass" if args.expect_version in version else "warn",
        "warning",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:3],
        "refresh baseline if native version intentionally changed",
    )
    add_check(
        checks,
        "native-clean",
        "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked",
        "blocker",
        "status/selftest rc=0 fail=0 expected",
        [line.strip() for line in (status + "\n" + selftest).splitlines() if line.strip().startswith("selftest:")][:4],
        "fix native health before helper deploy",
    )
    add_check(
        checks,
        "ncm-host-reachable",
        "pass" if ping and ping["ok"] else "blocked",
        "blocker",
        f"ping_rc={ping['rc'] if ping else 'skipped'} device_ip={args.device_ip}",
        [ping["file"]] if ping else [],
        "run ncm_host_setup.py setup before deploy",
    )
    add_check(
        checks,
        "service-manager-processes-clean",
        "pass" if not managers else "blocked",
        "blocker",
        f"process_count={len(managers)}",
        managers[:8],
        "do not deploy over an active service-manager experiment",
    )
    add_check(
        checks,
        "wifi-link-surface-clean",
        "pass" if not wifi_links else "blocked",
        "blocker",
        f"wifi_link_count={len(wifi_links)}",
        wifi_links[:8],
        "do not deploy while Wi-Fi bring-up is active",
    )
    add_check(
        checks,
        "remote-helper-v12",
        "pass" if remote_sha_match and remote_has_mode else "needs-deploy",
        "deploy",
        f"sha_match={remote_sha_match} marker_mode={remote_has_mode}",
        [line for line in helper_sha.splitlines() if args.remote_helper in line][:2] + [line for line in helper_usage.splitlines() if "usage:" in line or "a90_android_execns_probe" in line][:4],
        "approved V375 run installs local v12 helper if needed",
    )
    add_check(
        checks,
        "approval-gate",
        "pass" if approved(args) else "needs-operator",
        "approval",
        f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
        [APPROVAL_PHRASE],
        "exact phrase and flags required before /cache/bin write",
    )
    return checks


def blocking_checks(checks: list[Check], *, ignore_deploy: bool) -> list[str]:
    blocked = []
    for check in checks:
        if check.severity == "blocker" and check.status != "pass":
            blocked.append(check.name)
        if check.severity == "deploy" and check.status != "pass" and not ignore_deploy:
            blocked.append(check.name)
    return blocked


def run_install(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = [
        sys.executable,
        str(repo_path(TCPCTL_SCRIPT)),
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--device-ip",
        args.device_ip,
        "--device-binary",
        args.remote_helper,
        "--toybox",
        args.toybox,
        "install",
        "--local-binary",
        str(repo_path(args.local_helper)),
        "--transfer-port",
        str(args.transfer_port),
    ]
    rc, output = run_host(command, timeout=150)
    store.write_text("host/tcpctl-install-helper.txt", output)
    return {"command": " ".join(command), "rc": rc, "ok": rc == 0, "file": "host/tcpctl-install-helper.txt"}


def run_v373_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    out_dir = store.path("v373-preflight")
    command = [
        sys.executable,
        str(repo_path(V373_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "preflight",
    ]
    rc, output = run_host(command, timeout=180)
    store.write_text("host/v373-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v373-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: argparse.Namespace, checks: list[Check], deploy_result: dict[str, Any] | None,
           v373_result: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v12-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = blocking_checks(checks, ignore_deploy=args.command == "run" and approved(args))
    if blockers:
        return "execns-helper-v12-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return "execns-helper-v12-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V375 deploy"
    if not approved(args):
        return "execns-helper-v12-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v12-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v373_result and v373_result["decision"] not in {"service-manager-start-only-smoke-approval-required", "service-manager-start-only-smoke-ready-to-execute"}:
        return "execns-helper-v12-deploy-postflight-blocked", False, f"V373 preflight decision={v373_result['decision']}", "resolve V373 post-deploy blockers"
    return "execns-helper-v12-deploy-pass", True, "helper v12 deployed or already current; V373 preflight advanced past helper-mode blocker", "next requires separate V373 daemon-start approval"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    lines = [
        "# v375 Execns Helper v12 Deploy Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ]
    if manifest["deploy_result"]:
        lines.extend([
            "## Deploy Result",
            "",
            f"- rc: `{manifest['deploy_result']['rc']}`",
            f"- ok: `{manifest['deploy_result']['ok']}`",
            f"- file: `{manifest['deploy_result']['file']}`",
            "",
        ])
    if manifest["v373_preflight_result"]:
        lines.extend([
            "## V373 Post-Deploy Preflight",
            "",
            f"- decision: `{manifest['v373_preflight_result']['decision']}`",
            f"- pass: `{manifest['v373_preflight_result']['pass']}`",
            f"- file: `{manifest['v373_preflight_result']['file']}`",
            f"- manifest: `{manifest['v373_preflight_result']['manifest']}`",
            "",
        ])
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    store.write_json("local-helper.json", local)
    steps: list[StepResult] = []
    ping: dict[str, Any] | None = None
    deploy_result: dict[str, Any] | None = None
    v373_result: dict[str, Any] | None = None
    device_mutations = False

    if args.command != "plan":
        ping = run_host_ping(args, store)
        steps = run_read_only_preflight(args, store)

    checks = build_checks(args, store, steps, local, ping)
    pre_deploy_blockers = blocking_checks(checks, ignore_deploy=args.command == "run" and approved(args))
    if args.command == "run" and approved(args) and not pre_deploy_blockers:
        remote_v12 = any(check.name == "remote-helper-v12" and check.status == "pass" for check in checks)
        if remote_v12:
            deploy_result = {"command": "skip", "rc": 0, "ok": True, "file": "", "skipped": True}
        else:
            deploy_result = run_install(args, store)
            device_mutations = True
        if deploy_result["ok"]:
            post_steps = run_read_only_preflight(args, store)
            store.write_json("post-deploy-steps.json", {"steps": [asdict(step) for step in post_steps]})
            v373_result = run_v373_preflight(args, store)

    decision, pass_ok, reason, next_step = decide(args, checks, deploy_result, v373_result)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "local_helper": local,
        "remote_helper": args.remote_helper,
        "helper_expected_sha256": args.helper_sha256,
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "host_ping": ping,
        "deploy_result": deploy_result,
        "v373_preflight_result": v373_result,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_mutations": device_mutations,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "service-manager, hwservicemanager, vndservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "Android partition write, firmware mutation, rfkill write, driver bind/unbind",
        ],
    }
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
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
