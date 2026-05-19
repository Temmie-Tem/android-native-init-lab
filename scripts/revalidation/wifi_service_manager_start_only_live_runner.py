#!/usr/bin/env python3
"""V376 guarded service-manager start-only live runner.

This is the execution body that V373 intentionally did not implement.  The
runner remains fail-closed:

* plan/preflight never starts a daemon
* run without the exact V373 approval phrase executes no bridge command
* approved run executes only bounded service-manager start-only helper calls

It does not start Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or Wi-Fi
bring-up flows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_service_manager_start_only_approval_packet import APPROVAL_PHRASE, DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v376-service-manager-start-only-live-runner")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918"
DEFAULT_PROPERTY_ROOT = ""
DEFAULT_DATA_WIFI_MODE = "none"
DEFAULT_CAPTURE_MODE = "none"
SUMMARY_TITLE = "v376 Service-Manager Start-Only Live Runner"
HELPER_LABEL = "v12"
HELPER_DEPLOY_HINT = "run V375 deploy first"
TOYBOX = "/cache/bin/toybox"
SERVICE_TARGETS = ("system-servicemanager", "system-hwservicemanager")
SERVICE_PROCESS_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
SERVICE_KEY_RE = re.compile(r"^service_manager_start\.([A-Za-z0-9_]+)=(.*)$")
NATIVE_SHELL_MAX_COMMAND_ARGS = 30

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("sha-helper", ["run", TOYBOX, "sha256sum", DEFAULT_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_HELPER], 10.0),
    ("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("stat-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("stat-real-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"], 10.0),
    ("stat-real-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"], 10.0),
    ("stat-sda29-sysfs", ["stat", "/sys/class/block/sda29/dev"], 10.0),
    ("stat-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
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
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


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
    parser.add_argument("--data-wifi-mode", choices=("none", "private-empty"), default=DEFAULT_DATA_WIFI_MODE)
    parser.add_argument("--capture-mode", choices=("none", "ptrace-lite"), default=DEFAULT_CAPTURE_MODE)
    parser.add_argument("--max-runtime-sec", type=int, default=8)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    args = parser.parse_args()
    if args.max_runtime_sec < 1 or args.max_runtime_sec > 30:
        raise SystemExit("--max-runtime-sec must be 1..30")
    return args


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def capture_command(args: argparse.Namespace, store: EvidenceStore, name: str,
                    command: list[str], timeout: float) -> Step:
    command = [args.helper if item == DEFAULT_HELPER else item for item in command]
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return Step(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def capture_text(store: EvidenceStore, steps: list[Step], name: str) -> str:
    for step in steps:
        if step.name == name:
            return store.path(step.file).read_text(encoding="utf-8", errors="replace")
    return ""


def step_ok(steps: list[Step], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[Step]:
    store.mkdir("native")
    commands = list(READ_ONLY_COMMANDS)
    if args.property_root:
        commands.append(("stat-property-root", ["stat", args.property_root], 10.0))
    return [capture_command(args, store, name, command, timeout) for name, command, timeout in commands]


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_helper_argv(args: argparse.Namespace, target_profile: str) -> list[str]:
    return build_helper_argv_with_options(args, target_profile, include_data_wifi=True)


def build_helper_argv_with_options(args: argparse.Namespace,
                                   target_profile: str,
                                   *,
                                   include_data_wifi: bool) -> list[str]:
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "service-manager-start-only",
        "--target-profile",
        target_profile,
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]
    if args.capture_mode != "none":
        argv.extend(["--capture-mode", args.capture_mode])
    if include_data_wifi and args.data_wifi_mode != "none":
        argv.extend(["--data-wifi-mode", args.data_wifi_mode])
    if args.property_root:
        argv.extend(["--property-root", args.property_root])
    if approved(args):
        argv.append("--allow-service-manager-start-only")
    return argv


def build_native_run_command(args: argparse.Namespace, target_profile: str) -> list[str]:
    command = ["run", *build_helper_argv(args, target_profile)]
    if len(command) > NATIVE_SHELL_MAX_COMMAND_ARGS and args.data_wifi_mode != "none":
        command = [
            "run",
            *build_helper_argv_with_options(
                args,
                target_profile,
                include_data_wifi=False,
            ),
        ]
    if len(command) <= NATIVE_SHELL_MAX_COMMAND_ARGS:
        return command
    raise RuntimeError(
        f"service-manager helper command has {len(command)} args; "
        f"native shell limit is {NATIVE_SHELL_MAX_COMMAND_ARGS}"
    )


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "targets": list(SERVICE_TARGETS),
        "helper": args.helper,
        "expected_sha256": args.helper_sha256,
        "max_runtime_sec": args.max_runtime_sec,
        "property_root": args.property_root,
        "data_wifi_mode": args.data_wifi_mode,
        "capture_mode": args.capture_mode,
        "native_shell_max_command_args": NATIVE_SHELL_MAX_COMMAND_ARGS,
        "arg_compaction": (
            "drops --data-wifi-mode from service-manager live command if needed; "
            "service-manager start-only does not require /data/vendor/wifi"
        ),
        "commands": {
            target: build_native_run_command(args, target)
            for target in SERVICE_TARGETS
        },
        "not_approved": [
            "Wi-Fi HAL start",
            "wificond/supplicant/hostapd start",
            "CNSS/diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, firmware mutation, Android partition write",
        ],
    }


def build_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[Step]) -> list[Check]:
    checks: list[Check] = []
    version = capture_text(store, steps, "version")
    status = capture_text(store, steps, "status")
    selftest = capture_text(store, steps, "selftest")
    helper_sha = capture_text(store, steps, "sha-helper")
    helper_usage = capture_text(store, steps, "helper-usage")
    ps = capture_text(store, steps, "ps")
    netdev = capture_text(store, steps, "proc-net-dev")
    managers = [line.strip() for line in ps.splitlines() if SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]

    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    add_check(checks, "native-clean", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [line.strip() for line in (status + "\n" + selftest).splitlines() if line.strip().startswith("selftest:")][:4], "fix native health before live run")
    add_check(checks, f"helper-{HELPER_LABEL}", "pass" if args.helper_sha256 in helper_sha and "service-manager-start-only" in helper_usage and "--allow-service-manager-start-only" in helper_usage else "blocked", "blocker", f"remote helper must be deployed {HELPER_LABEL} with service-manager mode", [line for line in helper_sha.splitlines() if args.helper in line][:2], HELPER_DEPLOY_HINT)
    add_check(checks, "service-manager-binaries", "pass" if step_ok(steps, "stat-servicemanager") and step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={step_ok(steps, 'stat-servicemanager')} hwservicemanager={step_ok(steps, 'stat-hwservicemanager')} vndservicemanager={step_ok(steps, 'stat-vndservicemanager')}", [], "both core service-manager binaries must be visible")
    add_check(checks, "runtime-materials", "pass" if step_ok(steps, "stat-real-ld-config") and step_ok(steps, "stat-real-apex-libraries") and step_ok(steps, "stat-sda29-sysfs") else "blocked", "blocker", f"ld={step_ok(steps, 'stat-real-ld-config')} apex={step_ok(steps, 'stat-real-apex-libraries')} sda29_sysfs={step_ok(steps, 'stat-sda29-sysfs')}", [], "runtime materialization inputs must be present")
    if args.property_root:
        add_check(checks, "property-root-visible", "pass" if step_ok(steps, "stat-property-root") else "blocked", "blocker", f"path={args.property_root} visible={step_ok(steps, 'stat-property-root')}", [args.property_root], "private property root must be exported before start-only run")
    add_check(checks, "data-wifi-mode", "pass", "info", f"mode={args.data_wifi_mode}", [], "helper creates private-empty data tree only inside its temp namespace")
    add_check(checks, "capture-mode", "pass", "info", f"mode={args.capture_mode}", [], "ptrace-lite is capture-only and still bounded by service-manager start-only approval")
    add_check(checks, "process-surface-clean", "pass" if not managers else "blocked", "blocker", f"process_count={len(managers)}", managers[:8], "do not run over existing manager processes")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    add_check(checks, "temporary-binder-nodes-clean", "pass" if not step_ok(steps, "stat-binder") and not step_ok(steps, "stat-hwbinder") and not step_ok(steps, "stat-vndbinder") else "blocked", "blocker", f"binder={step_ok(steps, 'stat-binder')} hwbinder={step_ok(steps, 'stat-hwbinder')} vndbinder={step_ok(steps, 'stat-vndbinder')}", [], "helper must own temporary node lifecycle")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [APPROVAL_PHRASE], "exact phrase and flags required before daemon start")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def parse_service_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = SERVICE_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_target(args: argparse.Namespace, store: EvidenceStore, target_profile: str) -> dict[str, Any]:
    command = build_native_run_command(args, target_profile)
    record = run_capture(args, f"run-{target_profile}", command, timeout=args.timeout + args.max_runtime_sec + 20.0)
    rel = f"native/run-{target_profile}.txt"
    store.write_text(rel, strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    keys = parse_service_keys(text)
    return {
        "target_profile": target_profile,
        "capture": capture_to_manifest(record),
        "file": rel,
        "keys": keys,
        "helper_result": keys.get("result", "missing"),
        "helper_reason": keys.get("reason", ""),
        "exec_attempted": keys.get("exec_attempted") == "1",
        "child_started": keys.get("child_started") == "1",
        "postflight_safe": keys.get("postflight_safe") == "1",
        "reaped": keys.get("reaped") == "1",
        "timed_out": keys.get("timed_out") == "1",
    }


def run_postflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ps = capture_command(args, store, "post-ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    netdev = capture_command(args, store, "post-proc-net-dev", ["cat", "/proc/net/dev"], 10.0)
    ps_text = capture_text(store, [ps], "post-ps")
    netdev_text = capture_text(store, [netdev], "post-proc-net-dev")
    managers = [line.strip() for line in ps_text.splitlines() if SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev_text.splitlines() if WIFI_RE.search(line)]
    return {
        "ps_ok": ps.ok,
        "netdev_ok": netdev.ok,
        "manager_processes": managers,
        "wifi_links": wifi_links,
        "clean": ps.ok and netdev.ok and not managers and not wifi_links,
    }


def decide(args: argparse.Namespace, checks: list[Check],
           observations: list[dict[str, Any]], postflight: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    blocked = blockers(checks)
    if args.command == "plan":
        return "service-manager-start-only-live-plan-ready", True, "plan-only; no live command executed", "run preflight"
    if blocked:
        return "service-manager-start-only-live-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before approval"
    if args.command == "preflight":
        return "service-manager-start-only-live-preflight-ready", True, "read-only preflight is ready; live run still needs approval", "operator may approve V373 phrase"
    if not approved(args):
        return "service-manager-start-only-live-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if live smoke is intended"
    if not observations:
        return "service-manager-start-only-live-failed", False, "approved run produced no observations", "inspect runner"
    unsafe = [item for item in observations if not item["postflight_safe"]]
    missing = [item for item in observations if item["helper_result"] == "missing"]
    if unsafe or missing or not postflight or not postflight["clean"]:
        return "service-manager-start-only-live-review-required", False, "helper or postflight did not prove clean bounded stop", "inspect evidence and consider recovery reboot"
    results = {item["helper_result"] for item in observations}
    if results <= {"start-only-pass"}:
        return "service-manager-start-only-live-pass", True, "service-manager targets observed until timeout and cleaned", "next evaluate HAL readiness"
    if results <= {"start-only-pass", "start-only-runtime-gap"}:
        return "service-manager-start-only-live-runtime-gap", True, "one or more targets exited before observe window but cleanup is safe", "classify runtime gap before HAL start"
    return "service-manager-start-only-live-review-required", False, f"unexpected helper results: {sorted(results)}", "inspect helper outputs"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    lines = [
        f"# {SUMMARY_TITLE}",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
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
    if manifest["observations"]:
        rows = [
            [
                item["target_profile"],
                item["helper_result"],
                item["helper_reason"],
                item["exec_attempted"],
                item["postflight_safe"],
                item["file"],
            ]
            for item in manifest["observations"]
        ]
        lines.extend(["## Observations", "", markdown_table(["target", "result", "reason", "exec", "safe", "file"], rows), ""])
    if manifest["postflight"]:
        lines.extend([
            "## Postflight",
            "",
            f"- clean: `{manifest['postflight']['clean']}`",
            f"- manager_processes: `{len(manifest['postflight']['manager_processes'])}`",
            f"- wifi_links: `{len(manifest['postflight']['wifi_links'])}`",
            "",
        ])
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    plan = build_plan(args)
    store.write_json("plan.json", plan)
    steps: list[Step] = []
    checks: list[Check] = []
    observations: list[dict[str, Any]] = []
    postflight: dict[str, Any] | None = None
    daemon_start_executed = False

    if args.command == "run" and not approved(args):
        add_check(checks, "approval-gate", "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [APPROVAL_PHRASE], "exact phrase and flags required before live command")
    else:
        steps = [] if args.command == "plan" else run_preflight(args, store)
        checks = [] if args.command == "plan" else build_checks(args, store, steps)
    if args.command == "run" and approved(args) and not blockers(checks):
        for target in SERVICE_TARGETS:
            observation = run_target(args, store, target)
            observations.append(observation)
            daemon_start_executed = daemon_start_executed or observation["exec_attempted"]
        postflight = run_postflight(args, store)
    decision, pass_ok, reason, next_step = decide(args, checks, observations, postflight)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "plan": plan,
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "observations": observations,
        "postflight": postflight,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "daemon_start_executed": daemon_start_executed,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": plan["not_approved"],
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
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
