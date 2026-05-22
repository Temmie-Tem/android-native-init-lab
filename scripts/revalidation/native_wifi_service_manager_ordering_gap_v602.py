#!/usr/bin/env python3
"""V602 host-only service-manager ordering gap classifier.

This classifier compares Android reference evidence, V598's modem-holder WLFW
readback proof, and V601's service-manager binder proof. It does not contact
the device, start daemons, write sysfs, send QRTR/QMI packets, start Wi-Fi HAL,
scan, connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v602-service-manager-ordering-gap")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_V598_MANIFEST = Path("tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json")
DEFAULT_V598_DMESG = Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt")
DEFAULT_V598_COMPANION = Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/companion-start-only-with-holder.txt")
DEFAULT_V601_MANIFEST = Path("tmp/wifi/v601-modem-holder-service-manager/manifest.json")
DEFAULT_V601_DMESG = Path("tmp/wifi/v601-modem-holder-service-manager/native/dmesg-delta.txt")
DEFAULT_V601_COMPANION = Path("tmp/wifi/v601-modem-holder-service-manager/native/companion-start-only-with-holder.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("binder_transaction_failed", re.compile(r"binder: .*transaction failed|binder transaction failed", re.I)),
    ("binder_ioctl_unsupported", re.compile(r"BINDER_ENABLE_ONEWAY_SPAM_DETECTION|oneway spam|binder: .*ioctl .* returned -22", re.I)),
    ("perfd_client_failed", re.compile(r"Failed to become a perfd client", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|wlfw_start", re.I)),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request|wlfw.*thread", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready|WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
)

MATRIX_MARKERS = [
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "service_notifier_180",
    "service_notifier_74",
    "wlan_pd",
    "cnss_diag_netlink",
    "cnss_daemon_netlink",
    "binder_transaction_failed",
    "binder_ioctl_unsupported",
    "perfd_client_failed",
    "wlfw_start",
    "wlfw_thread",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
]

FORBIDDEN_ACTIONS = [
    "device command",
    "QRTR/QMI payload",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "qcwlanstate write",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--v598-manifest", type=Path, default=DEFAULT_V598_MANIFEST)
    parser.add_argument("--v598-dmesg", type=Path, default=DEFAULT_V598_DMESG)
    parser.add_argument("--v598-companion", type=Path, default=DEFAULT_V598_COMPANION)
    parser.add_argument("--v601-manifest", type=Path, default=DEFAULT_V601_MANIFEST)
    parser.add_argument("--v601-dmesg", type=Path, default=DEFAULT_V601_DMESG)
    parser.add_argument("--v601-companion", type=Path, default=DEFAULT_V601_COMPANION)
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        match = TS_RE.match(line)
        timestamp = float(match.group("ts")) if match else None
        for marker, pattern in MARKERS:
            if pattern.search(line):
                events.append(Event(marker, timestamp, line, source))
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


def parse_keys(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def readback_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    readback = ((manifest.get("live") or {}).get("qrtr_readback") or {})
    return {
        "send_attempted": readback.get("send_attempted", ""),
        "service_events": int(readback.get("service_events") or 0),
        "end_of_list": int(readback.get("end_of_list") or 0),
        "timeouts": int(readback.get("timeouts") or 0),
        "qmi_attempted": int(readback.get("qmi_attempted") or 0),
    }


def time_delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    left = found.get(newer)
    right = found.get(older)
    if not left or not right or left.timestamp is None or right.timestamp is None:
        return None
    return round((left.timestamp - right.timestamp) * 1000.0, 3)


def source_summary(label: str,
                   manifest: dict[str, Any],
                   dmesg: str,
                   companion_text: str = "") -> dict[str, Any]:
    events = parse_events(dmesg + "\n" + companion_text, label)
    found = first_by_marker(events)
    counts = count_by_marker(events)
    keys = parse_keys(companion_text)
    return {
        "label": label,
        "manifest_decision": manifest.get("decision"),
        "manifest_pass": manifest.get("pass"),
        "events": events,
        "found": found,
        "counts": counts,
        "keys": keys,
        "readback": readback_summary(manifest),
        "service_manager_executed": bool(manifest.get("service_manager_start_executed")),
        "copy_real_linkerconfig": bool(manifest.get("copy_real_linkerconfig_executed")),
        "daemon_start_executed": bool(manifest.get("daemon_start_executed")),
        "wifi_bringup_executed": bool(manifest.get("wifi_bringup_executed")),
    }


def has(summary: dict[str, Any], marker: str) -> bool:
    return marker in (summary.get("found") or {})


def count(summary: dict[str, Any], marker: str) -> int:
    return int((summary.get("counts") or {}).get(marker, 0))


def first_line(summary: dict[str, Any], marker: str) -> str:
    event = (summary.get("found") or {}).get(marker)
    return event.line if event else ""


def matrix_rows(android: dict[str, Any],
                v598: dict[str, Any],
                v601: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in MATRIX_MARKERS:
        rows.append([
            marker,
            str(count(android, marker)),
            str(count(v598, marker)),
            str(count(v601, marker)),
            "yes" if has(android, marker) else "no",
            "yes" if has(v598, marker) else "no",
            "yes" if has(v601, marker) else "no",
            first_line(android, marker)[:160],
            first_line(v598, marker)[:160],
            first_line(v601, marker)[:160],
        ])
    return rows


def timing_rows(android: dict[str, Any],
                v598: dict[str, Any],
                v601: dict[str, Any]) -> list[list[str]]:
    pairs = [
        ("qrtr_tx", "qrtr_rx"),
        ("sysmon_modem", "qrtr_tx"),
        ("service_notifier_180", "sysmon_modem"),
        ("service_notifier_74", "service_notifier_180"),
        ("wlan_pd", "wlfw_thread"),
        ("qmi_server_connected", "wlan_pd"),
        ("bdf_regdb", "wlan_pd"),
        ("wlan_fw_ready", "bdf_bdwlan"),
    ]
    return [
        [
            f"{newer}-{older}",
            "" if time_delta_ms(android["found"], newer, older) is None else str(time_delta_ms(android["found"], newer, older)),
            "" if time_delta_ms(v598["found"], newer, older) is None else str(time_delta_ms(v598["found"], newer, older)),
            "" if time_delta_ms(v601["found"], newer, older) is None else str(time_delta_ms(v601["found"], newer, older)),
        ]
        for newer, older in pairs
    ]


def classify(android: dict[str, Any],
             v598: dict[str, Any],
             v601: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_reaches_wlfw = has(android, "service_notifier_180") and has(android, "service_notifier_74") and has(android, "wlan_pd") and has(android, "qmi_server_connected")
    v598_lower_path = has(v598, "qrtr_tx") and has(v598, "sysmon_modem") and has(v598, "service_notifier_180")
    v601_binder_clear = v601["service_manager_executed"] and count(v601, "binder_transaction_failed") == 0
    v601_lower_regressed = has(v601, "qrtr_tx") and has(v601, "sysmon_modem") and not has(v601, "service_notifier_180")
    v601_readback_empty = v601["readback"]["service_events"] == 0 and v601["readback"]["end_of_list"] > 0 and v601["readback"]["qmi_attempted"] == 0
    if android_reaches_wlfw and v598_lower_path and v601_binder_clear and v601_lower_regressed and v601_readback_empty:
        return (
            "v602-service-manager-ordering-gap-classified",
            True,
            "V598 proves QRTR TX/sysmon/service-notifier 180 without service-manager, while V601 proves service-manager clears binder transaction failures but loses service-notifier 180 and still has empty WLFW readback",
            "implement a bounded qrtr-first/delayed service-manager companion proof before any qcwlanstate, Wi-Fi HAL, scan/connect, or external ping",
        )
    if android_reaches_wlfw and v601_binder_clear and has(v601, "service_notifier_180") and not has(v601, "service_notifier_74"):
        return (
            "v602-service-registry-sibling-gap-classified",
            True,
            "service-manager path preserves service-notifier 180 but still misses service-notifier 74/WLAN-PD/WLFW",
            "classify sibling sysmon/service-registry trigger before qcwlanstate or HAL",
        )
    if has(v601, "wlfw_start") or v601["readback"]["service_events"] > 0:
        return (
            "v602-wlfw-advance-detected",
            True,
            "V601 already contains WLFW evidence; move toward bounded qcwlanstate/HAL gate",
            "validate current evidence and plan bounded qcwlanstate/HAL without scan/connect first",
        )
    return (
        "v602-review-required",
        False,
        "evidence does not match expected V598/V601 progression",
        "inspect V598/V601 manifests and dmesg before another live action",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    android_dmesg = read_text(args.android_dmesg)
    v598_manifest = load_json(args.v598_manifest)
    v598_dmesg = read_text(args.v598_dmesg)
    v598_companion = read_text(args.v598_companion)
    v601_manifest = load_json(args.v601_manifest)
    v601_dmesg = read_text(args.v601_dmesg)
    v601_companion = read_text(args.v601_companion)

    android = source_summary("android", {}, android_dmesg)
    v598 = source_summary("v598", v598_manifest, v598_dmesg, v598_companion)
    v601 = source_summary("v601", v601_manifest, v601_dmesg, v601_companion)

    decision, pass_ok, reason, next_step = classify(android, v598, v601)
    evidence_inputs = {
        "android_dmesg": str(repo_path(args.android_dmesg)),
        "v598_manifest": str(repo_path(args.v598_manifest)),
        "v598_dmesg": str(repo_path(args.v598_dmesg)),
        "v598_companion": str(repo_path(args.v598_companion)),
        "v601_manifest": str(repo_path(args.v601_manifest)),
        "v601_dmesg": str(repo_path(args.v601_dmesg)),
        "v601_companion": str(repo_path(args.v601_companion)),
    }
    matrix = matrix_rows(android, v598, v601)
    timings = timing_rows(android, v598, v601)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "input_paths": evidence_inputs,
        "matrix": matrix,
        "timings_ms": timings,
        "summaries": {
            "android_counts": dict(sorted(android["counts"].items())),
            "v598_counts": dict(sorted(v598["counts"].items())),
            "v601_counts": dict(sorted(v601["counts"].items())),
            "v598_readback": v598["readback"],
            "v601_readback": v601["readback"],
            "v601_service_manager_executed": v601["service_manager_executed"],
            "v601_copy_real_linkerconfig": v601["copy_real_linkerconfig"],
            "v601_wifi_bringup_executed": v601["wifi_bringup_executed"],
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "explicitly_not_executed": FORBIDDEN_ACTIONS,
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V602 Service-Manager Ordering Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Marker Matrix",
        "",
        markdown_table(
            ["marker", "android_count", "v598_count", "v601_count", "android", "v598", "v601", "android_first", "v598_first", "v601_first"],
            manifest["matrix"],
        ),
        "",
        "## Timing Deltas",
        "",
        markdown_table(["delta_ms", "android", "v598", "v601"], manifest["timings_ms"]),
        "",
        "## Summaries",
        "",
        "```json",
        json.dumps(manifest["summaries"], indent=2, sort_keys=True),
        "```",
        "",
        "## Guardrails",
        "",
        *[f"- no {item}" for item in FORBIDDEN_ACTIONS],
        "",
    ])


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
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
