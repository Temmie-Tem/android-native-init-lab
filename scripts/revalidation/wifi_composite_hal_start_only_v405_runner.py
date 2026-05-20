#!/usr/bin/env python3
"""V405 guarded composite Wi-Fi HAL start-only runner.

This runner is fail-closed:

* plan never touches the device
* preflight uses read-only native commands only
* run without the exact approval phrase executes no device command
* approved run starts only servicemanager + hwservicemanager + one Wi-Fi HAL
  candidate inside one helper-owned private namespace

It does not start wificond, supplicant, hostapd, CNSS/diag, scan, connect,
link-up, credentials, DHCP, routing, rfkill, firmware mutation, or persistent
boot/autostart flows.
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
from wifi_service_manager_start_only_approval_packet import DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v405-composite-hal-start-only-runner")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
DEFAULT_V404 = Path("tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/manifest.json")
TOYBOX = "/cache/bin/toybox"
HELPER_LABEL = "v23"
APPROVAL_PHRASE = (
    "approve v405 composite Wi-Fi HAL start-only smoke only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
NATIVE_SHELL_MAX_COMMAND_ARGS = 30
SERVICE_PROCESS_RE = re.compile(
    r"\b(servicemanager|hwservicemanager|vndservicemanager|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d+|phy\d+)\b", re.IGNORECASE)
COMPOSITE_KEY_RE = re.compile(r"^wifi_hal_composite_start\.([A-Za-z0-9_.]+)=(.*)$")

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("sha-helper", ["run", TOYBOX, "sha256sum", DEFAULT_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_HELPER], 10.0),
    ("stat-property-root", ["stat", DEFAULT_PROPERTY_ROOT], 10.0),
    ("stat-real-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"], 10.0),
    ("stat-real-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"], 10.0),
    ("stat-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
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
    parser.add_argument("--v404-manifest", type=Path, default=DEFAULT_V404)
    parser.add_argument("--target-profile", choices=("vendor-wifi-hal-ext", "vendor-wifi-hal-legacy"), default="vendor-wifi-hal-ext")
    parser.add_argument("--max-runtime-sec", type=int, default=6)
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


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def capture_command(args: argparse.Namespace, store: EvidenceStore, name: str,
                    command: list[str], timeout: float) -> Step:
    command = [
        args.helper if item == DEFAULT_HELPER else
        args.property_root if item == DEFAULT_PROPERTY_ROOT else
        item
        for item in command
    ]
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return Step(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[Step]:
    store.mkdir("native")
    return [capture_command(args, store, name, command, timeout) for name, command, timeout in READ_ONLY_COMMANDS]


def step_text(store: EvidenceStore, steps: list[Step], name: str) -> str:
    for step in steps:
        if step.name == name:
            path = store.path(step.file)
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[Step], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_helper_argv(args: argparse.Namespace, *, include_data_wifi: bool = True) -> list[str]:
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-hal-composite-start-only",
        "--target-profile",
        args.target_profile,
        "--null-device-mode",
        "dev-null-selinux",
    ]
    if include_data_wifi:
        argv.extend(["--data-wifi-mode", "private-empty"])
    argv.extend([
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
        str(args.max_runtime_sec),
    ])
    if approved(args):
        argv.extend(["--allow-service-manager-start-only", "--allow-wifi-hal-start-only"])
    return argv


def build_native_run_command(args: argparse.Namespace) -> list[str]:
    command = ["run", *build_helper_argv(args)]
    if len(command) <= NATIVE_SHELL_MAX_COMMAND_ARGS:
        return command
    command = ["run", *build_helper_argv(args, include_data_wifi=False)]
    if len(command) <= NATIVE_SHELL_MAX_COMMAND_ARGS:
        return command
    raise RuntimeError(f"composite helper command has {len(command)} args; limit is {NATIVE_SHELL_MAX_COMMAND_ARGS}")


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "helper": args.helper,
        "expected_sha256": args.helper_sha256,
        "target_profile": args.target_profile,
        "max_runtime_sec": args.max_runtime_sec,
        "native_shell_max_command_args": NATIVE_SHELL_MAX_COMMAND_ARGS,
        "command": build_native_run_command(args),
        "not_approved": [
            "wificond/supplicant/hostapd start",
            "CNSS/diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def build_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[Step],
                 v404: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight after helper v23 deploy")
        return checks
    version = step_text(store, steps, "version")
    status = step_text(store, steps, "status")
    selftest = step_text(store, steps, "selftest")
    helper_sha = step_text(store, steps, "sha-helper")
    helper_usage = step_text(store, steps, "helper-usage")
    ps = step_text(store, steps, "ps")
    netdev = step_text(store, steps, "proc-net-dev")
    processes = [line.strip() for line in ps.splitlines() if SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]
    add_check(checks, "v404-readiness-pass", "pass" if v404.get("decision") == "v404-private-composite-hal-readiness-packet-ready" and v404.get("pass") else "blocked", "blocker", f"decision={v404.get('decision')} pass={v404.get('pass')}", [str(v404.get("path", ""))], "V404 readiness must pass before V405")
    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    add_check(checks, "native-clean", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before live run")
    add_check(checks, f"helper-{HELPER_LABEL}", "pass" if args.helper_sha256 in helper_sha and "a90_android_execns_probe v23" in helper_usage and "wifi-hal-composite-start-only" in helper_usage and "--allow-wifi-hal-start-only" in helper_usage else "blocked", "blocker", "remote helper must be v23 with composite HAL mode", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v23 before live composite HAL runner")
    add_check(checks, "runtime-materials", "pass" if step_ok(steps, "stat-real-ld-config") and step_ok(steps, "stat-real-apex-libraries") and step_ok(steps, "stat-property-root") else "blocked", "blocker", f"ld={step_ok(steps, 'stat-real-ld-config')} apex={step_ok(steps, 'stat-real-apex-libraries')} property={step_ok(steps, 'stat-property-root')}", [], "restore private runtime materialization inputs")
    add_check(checks, "service-manager-binaries", "pass" if step_ok(steps, "stat-servicemanager") and step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={step_ok(steps, 'stat-servicemanager')} hwservicemanager={step_ok(steps, 'stat-hwservicemanager')}", [], "core managers must be visible")
    add_check(checks, "process-surface-clean", "pass" if not processes else "blocked", "blocker", f"process_count={len(processes)}", processes[:8], "do not run over existing manager/HAL processes")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [APPROVAL_PHRASE], "exact phrase and flags required before HAL start-only")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def parse_composite_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = COMPOSITE_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = build_native_run_command(args)
    record = run_capture(args, "run-composite-hal", command, timeout=args.timeout + args.max_runtime_sec + 30.0)
    rel = "native/run-composite-hal.txt"
    store.write_text(rel, strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    keys = parse_composite_keys(text)
    return {
        "capture": capture_to_manifest(record),
        "file": rel,
        "keys": keys,
        "helper_result": keys.get("result", "missing"),
        "helper_reason": keys.get("reason", ""),
        "timed_out": keys.get("timed_out") == "1",
        "all_postflight_safe": keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": keys.get("all_observable_at_timeout") == "1",
    }


def postflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ps = capture_command(args, store, "post-ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    netdev = capture_command(args, store, "post-proc-net-dev", ["cat", "/proc/net/dev"], 10.0)
    ps_text = step_text(store, [ps], "post-ps")
    netdev_text = step_text(store, [netdev], "post-proc-net-dev")
    processes = [line.strip() for line in ps_text.splitlines() if SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev_text.splitlines() if WIFI_RE.search(line)]
    return {"ps_ok": ps.ok, "netdev_ok": netdev.ok, "processes": processes, "wifi_links": wifi_links, "clean": ps.ok and netdev.ok and not processes and not wifi_links}


def refusal_manifest(args: argparse.Namespace, v404: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "composite-hal-start-only-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no device command executed",
        "next_step": "rerun with exact approval only after helper v23 deploy and review",
        "host": collect_host_metadata(),
        "v404": {"path": v404.get("path"), "decision": v404.get("decision"), "pass": v404.get("pass")},
        "plan": build_plan(args),
        "steps": [],
        "checks": [asdict(Check("approval-gate", "needs-operator", "approval", APPROVAL_PHRASE, [APPROVAL_PHRASE], "approve before live HAL start-only"))],
        "live_result": None,
        "postflight": None,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
    }


def decide(args: argparse.Namespace, checks: list[Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "composite-hal-start-only-plan-ready", True, "plan-only; no device command executed", "run preflight after helper v23 deploy", False
    blocked = blockers(checks)
    if blocked:
        return "composite-hal-start-only-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before approval", False
    if args.command == "preflight":
        return "composite-hal-start-only-preflight-ready", True, "read-only preflight is ready; live run still needs approval", "operator may approve exact V405 phrase", False
    if not approved(args):
        return "composite-hal-start-only-approval-required", True, "exact approval phrase required; no device command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "composite-hal-start-only-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    result = live_result.get("helper_result")
    if result == "start-only-pass" and live_result.get("all_postflight_safe") and post.get("clean"):
        return "composite-hal-start-only-pass", True, "composite HAL target observed until timeout and cleaned", "route next Wi-Fi HAL registration evidence", True
    if result == "start-only-runtime-gap" and live_result.get("all_postflight_safe") and post.get("clean"):
        return "composite-hal-start-only-runtime-gap", True, "composite HAL exited before observe window but cleanup is safe", "classify HAL runtime gap", True
    return "composite-hal-start-only-review-required", False, f"helper_result={result}", "inspect helper output before widening scope", True


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v404 = load_json(args.v404_manifest)
    if args.command == "run" and not approved(args):
        return refusal_manifest(args, v404)
    steps: list[Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = run_preflight(args, store)
    checks = build_checks(args, store, steps, v404)
    if args.command == "run" and approved(args) and not blockers(checks):
        live_result = run_live(args, store)
        post = postflight(args, store)
    decision, pass_ok, reason, next_step, daemon_started = decide(args, checks, live_result, post)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v404": {"path": v404.get("path"), "decision": v404.get("decision"), "pass": v404.get("pass")},
        "plan": build_plan(args),
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "live_result": live_result,
        "postflight": post,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" and (args.command != "run" or approved(args)),
        "device_mutations": daemon_started,
        "daemon_start_executed": daemon_started,
        "wifi_hal_start_executed": daemon_started,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], "<br>".join(c["evidence"]), c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    return "\n".join([
        "# V405 Composite Wi-Fi HAL Start-Only Runner",
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
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Command",
        "",
        "`" + " ".join(manifest["plan"]["command"]) + "`",
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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
