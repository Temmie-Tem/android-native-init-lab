#!/usr/bin/env python3
"""V600 host-only service-registry and CNSS runtime matrix classifier.

This classifier compares Android reference dmesg with V598/V599 native
evidence. It does not contact the device, start daemons, write sysfs, send
QRTR/QMI packets, start Wi-Fi HAL, scan, connect, use credentials, or ping
externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v600-registry-cnss-matrix")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_V598_MANIFEST = Path("tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json")
DEFAULT_V598_DMESG = Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt")
DEFAULT_V598_COMPANION = Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/companion-start-only-with-holder.txt")
DEFAULT_V599_MANIFEST = Path("tmp/wifi/v599-service-notifier-instance-gap/manifest.json")

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
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init now waiting for messages", re.I)),
    ("tftp_server_start", re.compile(r"wifi_companion_start\.child\.tftp_server\.start_order=3", re.I)),
    ("pd_mapper_start", re.compile(r"wifi_companion_start\.child\.pd_mapper\.start_order=4", re.I)),
    ("cnss_diag_start", re.compile(r"starting service 'cnss_diag'|wifi_companion_start\.child\.cnss_diag\.start_order=5", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'|wifi_companion_start\.child\.cnss_daemon\.start_order=6", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_genl_failure", re.compile(r"cnss-daemon Failed to init genl between daemon and platform", re.I)),
    ("cnss_daemon_binder_ioctl_fail", re.compile(r"cnss-daemon:.*binder: .*ioctl .* returned -22", re.I)),
    ("cnss_daemon_binder_tx_fail", re.compile(r"cnss-daemon:.*binder: .*transaction failed .*[-/]22", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.I)),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("dms_get_mac_fail", re.compile(r"cnss-daemon Send DMS get mac address failed|Failed to get WLAN MAC address", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready", re.I)),
    ("wlan0_event", re.compile(r"\bwlan0\b", re.I)),
    ("audit_overflow", re.compile(r"audit: kauditd hold queue overflow", re.I)),
    ("ext4_active_namespace_umount", re.compile(r"EXT4-fs .* active namespaces on umount", re.I)),
)

MATRIX_MARKERS = [
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
    "rmt_storage_ready",
    "cnss_diag_start",
    "cnss_diag_netlink",
    "cnss_daemon_start",
    "cnss_daemon_netlink",
    "cnss_daemon_genl_failure",
    "cnss_daemon_binder_ioctl_fail",
    "cnss_daemon_binder_tx_fail",
    "wlfw_start",
    "wlfw_thread",
    "wlan_pd",
    "wlan_pd_ack_180",
    "qmi_server_connected",
    "dms_get_mac_fail",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "sysmon_esoc0",
    "wlan0_event",
]

REGISTRY_MARKERS = [
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "service_notifier_180",
    "service_notifier_74",
    "sysmon_esoc0",
]

CNSS_MARKERS = [
    "cnss_diag_netlink",
    "cnss_daemon_netlink",
    "cnss_daemon_genl_failure",
    "cnss_daemon_binder_ioctl_fail",
    "cnss_daemon_binder_tx_fail",
    "wlfw_start",
    "wlfw_thread",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--v598-manifest", type=Path, default=DEFAULT_V598_MANIFEST)
    parser.add_argument("--v598-dmesg", type=Path, default=DEFAULT_V598_DMESG)
    parser.add_argument("--v598-companion", type=Path, default=DEFAULT_V598_COMPANION)
    parser.add_argument("--v599-manifest", type=Path, default=DEFAULT_V599_MANIFEST)
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


def parse_event_line(raw_line: str, source: str) -> list[Event]:
    line = clean_line(raw_line)
    match = TS_RE.match(line)
    timestamp = float(match.group("ts")) if match else None
    events: list[Event] = []
    for marker, pattern in MARKERS:
        if pattern.search(line):
            events.append(Event(marker, timestamp, line, source))
    return events


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        events.extend(parse_event_line(raw_line, source))
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


def matrix_rows(android: dict[str, Event],
                native: dict[str, Event],
                android_counts: dict[str, int],
                native_counts: dict[str, int]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in MATRIX_MARKERS:
        android_event = android.get(marker)
        native_event = native.get(marker)
        rows.append([
            marker,
            "yes" if android_event else "no",
            "" if android_event is None or android_event.timestamp is None else f"{android_event.timestamp:.6f}",
            str(android_counts.get(marker, 0)),
            "yes" if native_event else "no",
            "" if native_event is None or native_event.timestamp is None else f"{native_event.timestamp:.6f}",
            str(native_counts.get(marker, 0)),
            "missing-native" if android_event and not native_event else ("native-only" if native_event and not android_event else "matched" if android_event else "absent"),
        ])
    return rows


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
        "rows": list(readback.get("rows") or []),
    }


def missing_from_native(android: dict[str, Event], native: dict[str, Event], markers: list[str]) -> list[str]:
    return [marker for marker in markers if has(android, marker) and not has(native, marker)]


def classify(android: dict[str, Event],
             native: dict[str, Event],
             native_counts: dict[str, int],
             readback: dict[str, Any]) -> tuple[str, bool, str, str]:
    registry_missing = missing_from_native(android, native, REGISTRY_MARKERS)
    cnss_missing = missing_from_native(android, native, CNSS_MARKERS)
    lower_ready = has(native, "qrtr_tx") and has(native, "sysmon_modem") and has(native, "service_notifier_180")
    cnss_netlink_ready = has(native, "cnss_diag_netlink") and has(native, "cnss_daemon_netlink")
    cnss_binder_failed = native_counts.get("cnss_daemon_binder_tx_fail", 0) > 0
    readback_empty = readback["service_events"] == 0 and readback["end_of_list"] > 0 and readback["timeouts"] == 0
    if readback["qmi_attempted"]:
        return (
            "v600-readback-qmi-guard-failed",
            False,
            f"unexpected qmi_attempted={readback['qmi_attempted']}",
            "stop and inspect helper before any further Wi-Fi live action",
        )
    if lower_ready and cnss_netlink_ready and cnss_binder_failed and not has(native, "wlfw_start") and readback_empty:
        return (
            "v600-cnss-runtime-and-registry-gap-classified",
            True,
            (
                "native reaches QRTR TX, modem sysmon, service-notifier 180, and CNSS netlink, "
                "but cnss-daemon never reaches wlfw_start and repeats binder -22; "
                f"registry_missing={','.join(registry_missing)}; WLFW service 69 readback is empty"
            ),
            "next gate: bounded service-manager/binder dependency proof around CNSS daemon; still no qcwlanstate, Wi-Fi HAL, scan/connect, or external ping",
        )
    if lower_ready and registry_missing and readback_empty:
        return (
            "v600-service-registry-gap-classified",
            True,
            f"lower modem readiness exists but native is missing registry markers: {','.join(registry_missing)}",
            "next gate: bounded service-registry/sysmon instance probe; no HAL or scan/connect",
        )
    if lower_ready and cnss_missing:
        return (
            "v600-cnss-runtime-gap-classified",
            True,
            f"lower modem readiness exists but CNSS runtime markers missing: {','.join(cnss_missing)}",
            "next gate: inspect CNSS daemon runtime dependencies before HAL/qcwlanstate",
        )
    return (
        "v600-review-required",
        False,
        (
            f"lower_ready={lower_ready} cnss_netlink_ready={cnss_netlink_ready} "
            f"binder_fail_count={native_counts.get('cnss_daemon_binder_tx_fail', 0)} "
            f"readback_events={readback['service_events']} registry_missing={','.join(registry_missing)}"
        ),
        "inspect matrix evidence before choosing a live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v598 = load_json(args.v598_manifest)
    v599 = load_json(args.v599_manifest)
    android_text = read_text(args.android_dmesg)
    native_text = "\n".join([
        read_text(args.v598_dmesg),
        read_text(args.v598_companion),
    ])
    android_events = parse_events(android_text, "android-dmesg")
    native_events = parse_events(native_text, "v598-native")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    android_counts = count_by_marker(android_events)
    native_counts = count_by_marker(native_events)
    readback = readback_summary(v598)
    decision, pass_ok, reason, next_step = classify(android_found, native_found, native_counts, readback)
    rows = matrix_rows(android_found, native_found, android_counts, native_counts)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "v598_manifest": str(repo_path(args.v598_manifest)),
            "v598_dmesg": str(repo_path(args.v598_dmesg)),
            "v598_companion": str(repo_path(args.v598_companion)),
            "v599_manifest": str(repo_path(args.v599_manifest)),
        },
        "v598_decision": v598.get("decision"),
        "v599_decision": v599.get("decision"),
        "matrix_rows": rows,
        "android_deltas_ms": {
            "sysmon_modem_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "sysmon_modem"),
            "service_notifier_180_to_service_notifier_74": delta_ms(android_found, "service_notifier_74", "service_notifier_180"),
            "cnss_daemon_start_to_wlfw_start": delta_ms(android_found, "wlfw_start", "cnss_daemon_start"),
            "wlfw_thread_to_wlan_pd": delta_ms(android_found, "wlan_pd", "wlfw_thread"),
            "wlan_pd_to_qmi_server_connected": delta_ms(android_found, "qmi_server_connected", "wlan_pd"),
            "wlan_pd_to_bdf_regdb": delta_ms(android_found, "bdf_regdb", "wlan_pd"),
        },
        "native_deltas_ms": {
            "sysmon_modem_to_service_notifier_180": delta_ms(native_found, "service_notifier_180", "sysmon_modem"),
            "service_notifier_180_to_wlfw_start": delta_ms(native_found, "wlfw_start", "service_notifier_180"),
            "cnss_daemon_netlink_to_binder_fail": delta_ms(native_found, "cnss_daemon_binder_tx_fail", "cnss_daemon_netlink"),
        },
        "missing_native": {
            "registry": missing_from_native(android_found, native_found, REGISTRY_MARKERS),
            "cnss_runtime": missing_from_native(android_found, native_found, CNSS_MARKERS),
            "wl_fw_path": missing_from_native(android_found, native_found, ["wlan_pd", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0_event"]),
        },
        "native_counts": native_counts,
        "android_counts": android_counts,
        "qrtr_readback": readback,
        "inferences": {
            "service_notifier_180_is_not_sufficient": True,
            "cnss_daemon_started_but_wlfw_start_missing": has(native_found, "cnss_daemon_netlink") and not has(native_found, "wlfw_start"),
            "binder_dependency_is_next_runtime_gap": native_counts.get("cnss_daemon_binder_tx_fail", 0) > 0,
            "wifi_bringup_still_blocked": True,
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
    readback = manifest["qrtr_readback"]
    return "\n".join([
        "# V600 Service-Registry and CNSS Runtime Matrix",
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
        markdown_table(["delta", "ms"], [[key, value] for key, value in manifest["android_deltas_ms"].items()]),
        "",
        "## Native Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, value] for key, value in manifest["native_deltas_ms"].items()]),
        "",
        "## Matrix",
        "",
        markdown_table(["marker", "android", "android_ts", "android_count", "native", "native_ts", "native_count", "status"], manifest["matrix_rows"]),
        "",
        "## Missing Native",
        "",
        markdown_table(["group", "markers"], [[key, ", ".join(value)] for key, value in manifest["missing_native"].items()]),
        "",
        "## WLFW QRTR Readback",
        "",
        f"- result: `{readback.get('result')}`",
        f"- service_events: `{readback.get('service_events')}`",
        f"- end_of_list: `{readback.get('end_of_list')}`",
        f"- timeouts: `{readback.get('timeouts')}`",
        f"- qmi_attempted: `{readback.get('qmi_attempted')}`",
        "",
        "## Inferences",
        "",
        "- Native `service-notifier 180` is necessary but not sufficient for WLAN-PD/WLFW readiness.",
        "- Native `cnss-daemon` reaches netlink setup but does not reach `wlfw_start`.",
        "- The observed binder `-22` loop is the next runtime dependency to prove or remove.",
        "- Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP, routing, and external ping remain blocked.",
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
