#!/usr/bin/env python3
"""V597 host-only post-sysmon readiness gap classifier.

This classifier compares the captured Android QRTR/sysmon/service-notifier
timeline against V596 native evidence. It does not contact the device, start
daemons, write sysfs, send QRTR/QMI packets, start Wi-Fi HAL, scan, connect,
or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v597-post-sysmon-gap")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_SUMMARY = Path("tmp/wifi/v206-android-icnss-cnss-map/summary.md")
DEFAULT_V596_MANIFEST = Path("tmp/wifi/v596-modem-holder-companion-proof/manifest.json")
DEFAULT_V596_DMESG = Path("tmp/wifi/v596-modem-holder-companion-proof/native/dmesg-delta.txt")
DEFAULT_V596_COMPANION = Path("tmp/wifi/v596-modem-holder-companion-proof/native/companion-start-only-with-holder.txt")

TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("firmware_mounts", re.compile(r"target=/vendor/firmware_mnt|target=/vendor/firmware-modem")),
    ("wlan_driver_load", re.compile(r"wlan: Loading driver")),
    ("wlan_state_initialized", re.compile(r"wlan_hdd_state.*initialized")),
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX")),
    ("wifi_hal_legacy_start", re.compile(r"starting service 'vendor\.wifi_hal_legacy'")),
    ("wifi_hal_ext_start", re.compile(r"starting service 'vendor\.wifi_hal_ext'")),
    ("qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'|wifi_companion_start\.child\.qrtr_ns\.start_order=1")),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX")),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service")),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service")),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service")),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service")),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service")),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service")),
    ("cnss_diag_start", re.compile(r"starting service 'cnss_diag'|wifi_companion_start\.child\.cnss_diag\.start_order=5")),
    ("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'|wifi_companion_start\.child\.cnss_daemon\.start_order=6")),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting")),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request")),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd")),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected")),
    ("bdf_regdb", re.compile(r"BDF file : regdb\.bin")),
    ("bdf_bdwlan", re.compile(r"BDF file : bdwlan\.bin")),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready")),
    ("wlan0_event", re.compile(r"\bwlan0\b")),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-summary", type=Path, default=DEFAULT_ANDROID_SUMMARY)
    parser.add_argument("--v596-manifest", type=Path, default=DEFAULT_V596_MANIFEST)
    parser.add_argument("--v596-dmesg", type=Path, default=DEFAULT_V596_DMESG)
    parser.add_argument("--v596-companion", type=Path, default=DEFAULT_V596_COMPANION)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def parse_event_line(raw_line: str, source: str) -> Event | None:
    line = ANSI_RE.sub("", raw_line).strip()
    match = TS_RE.match(line)
    timestamp = float(match.group("ts")) if match else None
    for marker, pattern in MARKERS:
        if pattern.search(line):
            return Event(marker, timestamp, line, source)
    return None


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        event = parse_event_line(raw_line, source)
        if event:
            events.append(event)
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    found: dict[str, Event] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def marker_time(found: dict[str, Event], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    left = marker_time(found, newer)
    right = marker_time(found, older)
    if left is None or right is None:
        return None
    return round((left - right) * 1000.0, 3)


def event_rows(found: dict[str, Event], markers: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in markers:
        event = found.get(marker)
        rows.append([
            marker,
            "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}",
            "missing" if event is None else event.line,
        ])
    return rows


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def classify(android_found: dict[str, Event],
             native_found: dict[str, Event],
             v596: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_has_service_notifier = "service_notifier_180" in android_found and "service_notifier_74" in android_found
    native_has_service_notifier = "service_notifier_180" in native_found or "service_notifier_74" in native_found
    native_has_sysmon = "sysmon_modem" in native_found
    native_has_qrtr_tx = "qrtr_tx" in native_found
    native_kernel_warning = ((v596.get("live") or {}).get("markers") or {}).get("counts", {}).get("kernel_warning", 0)
    sysmon_to_service = delta_ms(android_found, "service_notifier_180", "sysmon_modem")
    service_to_wlan_pd = delta_ms(android_found, "wlan_pd", "service_notifier_180")
    daemon_to_wlfw = delta_ms(android_found, "wlfw_start", "cnss_daemon_start")
    wlfw_to_wlan_pd = delta_ms(android_found, "wlan_pd", "wlfw_thread")

    if native_kernel_warning:
        return (
            "v597-post-sysmon-kernel-warning-review",
            False,
            f"V596 kernel_warning_count={native_kernel_warning}",
            "do not repeat holder path before resolving kernel warning",
        )
    if native_has_qrtr_tx and native_has_sysmon and android_has_service_notifier and not native_has_service_notifier:
        return (
            "v597-post-sysmon-service-notifier-gap-classified",
            True,
            (
                "Android service-notifier appears "
                f"{sysmon_to_service}ms after sysmon and before CNSS daemon WLFW; "
                f"native reaches QRTR TX/sysmon but has no service-notifier"
            ),
            "next gate: bounded service-notifier/WLFW visibility probe or WLFW QRTR readback; still no scan/connect",
        )
    if native_has_service_notifier and "wlan_pd" not in native_found:
        return (
            "v597-wlan-pd-gap-classified",
            True,
            f"native service-notifier present but WLAN-PD missing; Android service->WLAN-PD delta={service_to_wlan_pd}ms",
            "next gate: bounded cnss-daemon WLFW readback/start ordering classifier",
        )
    return (
        "v597-post-sysmon-review-required",
        False,
        f"native_qrtr_tx={native_has_qrtr_tx} native_sysmon={native_has_sysmon} native_service_notifier={native_has_service_notifier}",
        "inspect input evidence before live retry",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_text = read_text(args.android_dmesg) or read_text(args.android_summary)
    v596_dmesg_text = read_text(args.v596_dmesg)
    v596_companion_text = read_text(args.v596_companion)
    v596 = load_json(args.v596_manifest)
    android_events = parse_events(android_text, "android")
    native_events = parse_events(v596_dmesg_text + "\n" + v596_companion_text, "v596")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    decision, pass_ok, reason, next_step = classify(android_found, native_found, v596)
    markers = [
        "firmware_mounts",
        "wlan_driver_load",
        "wlan_state_initialized",
        "qrtr_rx",
        "wifi_hal_legacy_start",
        "wifi_hal_ext_start",
        "qrtr_ns_start",
        "qrtr_tx",
        "sysmon_modem",
        "sysmon_slpi",
        "sysmon_cdsp",
        "sysmon_adsp",
        "service_notifier_180",
        "service_notifier_74",
        "cnss_diag_start",
        "cnss_daemon_start",
        "wlfw_start",
        "wlfw_thread",
        "wlan_pd",
        "qmi_server_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0_event",
    ]
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "android_summary": str(repo_path(args.android_summary)),
            "v596_manifest": str(repo_path(args.v596_manifest)),
            "v596_dmesg": str(repo_path(args.v596_dmesg)),
            "v596_companion": str(repo_path(args.v596_companion)),
        },
        "android": {
            "event_count": len(android_events),
            "rows": event_rows(android_found, markers),
            "deltas_ms": {
                "sysmon_modem_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "sysmon_modem"),
                "service_notifier_180_to_service_notifier_74": delta_ms(android_found, "service_notifier_74", "service_notifier_180"),
                "service_notifier_180_to_cnss_diag_start": delta_ms(android_found, "cnss_diag_start", "service_notifier_180"),
                "service_notifier_180_to_cnss_daemon_start": delta_ms(android_found, "cnss_daemon_start", "service_notifier_180"),
                "cnss_daemon_start_to_wlfw_start": delta_ms(android_found, "wlfw_start", "cnss_daemon_start"),
                "wlfw_thread_to_wlan_pd": delta_ms(android_found, "wlan_pd", "wlfw_thread"),
                "wlan_pd_to_qmi_server_connected": delta_ms(android_found, "qmi_server_connected", "wlan_pd"),
            },
        },
        "native_v596": {
            "event_count": len(native_events),
            "rows": event_rows(native_found, markers),
            "decision": v596.get("decision"),
            "pass": v596.get("pass"),
            "reason": v596.get("reason"),
            "live_markers": ((v596.get("live") or {}).get("markers") or {}),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "explicitly_not_executed": [
            "device command",
            "QRTR/QMI packet",
            "daemon start",
            "service-manager or Wi-Fi HAL start",
            "qcwlanstate or sysfs write",
            "scan/connect/link-up/credential/DHCP/routing/external ping",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android_rows = manifest["android"]["rows"]
    native_rows = manifest["native_v596"]["rows"]
    deltas = [[key, value] for key, value in manifest["android"]["deltas_ms"].items()]
    return "\n".join([
        "# V597 Post-Sysmon Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Android Deltas",
        "",
        markdown_table(["delta", "ms"], deltas),
        "",
        "## Android Timeline",
        "",
        markdown_table(["marker", "timestamp", "line"], android_rows),
        "",
        "## Native V596 Timeline",
        "",
        markdown_table(["marker", "timestamp", "line"], native_rows),
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
