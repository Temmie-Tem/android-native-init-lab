#!/usr/bin/env python3
"""V930 deploy-only wrapper for a90_android_execns_probe v154."""

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

import wifi_execns_helper_v12_deploy_preflight as deploy_base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v930-execns-helper-v154-deploy")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v929-execns-helper-v154-build/a90_android_execns_probe")
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER_SHA256 = "f87fb6032a4333f4b3dfabc9766b8620bf6e3f2acc9c1081b09738933cc7c9ab"
HELPER_MARKER = "a90_android_execns_probe v154"
NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
ORDER_ENUM = "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd"
COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
APPROVAL_PHRASE = (
    "approve v930 deploy execns helper v154 only; "
    "no daemon start and no Wi-Fi bring-up"
)
LATEST_POINTER = Path("tmp/wifi/latest-v930-execns-helper-v154-deploy.txt")
MANAGER_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)


READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("bootstatus", ["bootstatus"], 10.0),
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--transfer-method", choices=("serial",), default="serial")
    parser.add_argument("--serial-chunk-size", type=int, default=1850)
    parser.add_argument("--serial-staging-dir", default="/cache/a90-runtime/bin")
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], timeout: float = 30.0) -> tuple[int, str]:
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


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "marker": False,
        "new_mode": False,
        "allow_flag": False,
        "order_enum": False,
        "compact_mode": False,
        "file_output": "",
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    file_rc, file_output = run_host(["file", str(path)], timeout=10)
    info["file_output"] = file_output.strip() if file_rc == 0 else file_output.strip()
    strings_rc, strings_output = run_host(["strings", str(path)], timeout=20)
    if strings_rc == 0:
        info["marker"] = HELPER_MARKER in strings_output
        info["new_mode"] = NEW_MODE in strings_output
        info["allow_flag"] = ALLOW_FLAG in strings_output
        info["order_enum"] = ORDER_ENUM in strings_output
        info["compact_mode"] = COMPACT_MODE in strings_output
    return info


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def capture_command(args: argparse.Namespace, store: EvidenceStore, name: str,
                    command: list[str], timeout: float) -> StepResult:
    command = [args.remote_helper if item == DEFAULT_REMOTE_HELPER else item for item in command]
    command = [args.toybox if item == DEFAULT_TOYBOX else item for item in command]
    record = run_capture(args, name, command, timeout=timeout)
    if record.status == "busy":
        hide_record = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(args.timeout, 8.0))
        store.write_text(
            f"native/{safe_name(name)}.hide-on-busy.txt",
            strip_cmdv1_text(hide_record.text) if hide_record.text else hide_record.error + "\n",
        )
        record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return StepResult(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def run_read_only(args: argparse.Namespace, store: EvidenceStore, prefix: str) -> list[StepResult]:
    store.mkdir(prefix)
    steps = []
    for name, command, timeout in READ_ONLY_COMMANDS:
        step = capture_command(args, store, f"{prefix}-{name}", command, timeout)
        steps.append(step)
    return steps


def read_step_text(store: EvidenceStore, steps: list[StepResult], suffix: str) -> str:
    for step in steps:
        if not step.name.endswith("-" + suffix):
            continue
        path = store.path(step.file)
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def add_check(checks: list[Check], name: str, status: str, severity: str,
              detail: str, evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 store: EvidenceStore,
                 local: dict[str, Any],
                 steps: list[StepResult],
                 post_steps: list[StepResult] | None = None) -> list[Check]:
    checks: list[Check] = []
    active_steps = post_steps or steps
    bootstatus = read_step_text(store, active_steps, "bootstatus")
    selftest = read_step_text(store, active_steps, "selftest")
    helper_sha = read_step_text(store, active_steps, "sha-helper")
    helper_usage = read_step_text(store, active_steps, "helper-usage")
    ps_text = read_step_text(store, active_steps, "ps")
    netdev = read_step_text(store, active_steps, "proc-net-dev")
    managers = [line.strip() for line in ps_text.splitlines() if MANAGER_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]
    remote_sha_match = args.helper_sha256 in helper_sha
    remote_has_contract = all(token in helper_usage for token in (HELPER_MARKER, NEW_MODE, ALLOW_FLAG, ORDER_ENUM, COMPACT_MODE))

    add_check(
        checks,
        "local-helper-v154",
        "pass" if (
            local["exists"] and
            local["sha256"] == args.helper_sha256 and
            local["marker"] and
            local["new_mode"] and
            local["allow_flag"] and
            local["order_enum"] and
            local["compact_mode"]
        ) else "blocked",
        "blocker",
        (
            f"exists={local['exists']} sha={local['sha256'] or 'missing'} "
            f"marker={local['marker']} mode={local['new_mode']} allow={local['allow_flag']} "
            f"order={local['order_enum']} compact={local['compact_mode']}"
        ),
        [str(local["path"])],
        "rebuild V929 helper v154 before deploy",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no bridge/device command executed", [], "run preflight next")
        return checks
    add_check(
        checks,
        "native-health",
        "pass" if "BOOT OK" in bootstatus and "fail=0" in bootstatus and "fail=0" in selftest else "blocked",
        "blocker",
        "bootstatus/selftest must be clean before helper replacement",
        [line.strip() for line in (bootstatus + "\n" + selftest).splitlines() if "BOOT OK" in line or "selftest:" in line][:6],
        "fix native health before helper deploy",
    )
    add_check(
        checks,
        "service-manager-processes-clean",
        "pass" if not managers else "blocked",
        "blocker",
        f"process_count={len(managers)}",
        managers[:8],
        "do not deploy over active service-manager experiment",
    )
    add_check(
        checks,
        "wifi-link-surface-clean",
        "pass" if not wifi_links else "blocked",
        "blocker",
        f"wifi_link_count={len(wifi_links)}",
        wifi_links[:8],
        "do not deploy while Wi-Fi link is active",
    )
    add_check(
        checks,
        "remote-helper-v154",
        "pass" if remote_sha_match and remote_has_contract else "needs-deploy",
        "deploy",
        f"sha_match={remote_sha_match} contract={remote_has_contract}",
        [line for line in helper_sha.splitlines() if args.remote_helper in line][:2] +
        [line for line in helper_usage.splitlines() if HELPER_MARKER in line or NEW_MODE in line or ALLOW_FLAG in line][:6],
        "approved V930 run installs helper v154 if needed",
    )
    add_check(
        checks,
        "approval-gate",
        "pass" if approved(args) else "needs-operator",
        "approval",
        f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
        [APPROVAL_PHRASE],
        "exact V930 phrase and flags required before /cache/bin write",
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


def run_serial_install(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    deploy_base.DEPLOY_LABEL = "v154"
    deploy_base.DEPLOY_LOG_PREFIX = "v930"
    return deploy_base.run_serial_install(args, store)


def decide(args: argparse.Namespace,
           checks: list[Check],
           deploy_result: dict[str, Any] | None,
           post_checks: list[Check] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v154-deploy-plan-ready", True, "plan-only; no live command executed", "run V930 preflight"
    blockers = blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and approved(args)),
    )
    if blockers:
        return "execns-helper-v154-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return "execns-helper-v154-deploy-preflight-ready", True, "preflight complete; helper v154 deploy requires V930 approval phrase", "run approved V930 deploy"
    if not approved(args):
        return "execns-helper-v154-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V930 phrase"
    if deploy_result and not deploy_result.get("ok"):
        return "execns-helper-v154-deploy-failed", False, "serial install failed", "inspect install transcript and retry after cleanup"
    if post_checks is None:
        return "execns-helper-v154-deploy-postflight-missing", False, "post-deploy checks missing", "rerun postflight"
    post_blockers = blocking_checks(post_checks, ignore_deploy=False)
    if post_blockers:
        return "execns-helper-v154-deploy-postflight-blocked", False, "postflight blocked by " + ", ".join(post_blockers), "inspect postflight captures"
    return "execns-helper-v154-deploy-pass", True, "helper v154 deployed or already current; no daemon or Wi-Fi bring-up executed", "run one V931 matrix order below Wi-Fi HAL"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    post_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest.get("post_checks", [])]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    lines = [
        "# V930 Execns Helper v154 Deploy",
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
        f"- transfer_method: `{manifest['transfer_method']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
    ]
    if post_rows:
        lines.extend([
            "## Post-Deploy Checks",
            "",
            markdown_table(["name", "status", "severity", "detail", "next"], post_rows),
            "",
        ])
    if manifest["deploy_result"]:
        lines.extend([
            "## Deploy Result",
            "",
            f"- method: `{manifest['deploy_result'].get('method', 'skip')}`",
            f"- rc: `{manifest['deploy_result'].get('rc')}`",
            f"- ok: `{manifest['deploy_result'].get('ok')}`",
            f"- file: `{manifest['deploy_result'].get('file')}`",
            "",
        ])
    lines.extend([
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ])
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    store.write_json("local-helper.json", local)
    steps: list[StepResult] = []
    post_steps: list[StepResult] | None = None
    deploy_result: dict[str, Any] | None = None
    post_checks: list[Check] | None = None
    device_mutations = False

    if args.command != "plan":
        steps = run_read_only(args, store, "pre")
    checks = build_checks(args, store, local, steps)
    blockers = blocking_checks(checks, ignore_deploy=args.command == "run" and approved(args))

    if args.command == "run" and approved(args) and not blockers:
        remote_current = any(check.name == "remote-helper-v154" and check.status == "pass" for check in checks)
        if remote_current:
            deploy_result = {"method": "skip", "command": "skip", "rc": 0, "ok": True, "file": "", "skipped": True}
        else:
            deploy_result = run_serial_install(args, store)
            device_mutations = bool(deploy_result.get("ok") or deploy_result.get("chunks_written", 0))
        if deploy_result.get("ok"):
            post_steps = run_read_only(args, store, "post")
            store.write_json("post-deploy-steps.json", {"steps": [asdict(step) for step in post_steps]})
            post_checks = build_checks(args, store, local, steps, post_steps=post_steps)

    decision, pass_ok, reason, next_step = decide(args, checks, deploy_result, post_checks)
    return {
        "generated_at": now_iso(),
        "tool": Path(__file__).name,
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "local_helper": local,
        "remote_helper": args.remote_helper,
        "helper_expected_sha256": args.helper_sha256,
        "transfer_method": args.transfer_method,
        "serial_chunk_size": args.serial_chunk_size,
        "steps": [asdict(step) for step in steps],
        "post_steps": [asdict(step) for step in post_steps] if post_steps else [],
        "checks": [asdict(check) for check in checks],
        "post_checks": [asdict(check) for check in post_checks] if post_checks else [],
        "deploy_result": deploy_result,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_mutations": device_mutations,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_executed": [
            "service-manager, hwservicemanager, vndservicemanager live start",
            "CNSS daemon, Wi-Fi HAL, wificond, supplicant, hostapd live start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot or partition write",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
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
