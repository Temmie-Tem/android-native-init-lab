#!/usr/bin/env python3
"""Fail-closed V402 private SELinux surface proof runner.

The approved run executes only /cache/bin/a90_android_execns_probe
private-selinux-proof mode. It proves private namespace visibility for
SELinuxfs status/enforce, Binder nodes, private properties, and service-context
inputs. It does not start service-manager or Wi-Fi.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_service_manager_start_only_approval_packet import DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v402-private-selinux-surface-live-runner")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
TOYBOX = "/cache/bin/toybox"
HELPER_LABEL = "v22"
APPROVAL_PHRASE = "approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up"
SERVICE_PROCESS_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d+|phy\d+)\b", re.IGNORECASE)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("sha-helper", ["run", TOYBOX, "sha256sum", DEFAULT_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_HELPER], 10.0),
    ("stat-property-root", ["stat", DEFAULT_PROPERTY_ROOT], 10.0),
    ("stat-selinux-status", ["stat", "/sys/fs/selinux/status"], 10.0),
    ("cat-selinux-enforce", ["cat", "/sys/fs/selinux/enforce"], 10.0),
    ("stat-real-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"], 10.0),
    ("stat-real-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"], 10.0),
    ("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
)


@dataclass
class Step:
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
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--property-root", default=DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.approval_phrase == APPROVAL_PHRASE and args.apply and args.assume_yes


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def command_text(command: list[str]) -> str:
    return " ".join(command)


def write_step(store: EvidenceStore, name: str, command: list[str], text: str, record: Any) -> Step:
    rel = f"steps/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return Step(
        name=name,
        command=command_text(command),
        ok=bool(record.ok),
        rc=record.rc,
        status=record.status,
        duration_sec=record.duration_sec,
        file=rel,
        error=record.error,
    )


def capture_step(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float) -> Step:
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    return write_step(store, name, command, text, record)


def step_text(store: EvidenceStore, steps: list[Step], name: str) -> str:
    for step in steps:
        if step.name == name:
            path = store.path(step.file)
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[Step], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[Step]:
    store.mkdir("steps")
    steps = []
    for name, command, timeout in READ_ONLY_COMMANDS:
        command = [
            args.helper if item == DEFAULT_HELPER else
            args.helper_sha256 if item == DEFAULT_HELPER_SHA256 else
            args.property_root if item == DEFAULT_PROPERTY_ROOT else
            item
            for item in command
        ]
        steps.append(capture_step(args, store, name, command, timeout))
    return steps


def build_helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "private-selinux-proof",
        "--target-profile",
        "system-servicemanager",
        "--null-device-mode",
        "dev-null-selinux",
        "--data-wifi-mode",
        "private-empty",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        args.property_root,
        "--timeout-sec",
        "3",
    ]


def context_value(text: str, key: str) -> str:
    prefix = key + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[Step], live_step: Step | None) -> list[Check]:
    checks: list[Check] = []
    version = step_text(store, steps, "version")
    status_text = step_text(store, steps, "status")
    selftest = step_text(store, steps, "selftest")
    helper_usage = step_text(store, steps, "helper-usage")
    helper_sha = step_text(store, steps, "sha-helper")
    ps = step_text(store, steps, "ps")
    netdev = step_text(store, steps, "proc-net-dev")
    live_text = step_text(store, [live_step] if live_step else [], "private-selinux-proof")
    managers = [line for line in ps.splitlines() if SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line for line in netdev.splitlines() if WIFI_RE.search(line)]

    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no bridge command executed", "run preflight next")
        return checks
    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", args.expect_version, "refresh baseline if intentional")
    add_check(checks, "native-health", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status_text and "fail=0" in selftest else "blocked", "blocker", "status/selftest fail=0 expected", "fix native health first")
    add_check(checks, f"helper-{HELPER_LABEL}", "pass" if args.helper_sha256 in helper_sha and "a90_android_execns_probe v22" in helper_usage and "private-selinux-proof" in helper_usage else "blocked", "blocker", "remote helper must be v22 with private-selinux-proof mode", "deploy v22 first")
    add_check(checks, "native-selinux-status-visible", "pass" if step_ok(steps, "stat-selinux-status") and step_ok(steps, "cat-selinux-enforce") else "blocked", "blocker", "global /sys/fs/selinux/status and enforce must be visible", "run/repair SELinuxfs mount first")
    add_check(checks, "private-property-root-visible", "pass" if step_ok(steps, "stat-property-root") else "blocked", "blocker", args.property_root, "restore private property snapshot")
    add_check(checks, "linkerconfig-inputs-visible", "pass" if step_ok(steps, "stat-real-ld-config") and step_ok(steps, "stat-real-apex-libraries") else "blocked", "blocker", "real linkerconfig/apex library config expected", "restore runtime repair inputs")
    add_check(checks, "service-manager-processes-clean", "pass" if not managers else "blocked", "blocker", f"process_count={len(managers)}", "stop active service-manager experiments")
    add_check(checks, "wifi-link-surface-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", "stop Wi-Fi experiments first")
    if args.command == "preflight":
        add_check(checks, "live-proof-not-run", "pass", "info", "preflight only", "run with exact approval")
        return checks
    if live_step is None:
        add_check(checks, "approval-gate", "blocked", "approval", "exact phrase required before private proof", "rerun with approval phrase")
        return checks

    required_context = {
        "context.selinux_status.exists": "1",
        "context.selinux_enforce.exists": "1",
        "context.dev_binder.exists": "1",
        "context.dev_hwbinder.exists": "1",
        "context.dev_vndbinder.exists": "1",
        "context.dev_properties.exists": "1",
        "context.plat_service_contexts.exists": "1",
        "context.plat_hwservice_contexts.exists": "1",
    }
    missing = [key for key, expected in required_context.items() if context_value(live_text, key) != expected]
    add_check(checks, "private-namespace-context", "pass" if not missing else "blocked", "blocker", "missing=" + ",".join(missing), "repair private namespace inputs")
    add_check(checks, "private-proof-result", "pass" if live_step.ok and "private_selinux_proof.result=pass" in live_text else "blocked", "blocker", f"ok={live_step.ok}", "inspect helper output")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decision(args: argparse.Namespace, checks: list[Check], live_step: Step | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "private-selinux-surface-proof-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = blockers(checks)
    if blocked:
        return "private-selinux-surface-proof-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before live proof", False
    if args.command == "preflight":
        return "private-selinux-surface-proof-preflight-ready", True, "read-only preflight is ready; live proof still needs approval", "operator may approve V402 private proof", False
    if not approved(args):
        return "private-selinux-surface-proof-approval-required", True, "exact approval phrase required; no device command executed", "rerun with exact approval if intended", False
    if live_step and live_step.ok:
        return "private-selinux-surface-proof-pass", True, "private namespace SELinux/status/context inputs are visible", "plan bounded service-manager start-only packet", True
    return "private-selinux-surface-proof-review", False, "private proof did not complete cleanly", "inspect helper output", True


def refusal_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "private-selinux-surface-proof-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no device command executed",
        "next_step": "rerun with exact approval if intended",
        "host": collect_host_metadata(),
        "helper": args.helper,
        "helper_expected_sha256": args.helper_sha256,
        "property_root": args.property_root,
        "live_command": command_text(build_helper_command(args)),
        "steps": [],
        "checks": [asdict(Check("approval-gate", "needs-operator", "approval", APPROVAL_PHRASE, "approve before live proof"))],
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "run" and not approved(args):
        return refusal_manifest(args)
    steps: list[Step] = []
    live_step: Step | None = None
    if args.command != "plan":
        steps = run_preflight(args, store)
    pre_checks = build_checks(args, store, steps, None)
    if args.command == "run" and approved(args) and not blockers(pre_checks):
        live_step = capture_step(args, store, "private-selinux-proof", build_helper_command(args), args.timeout)
    checks = build_checks(args, store, steps, live_step)
    decision_value, pass_ok, reason, next_step, mutated = decision(args, checks, live_step)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision_value,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper": args.helper,
        "helper_expected_sha256": args.helper_sha256,
        "property_root": args.property_root,
        "live_command": command_text(build_helper_command(args)),
        "steps": [asdict(step) for step in steps],
        "live_step": asdict(live_step) if live_step else None,
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" and (args.command != "run" or approved(args)),
        "device_mutations": mutated,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in manifest["checks"]]
    return "\n".join([
        "# V402 Private SELinux Surface Proof Runner",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
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
        markdown_table(["name", "status", "severity", "detail", "next"], rows),
        "",
        "## Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Live Command",
        "",
        f"`{manifest['live_command']}`",
        "",
    ]) + "\n"


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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
