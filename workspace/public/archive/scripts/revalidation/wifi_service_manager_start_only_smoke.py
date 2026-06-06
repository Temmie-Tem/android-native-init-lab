#!/usr/bin/env python3
"""Fail-closed service-manager start-only smoke runner scaffold.

V373 intentionally does not improvise service-manager execution.  It verifies the
V372 approval packet and current native state, refuses live run without the exact
approval phrase, and blocks approved run before mutation when the deployed
execns helper does not advertise a service-manager start-only mode.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_service_manager_start_only_approval_packet import APPROVAL_PHRASE, DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v373-service-manager-start-only-smoke")
DEFAULT_V372 = Path("tmp/wifi/v372-service-manager-start-only-approval-packet-live-20260520-013344/manifest.json")
TOYBOX = "/cache/bin/toybox"
HELPER = "/cache/bin/a90_android_execns_probe"
SERVICE_MODE_TOKEN = "service-manager-start-only"
MANAGER_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)

PREFLIGHT_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-helper", ["stat", HELPER], 10.0),
    ("helper-usage", ["run", HELPER], 10.0),
    ("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("stat-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("stat-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v372-manifest", type=Path, default=DEFAULT_V372)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def capture_command(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float) -> StepResult:
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return StepResult(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[StepResult]:
    store.mkdir("native")
    return [capture_command(args, store, name, command, timeout) for name, command, timeout in PREFLIGHT_COMMANDS]


def capture_text(store: EvidenceStore, steps: list[StepResult], name: str) -> str:
    for step in steps:
        if step.name != name:
            continue
        path = store.path(step.file)
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[StepResult], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def approved(args: argparse.Namespace) -> bool:
    return args.approval_phrase == APPROVAL_PHRASE and args.apply and args.assume_yes


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace, store: EvidenceStore, v372: dict[str, Any], steps: list[StepResult]) -> list[Check]:
    checks: list[Check] = []
    version = capture_text(store, steps, "version")
    status = capture_text(store, steps, "status")
    selftest = capture_text(store, steps, "selftest")
    helper_usage = capture_text(store, steps, "helper-usage")
    ps = capture_text(store, steps, "ps")
    netdev = capture_text(store, steps, "proc-net-dev")
    managers = [line.strip() for line in ps.splitlines() if MANAGER_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]
    helper_has_service_mode = SERVICE_MODE_TOKEN in helper_usage

    add_check(checks, "v372-approval-packet", "pass" if v372.get("decision") == "service-manager-start-only-approval-packet-ready" and bool(v372.get("pass")) else "blocked", "blocker", f"decision={v372.get('decision')} pass={v372.get('pass')}", [str(v372.get("path", ""))], "V372 packet must be ready before V373 runner")
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no bridge command executed", [], "run preflight before approval")
        return checks
    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version changed")
    add_check(checks, "status-selftest-clean", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [line.strip() for line in (status + "\n" + selftest).splitlines() if line.strip().startswith("selftest:")][:4], "device must be clean before start-only runner")
    add_check(checks, "service-manager-binaries", "pass" if step_ok(steps, "stat-servicemanager") and step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={step_ok(steps, 'stat-servicemanager')} hwservicemanager={step_ok(steps, 'stat-hwservicemanager')} vndservicemanager={step_ok(steps, 'stat-vndservicemanager')}", [], "runner requires exact binary resolution")
    add_check(checks, "service-manager-processes-clean", "pass" if not managers else "blocked", "blocker", f"process_count={len(managers)}", managers[:8], "runner must start from clean process state")
    add_check(checks, "wifi-link-surface-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "runner must not start from an existing Wi-Fi link surface")
    add_check(checks, "temporary-binder-nodes-clean", "pass" if not step_ok(steps, "stat-binder") and not step_ok(steps, "stat-hwbinder") and not step_ok(steps, "stat-vndbinder") else "blocked", "blocker", f"binder={step_ok(steps, 'stat-binder')} hwbinder={step_ok(steps, 'stat-hwbinder')} vndbinder={step_ok(steps, 'stat-vndbinder')}", [], "runner must own temporary node creation/cleanup")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [APPROVAL_PHRASE], "exact phrase and flags required before any mutation")
    add_check(checks, "helper-service-manager-mode", "pass" if helper_has_service_mode else "blocked", "blocker", f"token={SERVICE_MODE_TOKEN} present={helper_has_service_mode}", [line for line in helper_usage.splitlines() if "usage:" in line or "--mode" in line][:4], "V374 must add a bounded service-manager mode to a90_android_execns_probe before approved run")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace, checks: list[Check]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "service-manager-start-only-smoke-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blocking = blockers(checks)
    if blocking:
        return "service-manager-start-only-smoke-blocked", True, "blocked before mutation by " + ", ".join(blocking), "resolve blockers before approved run"
    if not approved(args):
        return "service-manager-start-only-smoke-approval-required", True, "exact approval phrase required; no mutation executed", "operator may approve only after accepting V372 packet"
    return "service-manager-start-only-smoke-ready-to-execute", False, "helper mode unexpectedly available; live execution body not implemented in V373", "manual review before daemon start"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v372 = load_json(args.v372_manifest)
    if args.command == "run" and not approved(args):
        store.mkdir("native")
        steps = []
        checks = [
            Check(
                "v372-approval-packet",
                "pass" if v372.get("decision") == "service-manager-start-only-approval-packet-ready" and bool(v372.get("pass")) else "blocked",
                "blocker",
                f"decision={v372.get('decision')} pass={v372.get('pass')}",
                [str(v372.get("path", ""))],
                "V372 packet must be ready before V373 runner",
            ),
            Check(
                "approval-gate",
                "needs-operator",
                "approval",
                f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
                [APPROVAL_PHRASE],
                "exact phrase and flags required before any live preflight or mutation",
            ),
        ]
    else:
        steps = [] if args.command == "plan" else run_preflight(args, store)
        checks = build_checks(args, store, v372, steps)
    decision, pass_ok, reason, next_step = decide(args, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v372_manifest": {"path": v372.get("path"), "present": bool(v372.get("present")), "decision": v372.get("decision"), "pass": v372.get("pass")},
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": APPROVAL_PHRASE,
        "live_execution_approved": bool(args.command == "run" and approved(args)),
        "daemon_start_executed": False,
        "device_mutations": False,
        "explicitly_not_approved": [
            "service-manager start before helper-service-manager-mode passes",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    return "\n".join([
        "# v373 Service-Manager Start-Only Smoke",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], rows),
        "",
        "## Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved"]),
        "",
    ])


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
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
