#!/usr/bin/env python3
"""V1347 Android read-only earliest SDX50M response recapture.

This collector runs only while Android ADB is available. It captures Android
properties, dmesg monotonic timestamps, process fd snapshots, and interrupt
state to classify the ordering between `__subsystem_get(esoc0)`, GPIO142,
PCIe RC1/L0, MHI, `ks`, WLFW/BDF, and `wlan0`.

It is read-only: no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes,
external ping, sysfs writes, eSoC ioctl/notify, PMIC/GPIO/GDSC mutation, flash,
or partition write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from native_wifi_android_lower_surface_recapture_v611 import (
    Capture,
    adb_devices,
    capture_shell,
    selected_device_available,
)
from native_wifi_qmi_publication_precondition_v610 import parse_key_values


DEFAULT_OUT_DIR = Path("tmp/wifi/v1347-android-earliest-response-recapture")
DEFAULT_TIMEOUT = 45.0

PROP_KEYS = [
    "sys.boot_completed",
    "init.svc.vendor.per_mgr",
    "init.svc.vendor.per_proxy",
    "init.svc.vendor.per_proxy_helper",
    "init.svc.vendor.mdm_launcher",
    "init.svc.vendor.mdm_helper",
    "init.svc.vendor.qrtr-ns",
    "init.svc.vendor.rmt_storage",
    "init.svc.vendor.tftp_server",
    "init.svc.vendor.pd_mapper",
    "init.svc.cnss_diag",
    "init.svc.cnss-daemon",
    "ro.boottime.vendor.per_mgr",
    "ro.boottime.vendor.per_proxy",
    "ro.boottime.vendor.per_proxy_helper",
    "ro.boottime.vendor.mdm_launcher",
    "ro.boottime.vendor.mdm_helper",
    "ro.boottime.vendor.qrtr-ns",
    "ro.boottime.vendor.rmt_storage",
    "ro.boottime.vendor.tftp_server",
    "ro.boottime.vendor.pd_mapper",
    "ro.boottime.cnss_diag",
    "ro.boottime.cnss-daemon",
]

DMESG_PATTERN = (
    "subsys-restart|__subsystem_get|subsys_esoc0|subsys_modem|"
    "mdm_subsys_powerup|mdm_do_first_power_on|esoc0|SDX50M|ap2mdm|mdm2ap|errfatal|err_fatal|"
    "GPIO 135|GPIO135|GPIO 142|GPIO142|msm_pcie|PCIe|RC1|LTSSM|"
    "MHI|mhi|mhi_0305_01\\.01\\.00_pipe_10|\\bks\\b|icnss|cnss|wlfw|"
    "BDF file|regdb\\.bin|bdwlan\\.bin|FW ready|WLAN FW is ready|wlan0"
)

PROCESS_FD_COMMAND = r"""
echo A90_V1347_PROCESS_FDS_BEGIN
for d in /proc/[0-9]*; do
  pid=${d##*/}
  comm=$(cat "$d/comm" 2>/dev/null || true)
  cmd=$(xargs -0 < "$d/cmdline" 2>/dev/null || true)
  wanted=0
  case "$comm" in
    pm-service|per_proxy|per_proxy_helper|mdm_helper|ks|cnss-daemon|cnss_diag) wanted=1 ;;
  esac
  case "$cmd" in
    */pm-service*|*/per_proxy*|*/per_proxy_helper*|*/mdm_helper*|*" ks "*|*/ks*|*cnss-daemon*|*cnss_diag*) wanted=1 ;;
  esac
  case "$cmd" in
    *A90_V1347_PROCESS_FDS*) wanted=0 ;;
  esac
  if [ "$wanted" = "1" ]; then
      echo "### pid=$pid comm=$comm cmd=$cmd"
      echo "wchan=$(cat "$d/wchan" 2>/dev/null || true)"
      ls -l "$d/fd" 2>/dev/null | grep -E 'subsys_esoc0|subsys_modem|esoc-0|mhi_0305_01\.01\.00_pipe_10' || true
  fi
done
echo A90_V1347_PROCESS_FDS_END
"""

INTERRUPTS_COMMAND = (
    "echo A90_V1347_INTERRUPTS_BEGIN; "
    "cat /proc/interrupts 2>&1 | grep -Ei 'mdm|esoc|gpio|status|err|fatal|pcie|mhi|142|135' || true; "
    "echo A90_V1347_INTERRUPTS_END"
)

FORBIDDEN_ACTIONS = [
    "Wi-Fi HAL start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP/routes/external ping",
    "sysfs write",
    "eSoC ioctl/notify or BOOT_DONE",
    "PMIC/GPIO/GDSC mutation",
    "flash or partition write",
]

TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("subsys_get_esoc0", re.compile(r"__subsystem_get:.*\besoc0\b|/dev/subsys_esoc0|subsys_esoc0", re.I)),
    ("subsys_get_modem", re.compile(r"__subsystem_get:.*\bmodem\b|/dev/subsys_modem|subsys_modem", re.I)),
    ("mdm_subsys_powerup", re.compile(r"mdm_subsys_powerup", re.I)),
    ("sdx50m", re.compile(r"SDX50M|ext-sdx50m", re.I)),
    ("ap2mdm_gpio135", re.compile(r"ap2mdm|GPIO\s*135|GPIO135", re.I)),
    ("mdm2ap_gpio142", re.compile(r"mdm2ap|GPIO\s*142|GPIO142", re.I)),
    ("mdm_errfatal", re.compile(r"errfatal|err_fatal|fatal_irq", re.I)),
    ("pcie_rc1", re.compile(r"PCIe.*RC1|RC1.*PCIe|msm_pcie|Assert the reset of endpoint of RC1|Current GEN[0-9].*lanes", re.I)),
    ("pcie_l0", re.compile(r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes", re.I)),
    ("mhi_pipe", re.compile(r"mhi_0305_01\.01\.00_pipe_10", re.I)),
    ("mhi", re.compile(r"\bmhi\b|MHI", re.I)),
    ("ks", re.compile(r"\bks\b|/vendor/bin/ks", re.I)),
    ("icnss_qmi", re.compile(r"icnss_qmi|QMI Server Connected", re.I)),
    ("wlfw", re.compile(r"\bwlfw\b|WLFW", re.I)),
    ("bdf", re.compile(r"BDF file|regdb\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"FW ready|WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
)

ORDER_MARKERS = [
    "subsys_get_modem",
    "subsys_get_esoc0",
    "mdm_subsys_powerup",
    "ap2mdm_gpio135",
    "mdm2ap_gpio142",
    "mdm_errfatal",
    "pcie_rc1",
    "pcie_l0",
    "mhi",
    "mhi_pipe",
    "ks",
    "icnss_qmi",
    "wlfw",
    "bdf",
    "wlan_fw_ready",
    "wlan0",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--no-su", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def prop_command() -> str:
    props = " ".join(PROP_KEYS)
    return "; ".join([
        "echo A90_V1347_PROPS_BEGIN",
        f"for p in {props}; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        "echo A90_V1347_PROPS_END",
    ])


def dmesg_filtered_command() -> str:
    return f"dmesg 2>&1 | grep -Ei {DMESG_PATTERN!r} || true"


def dmesg_early_filtered_command() -> str:
    return f"dmesg 2>&1 | head -n 2400 | grep -Ei {DMESG_PATTERN!r} || true"


def dmesg_unfiltered_command() -> str:
    return "dmesg 2>&1 | tail -n 2600 || true"


def pcie_mhi_surface_command() -> str:
    return r"""
echo A90_V1347_PCIE_MHI_SURFACE_BEGIN
echo "### pci devices"
find /sys/bus/pci/devices -maxdepth 2 -type f \( -name vendor -o -name device -o -name class -o -name current_link_speed -o -name current_link_width -o -name enable -o -name uevent \) -print 2>/dev/null | sort | while read f; do echo "### $f"; cat "$f" 2>&1 || true; done
echo "### mhi devices"
find /sys/bus/mhi/devices -maxdepth 3 -print 2>&1 || true
echo "### mhi devnodes"
ls -l /dev/mhi* /dev/*mhi* 2>/dev/null || true
echo "### wlan netdev"
ls -l /sys/class/net/wlan0 2>/dev/null || true
cat /sys/class/net/wlan0/operstate 2>/dev/null || true
echo A90_V1347_PCIE_MHI_SURFACE_END
"""


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    return [
        capture_shell(args, store, "v1347-props", prop_command(), 15.0),
        capture_shell(args, store, "v1347-dmesg-filtered", dmesg_filtered_command(), 35.0),
        capture_shell(args, store, "v1347-dmesg-early-filtered", dmesg_early_filtered_command(), 35.0),
        capture_shell(args, store, "v1347-dmesg-unfiltered-tail", dmesg_unfiltered_command(), 35.0),
        capture_shell(args, store, "v1347-process-fds", PROCESS_FD_COMMAND, 25.0),
        capture_shell(args, store, "v1347-interrupts", INTERRUPTS_COMMAND, 15.0),
        capture_shell(args, store, "v1347-pcie-mhi-surface", pcie_mhi_surface_command(), 25.0),
    ]


def capture_text(captures: list[Capture], *names: str) -> str:
    wanted = set(names)
    return "\n".join(capture.text for capture in captures if capture.name in wanted)


def parse_events(text: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = TS_RE.match(line)
        timestamp = float(match.group("ts")) if match else None
        for marker, pattern in MARKERS:
            if pattern.search(line):
                events.append(Event(marker, timestamp, line))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    found: dict[str, Event] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def count_by_marker(events: list[Event]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def ns_to_ms(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    try:
        return round(int(raw_value) / 1_000_000.0, 3)
    except ValueError:
        return None


def event_time(first: dict[str, Event], marker: str) -> float | None:
    event = first.get(marker)
    return event.timestamp if event else None


def process_flags(text: str) -> dict[str, Any]:
    return {
        "pm_service_seen": "pm-service" in text,
        "per_proxy_seen": "per_proxy" in text,
        "per_proxy_helper_seen": "per_proxy_helper" in text,
        "mdm_helper_seen": "mdm_helper" in text,
        "ks_seen": re.search(r"comm=ks\b|/vendor/bin/ks\b|\bks -m\b", text) is not None,
        "fd_subsys_esoc0_seen": "/dev/subsys_esoc0" in text,
        "fd_subsys_modem_seen": "/dev/subsys_modem" in text,
        "fd_esoc0_seen": "/dev/esoc-0" in text,
        "fd_mhi_pipe_seen": "/dev/mhi_0305_01.01.00_pipe_10" in text,
    }


def summarize(captures: list[Capture], store: EvidenceStore) -> dict[str, Any]:
    props = parse_key_values(capture_text(captures, "v1347-props"))
    dmesg_text = capture_text(captures, "v1347-dmesg-filtered", "v1347-dmesg-early-filtered", "v1347-dmesg-unfiltered-tail")
    process_text = capture_text(captures, "v1347-process-fds")
    interrupts_text = capture_text(captures, "v1347-interrupts")
    surface_text = capture_text(captures, "v1347-pcie-mhi-surface")
    events = parse_events(dmesg_text)
    first = first_by_marker(events)
    counts = count_by_marker(events)
    response_markers = ("mdm2ap_gpio142", "pcie_rc1", "pcie_l0", "mhi", "mhi_pipe", "wlfw", "bdf", "wlan_fw_ready", "wlan0")
    response_present = any(counts.get(marker, 0) > 0 for marker in response_markers)
    pcie_l0_time = event_time(first, "pcie_l0")
    subsys_esoc0_time = event_time(first, "subsys_get_esoc0")
    pcie_rc1_time = event_time(first, "pcie_rc1")
    gpio142_time = event_time(first, "mdm2ap_gpio142")
    normalized_props = "\n".join(f"{key}={props.get(key, '')}" for key in PROP_KEYS).rstrip() + "\n"
    store.write_text("android-v1347-props-normalized.txt", normalized_props)
    return {
        "boot_completed": props.get("sys.boot_completed") == "1",
        "all_commands_ok": all(capture.ok for capture in captures),
        "props": {key: props.get(key, "") for key in PROP_KEYS},
        "boottime_ms": {
            key: ns_to_ms(props.get(key))
            for key in PROP_KEYS
            if key.startswith("ro.boottime.")
        },
        "event_count": len(events),
        "counts": {marker: counts.get(marker, 0) for marker in ORDER_MARKERS},
        "first": {
            marker: asdict(event)
            for marker, event in first.items()
            if marker in ORDER_MARKERS
        },
        "first_times": {
            "subsys_get_esoc0": subsys_esoc0_time,
            "pcie_rc1": pcie_rc1_time,
            "pcie_l0": pcie_l0_time,
            "mdm2ap_gpio142": gpio142_time,
            "mhi": event_time(first, "mhi"),
            "mhi_pipe": event_time(first, "mhi_pipe"),
            "ks": event_time(first, "ks"),
            "wlfw": event_time(first, "wlfw"),
            "bdf": event_time(first, "bdf"),
            "wlan0": event_time(first, "wlan0"),
        },
        "response_present": response_present,
        "process_flags": process_flags(process_text),
        "surface_flags": {
            "pci_devices_seen": "/sys/bus/pci/devices/" in surface_text,
            "mhi_devices_seen": "/sys/bus/mhi/devices/" in surface_text,
            "mhi_devnode_seen": "/dev/mhi" in surface_text,
            "wlan0_sysfs_seen": "/sys/class/net/wlan0" in surface_text,
        },
        "interrupts_has_mdm2ap_or_gpio142": re.search(r"mdm2ap|GPIO\s*142|GPIO142|142", interrupts_text, re.I) is not None,
        "clock_source_note": "dmesg timestamps are monotonic seconds; ro.boottime values are labelled separately and not used for kernel ordering decisions",
    }


def decide(args: argparse.Namespace,
           devices: dict[str, Any],
           captures: list[Capture],
           summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1347-android-earliest-response-plan-ready",
            True,
            "plan-only; no adb command executed",
            "boot Android through the handoff wrapper or run preflight on an already-booted Android device",
        )
    if devices["device_count"] == 0:
        return (
            "v1347-android-adb-unavailable",
            False,
            "no Android ADB device is currently visible",
            "run V1347 Android handoff from native/recovery state or verify adb",
        )
    if not selected_device_available(args, devices):
        return (
            "v1347-android-adb-selection-needed",
            False,
            f"device_count={devices['device_count']}",
            "rerun with --serial",
        )
    if args.command == "preflight":
        return (
            "v1347-android-earliest-response-preflight-ready",
            True,
            "one Android ADB device is visible",
            "run V1347 Android read-only timing recapture",
        )
    if not captures:
        return "v1347-capture-missing", False, "run command produced no captures", "inspect adb or collector failure"
    if not summary.get("boot_completed"):
        return (
            "v1347-android-not-boot-complete",
            False,
            "Android ADB is visible but sys.boot_completed=1 was not captured",
            "wait for boot-complete and rerun V1347",
        )
    if not summary.get("response_present"):
        return (
            "v1347-android-response-chain-missing",
            False,
            "Android capture lacks GPIO142/PCIe/MHI/WLFW/wlan0 response markers",
            "recapture earlier dmesg or verify Android Wi-Fi lower stack state",
        )

    times = summary.get("first_times") or {}
    subsys_time = times.get("subsys_get_esoc0")
    pcie_time = times.get("pcie_l0") or times.get("pcie_rc1")
    wlfw_time = times.get("wlfw")
    bdf_time = times.get("bdf")
    wlan0_time = times.get("wlan0")
    gpio142_time = times.get("mdm2ap_gpio142")
    mhi_time = times.get("mhi_pipe") or times.get("mhi")
    process = summary.get("process_flags") or {}
    surface = summary.get("surface_flags") or {}
    pcie_or_mhi_detail = (
        pcie_time is not None
        or mhi_time is not None
        or bool(process.get("fd_mhi_pipe_seen"))
        or bool(surface.get("mhi_devices_seen"))
    )
    if pcie_or_mhi_detail and (wlfw_time is not None or bdf_time is not None or wlan0_time is not None):
        return (
            "v1347-android-earliest-response-order-captured",
            True,
            f"captured response order gpio142={gpio142_time}s pcie={pcie_time}s mhi={mhi_time}s wlfw={wlfw_time}s bdf={bdf_time}s wlan0={wlan0_time}s subsys_esoc0={subsys_time}s",
            "classify exact Android-only prerequisite ordering against native V1345 before any lower mutation",
        )
    if subsys_time is not None and wlfw_time is not None and wlfw_time < subsys_time:
        return (
            "v1347-android-wlfw-before-subsys-esoc0",
            True,
            f"first WLFW userspace marker {wlfw_time}s is before first subsys_esoc0 marker {subsys_time}s; BDF={bdf_time}s wlan0={wlan0_time}s",
            "classify earlier Android cnss-daemon/per_mgr/provider ordering before native lower mutation",
        )
    if subsys_time is not None and pcie_time is not None:
        if pcie_time > subsys_time:
            return (
                "v1347-android-pcie-after-subsys-esoc0",
                True,
                f"first PCIe response timestamp {pcie_time}s is after first subsys_esoc0 marker {subsys_time}s",
                "design native gate around reproducing the pre-subsys_esoc0 Android provider contract",
            )
        return (
            "v1347-android-pcie-before-captured-subsys-esoc0",
            True,
            f"first PCIe response timestamp {pcie_time}s is before first captured subsys_esoc0 marker {subsys_time}s",
            "classify earlier Android init/provider trigger before native lower mutation",
        )
    if subsys_time is None:
        return (
            "v1347-android-esoc0-marker-missing-but-response-present",
            True,
            "Android response chain is present but no dmesg subsys_esoc0 marker was captured",
            "classify earlier Android provider/fd evidence and consider broader read-only dmesg capture",
        )
    return (
        "v1347-android-clock-source-incomparable",
        True,
        "Android response chain is present but kernel ordering markers are incomplete",
        "do not compare ro.boottime to dmesg; recapture with broader dmesg markers if needed",
    )


def capture_rows(captures: list[Capture]) -> list[list[str]]:
    return [[item.name, item.status, str(item.rc), f"{item.duration_sec:.3f}s", item.file] for item in captures]


def marker_rows(summary: dict[str, Any]) -> list[list[str]]:
    counts = summary.get("counts") or {}
    first = summary.get("first") or {}
    rows: list[list[str]] = []
    for marker in ORDER_MARKERS:
        payload = first.get(marker) or {}
        rows.append([marker, str(counts.get(marker, 0)), str(payload.get("timestamp", "")), str(payload.get("line", ""))[:140]])
    return rows


def prop_rows(summary: dict[str, Any]) -> list[list[str]]:
    props = summary.get("props") or {}
    return [[key, props.get(key, "")] for key in PROP_KEYS]


def render_summary(manifest: dict[str, Any]) -> str:
    summary = manifest.get("android_summary") or {}
    process = summary.get("process_flags") or {}
    surface = summary.get("surface_flags") or {}
    process_rows = [[key, str(value)] for key, value in process.items()]
    surface_rows = [[key, str(value)] for key, value in surface.items()]
    return "\n".join([
        "# V1347 Android Earliest Response Recapture",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Marker Order",
        "",
        markdown_table(["marker", "count", "first_s", "line"], marker_rows(summary) if summary else [["-", "-", "-", "-"]]),
        "",
        "## Process/Fd Flags",
        "",
        markdown_table(["flag", "value"], process_rows if process_rows else [["-", "-"]]),
        "",
        "## PCIe/MHI Surface Flags",
        "",
        markdown_table(["flag", "value"], surface_rows if surface_rows else [["-", "-"]]),
        "",
        "## Properties",
        "",
        markdown_table(["key", "value"], prop_rows(summary) if summary else [["-", "-"]]),
        "",
        "## Captures",
        "",
        markdown_table(["capture", "status", "rc", "duration", "file"], capture_rows([Capture(**item) for item in manifest.get("captures", [])]) if manifest.get("captures") else [["none", "-", "-", "-", "-"]]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    devices = adb_devices(args) if args.command != "plan" else {
        "rc": None,
        "text": "",
        "error": "",
        "duration_sec": 0.0,
        "devices": [],
        "device_count": 0,
    }
    captures = collect(args, store) if args.command == "run" and selected_device_available(args, devices) else []
    summary = summarize(captures, store) if captures else {}
    decision, pass_ok, reason, next_step = decide(args, devices, captures, summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "android_summary": summary,
        "captures": [asdict(capture) for capture in captures],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": args.command in {"preflight", "run"},
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
