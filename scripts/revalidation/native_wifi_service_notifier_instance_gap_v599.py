#!/usr/bin/env python3
"""V599 host-only service-notifier instance gap classifier.

This classifier compares Android reference timing with V598 native evidence. It
does not contact the device, start daemons, write sysfs, send QRTR/QMI packets,
start Wi-Fi HAL, scan, connect, use credentials, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v599-service-notifier-instance-gap")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_V597_MANIFEST = Path("tmp/wifi/v597-post-sysmon-gap/manifest.json")
DEFAULT_V598_MANIFEST = Path("tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json")
DEFAULT_V598_DMESG = Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt")
DEFAULT_V598_COMPANION = Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/companion-start-only-with-holder.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("firmware_mounts", re.compile(r"target=/vendor/firmware_mnt|target=/vendor/firmware-modem", re.I)),
    ("wlan_driver_load", re.compile(r"wlan: Loading driver", re.I)),
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'|wifi_companion_start\.child\.qrtr_ns\.start_order=1", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I)),
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("cnss_diag_start", re.compile(r"starting service 'cnss_diag'|wifi_companion_start\.child\.cnss_diag\.start_order=5", re.I)),
    ("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'|wifi_companion_start\.child\.cnss_daemon\.start_order=6", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready", re.I)),
    ("wlan0_event", re.compile(r"\bwlan0\b", re.I)),
)

TIMELINE_MARKERS = [
    "firmware_mounts",
    "wlan_driver_load",
    "qrtr_rx",
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
    "wlan_pd_ack_180",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "sysmon_esoc0",
    "wlan0_event",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--v597-manifest", type=Path, default=DEFAULT_V597_MANIFEST)
    parser.add_argument("--v598-manifest", type=Path, default=DEFAULT_V598_MANIFEST)
    parser.add_argument("--v598-dmesg", type=Path, default=DEFAULT_V598_DMESG)
    parser.add_argument("--v598-companion", type=Path, default=DEFAULT_V598_COMPANION)
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


def parse_event_line(raw_line: str, source: str) -> Event | None:
    line = clean_line(raw_line)
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


def events_from_manifest_rows(rows: list[list[Any]], source: str) -> list[Event]:
    events: list[Event] = []
    for row in rows:
        if len(row) < 3:
            continue
        marker = str(row[0])
        if marker not in TIMELINE_MARKERS:
            continue
        timestamp: float | None
        try:
            timestamp = float(row[1]) if str(row[1]).strip() else None
        except ValueError:
            timestamp = None
        line = clean_line(str(row[2]))
        if line and line != "missing":
            events.append(Event(marker, timestamp, line, source))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    found: dict[str, Event] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def has(found: dict[str, Event], marker: str) -> bool:
    return marker in found


def event_time(found: dict[str, Event], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    left = event_time(found, newer)
    right = event_time(found, older)
    if left is None or right is None:
        return None
    return round((left - right) * 1000.0, 3)


def event_rows(found: dict[str, Event]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE_MARKERS:
        event = found.get(marker)
        rows.append([
            marker,
            "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}",
            "missing" if event is None else event.line,
        ])
    return rows


def readback_rows(v598: dict[str, Any]) -> list[dict[str, Any]]:
    readback = ((v598.get("live") or {}).get("qrtr_readback") or {})
    return list(readback.get("rows") or [])


def readback_summary(v598: dict[str, Any]) -> dict[str, Any]:
    readback = ((v598.get("live") or {}).get("qrtr_readback") or {})
    return {
        "allowed": readback.get("allowed"),
        "send_attempted": readback.get("send_attempted"),
        "result": readback.get("result"),
        "service_events": int(readback.get("service_events") or 0),
        "end_of_list": int(readback.get("end_of_list") or 0),
        "timeouts": int(readback.get("timeouts") or 0),
        "qmi_attempted": int(readback.get("qmi_attempted") or 0),
        "rows": readback_rows(v598),
    }


def count_present(found: dict[str, Event], markers: list[str]) -> int:
    return sum(1 for marker in markers if has(found, marker))


def classify(android: dict[str, Event],
             native: dict[str, Event],
             v598: dict[str, Any]) -> tuple[str, bool, str, str]:
    readback = readback_summary(v598)
    marker_counts = (((v598.get("live") or {}).get("markers") or {}).get("counts") or {})
    kernel_warning = int(marker_counts.get("kernel_warning") or 0)
    if kernel_warning:
        return (
            "v599-kernel-warning-review",
            False,
            f"V598 marker count has kernel_warning={kernel_warning}",
            "do not repeat companion/holder path before resolving kernel warning",
        )
    if readback["qmi_attempted"]:
        return (
            "v599-readback-qmi-guard-failed",
            False,
            f"unexpected qmi_attempted={readback['qmi_attempted']}",
            "stop and inspect helper before any further Wi-Fi live action",
        )
    if has(native, "qmi_server_connected") or has(native, "wlan_fw_ready") or has(native, "wlan0_event"):
        return (
            "v599-native-advanced-readiness-review",
            True,
            "native evidence already advanced past the V598 expected gap",
            "refresh classifier inputs and move to bounded scan/connect gates only after wlan0 readiness is proven",
        )
    android_has_root_pair = has(android, "service_notifier_180") and has(android, "service_notifier_74")
    native_has_partial_service = has(native, "service_notifier_180") and not has(native, "service_notifier_74")
    native_missing_sibling_sysmon = count_present(native, ["sysmon_slpi", "sysmon_cdsp", "sysmon_adsp"]) == 0
    readback_empty = readback["service_events"] == 0 and readback["end_of_list"] > 0 and readback["timeouts"] == 0
    if android_has_root_pair and native_has_partial_service and native_missing_sibling_sysmon and readback_empty:
        return (
            "v599-service-notifier-instance-gap-classified",
            True,
            (
                "Android reaches sysmon modem/slpi/cdsp/adsp plus service-notifier 180/74; "
                "native V598 reaches modem sysmon and service-notifier 180 only, while WLFW service 69 readback is clean end-of-list"
            ),
            "next gate: bounded service-registry/sysmon instance matrix; still no qcwlanstate, HAL, scan/connect, or external ping",
        )
    if android_has_root_pair and native_has_partial_service and readback_empty:
        return (
            "v599-service-notifier-74-gap-classified",
            True,
            "native V598 has service-notifier 180 but not 74; WLFW service 69 remains unpublished",
            "next gate: identify service-notifier instance 74 dependency before retrying CNSS/HAL",
        )
    if android_has_root_pair and not has(native, "service_notifier_180"):
        return (
            "v599-service-notifier-regression-review",
            False,
            "V599 input lacks native service-notifier 180 seen by V598 report",
            "refresh V598 evidence before planning a live retry",
        )
    return (
        "v599-review-required",
        False,
        (
            f"android_root_pair={android_has_root_pair} "
            f"native_180={has(native, 'service_notifier_180')} native_74={has(native, 'service_notifier_74')} "
            f"readback_events={readback['service_events']} readback_eol={readback['end_of_list']}"
        ),
        "inspect evidence manually before choosing a live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v597 = load_json(args.v597_manifest)
    v598 = load_json(args.v598_manifest)
    android_events = events_from_manifest_rows(((v597.get("android") or {}).get("rows") or []), "v597-android")
    android_events.extend(parse_events(read_text(args.android_dmesg), "android-dmesg"))
    native_text = "\n".join([
        read_text(args.v598_dmesg),
        read_text(args.v598_companion),
        "\n".join((((v598.get("live") or {}).get("markers") or {}).get("focus_tail") or [])),
    ])
    native_events = parse_events(native_text, "v598-native")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    decision, pass_ok, reason, next_step = classify(android_found, native_found, v598)
    android_deltas = {
        "sysmon_modem_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "sysmon_modem"),
        "service_notifier_180_to_service_notifier_74": delta_ms(android_found, "service_notifier_74", "service_notifier_180"),
        "service_notifier_180_to_cnss_daemon_start": delta_ms(android_found, "cnss_daemon_start", "service_notifier_180"),
        "cnss_daemon_start_to_wlfw_start": delta_ms(android_found, "wlfw_start", "cnss_daemon_start"),
        "wlfw_thread_to_wlan_pd": delta_ms(android_found, "wlan_pd", "wlfw_thread"),
        "wlan_pd_to_qmi_server_connected": delta_ms(android_found, "qmi_server_connected", "wlan_pd"),
        "wlan_pd_to_bdf_regdb": delta_ms(android_found, "bdf_regdb", "wlan_pd"),
    }
    native_deltas = {
        "sysmon_modem_to_service_notifier_180": delta_ms(native_found, "service_notifier_180", "sysmon_modem"),
        "service_notifier_180_to_service_notifier_74": delta_ms(native_found, "service_notifier_74", "service_notifier_180"),
        "service_notifier_180_to_wlan_pd": delta_ms(native_found, "wlan_pd", "service_notifier_180"),
        "wlan_pd_to_qmi_server_connected": delta_ms(native_found, "qmi_server_connected", "wlan_pd"),
    }
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "v597_manifest": str(repo_path(args.v597_manifest)),
            "v598_manifest": str(repo_path(args.v598_manifest)),
            "v598_dmesg": str(repo_path(args.v598_dmesg)),
            "v598_companion": str(repo_path(args.v598_companion)),
        },
        "android": {
            "event_count": len(android_events),
            "rows": event_rows(android_found),
            "deltas_ms": android_deltas,
        },
        "native_v598": {
            "event_count": len(native_events),
            "rows": event_rows(native_found),
            "deltas_ms": native_deltas,
            "decision": v598.get("decision"),
            "pass": v598.get("pass"),
            "reason": v598.get("reason"),
            "marker_counts": (((v598.get("live") or {}).get("markers") or {}).get("counts") or {}),
            "qrtr_readback": readback_summary(v598),
        },
        "inferences": {
            "service_notifier_is_kernel_qmi_callback": True,
            "userspace_cnss_daemon_not_direct_trigger_for_initial_service_notifier_pair": True,
            "native_gap_after_v598": "missing service-notifier 74, sibling sysmon services, WLAN-PD, WLFW service 69, QMI Server Connected, BDF, and wlan0",
        },
        "references": [
            "https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/service-notifier.c",
            "https://android.googlesource.com/kernel/msm.git/+/330705db41eb77d77476c5fccf3527f5db1d1525/drivers/soc/qcom/sysmon-qmi.c",
            "https://android.googlesource.com/kernel/msm.git/+/03c2d42aa4bc362578b3824a81583638e2e23151/drivers/soc/qcom/icnss_qmi.c",
        ],
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
    android_deltas = [[key, value] for key, value in manifest["android"]["deltas_ms"].items()]
    native_deltas = [[key, value] for key, value in manifest["native_v598"]["deltas_ms"].items()]
    readback = manifest["native_v598"]["qrtr_readback"]
    readback_rows = [
        [
            row.get("case", ""),
            row.get("service", ""),
            row.get("instance", ""),
            row.get("new_lookup_rc", ""),
            row.get("service_events", ""),
            row.get("end_of_list", ""),
            row.get("timeout", ""),
            row.get("qmi_attempted", ""),
            row.get("status", ""),
        ]
        for row in readback.get("rows", [])
    ]
    return "\n".join([
        "# V599 Service-Notifier Instance Gap Classifier",
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
        markdown_table(["delta", "ms"], android_deltas),
        "",
        "## Native V598 Deltas",
        "",
        markdown_table(["delta", "ms"], native_deltas),
        "",
        "## Android Timeline",
        "",
        markdown_table(["marker", "timestamp", "line"], manifest["android"]["rows"]),
        "",
        "## Native V598 Timeline",
        "",
        markdown_table(["marker", "timestamp", "line"], manifest["native_v598"]["rows"]),
        "",
        "## Native V598 WLFW QRTR Readback",
        "",
        f"- allowed: `{readback.get('allowed')}`",
        f"- send_attempted: `{readback.get('send_attempted')}`",
        f"- result: `{readback.get('result')}`",
        f"- service_events: `{readback.get('service_events')}`",
        f"- end_of_list: `{readback.get('end_of_list')}`",
        f"- timeouts: `{readback.get('timeouts')}`",
        f"- qmi_attempted: `{readback.get('qmi_attempted')}`",
        "",
        markdown_table(
            ["case", "service", "instance", "new_lookup_rc", "service_events", "end_of_list", "timeout", "qmi_attempted", "status"],
            readback_rows,
        ) if readback_rows else "- none",
        "",
        "## Inferences",
        "",
        "- `service-notifier` is a kernel QMI callback path, not an ordinary userspace daemon trigger.",
        "- Android publishes service-notifier instances `180` and `74` before CNSS daemon WLFW work reaches WLAN-PD.",
        "- Native V598 publishes only instance `180`; WLFW service `69` remains absent from QRTR nameservice readback.",
        "- The next useful live gate is an instance/sysmon matrix, not qcwlanstate, HAL, scan, or connect.",
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
