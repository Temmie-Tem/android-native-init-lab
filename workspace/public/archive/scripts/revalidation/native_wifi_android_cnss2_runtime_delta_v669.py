#!/usr/bin/env python3
"""V669 Android/native cnss2 runtime delta classifier.

This host-only classifier consumes existing Android and native evidence. It
does not contact the device, write sysfs, start daemons, start Wi-Fi HAL, scan,
connect, run DHCP, change routes, use credentials, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v669-android-cnss2-runtime-delta")
DEFAULT_V668_MANIFEST = Path("tmp/wifi/v668-cnss2-focused-capture-live/manifest.json")
DEFAULT_V668_DMESG = Path("tmp/wifi/v668-cnss2-focused-capture-live/native/dmesg-delta.txt")
DEFAULT_V668_HELPER_TEXT = Path("tmp/wifi/v668-cnss2-focused-capture-live/native/companion-start-only-with-holder.txt")
DEFAULT_ANDROID_DMESG = Path(
    "tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/"
    "v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt"
)
DEFAULT_ANDROID_SYSFS = Path("tmp/wifi/v204-android-baseline/root-icnss-sysfs-files.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("wifi_hal_ext_start", re.compile(r"starting service 'vendor\.wifi_hal_ext'", re.I)),
    ("wificond_start", re.compile(r"starting service 'wificond'", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("cnss_diag_start", re.compile(r"starting service 'cnss_diag'", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_genl_continue", re.compile(r"cnss-daemon Failed to init genl.*continue", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start|\bwlfw_start\b", re.I)),
    ("wlfw_service_request", re.compile(r"cnss-daemon wlfw_service_request", re.I)),
    ("wlan_pd_indication", re.compile(r"wlan_pd|service msm/modem/wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready|FW ready event received", re.I)),
    ("wlan0_event", re.compile(r"dev\s*:\s*wlan0\s*:|icnss .*wlan0:|\bwlan0\b", re.I)),
    ("pm_qos_warning", re.compile(r"kernel/power/qos\.c:616|pm_qos_add_request", re.I)),
    ("binder_ioctl_unsupported", re.compile(r"binder:.*ioctl .* returned -22", re.I)),
    ("binder_transaction_failed", re.compile(r"binder:.*transaction failed .*?-22", re.I)),
    ("pcie_mhi", re.compile(r"\bpcie\b|\bmhi\b", re.I)),
)

TIMELINE = tuple(name for name, _ in PATTERNS)
ANDROID_ADVANCEMENT = (
    "wlfw_start",
    "wlan_pd_indication",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0_event",
)
NATIVE_BLOCKER_MARKERS = (
    "pm_qos_warning",
    "binder_ioctl_unsupported",
    "binder_transaction_failed",
)
FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v668-manifest", type=Path, default=DEFAULT_V668_MANIFEST)
    parser.add_argument("--v668-dmesg", type=Path, default=DEFAULT_V668_DMESG)
    parser.add_argument("--v668-helper-text", type=Path, default=DEFAULT_V668_HELPER_TEXT)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-sysfs", type=Path, default=DEFAULT_ANDROID_SYSFS)
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


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line or line.startswith("$ "):
            continue
        for marker, pattern in PATTERNS:
            if pattern.search(line):
                events.append(Event(marker, line_time(line), line, source))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    first: dict[str, Event] = {}
    for event in events:
        first.setdefault(event.marker, event)
    return first


def count_by_marker(events: list[Event]) -> dict[str, int]:
    counts = {marker: 0 for marker in TIMELINE}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def event_time(first: dict[str, Event], marker: str) -> float | None:
    event = first.get(marker)
    return event.timestamp if event else None


def delta_ms(first: dict[str, Event], later: str, earlier: str) -> float | None:
    later_time = event_time(first, later)
    earlier_time = event_time(first, earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def source_summary(events: list[Event]) -> dict[str, Any]:
    first = first_by_marker(events)
    counts = count_by_marker(events)
    return {
        "counts": counts,
        "first_times": {marker: event_time(first, marker) for marker in TIMELINE},
        "first_lines": {
            marker: first.get(marker, Event(marker, None, "missing", "")).line for marker in TIMELINE
        },
        "deltas_ms": {
            "wifi_hal_ext_to_service74": delta_ms(first, "service_notifier_74", "wifi_hal_ext_start"),
            "service74_to_cnss_daemon_start": delta_ms(first, "cnss_daemon_start", "service_notifier_74"),
            "service74_to_cnss_daemon_netlink": delta_ms(first, "cnss_daemon_netlink", "service_notifier_74"),
            "cnss_daemon_start_to_wlfw_start": delta_ms(first, "wlfw_start", "cnss_daemon_start"),
            "cnss_daemon_netlink_to_wlfw_start": delta_ms(first, "wlfw_start", "cnss_daemon_netlink"),
            "wlfw_start_to_wlan_pd": delta_ms(first, "wlan_pd_indication", "wlfw_start"),
            "wlfw_start_to_qmi_server": delta_ms(first, "qmi_server_connected", "wlfw_start"),
            "qmi_server_to_bdf_regdb": delta_ms(first, "bdf_regdb", "qmi_server_connected"),
            "bdf_regdb_to_bdf_bdwlan": delta_ms(first, "bdf_bdwlan", "bdf_regdb"),
            "bdf_bdwlan_to_fw_ready": delta_ms(first, "wlan_fw_ready", "bdf_bdwlan"),
            "fw_ready_to_wlan0": delta_ms(first, "wlan0_event", "wlan_fw_ready"),
            "service74_to_pm_qos_warning": delta_ms(first, "pm_qos_warning", "service_notifier_74"),
            "service74_to_binder_transaction": delta_ms(first, "binder_transaction_failed", "service_notifier_74"),
        },
    }


def timeline_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE:
        rows.append([
            marker,
            str(android["counts"].get(marker, 0)),
            str(android["first_times"].get(marker)),
            str(native["counts"].get(marker, 0)),
            str(native["first_times"].get(marker)),
        ])
    return rows


def parse_android_sysfs(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    netdevs: set[str] = set()
    for line in lines:
        match = re.search(r"/net/([^/]+)/", line)
        if match:
            netdevs.add(match.group(1))
    return {
        "line_count": len(lines),
        "icnss_paths": sum(1 for line in lines if "18800000.qcom,icnss" in line),
        "netdevs": sorted(netdevs),
        "wlan0": "wlan0" in netdevs,
        "swlan0": "swlan0" in netdevs,
        "p2p0": "p2p0" in netdevs,
        "wifi_aware0": "wifi-aware0" in netdevs,
        "phy0": any("/ieee80211/phy0/" in line for line in lines),
        "sample": [line for line in lines if "/net/" in line or "/ieee80211/" in line][:40],
    }


def parse_focus_values(helper_text: str) -> dict[str, Any]:
    clean = helper_text.replace("\0", "\n")
    phase_data: dict[str, dict[str, str]] = {}
    for phase in ("service74_open", "window"):
        prefix = f"wifi_companion_start.cnss2_focus_{phase}."
        values: dict[str, str] = {}
        for line in clean.splitlines():
            if line.startswith(prefix) and "=" in line:
                key, value = line[len(prefix):].split("=", 1)
                values[key] = value.strip()
        phase_data[phase] = values
    path_values: dict[str, list[str]] = {}
    current_label = ""
    for line in clean.splitlines():
        begin = re.match(r"A90_EXECNS_PATH_(wifi_cnss2_focus_[^_]+(?:_[^_]+)*)_BEGIN", line)
        if begin:
            current_label = begin.group(1)
            path_values.setdefault(current_label, [])
            continue
        if current_label:
            if line.startswith(f"A90_EXECNS_PATH_{current_label}_END"):
                current_label = ""
                continue
            path_values[current_label].append(line.strip())
    return {"phases": phase_data, "path_values": path_values}


def build_checks(v668: dict[str, Any],
                 android: dict[str, Any],
                 native: dict[str, Any],
                 android_sysfs: dict[str, Any],
                 focus: dict[str, Any]) -> list[dict[str, Any]]:
    v668_live = v668.get("live") or {}
    focused_ready = bool(v668_live.get("v668_cnss2_focus_ready"))
    android_counts = android["counts"]
    native_counts = native["counts"]
    return [
        {
            "name": "v668-focused-capture-ready",
            "status": "pass" if focused_ready else "blocked",
            "detail": f"decision={v668.get('decision')} focused_ready={focused_ready}",
            "next_step": "rerun V668 if focused capture is missing",
        },
        {
            "name": "android-runtime-advances-to-wlan0",
            "status": "pass" if all(android_counts.get(marker, 0) > 0 for marker in ANDROID_ADVANCEMENT) else "blocked",
            "detail": {marker: android_counts.get(marker, 0) for marker in ANDROID_ADVANCEMENT},
            "next_step": "refresh Android evidence if WLFW/BDF/wlan0 markers are missing",
        },
        {
            "name": "android-icnss-netdev-sysfs-present",
            "status": "pass" if android_sysfs["wlan0"] and android_sysfs["phy0"] else "blocked",
            "detail": {
                "netdevs": android_sysfs["netdevs"],
                "phy0": android_sysfs["phy0"],
                "icnss_paths": android_sysfs["icnss_paths"],
            },
            "next_step": "recapture Android ICNSS sysfs if netdev/phy evidence is missing",
        },
        {
            "name": "native-v668-remains-before-wlfw",
            "status": "pass" if all(native_counts.get(marker, 0) == 0 for marker in ANDROID_ADVANCEMENT) else "review",
            "detail": {marker: native_counts.get(marker, 0) for marker in ANDROID_ADVANCEMENT},
            "next_step": "if native advanced, move directly to a WLFW/BDF readiness gate",
        },
        {
            "name": "native-focused-sysfs-has-device-no-netdev",
            "status": "pass" if focus["phases"].get("window", {}).get("qca6390_device_captured") == "1"
            and focus["phases"].get("window", {}).get("wlan0_captured") == "0" else "blocked",
            "detail": focus["phases"].get("window", {}),
            "next_step": "rerun focused capture if QCA6390/window evidence is incomplete",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], android: dict[str, Any], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v669-android-cnss2-runtime-delta-plan-ready",
            True,
            "plan-only; no evidence classification or device command executed",
            "run V669 host-only classifier using V649/V204 Android evidence and V668 native evidence",
        )
    blocking = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocking:
        return (
            "v669-android-cnss2-runtime-delta-blocked",
            False,
            "blocked by " + ", ".join(blocking),
            "refresh missing input evidence before choosing a live Wi-Fi gate",
        )
    android_has_advancement = all(android["counts"].get(marker, 0) > 0 for marker in ANDROID_ADVANCEMENT)
    native_has_advancement = any(native["counts"].get(marker, 0) > 0 for marker in ANDROID_ADVANCEMENT)
    native_has_blocker = any(native["counts"].get(marker, 0) > 0 for marker in NATIVE_BLOCKER_MARKERS)
    if android_has_advancement and not native_has_advancement and native_has_blocker:
        return (
            "v669-android-native-cnss2-runtime-delta-classified",
            True,
            "Android advances from service74/CNSS into WLFW/BDF/wlan0, while V668 native has icnss/QCA6390 devices but remains before WLFW with binder/pm_qos blocker markers",
            "plan V670 as Android init-order/service-trigger classifier before changing the live Wi-Fi HAL or scan/connect surface",
        )
    if android_has_advancement and native_has_advancement:
        return (
            "v669-native-wifi-surface-advanced-review",
            True,
            "native evidence already contains WLFW/BDF/wlan0 advancement",
            "review native evidence and move to the first bounded HAL/netdev readiness gate",
        )
    return (
        "v669-android-native-delta-inconclusive",
        True,
        "inputs passed but the Android/native advancement relationship is not decisive",
        "add one narrower host-only comparison before a live mutation",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v668_manifest = load_json(args.v668_manifest)
    android_events = parse_events(read_text(args.android_dmesg), "android")
    native_events = parse_events(read_text(args.v668_dmesg), "native-v668")
    android = source_summary(android_events)
    native = source_summary(native_events)
    android_sysfs = parse_android_sysfs(read_text(args.android_sysfs))
    focus = parse_focus_values(read_text(args.v668_helper_text))
    checks = build_checks(v668_manifest, android, native, android_sysfs, focus)
    decision, pass_ok, reason, next_step = decide(args.command, checks, android, native)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v668_manifest": str(repo_path(args.v668_manifest)),
            "v668_dmesg": str(repo_path(args.v668_dmesg)),
            "v668_helper_text": str(repo_path(args.v668_helper_text)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "android_sysfs": str(repo_path(args.android_sysfs)),
        },
        "checks": checks,
        "android": android,
        "native_v668": native,
        "android_sysfs": android_sysfs,
        "v668_focus": focus,
        "timeline_rows": timeline_rows(android, native),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def check_rows(checks: list[dict[str, Any]]) -> list[list[str]]:
    return [[check["name"], check["status"], str(check["detail"]), check["next_step"]] for check in checks]


def marker_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return manifest["timeline_rows"]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V669 Android/native cnss2 Runtime Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows(manifest["checks"])),
        "",
        "## Marker Matrix",
        "",
        markdown_table(["marker", "android_count", "android_first_ts", "native_v668_count", "native_v668_first_ts"], marker_rows(manifest)),
        "",
        "## Android Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in manifest["android"]["deltas_ms"].items()]),
        "",
        "## Native V668 Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in manifest["native_v668"]["deltas_ms"].items()]),
        "",
        "## Interpretation",
        "",
        "- Android has the ICNSS-backed `wlan0`/`phy0` sysfs surface and advances through WLFW, BDF, firmware-ready, and `wlan0`.",
        "- V668 native has the ICNSS/QCA6390 platform devices during the service `74` window, but no `wlan0`, WLFW, BDF, or firmware-ready markers.",
        "- The next step should classify Android init/service ordering and trigger differences before authorizing Wi-Fi HAL, scan/connect, DHCP, or external ping.",
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
