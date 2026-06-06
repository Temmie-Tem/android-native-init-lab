#!/usr/bin/env python3
"""V706 read-only cnss2 pd-notifier firing classifier.

This runner checks whether native init has kernel-level CNSS/ICNSS progression
after service-notifier 180 without starting daemons, writing sysfs, bringing
Wi-Fi up, scanning, connecting, running DHCP, or pinging externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v706-cnss2-pd-notifier-readonly")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
APPROVAL_PHRASES = {
    "approve v666 cnss2 pd-notifier firing check and modem subsys state read; no Wi-Fi HAL start, no scan/connect, no DHCP, no external ping",
    "approve v706 cnss2 pd-notifier firing check and modem subsys state read; no Wi-Fi HAL start, no scan/connect, no DHCP, no external ping",
}
ESSENTIAL_STEP_NAMES = {
    "status",
    "selftest",
    "firmware-class-path",
    "msm-subsys-devices",
    "class-subsys",
    "sys-class-net",
    "dmesg",
}

DMESG_MARKERS: dict[str, re.Pattern[str]] = {
    "service_notifier_180": re.compile(r"service-notifier:.*\b180 service\b|wlan_pd", re.I),
    "service_notifier_74": re.compile(r"service-notifier:.*\b74 service\b", re.I),
    "pd_notifier": re.compile(r"\bpd[_ -]?notifier\b|\bserver[_ -]?arrive\b", re.I),
    "icnss": re.compile(r"\bicnss\b", re.I),
    "cnss2": re.compile(r"\bcnss2\b", re.I),
    "qca6390": re.compile(r"\bqca6390\b", re.I),
    "power_on": re.compile(
        r"(icnss|cnss2|cnss|qca6390|wlan).*(power[_ -]?on|power on|powering)|"
        r"(power[_ -]?on|power on|powering).*(icnss|cnss2|cnss|qca6390|wlan)",
        re.I,
    ),
    "mhi_pcie": re.compile(
        r"(icnss|cnss2|cnss|qca6390|wlan).*(MHI|PCIe|pcie)|"
        r"(MHI|PCIe|pcie).*(icnss|cnss2|cnss|qca6390|wlan)",
        re.I,
    ),
    "icnss_qmi": re.compile(r"icnss[_ -]?qmi|QMI Server Connected", re.I),
    "wlfw_service": re.compile(r"\bWLFW\b|wlfw[_ -]?start|service\s+69", re.I),
    "bdf": re.compile(r"\bBDF\b|bdwlan|regdb", re.I),
    "fw_ready": re.compile(r"WLAN FW is ready|fw_ready", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
    "pil_failure": re.compile(r"\bPIL\b.*fail|firmware.*fail|authentication.*fail|load.*fail", re.I),
}
DMESG_TS_RE = re.compile(r"\[\s*(?P<ts>\d+(?:\.\d+)?)\]")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


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
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--approval", default="")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.approval.strip() in APPROVAL_PHRASES


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


def is_busy_step(step: dict[str, Any]) -> bool:
    text = str(step.get("payload") or step.get("text") or step.get("error") or "")
    return step.get("status") == "busy" or step.get("rc") == -16 or "[busy]" in text


def hide_menu(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    item = run_step(args, store, "hide-menu", ["hide"], 8.0)
    time.sleep(0.4)
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def cat_step(name: str, path: str) -> tuple[str, list[str]]:
    return name, ["cat", path]


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    steps = [hide_menu(args, store)]
    commands: list[tuple[str, list[str], float]] = [
        ("status", ["status"], 20.0),
        ("selftest", ["selftest"], 25.0),
        ("firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0),
        ("msm-subsys-devices", ["ls", "/sys/bus/msm_subsys/devices"], 10.0),
        ("class-subsys", ["ls", "/sys/class/subsys"], 10.0),
        ("platform-driver-icnss", ["ls", "/sys/bus/platform/drivers/icnss"], 10.0),
        ("platform-driver-cnss2", ["ls", "/sys/bus/platform/drivers/cnss2"], 10.0),
        ("platform-device-icnss", ["ls", "/sys/bus/platform/devices/18800000.qcom,icnss"], 10.0),
        ("platform-device-qca6390", ["ls", "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390"], 10.0),
        ("sys-class-net", ["ls", "/sys/class/net"], 10.0),
        ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
        ("proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0),
        ("dmesg", ["run", args.toybox, "dmesg"], args.timeout),
    ]
    sysfs_files = [
        cat_step("mss-subsys0-name", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/name"),
        cat_step("mss-subsys0-state", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"),
        cat_step("mss-subsys0-restart-level", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/restart_level"),
        cat_step("mss-subsys0-firmware-name", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/firmware_name"),
        cat_step("mss-subsys0-crash-count", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/crash_count"),
        cat_step("mdm3-subsys9-name", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/name"),
        cat_step("mdm3-subsys9-state", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"),
        cat_step("mdm3-subsys9-restart-level", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/restart_level"),
        cat_step("mdm3-subsys9-firmware-name", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/firmware_name"),
        cat_step("mdm3-subsys9-crash-count", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/crash_count"),
        cat_step("class-subsys-modem-name", "/sys/class/subsys/subsys_modem/name"),
        cat_step("class-subsys-modem-state", "/sys/class/subsys/subsys_modem/state"),
        cat_step("class-subsys-esoc0-name", "/sys/class/subsys/subsys_esoc0/name"),
        cat_step("class-subsys-esoc0-state", "/sys/class/subsys/subsys_esoc0/state"),
        cat_step("icnss-uevent", "/sys/bus/platform/devices/18800000.qcom,icnss/uevent"),
        cat_step("icnss-runtime-status", "/sys/bus/platform/devices/18800000.qcom,icnss/power/runtime_status"),
        cat_step("qca6390-uevent", "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/uevent"),
        cat_step("qca6390-runtime-status", "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power/runtime_status"),
    ]
    commands.extend((name, command, 10.0) for name, command in sysfs_files)
    steps.extend(run_step(args, store, name, command, timeout) for name, command, timeout in commands)
    return steps


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def dmesg_ts(line: str) -> float | None:
    match = DMESG_TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in DMESG_MARKERS}
    focus_lines: list[str] = []
    for index, raw_line in enumerate(text.splitlines()):
        line = clean_line(raw_line)
        if not line:
            continue
        matched = False
        for name, pattern in DMESG_MARKERS.items():
            if pattern.search(line):
                events[name].append({"index": index, "ts": dmesg_ts(line), "line": line[:360]})
                matched = True
        if matched:
            focus_lines.append(line[:360])
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "last_ts": {name: rows[-1]["ts"] for name, rows in events.items() if rows and rows[-1]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "focus_tail": focus_lines[-160:],
    }


def read_value(steps: list[dict[str, Any]], name: str) -> str:
    text = step_payload(steps, name).strip()
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""


def captured_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok"))
    return False


def build_surface(steps: list[dict[str, Any]]) -> dict[str, Any]:
    dmesg = parse_dmesg(step_payload(steps, "dmesg"))
    busy_steps = [str(step.get("name")) for step in steps if is_busy_step(step)]
    failed_steps = [
        str(step.get("name"))
        for step in steps
        if step.get("name") in ESSENTIAL_STEP_NAMES and not step.get("ok") and not is_busy_step(step)
    ]
    return {
        "busy_steps": busy_steps,
        "failed_steps": failed_steps,
        "firmware_class_path": read_value(steps, "firmware-class-path"),
        "mss_state": read_value(steps, "mss-subsys0-state"),
        "mdm3_state": read_value(steps, "mdm3-subsys9-state"),
        "class_modem_state": read_value(steps, "class-subsys-modem-state"),
        "class_esoc0_state": read_value(steps, "class-subsys-esoc0-state"),
        "icnss_driver_dir_ok": captured_ok(steps, "platform-driver-icnss"),
        "cnss2_driver_dir_ok": captured_ok(steps, "platform-driver-cnss2"),
        "icnss_device_ok": captured_ok(steps, "platform-device-icnss"),
        "qca6390_device_ok": captured_ok(steps, "platform-device-qca6390"),
        "qca6390_runtime_status": read_value(steps, "qca6390-runtime-status"),
        "wlan0_visible": "wlan0" in step_payload(steps, "sys-class-net"),
        "qrtr_service69_visible": bool(re.search(r"\b69\b", step_payload(steps, "proc-net-qrtr"))),
        "dmesg": dmesg,
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 surface: dict[str, Any] | None,
                 steps: list[dict[str, Any]]) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "scope-read-only",
        "pass",
        "blocker",
        "runner only reads cmdv1 status/selftest, sysfs/procfs, QRTR table, and dmesg",
        [],
        "keep Wi-Fi HAL/scan/connect blocked until wlan0 exists",
    )
    if args.command == "run":
        add_check(
            checks,
            "approval",
            "pass" if approved(args) else "blocked",
            "blocker",
            "exact V666/V706 read-only approval phrase is required for live collection",
            [],
            "rerun with approved phrase",
        )
    if surface is None:
        return checks

    busy_steps = list(surface.get("busy_steps") or [])
    failed_steps = list(surface.get("failed_steps") or [])
    add_check(
        checks,
        "capture-not-busy",
        "pass" if not busy_steps else "blocked",
        "blocker",
        f"busy_steps={','.join(busy_steps[:12])}" if busy_steps else "no busy steps",
        [],
        "hide menu and rerun before interpreting CNSS2 state",
    )
    add_check(
        checks,
        "capture-essential-steps-ok",
        "pass" if not failed_steps and captured_ok(steps, "dmesg") else "blocked",
        "blocker",
        f"failed_steps={','.join(failed_steps[:12])}; dmesg_ok={captured_ok(steps, 'dmesg')}",
        [],
        "fix bridge/device read-only capture before interpreting CNSS2 state",
    )

    dmesg_counts = (surface.get("dmesg") or {}).get("counts") or {}
    service180 = int(dmesg_counts.get("service_notifier_180", 0))
    pd_notifier = int(dmesg_counts.get("pd_notifier", 0))
    power_on = int(dmesg_counts.get("power_on", 0))
    wlfw = int(dmesg_counts.get("wlfw_service", 0))
    wlan0 = bool(surface.get("wlan0_visible"))
    add_check(
        checks,
        "service180-present",
        "pass" if service180 > 0 else "warn",
        "info",
        f"service-notifier 180/WLAN-PD marker count={service180}",
        [],
        "if absent, restore lower modem/WLAN-PD path before CNSS retry",
    )
    add_check(
        checks,
        "kernel-pd-notifier-visible",
        "pass" if pd_notifier > 0 else "warn",
        "info",
        f"pd_notifier/server_arrive-like CNSS marker count={pd_notifier}",
        [],
        "if absent, focus on kernel-level notifier registration rather than cnss-daemon Binder",
    )
    add_check(
        checks,
        "qca6390-power-progress",
        "pass" if power_on > 0 else "warn",
        "info",
        f"QCA6390/CNSS power-on-like marker count={power_on}",
        [],
        "if absent after service180, inspect cnss2/icnss notifier-to-power edge",
    )
    add_check(
        checks,
        "wlfw-or-wlan0-progress",
        "pass" if wlfw > 0 or wlan0 else "warn",
        "info",
        f"wlfw_count={wlfw}; wlan0_visible={wlan0}",
        [],
        "do not start HAL connect path until WLFW/wlan0 progresses",
    )
    add_check(
        checks,
        "subsys-state-read",
        "pass" if any(surface.get(key) for key in ("mss_state", "mdm3_state", "class_modem_state")) else "warn",
        "info",
        f"mss={surface.get('mss_state')}; mdm3={surface.get('mdm3_state')}; class_modem={surface.get('class_modem_state')}",
        [],
        "if modem is offline, plan a separate explicit PIL trigger proof; do not write state in V706",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace,
           checks: list[Check],
           surface: dict[str, Any] | None,
           steps: list[dict[str, Any]]) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v706-cnss2-pd-notifier-readonly-plan-ready",
            True,
            "plan-only; no device command executed",
            "run preflight or approved read-only live collection",
            False,
        )
    if args.command == "preflight":
        return (
            "v706-cnss2-pd-notifier-readonly-preflight-ready",
            True,
            "preflight-only; live run needs exact approval phrase",
            "run V706 read-only live collection",
            False,
        )
    blockers = blocking_checks(checks)
    if blockers:
        if blockers == ["approval"]:
            return (
                "v706-cnss2-pd-notifier-readonly-approval-required",
                True,
                "blocked by approval; no live command executed",
                "rerun with exact V666/V706 read-only approval phrase",
                False,
            )
        return (
            "v706-cnss2-pd-notifier-readonly-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix read-only capture gate before interpreting CNSS2 state",
            bool(surface),
        )
    if surface is None:
        return (
            "v706-cnss2-pd-notifier-readonly-missing-surface",
            False,
            "live surface was not collected",
            "inspect runner failure",
            False,
        )

    busy_steps = list(surface.get("busy_steps") or [])
    failed_steps = list(surface.get("failed_steps") or [])
    if busy_steps:
        return (
            "v706-readonly-capture-busy",
            False,
            "read-only capture was blocked by active menu: " + ", ".join(busy_steps[:12]),
            "hide menu and rerun before interpreting CNSS2 state",
            True,
        )
    if failed_steps or not captured_ok(steps, "dmesg"):
        return (
            "v706-readonly-capture-incomplete",
            False,
            f"failed_steps={failed_steps[:12]}; dmesg_ok={captured_ok(steps, 'dmesg')}",
            "fix bridge/device read-only capture before interpreting CNSS2 state",
            True,
        )

    counts = (surface.get("dmesg") or {}).get("counts") or {}
    service180 = int(counts.get("service_notifier_180", 0))
    pd_notifier = int(counts.get("pd_notifier", 0))
    power_on = int(counts.get("power_on", 0))
    wlfw = int(counts.get("wlfw_service", 0))
    wlan0 = bool(surface.get("wlan0_visible"))
    if wlfw > 0 or wlan0:
        return (
            "v706-wlfw-or-wlan0-progressed",
            True,
            f"WLFW/wlan0 progressed; counts={counts}; wlan0={wlan0}",
            "classify WLAN netdev state before any scan/connect",
            True,
        )
    if service180 > 0 and pd_notifier == 0 and power_on == 0:
        return (
            "v706-service180-without-kernel-cnss2-firing",
            True,
            f"service180={service180} but pd_notifier={pd_notifier}, power_on={power_on}, wlfw={wlfw}",
            "inspect cnss2/icnss notifier registration and Android kernel logs",
            True,
        )
    if service180 > 0 and power_on == 0:
        return (
            "v706-service180-without-qca6390-power",
            True,
            f"service180={service180}; pd_notifier={pd_notifier}; power_on={power_on}; wlfw={wlfw}",
            "focus next proof on notifier-to-QCA6390 power transition",
            True,
        )
    if service180 == 0:
        return (
            "v706-service180-absent-current-boot",
            True,
            f"counts={counts}; mss={surface.get('mss_state')}; mdm3={surface.get('mdm3_state')}",
            "restore lower modem/WLAN-PD evidence before CNSS retry",
            True,
        )
    return (
        "v706-pre-wlfw-kernel-gap-classified",
        True,
        f"counts={counts}; wlan0={wlan0}; qca6390_runtime={surface.get('qca6390_runtime_status')}",
        "use V705 helper v120 stall capture or a targeted icnss notifier probe next",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    surface = manifest.get("surface") or {}
    dmesg = surface.get("dmesg") or {}
    counts = dmesg.get("counts") or {}
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in checks
    ]
    count_rows = [[name, str(value)] for name, value in sorted(counts.items())]
    sysfs_rows = [
        ["busy_steps", ", ".join(surface.get("busy_steps") or [])],
        ["failed_steps", ", ".join(surface.get("failed_steps") or [])],
        ["firmware_class.path", surface.get("firmware_class_path", "")],
        ["mss_state", surface.get("mss_state", "")],
        ["mdm3_state", surface.get("mdm3_state", "")],
        ["class_modem_state", surface.get("class_modem_state", "")],
        ["class_esoc0_state", surface.get("class_esoc0_state", "")],
        ["icnss_driver_dir_ok", str(surface.get("icnss_driver_dir_ok", ""))],
        ["cnss2_driver_dir_ok", str(surface.get("cnss2_driver_dir_ok", ""))],
        ["icnss_device_ok", str(surface.get("icnss_device_ok", ""))],
        ["qca6390_device_ok", str(surface.get("qca6390_device_ok", ""))],
        ["qca6390_runtime_status", surface.get("qca6390_runtime_status", "")],
        ["wlan0_visible", str(surface.get("wlan0_visible", ""))],
        ["qrtr_service69_visible", str(surface.get("qrtr_service69_visible", ""))],
    ]
    lines = [
        "# V706 CNSS2 PD-Notifier Read-Only Summary",
        "",
        f"- decision: `{manifest.get('decision')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason')}",
        f"- next: {manifest.get('next')}",
        f"- live_executed: `{manifest.get('live_executed')}`",
        f"- evidence: `{manifest.get('evidence_dir')}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows) if check_rows else "- none",
        "",
        "## Sysfs Surface",
        "",
        markdown_table(["item", "value"], sysfs_rows),
        "",
        "## Dmesg Marker Counts",
        "",
        markdown_table(["marker", "count"], count_rows) if count_rows else "- not collected",
        "",
        "## Dmesg Focus Tail",
        "",
    ]
    focus_tail = dmesg.get("focus_tail") or []
    lines.extend(f"- `{line}`" for line in focus_tail[-40:])
    if not focus_tail:
        lines.append("- not collected")
    lines.append("")
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    surface: dict[str, Any] | None = None
    live_executed = False
    if args.command == "run" and approved(args):
        steps = collect_steps(args, store)
        surface = build_surface(steps)
        live_executed = True
    checks = build_checks(args, surface, steps)
    decision, pass_ok, reason, next_step, live_executed = decide(args, checks, surface, steps)
    return {
        "cycle": "v706",
        "created_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next": next_step,
        "live_executed": live_executed,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_linkup_executed": False,
        "dhcp_or_external_ping_executed": False,
        "evidence_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "surface": surface or {},
        "steps": [{key: value for key, value in step.items() if key != "payload"} for step in steps],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"dhcp_or_external_ping_executed: {manifest['dhcp_or_external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
