#!/usr/bin/env python3
"""V704 host-only CNSS retry pre-WLFW stall snapshot classifier.

This classifier consumes V700 provider-first CNSS evidence and V703
Android/native binding comparison evidence. It decides whether the provider
first retry crashed, failed Binder, or stayed alive below WLFW, and identifies
the next live capture needed. It does not contact the device, start daemons,
scan/connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v704-cnss-retry-stall-snapshot")
DEFAULT_V700_MANIFEST = Path("tmp/wifi/v700-provider-first-cnss-orchestrated-run/manifest.json")
DEFAULT_V703_MANIFEST = Path("tmp/wifi/v703-android-native-binding-compare/manifest.json")
DEFAULT_V700_HELPER = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt"
)
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt")

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)

KEY_VALUE_RE = re.compile(r"^(?P<key>[^=\s][^=]*?)=(?P<value>.*)$")
STATUS_BEGIN_RE = re.compile(r"^A90_EXECNS_CNSS_PROC_status_BEGIN path=/proc/(?P<pid>\d+)/status ")
STATUS_END_RE = re.compile(r"^A90_EXECNS_CNSS_PROC_status_END ")
ATTR_BEGIN_RE = re.compile(r"^A90_EXECNS_CNSS_PROC_attr_current_BEGIN path=/proc/(?P<pid>\d+)/attr/current ")
ATTR_END_RE = re.compile(r"^A90_EXECNS_CNSS_PROC_attr_current_END ")
FD_TARGET_RE = re.compile(r"^capture\.wifi_hal_composite_cnss_daemon_retry\.fd_links\.entry_\d+\.target=(?P<target>.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v700-manifest", type=Path, default=DEFAULT_V700_MANIFEST)
    parser.add_argument("--v703-manifest", type=Path, default=DEFAULT_V703_MANIFEST)
    parser.add_argument("--v700-helper", type=Path, default=DEFAULT_V700_HELPER)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = KEY_VALUE_RE.match(line)
        if match:
            values.setdefault(match.group("key"), []).append(match.group("value"))
    return values


def latest(values: dict[str, list[str]], key: str) -> str:
    rows = values.get(key) or []
    return rows[-1] if rows else ""


def parse_proc_blocks(text: str, pid: str) -> dict[str, Any]:
    status_lines: list[str] = []
    attr_lines: list[str] = []
    in_status = False
    in_attr = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        status_begin = STATUS_BEGIN_RE.match(line)
        if status_begin:
            in_status = status_begin.group("pid") == pid
            continue
        if in_status and STATUS_END_RE.match(line):
            in_status = False
            continue
        if in_status:
            status_lines.append(line)
            continue
        attr_begin = ATTR_BEGIN_RE.match(line)
        if attr_begin:
            in_attr = attr_begin.group("pid") == pid
            continue
        if in_attr and ATTR_END_RE.match(line):
            in_attr = False
            continue
        if in_attr:
            attr_lines.append(line)

    status: dict[str, str] = {}
    for line in status_lines:
        key, sep, value = line.partition(":")
        if sep:
            status[key.strip()] = value.strip()
    return {
        "status": status,
        "status_line_count": len(status_lines),
        "attr_current": "\n".join(attr_lines).strip(),
    }


def parse_fd_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw_line in text.splitlines():
        match = FD_TARGET_RE.match(raw_line.strip())
        if match:
            targets.append(match.group("target"))
    return targets


def count_android_markers(text: str) -> dict[str, int]:
    patterns = {
        "cnss_daemon_start": re.compile(r"starting service 'cnss-daemon'", re.I),
        "wlfw_start": re.compile(r"cnss-daemon\s+wlfw_start", re.I),
        "wlfw_service_request": re.compile(r"wlfw_service_request", re.I),
        "icnss_qmi_connected": re.compile(r"icnss_qmi:\s*QMI Server Connected", re.I),
        "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I),
        "wlan_fw_ready": re.compile(r"WLAN FW is ready", re.I),
    }
    return {name: sum(1 for line in text.splitlines() if pattern.search(line)) for name, pattern in patterns.items()}


def build_surface(args: argparse.Namespace) -> dict[str, Any]:
    v700 = load_json(args.v700_manifest)
    v703 = load_json(args.v703_manifest)
    helper_text = read_text(args.v700_helper)
    values = parse_key_values(helper_text)
    retry_pid = latest(values, "wifi_hal_composite_start.child.cnss_daemon_retry.pid")
    proc = parse_proc_blocks(helper_text, retry_pid)
    fd_targets = parse_fd_targets(helper_text)
    counts = ((v700.get("arm_v700") or {}).get("counts") or {})
    peripheral = ((v700.get("arm_v700") or {}).get("peripheral") or {})
    children = peripheral.get("children") or {}
    cnss_child = children.get("cnss_daemon_retry") or {}
    status = proc["status"]
    return {
        "v700": {
            "decision": v700.get("decision", ""),
            "pass": boolish(v700.get("pass")),
            "counts": counts,
            "initial_cnss_suppressed": boolish((v700.get("arm_v700") or {}).get("initial_cnss_suppressed")),
            "provider_query_exact": boolish((v700.get("arm_v700") or {}).get("query_exact_match")),
            "cnss_retry_started": boolish((v700.get("arm_v700") or {}).get("cnss_retry_started")),
        },
        "v703": {
            "decision": v703.get("decision", ""),
            "pass": boolish(v703.get("pass")),
        },
        "helper": {
            "retry_pid": retry_pid,
            "result": peripheral.get("result", ""),
            "reason": peripheral.get("reason", ""),
            "timed_out": latest(values, "wifi_companion_start.timed_out"),
            "stdout_has_no_interop_line": "cnss-daemon no interop issues ap currently" in helper_text,
            "cnss_child": cnss_child,
            "preexec_status": latest(values, "wifi_hal_composite_child.cnss_daemon_retry.preexec_status"),
            "selinux_exec": latest(values, "wifi_hal_composite_child.cnss_daemon_retry.selinux.exec"),
            "proc_status_captured": "1" if proc["status_line_count"] else cnss_child.get("proc_status_captured", ""),
            "proc_attr_current_captured": "1" if proc["attr_current"] else cnss_child.get("proc_attr_current_captured", ""),
            "fd_summary_captured": "1" if fd_targets else cnss_child.get("fd_summary_captured", ""),
        },
        "proc": {
            "state": status.get("State", ""),
            "threads": intish(status.get("Threads")),
            "uid": status.get("Uid", ""),
            "gid": status.get("Gid", ""),
            "groups": status.get("Groups", ""),
            "cap_eff": status.get("CapEff", ""),
            "cap_amb": status.get("CapAmb", ""),
            "vm_rss": status.get("VmRSS", ""),
            "voluntary_ctxt_switches": status.get("voluntary_ctxt_switches", ""),
            "nonvoluntary_ctxt_switches": status.get("nonvoluntary_ctxt_switches", ""),
            "attr_current": proc["attr_current"],
            "status_line_count": proc["status_line_count"],
        },
        "fd": {
            "count": len(fd_targets),
            "socket_count": sum(1 for target in fd_targets if target.startswith("socket:[")),
            "pipe_count": sum(1 for target in fd_targets if target.startswith("pipe:[")),
            "vndbinder_present": any(target.endswith("/dev/vndbinder") for target in fd_targets),
            "tty_present": any(target == "/dev/ttyGS0" for target in fd_targets),
            "sample": fd_targets[:24],
        },
        "android": {
            "dmesg_counts": count_android_markers(read_text(args.android_dmesg)),
        },
    }


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    counts = surface["v700"]["counts"]
    helper = surface["helper"]
    proc = surface["proc"]
    fd = surface["fd"]
    android = surface["android"]["dmesg_counts"]
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if (
                surface["v700"]["pass"]
                and surface["v700"]["decision"] == "v700-provider-first-cnss-gap-persists"
                and surface["v703"]["pass"]
                and surface["v703"]["decision"] == "v703-android-icnss-wlfw-delta-classified"
            ) else "blocked",
            "detail": {"v700": surface["v700"]["decision"], "v703": surface["v703"]["decision"]},
            "next_step": "refresh V700/V703 evidence before classifying retry stall",
        },
        {
            "name": "provider-first-cnss-started",
            "status": "pass" if (
                surface["v700"]["initial_cnss_suppressed"]
                and surface["v700"]["provider_query_exact"]
                and surface["v700"]["cnss_retry_started"]
            ) else "blocked",
            "detail": surface["v700"],
            "next_step": "do not classify stall until provider-first retry contract is intact",
        },
        {
            "name": "native-no-wlfw-without-binder-failure",
            "status": "finding" if (
                intish(counts.get("cnss_daemon_netlink")) > 0
                and intish(counts.get("cnss_binder_transaction_failed")) == 0
                and intish(counts.get("binder_transaction_failed")) == 0
                and intish(counts.get("wlfw_start")) == 0
                and intish(counts.get("qmi_server_connected")) == 0
            ) else "review",
            "detail": counts,
            "next_step": "do not repeat Binder-failure repair; capture live stall point",
        },
        {
            "name": "cnss-process-alive-sleeping-before-cleanup",
            "status": "finding" if (
                helper["retry_pid"]
                and "sleeping" in proc["state"]
                and proc["threads"] >= 1
                and helper["proc_status_captured"] == "1"
            ) else "review",
            "detail": {"helper": helper, "proc": proc},
            "next_step": "add wchan/syscall/task stack capture while retry process is alive",
        },
        {
            "name": "cnss-runtime-fds-present",
            "status": "finding" if fd["vndbinder_present"] and fd["socket_count"] >= 4 else "review",
            "detail": fd,
            "next_step": "map socket inodes to netlink/unix/QRTR tables in the next live helper",
        },
        {
            "name": "android-wlfw-reference-positive",
            "status": "finding" if (
                android["cnss_daemon_start"] > 0
                and android["wlfw_start"] > 0
                and android["icnss_qmi_connected"] > 0
                and android["bdf_bdwlan"] > 0
                and android["wlan_fw_ready"] > 0
            ) else "blocked",
            "detail": android,
            "next_step": "refresh Android reference if the expected WLFW path is missing",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v704-cnss-retry-stall-snapshot-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V704 host-only classifier over V700/V703 evidence",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v704-cnss-retry-stall-snapshot-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing evidence before planning another live change",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "native-no-wlfw-without-binder-failure",
        "cnss-process-alive-sleeping-before-cleanup",
        "cnss-runtime-fds-present",
        "android-wlfw-reference-positive",
    }
    if required <= findings:
        return (
            "v704-cnss-daemon-alive-pre-wlfw-stall-classified",
            True,
            "V700 provider-first retry starts cnss-daemon, keeps it alive/sleeping with vndbinder and sockets, has no Binder transaction failure, but never reaches WLFW/ICNSS-QMI/BDF/wlan0 while Android does.",
            "plan helper v120 live stall capture: proc wchan/syscall/task stacks and socket inode mapping for cnss-daemon retry before any HAL connect or credential use",
        )
    return (
        "v704-cnss-retry-stall-manual-review",
        False,
        "retry snapshot did not match known pre-WLFW stall pattern",
        "inspect V700 helper transcript manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    surface = build_surface(args)
    checks = [] if args.command == "plan" else build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v704",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v700_manifest": str(repo_path(args.v700_manifest)),
            "v703_manifest": str(repo_path(args.v703_manifest)),
            "v700_helper": str(repo_path(args.v700_helper)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
        },
        "surface": surface,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    surface_rows: list[list[str]] = []
    for section, values in manifest["surface"].items():
        if isinstance(values, dict):
            for key, value in sorted(values.items()):
                surface_rows.append([section, key, json.dumps(value, sort_keys=True)])
    return "\n".join([
        "# V704 CNSS Retry Stall Snapshot",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Surface",
        "",
        markdown_table(["section", "key", "value"], surface_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
