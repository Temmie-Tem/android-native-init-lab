#!/usr/bin/env python3
"""V406 system_ext VNDK APEX Wi-Fi HAL linker-list runner.

This runner is fail-closed:

* plan never touches the device
* preflight uses read-only native commands only
* run without the exact approval phrase executes no device command
* approved run executes only the helper ``linker-list`` proof for the Wi-Fi HAL
  inside the helper-owned private namespace

It does not start servicemanager, hwservicemanager, Wi-Fi HAL, wificond,
supplicant, hostapd, CNSS/diag, scan, connect, link-up, credentials, DHCP,
routing, rfkill, firmware mutation, persistence, or Wi-Fi bring-up.
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
from wifi_android_exec_namespace_probe import parse_execns_helper_output
from wifi_service_manager_start_only_approval_packet import DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v406-system-ext-vndk-apex-runner")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063"
DEFAULT_V405 = Path("tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/manifest.json")
TOYBOX = "/cache/bin/toybox"
HELPER_LABEL = "v24"
APPROVAL_PHRASE = (
    "approve v406 system_ext VNDK APEX linker-list proof only; "
    "no daemon start and no Wi-Fi bring-up"
)
MISSING_LIB_RE = re.compile(r'library "([^"]+)" not found')
SERVICE_PROCESS_RE = re.compile(
    r"\b(servicemanager|hwservicemanager|vndservicemanager|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d+|phy\d+)\b", re.IGNORECASE)
NATIVE_SHELL_MAX_COMMAND_ARGS = 30

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("sha-helper", ["run", TOYBOX, "sha256sum", DEFAULT_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_HELPER], 10.0),
    ("stat-real-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"], 10.0),
    ("stat-real-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"], 10.0),
    ("stat-system-apex-current", ["stat", "/mnt/system/system/apex/com.android.vndk.current"], 10.0),
    ("stat-system-ext-vndk-v30", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30"], 10.0),
    ("stat-system-ext-wifi-1-0", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so"], 10.0),
    ("stat-system-ext-wifi-1-4", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.4.so"], 10.0),
    ("cat-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 10.0),
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
    parser.add_argument("--v405-manifest", type=Path, default=DEFAULT_V405)
    parser.add_argument("--target-profile", choices=("vendor-wifi-hal-ext", "vendor-wifi-hal-legacy"), default="vendor-wifi-hal-ext")
    parser.add_argument("--linker", choices=("/system/bin/linker64", "/apex/com.android.runtime/bin/linker64"), default="/apex/com.android.runtime/bin/linker64")
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
    command = [args.helper if item == DEFAULT_HELPER else item for item in command]
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


def parse_int(value: Any, default: int = -1) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def extract_missing_libs(text: str) -> list[str]:
    libs: list[str] = []
    for match in MISSING_LIB_RE.finditer(text):
        lib = match.group(1)
        if lib not in libs:
            libs.append(lib)
    return libs


def build_helper_argv(args: argparse.Namespace) -> list[str]:
    return [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "linker-list",
        "--target-profile",
        args.target_profile,
        "--linker",
        args.linker,
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]


def build_native_run_command(args: argparse.Namespace) -> list[str]:
    command = ["run", *build_helper_argv(args)]
    if len(command) > NATIVE_SHELL_MAX_COMMAND_ARGS:
        raise RuntimeError(f"V406 helper command has {len(command)} args; limit is {NATIVE_SHELL_MAX_COMMAND_ARGS}")
    return command


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "helper": args.helper,
        "expected_sha256": args.helper_sha256,
        "target_profile": args.target_profile,
        "linker": args.linker,
        "max_runtime_sec": args.max_runtime_sec,
        "native_shell_max_command_args": NATIVE_SHELL_MAX_COMMAND_ARGS,
        "command": build_native_run_command(args),
        "not_approved": [
            "servicemanager/hwservicemanager/Wi-Fi HAL daemon start",
            "wificond/supplicant/hostapd/CNSS/diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def build_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[Step],
                 v405: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight after helper v24 build")
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
    helper_ready = args.helper_sha256 in helper_sha and "a90_android_execns_probe v24" in helper_usage and "v30-to-system-ext-v30" in helper_usage

    add_check(checks, "v405-runtime-gap-confirmed", "pass" if v405.get("decision") == "composite-hal-start-only-runtime-gap" and v405.get("pass") else "blocked", "blocker", f"decision={v405.get('decision')} pass={v405.get('pass')}", [str(v405.get("path", ""))], "V405 runtime gap must be the current input")
    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    add_check(checks, "native-clean", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before linker-list proof")
    add_check(checks, f"helper-{HELPER_LABEL}", "pass" if helper_ready else "needs-deploy", "deploy", "remote helper must be v24 with system_ext VNDK APEX mode", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v24 before V406 linker-list proof")
    add_check(checks, "runtime-materials", "pass" if step_ok(steps, "stat-real-ld-config") and step_ok(steps, "stat-real-apex-libraries") else "blocked", "blocker", f"ld={step_ok(steps, 'stat-real-ld-config')} apex={step_ok(steps, 'stat-real-apex-libraries')}", [], "restore real linkerconfig inputs")
    add_check(checks, "system-ext-vndk-v30", "pass" if step_ok(steps, "stat-system-ext-vndk-v30") and step_ok(steps, "stat-system-ext-wifi-1-0") else "blocked", "blocker", "system_ext VNDK v30 and android.hardware.wifi@1.0.so must exist", [], "V406 requires system_ext VNDK v30 source")
    add_check(checks, "vendor-block-source", "pass" if step_ok(steps, "cat-sda29-dev") else "blocked", "blocker", "helper can synthesize private /dev/block/sda29 from /sys/class/block/sda29/dev", [], "restore sda29 sysfs visibility before linker-list proof")
    add_check(checks, "process-surface-clean", "pass" if not processes else "blocked", "blocker", f"process_count={len(processes)}", processes[:8], "do not run linker proof over active manager/HAL processes")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [APPROVAL_PHRASE], "exact phrase and flags required before linker-list proof")
    return checks


def blocker_names(checks: list[Check], *, include_deploy: bool) -> list[str]:
    blocked: list[str] = []
    for check in checks:
        if check.severity == "blocker" and check.status != "pass":
            blocked.append(check.name)
        if include_deploy and check.severity == "deploy" and check.status != "pass":
            blocked.append(check.name)
    return blocked


def run_linker_proof(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = build_native_run_command(args)
    record = run_capture(args, "run-system-ext-vndk-linker-list", command, timeout=args.timeout + args.max_runtime_sec + 30.0)
    rel = "native/run-system-ext-vndk-linker-list.txt"
    store.write_text(rel, strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    parsed = parse_execns_helper_output(text)
    fields = parsed.get("fields", {})
    stderr_text = str(parsed.get("stderr", ""))
    stdout_text = str(parsed.get("stdout", ""))
    missing_libs = extract_missing_libs(stderr_text)
    return {
        "capture": capture_to_manifest(record),
        "file": rel,
        "has_end": parsed.get("has_end"),
        "end_rc": parsed.get("end_rc"),
        "helper_status": fields.get("helper_status", "missing"),
        "probe_run_rc": parse_int(fields.get("probe_run_rc")),
        "child_exit_code": parse_int(fields.get("child_exit_code")),
        "child_signal": parse_int(fields.get("child_signal"), 0),
        "timed_out": fields.get("timed_out") == "1",
        "missing_libs": missing_libs,
        "stdout_bytes": len(stdout_text.encode("utf-8")),
        "stderr_bytes": len(stderr_text.encode("utf-8")),
        "apex_vndk_v30_wifi_1_0_exists": fields.get("context.apex_vndk_v30_wifi_1_0.exists"),
        "system_ext_apex_vndk_v30_exists": fields.get("context.system_ext_apex_vndk_v30.exists"),
    }


def refusal_manifest(args: argparse.Namespace, v405: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "system-ext-vndk-linker-list-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no device command executed",
        "next_step": "rerun with exact V406 phrase only after helper v24 deploy",
        "host": collect_host_metadata(),
        "v405": {"path": v405.get("path"), "decision": v405.get("decision"), "pass": v405.get("pass")},
        "plan": build_plan(args),
        "steps": [],
        "checks": [asdict(Check("approval-gate", "needs-operator", "approval", APPROVAL_PHRASE, [APPROVAL_PHRASE], "approve before linker-list proof"))],
        "linker_result": None,
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


def decide(args: argparse.Namespace, checks: list[Check], linker_result: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "system-ext-vndk-linker-list-plan-ready", True, "plan-only; no device command executed", "run preflight"
    blocked = blocker_names(checks, include_deploy=args.command == "run")
    deploy_needed = any(check.name == f"helper-{HELPER_LABEL}" and check.status != "pass" for check in checks)
    if blocked:
        return "system-ext-vndk-linker-list-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before linker-list proof"
    if args.command == "preflight":
        if deploy_needed:
            return "system-ext-vndk-linker-list-preflight-ready-needs-deploy", True, "preflight complete; helper v24 deploy still requires exact approval", "operator may approve V406 helper deploy"
        return "system-ext-vndk-linker-list-preflight-ready", True, "preflight complete; linker-list proof still requires exact approval", "operator may approve V406 linker-list proof"
    if not approved(args):
        return "system-ext-vndk-linker-list-approval-required", True, "exact approval phrase required; no device command executed", "rerun with exact approval if intended"
    if not linker_result:
        return "system-ext-vndk-linker-list-review-required", False, "missing linker result", "inspect evidence"
    if linker_result["helper_status"] != "namespace-ready" or linker_result["probe_run_rc"] != 0:
        return "system-ext-vndk-linker-list-runtime-gap", True, "helper did not reach namespace-ready linker proof", "inspect helper setup output"
    if linker_result["timed_out"]:
        return "system-ext-vndk-linker-list-timeout", False, "linker-list proof timed out", "inspect and cleanup before retry"
    if linker_result["child_signal"] == 0 and linker_result["child_exit_code"] == 0 and not linker_result["missing_libs"]:
        return "system-ext-vndk-wifi-hal-linker-list-pass", True, "Wi-Fi HAL linker-list dependency closure passed with system_ext VNDK v30", "next may plan bounded HAL start-only retry"
    if "android.hardware.wifi@1.0.so" in linker_result["missing_libs"]:
        return "system-ext-vndk-wifi-hal-linker-list-still-missing-wifi-lib", True, "android.hardware.wifi@1.0.so is still missing from linker namespace", "inspect APEX bind target and linker namespace"
    return "system-ext-vndk-wifi-hal-linker-list-runtime-gap", True, f"child_exit={linker_result['child_exit_code']} signal={linker_result['child_signal']} missing={linker_result['missing_libs']}", "classify next missing dependency"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v405 = load_json(args.v405_manifest)
    if args.command == "run" and not approved(args):
        return refusal_manifest(args, v405)
    steps: list[Step] = []
    linker_result: dict[str, Any] | None = None
    if args.command != "plan":
        steps = run_preflight(args, store)
    checks = build_checks(args, store, steps, v405)
    if args.command == "run" and approved(args) and not blocker_names(checks, include_deploy=True):
        linker_result = run_linker_proof(args, store)
    decision, pass_ok, reason, next_step = decide(args, checks, linker_result)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v405": {"path": v405.get("path"), "decision": v405.get("decision"), "pass": v405.get("pass")},
        "plan": build_plan(args),
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "linker_result": linker_result,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" and (args.command != "run" or approved(args)),
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": build_plan(args)["not_approved"],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], "<br>".join(c["evidence"]), c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    linker = manifest.get("linker_result") or {}
    return "\n".join([
        "# V406 System_ext VNDK APEX Runner",
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
        "## Linker Result",
        "",
        f"- child_exit_code: `{linker.get('child_exit_code')}`",
        f"- child_signal: `{linker.get('child_signal')}`",
        f"- missing_libs: `{linker.get('missing_libs')}`",
        f"- file: `{linker.get('file')}`",
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
