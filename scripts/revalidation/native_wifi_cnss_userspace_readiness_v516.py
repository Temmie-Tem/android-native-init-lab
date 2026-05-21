#!/usr/bin/env python3
"""V516 bounded CNSS userspace-readiness proof.

This proof starts helper-owned `cnss_diag` and `cnss-daemon` only, in Android
order, then classifies whether WLFW/QMI/BDF/FW-ready markers appear. It does
not write qcwlanstate, write boot_wlan, start Wi-Fi HAL, scan, connect, request
DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v516-cnss-userspace-readiness")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "1a447e5e4ff1f6ae8fa3fc4666c4dacee3b760824d09c51d11a8289760a2e76b"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v60"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
DEFAULT_V515_MANIFEST = Path("tmp/wifi/v515-android-native-sequence-delta/manifest.json")
HELPER_MODE = "cnss-userspace-readiness"
APPROVAL_PHRASE = (
    "approve v516 cnss userspace readiness proof only; "
    "no qcwlanstate write, no scan/connect/link-up and no external ping"
)

KEY_RE = re.compile(r"^(cnss_userspace_readiness|wifi_hal_composite_start|wifi_hal_composite_child)\.([A-Za-z0-9_.-]+)=(.*)$")
PROCESS_RE = re.compile(r"\b(cnss-daemon|cnss_diag|wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b", re.IGNORECASE)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_PATTERNS = {
    "cnss_diag_netlink": re.compile(r"netlink_create.*comm:\s*cnss_diag|comm:cnss_diag", re.IGNORECASE),
    "cnss_daemon_netlink": re.compile(r"netlink_create.*comm:\s*cnss-daemon|comm:cnss-daemon|cnss-daemon.*ctrl_getfamily", re.IGNORECASE),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.IGNORECASE),
    "wlfw_thread": re.compile(r"cnss-daemon wlfw_service_request", re.IGNORECASE),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE),
    "wifi_turning_on": re.compile(r"Wifi Turning On from UI", re.IGNORECASE),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE),
    "wcnss_cfg_request": re.compile(r"WCNSS_qcom_cfg\.ini", re.IGNORECASE),
    "wma_service_ready": re.compile(r"wma_rx_service_ready_event|FW ready event received", re.IGNORECASE),
    "wlan0_event": re.compile(r"dev\s*:\s*wlan0\s*:\s*event", re.IGNORECASE),
    "timed_out": re.compile(r"Timed-out!!", re.IGNORECASE),
    "modules_not_initialized": re.compile(r"Modules not initialized just return", re.IGNORECASE),
}
READINESS_MARKERS = (
    "wlfw_start",
    "wlfw_thread",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wcnss_cfg_request",
    "wma_service_ready",
    "wlan0_event",
)


@dataclass(frozen=True)
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--property-root", default=DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--v515-manifest", type=Path, default=DEFAULT_V515_MANIFEST)
    parser.add_argument("--max-runtime-sec", type=int, default=10)
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


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 20.0),
        run_step(args, store, "selftest", ["selftest"], 20.0),
        run_step(args, store, "sha-helper", ["run", "/cache/bin/toybox", "sha256sum", args.helper], 20.0),
        run_step(args, store, "helper-usage", ["run", args.helper, "--help"], 20.0),
        run_step(args, store, "ps", ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "sys-class-net", ["ls", "/sys/class/net"], 10.0),
        run_step(args, store, "sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0),
    ]


def helper_command(args: argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", HELPER_MODE,
        "--null-device-mode", "dev-null",
        "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
        "--linkerconfig-mode", "minimal-vendor",
        "--android-selinux-context-mode", "service-defaults",
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if approved(args):
        command.extend(["--allow-cnss-start-only", "--allow-cnss-userspace-readiness"])
    return command


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    before = run_step(args, store, "dmesg-before", ["run", "/cache/bin/toybox", "dmesg"], 60.0)
    live = run_step(args, store, "v516-helper-run", helper_command(args), args.max_runtime_sec + 35.0)
    after = run_step(args, store, "dmesg-after", ["run", "/cache/bin/toybox", "dmesg"], 60.0)
    post_ps = run_step(args, store, "post-ps", ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    post_net = run_step(args, store, "post-proc-net-dev", ["cat", "/proc/net/dev"], 10.0)
    keys = parse_keys(step_payload([live], "v516-helper-run"))
    before_payload = step_payload([before], "dmesg-before")
    after_payload = step_payload([after], "dmesg-after")
    dmesg_delta = after_payload[len(before_payload):] if after_payload.startswith(before_payload) else after_payload
    write_capture(store, "dmesg-delta", dmesg_delta)
    return {
        "before": before,
        "live": live,
        "after": after,
        "dmesg_delta": dmesg_delta,
        "post_ps": post_ps,
        "post_net": post_net,
        "keys": keys,
        "helper_result": keys.get("cnss_userspace_readiness.result", "missing"),
        "all_postflight_safe": keys.get("cnss_userspace_readiness.all_postflight_safe") == "1",
    }


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = KEY_RE.match(line)
        if match:
            keys[f"{match.group(1)}.{match.group(2)}"] = match.group(3).strip()
    return keys


def dmesg_summary(text: str) -> dict[str, Any]:
    lines = [ANSI_RE.sub("", line).strip() for line in text.splitlines() if line.strip()]
    events: dict[str, list[str]] = {name: [] for name in DMESG_PATTERNS}
    for line in lines:
        for name, pattern in DMESG_PATTERNS.items():
            if pattern.search(line):
                events[name].append(line)
    counts = {name: len(items) for name, items in events.items()}
    latest = {name: (items[-1] if items else "") for name, items in events.items()}
    return {
        "counts": counts,
        "latest": latest,
        "readiness_markers": [name for name in READINESS_MARKERS if counts.get(name, 0) > 0],
        "focus_tail": [line for name in DMESG_PATTERNS for line in events[name]][-160:],
    }


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "exists": True,
        "path": str(resolved),
        "decision": data.get("decision"),
        "pass": data.get("pass"),
        "reason": data.get("reason"),
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], v515: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    helper_sha = step_payload(steps, "sha-helper")
    helper_usage = step_payload(steps, "helper-usage")
    ps = step_payload(steps, "ps")
    netdev = step_payload(steps, "proc-net-dev")
    sys_net = step_payload(steps, "sys-class-net")
    sys_ieee = step_payload(steps, "sys-class-ieee80211")
    process_hits = [line.strip() for line in ps.splitlines() if PROCESS_RE.search(line)]
    wifi_hits = [line.strip() for line in (netdev + "\n" + sys_net + "\n" + sys_ieee).splitlines() if WIFI_RE.search(line)]
    helper_ready = args.helper_sha256 in helper_sha and args.helper_marker in helper_usage and HELPER_MODE in helper_usage

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2],
              "restore native baseline before V516")
    add_check(checks, "helper-v60-ready", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={args.helper_sha256 in helper_sha} marker={args.helper_marker in helper_usage} mode={HELPER_MODE in helper_usage}",
              [args.helper_sha256, args.helper_marker, HELPER_MODE],
              "deploy helper v60 over NCM")
    add_check(checks, "v515-gap-classified", "pass" if v515.get("decision") == "v515-android-native-sequence-gap-classified" else "blocked", "blocker",
              f"decision={v515.get('decision')}", [str(v515.get("path"))],
              "run V515 sequence comparator first")
    add_check(checks, "no-active-wifi-processes", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8],
              "cleanup residual Wi-Fi/CNSS processes before bounded replay")
    add_check(checks, "no-wifi-link-surface", "pass" if not wifi_hits else "blocked", "blocker",
              f"wifi_hits={len(wifi_hits)}", wifi_hits[:8],
              "if wlan0 already exists, move to scan-only instead of V516")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def classify(args: argparse.Namespace,
             checks: list[Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v516-cnss-userspace-readiness-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = blockers(checks)
    if blocked:
        return "v516-cnss-userspace-readiness-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V516", False
    if args.command == "preflight":
        return "v516-cnss-userspace-readiness-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V516 readiness proof", False
    if not approved(args):
        return "v516-cnss-userspace-readiness-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V516 approval", False
    if not live_result:
        return "v516-cnss-userspace-readiness-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v516-cnss-userspace-readiness-cleanup-review", False, "helper-owned CNSS children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    helper_result = live_result["helper_result"]
    readiness_markers = dmesg.get("readiness_markers") or []
    if readiness_markers:
        return "v516-cnss-userspace-readiness-marker-observed", True, "bounded CNSS userspace replay observed readiness markers: " + ",".join(readiness_markers), "advance to bounded qcwlanstate/HAL retry; still no scan/connect", True
    if helper_result == "readiness-window-pass":
        return "v516-cnss-userspace-readiness-no-fw-marker", True, "cnss_diag/cnss-daemon were observable and cleaned, but no WLFW/QMI/BDF/FW-ready marker appeared", "add missing QRTR/modem/vendor service prerequisite before qcwlanstate retry", True
    if helper_result == "start-only-runtime-gap":
        return "v516-cnss-userspace-readiness-runtime-gap", True, "one CNSS userspace child exited before the observe window", "inspect child stdout/stderr and identity/runtime gaps", True
    return "v516-cnss-userspace-readiness-review-required", False, f"helper_result={helper_result}", "inspect V516 transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    dmesg = manifest.get("dmesg_summary") or {}
    count_rows = [[key, value] for key, value in sorted((dmesg.get("counts") or {}).items())]
    return "\n".join([
        "# V516 CNSS Userspace Readiness Proof",
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
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Dmesg Pattern Counts",
        "",
        markdown_table(["pattern", "count"], count_rows) if count_rows else "- none",
        "",
        "## Readiness Markers",
        "",
        ", ".join(dmesg.get("readiness_markers") or []) or "- none",
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    live_result: dict[str, Any] | None = None
    if args.command != "plan":
        steps = preflight_steps(args, store)
    if args.command == "run" and approved(args) and not blockers(build_checks(args, steps, load_manifest(args.v515_manifest))):
        live_result = run_live(args, store)
    v515 = load_manifest(args.v515_manifest)
    checks = build_checks(args, steps, v515)
    dmesg = dmesg_summary(str(live_result.get("dmesg_delta", ""))) if live_result else dmesg_summary("")
    decision, pass_ok, reason, next_step, live_executed = classify(args, checks, live_result, dmesg)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "live_result": live_result,
        "dmesg_summary": dmesg,
        "v515_manifest": v515,
        "device_commands_executed": args.command != "plan",
        "device_mutations": live_executed,
        "daemon_start_executed": live_executed,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    global args
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
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
