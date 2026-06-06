#!/usr/bin/env python3
"""V610 host-only QMI publication precondition classifier.

This classifier compares Android reference evidence with the V609 no-CNSS
observer evidence. It does not contact the device, start daemons, write sysfs,
send QRTR/QMI packets, start Wi-Fi HAL, scan, connect, use credentials, run
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

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v610-qmi-publication-precondition")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_STATE = Path(
    "tmp/wifi/v591-android-subsys-state-sample-handoff/"
    "v590-android-subsys-state-sample-run/android-subsys-state.txt"
)
DEFAULT_V609_DIR = Path("tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live")

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
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|wlfw_start", re.I)),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request|wlfw.*thread", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready|WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'|wifi_companion_start\.child\.qrtr_ns\.start_order=1", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init now waiting for messages", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server: Connection established with the Service locator", re.I)),
    ("memshare_request", re.compile(r"memshare_alloc: memory alloc request received", re.I)),
    ("memshare_fail", re.compile(r"memshare_alloc: unable to allocate memory|alloc_resp\.resp\.result:\s*1", re.I)),
    ("cma_alloc_fail", re.compile(r"cma: cma_alloc: alloc failed", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
)

TIMELINE_MARKERS = [
    "qrtr_rx",
    "qrtr_ns_start",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "sysmon_esoc0",
    "service_notifier_180",
    "service_notifier_74",
    "wlan_pd",
    "wlan_pd_ack_180",
    "qmi_server_connected",
    "wlfw_start",
    "wlfw_thread",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
    "rmt_storage_ready",
    "rmt_storage_open",
    "service_locator",
    "memshare_request",
    "memshare_fail",
    "cma_alloc_fail",
    "cnss_diag_netlink",
    "cnss_daemon_netlink",
]

FORBIDDEN_ACTIONS = [
    "device command",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "QRTR/QMI payload",
    "qcwlanstate or sysfs driver-state write",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-state", type=Path, default=DEFAULT_ANDROID_STATE)
    parser.add_argument("--v609-dir", type=Path, default=DEFAULT_V609_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_binary_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


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


def event_time(found: dict[str, Event], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    newer_time = event_time(found, newer)
    older_time = event_time(found, older)
    if newer_time is None or older_time is None:
        return None
    return round((newer_time - older_time) * 1000.0, 3)


def deltas(found: dict[str, Event]) -> dict[str, float | None]:
    return {
        "qrtr_rx_to_qrtr_tx": delta_ms(found, "qrtr_tx", "qrtr_rx"),
        "qrtr_tx_to_sysmon_modem": delta_ms(found, "sysmon_modem", "qrtr_tx"),
        "sysmon_modem_to_sysmon_slpi": delta_ms(found, "sysmon_slpi", "sysmon_modem"),
        "sysmon_modem_to_sysmon_cdsp": delta_ms(found, "sysmon_cdsp", "sysmon_modem"),
        "sysmon_modem_to_sysmon_adsp": delta_ms(found, "sysmon_adsp", "sysmon_modem"),
        "sysmon_modem_to_service_notifier_180": delta_ms(found, "service_notifier_180", "sysmon_modem"),
        "service_notifier_180_to_service_notifier_74": delta_ms(found, "service_notifier_74", "service_notifier_180"),
        "service_notifier_180_to_wlan_pd": delta_ms(found, "wlan_pd", "service_notifier_180"),
        "service_notifier_180_to_qmi_server_connected": delta_ms(found, "qmi_server_connected", "service_notifier_180"),
        "service_notifier_180_to_wlfw_start": delta_ms(found, "wlfw_start", "service_notifier_180"),
        "wlan_pd_to_qmi_server_connected": delta_ms(found, "qmi_server_connected", "wlan_pd"),
        "wlan_pd_to_bdf_regdb": delta_ms(found, "bdf_regdb", "wlan_pd"),
        "sysmon_modem_to_rmt_storage_ready": delta_ms(found, "rmt_storage_ready", "sysmon_modem"),
        "sysmon_modem_to_service_locator": delta_ms(found, "service_locator", "sysmon_modem"),
        "sysmon_modem_to_memshare_fail": delta_ms(found, "memshare_fail", "sysmon_modem"),
        "sysmon_modem_to_cma_alloc_fail": delta_ms(found, "cma_alloc_fail", "sysmon_modem"),
    }


def event_rows(android_found: dict[str, Event],
               native_found: dict[str, Event],
               android_counts: dict[str, int],
               native_counts: dict[str, int]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE_MARKERS:
        android_event = android_found.get(marker)
        native_event = native_found.get(marker)
        rows.append([
            marker,
            str(android_counts.get(marker, 0)),
            "" if android_event is None or android_event.timestamp is None else f"{android_event.timestamp:.6f}",
            str(native_counts.get(marker, 0)),
            "" if native_event is None or native_event.timestamp is None else f"{native_event.timestamp:.6f}",
            "missing-native" if android_event and not native_event else ("native-only" if native_event and not android_event else "matched" if android_event else "absent"),
        ])
    return rows


def readback_summary(v609_manifest: dict[str, Any]) -> dict[str, Any]:
    readback = ((v609_manifest.get("live") or {}).get("qrtr_readback") or {})
    return {
        "allowed": readback.get("allowed"),
        "send_attempted": readback.get("send_attempted"),
        "result": readback.get("result"),
        "service_events": int(readback.get("service_events") or 0),
        "timeouts": int(readback.get("timeouts") or 0),
        "end_of_list": int(readback.get("end_of_list") or 0),
        "qmi_attempted": int(readback.get("qmi_attempted") or 0),
        "rows": list(readback.get("rows") or []),
    }


def android_filter_notes(android_text: str) -> dict[str, Any]:
    first_line = android_text.splitlines()[0] if android_text.splitlines() else ""
    lower_line = first_line.lower()
    omitted = [
        token
        for token in ("memshare", "servloc", "service_locator", "rmt_storage", "qipcrtr", "rpmsg")
        if token not in lower_line
    ]
    return {
        "first_line": first_line,
        "appears_filtered": "grep -ei" in lower_line or "grep -e" in lower_line,
        "omitted_lower_surface_terms": omitted,
    }


def native_surface(v609_manifest: dict[str, Any], companion_keys: dict[str, str]) -> dict[str, Any]:
    live = v609_manifest.get("live") or {}
    return {
        "decision": v609_manifest.get("decision"),
        "pass": v609_manifest.get("pass"),
        "mss_after_holder": live.get("mss_after_holder"),
        "mss_after_companion": live.get("mss_after_companion"),
        "mdm3_after_companion": live.get("mdm3_after_companion"),
        "firmware_class_path": live.get("firmware_class_path"),
        "mounted_hits": live.get("mounted_hits") or {},
        "modem_blob_visible": live.get("modem_blob_visible") or {},
        "companion_order": companion_keys.get("wifi_companion_start.order", ""),
        "child_started": companion_keys.get("wifi_companion_start.child_started", ""),
        "qipcrtr_before": companion_keys.get("wifi_companion_start.net_before.qipcrtr_sockets", ""),
        "qipcrtr_after_spawn": companion_keys.get("wifi_companion_start.net_after_spawn.qipcrtr_sockets", ""),
        "qipcrtr_window": companion_keys.get("wifi_companion_start.net_window.qipcrtr_sockets", ""),
        "qipcrtr_after_cleanup": companion_keys.get("wifi_companion_start.net_after_cleanup.qipcrtr_sockets", ""),
        "proc_qrtr_captured": companion_keys.get("wifi_companion_start.surface_window.proc_qrtr_captured", ""),
        "service_notifier_captured": companion_keys.get("wifi_companion_start.surface_window.service_notifier_captured", ""),
        "qmi_payload": companion_keys.get("wifi_companion_start.qmi_payload", ""),
        "service_manager": companion_keys.get("wifi_companion_start.service_manager", ""),
        "wifi_hal": companion_keys.get("wifi_companion_start.wifi_hal", ""),
        "scan_connect_linkup": companion_keys.get("wifi_companion_start.scan_connect_linkup", ""),
        "external_ping": companion_keys.get("wifi_companion_start.external_ping", ""),
    }


def classify(android_state: dict[str, str],
             android_found: dict[str, Event],
             native_found: dict[str, Event],
             native_counts: dict[str, int],
             surface: dict[str, Any],
             readback: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    android_has_publication = "service_notifier_180" in android_found and "service_notifier_74" in android_found
    native_base_ready = all(marker in native_found for marker in ("qrtr_rx", "qrtr_tx", "sysmon_modem"))
    native_has_publication = "service_notifier_180" in native_found or "service_notifier_74" in native_found
    android_sibling_sysmon_count = sum(1 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp", "sysmon_esoc0") if marker in android_found)
    native_sibling_sysmon_count = sum(1 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp", "sysmon_esoc0") if marker in native_found)
    android_mdm3_online = android_state.get("mdm3_state") == "ONLINE"
    android_mss_online = android_state.get("mss_state") == "ONLINE"
    native_mss_online = surface.get("mss_after_companion") == "ONLINE"
    native_mdm3_offlining = surface.get("mdm3_after_companion") == "OFFLINING"
    readback_empty = readback["service_events"] == 0 and readback["end_of_list"] > 0 and readback["timeouts"] == 0
    native_memshare_fail = native_counts.get("memshare_fail", 0) > 0 or native_counts.get("cma_alloc_fail", 0) > 0
    diagnostics = {
        "android_has_service_notifier_pair": android_has_publication,
        "native_base_ready": native_base_ready,
        "native_has_service_notifier": native_has_publication,
        "android_sibling_sysmon_count": android_sibling_sysmon_count,
        "native_sibling_sysmon_count": native_sibling_sysmon_count,
        "android_mss_online": android_mss_online,
        "android_mdm3_online": android_mdm3_online,
        "native_mss_online": native_mss_online,
        "native_mdm3_offlining": native_mdm3_offlining,
        "native_wlfw_readback_empty": readback_empty,
        "native_memshare_or_cma_fail": native_memshare_fail,
    }
    if readback["qmi_attempted"]:
        return (
            "v610-qmi-guard-failed",
            False,
            f"unexpected native qmi_attempted={readback['qmi_attempted']}",
            "stop and inspect helper before any further live Wi-Fi action",
            diagnostics,
        )
    if android_has_publication and native_base_ready and not native_has_publication and native_mdm3_offlining:
        return (
            "v610-companion-surface-gap",
            True,
            (
                "Android reaches service-notifier with mss/mdm3 ONLINE and sibling sysmon services, "
                "while native V609 reaches QRTR TX/sysmon with mss ONLINE but mdm3 remains OFFLINING"
            ),
            "compare Android/native mdm3/esoc0, memshare, service-locator, and QIPCRTR surfaces before any CNSS/HAL retry",
            diagnostics,
        )
    if android_has_publication and native_base_ready and not native_has_publication and native_sibling_sysmon_count == 0:
        return (
            "v610-android-has-lower-qmi-publication-trigger",
            True,
            "Android publishes sibling sysmon/service-notifier after modem sysmon; native has only modem sysmon and no service-notifier",
            "capture the missing lower publication trigger before starting CNSS/HAL again",
            diagnostics,
        )
    if not android_has_publication:
        return (
            "v610-native-capture-insufficient",
            False,
            "Android reference evidence lacks the service-notifier pair needed for comparison",
            "recapture Android read-only dmesg before another native live proof",
            diagnostics,
        )
    return (
        "v610-publication-nondeterministic",
        True,
        "available evidence does not isolate one lower precondition beyond native service-notifier nondeterminism",
        "repeat bounded V609-style observation only after documenting the evidence gap",
        diagnostics,
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v609_dir = repo_path(args.v609_dir)
    v609_manifest_path = v609_dir / "manifest.json"
    v609_dmesg_path = v609_dir / "native" / "dmesg-delta.txt"
    v609_companion_path = v609_dir / "native" / "companion-start-only-with-holder.txt"
    android_text = read_text(args.android_dmesg)
    android_state_text = read_text(args.android_state)
    v609_manifest = load_json(v609_manifest_path)
    native_text = "\n".join([
        read_text(v609_dmesg_path),
        read_binary_text(v609_companion_path),
    ])
    android_events = parse_events(android_text, "android")
    native_events = parse_events(native_text, "v609-native")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    android_counts = count_by_marker(android_events)
    native_counts = count_by_marker(native_events)
    android_state = parse_key_values(android_state_text)
    companion_keys = parse_key_values(read_binary_text(v609_companion_path))
    surface = native_surface(v609_manifest, companion_keys)
    readback = readback_summary(v609_manifest)
    decision, pass_ok, reason, next_step, diagnostics = classify(
        android_state,
        android_found,
        native_found,
        native_counts,
        surface,
        readback,
    )
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "diagnostics": diagnostics,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "android_state": str(repo_path(args.android_state)),
            "v609_manifest": str(v609_manifest_path),
            "v609_dmesg": str(v609_dmesg_path),
            "v609_companion": str(v609_companion_path),
        },
        "android": {
            "event_count": len(android_events),
            "counts": {marker: android_counts.get(marker, 0) for marker in TIMELINE_MARKERS},
            "first": {marker: asdict(event) for marker, event in android_found.items() if marker in TIMELINE_MARKERS},
            "deltas_ms": deltas(android_found),
            "state": android_state,
            "filter_notes": android_filter_notes(android_text),
        },
        "native_v609": {
            "event_count": len(native_events),
            "counts": {marker: native_counts.get(marker, 0) for marker in TIMELINE_MARKERS},
            "first": {marker: asdict(event) for marker, event in native_found.items() if marker in TIMELINE_MARKERS},
            "deltas_ms": deltas(native_found),
            "surface": surface,
            "qrtr_readback": readback,
            "manifest_decision": v609_manifest.get("decision"),
            "manifest_pass": v609_manifest.get("pass"),
        },
        "timeline_matrix": event_rows(android_found, native_found, android_counts, native_counts),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native_v609"]
    return "\n".join([
        "# V610 QMI Publication Precondition Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Diagnostics",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["diagnostics"].items()]),
        "",
        "## Android State",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in sorted(android["state"].items())]),
        "",
        "## Native V609 Surface",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in native["surface"].items()]),
        "",
        "## Timing Deltas (ms)",
        "",
        markdown_table(
            ["delta", "android", "native_v609"],
            [[key, android["deltas_ms"].get(key), native["deltas_ms"].get(key)] for key in android["deltas_ms"]],
        ),
        "",
        "## Timeline Matrix",
        "",
        markdown_table(["marker", "android_count", "android_ts", "native_count", "native_ts", "status"], manifest["timeline_matrix"]),
        "",
        "## Native WLFW QRTR Readback",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in native["qrtr_readback"].items() if key != "rows"]),
        "",
        "## Evidence Limit",
        "",
        f"- android_appears_filtered: `{android['filter_notes']['appears_filtered']}`",
        f"- omitted_lower_surface_terms: `{', '.join(android['filter_notes']['omitted_lower_surface_terms'])}`",
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
