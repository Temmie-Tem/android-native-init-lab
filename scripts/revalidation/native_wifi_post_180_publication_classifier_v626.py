#!/usr/bin/env python3
"""V626 host-only post-180 service publication classifier.

This compares Android V622 against the fresh native V625 replay. It does not
contact the device, write sysfs, start daemons, start service-manager, start
Wi-Fi HAL, scan, connect, use credentials, run DHCP, change routes, or ping
externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v626-post-180-publication-classifier")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_NATIVE_V625_MANIFEST = Path("tmp/wifi/v625-fresh-v598-class-live/manifest.json")
DEFAULT_NATIVE_V625_DMESG = Path("tmp/wifi/v625-fresh-v598-class-live/native/dmesg-delta.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

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
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_binder_failure", re.compile(r"cnss-daemon.*binder: .*transaction failed|cnss-daemon.*ioctl .* returned -22", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request\(\) called for already added request|Reference count mismatch", re.I)),
)

TIMELINE = [
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "service_notifier_180",
    "service_notifier_74",
    "rmt_storage_ready",
    "rmt_storage_open",
    "cnss_diag_netlink",
    "cnss_daemon_netlink",
    "cnss_daemon_binder_failure",
    "wlfw_start",
    "wlan_pd",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
    "sysmon_esoc0",
    "kernel_warning",
]

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


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
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--native-v625-manifest", type=Path, default=DEFAULT_NATIVE_V625_MANIFEST)
    parser.add_argument("--native-v625-dmesg", type=Path, default=DEFAULT_NATIVE_V625_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


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


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"exists": False, "path": str(repo_path(path))}
    data = json.loads(text)
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(repo_path(path)))
        return data
    return {"exists": True, "path": str(repo_path(path)), "value": data}


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        for marker, pattern in MARKERS:
            if pattern.search(line):
                events.append(Event(marker, line_time(line), line, source))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    found: dict[str, Event] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def count_by_marker(events: list[Event]) -> dict[str, int]:
    counts = {marker: 0 for marker in TIMELINE}
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


def first_line(found: dict[str, Event], marker: str) -> str:
    event = found.get(marker)
    return event.line if event else "missing"


def android_first_events(android_manifest: dict[str, Any]) -> list[Event]:
    first = ((android_manifest.get("android_summary") or {}).get("first") or {})
    events: list[Event] = []
    for marker, payload in first.items():
        if not isinstance(payload, dict):
            continue
        timestamp = payload.get("timestamp")
        events.append(Event(
            str(marker),
            float(timestamp) if isinstance(timestamp, int | float) else None,
            str(payload.get("line", "")),
            "android-v622",
        ))
    return events


def timeline_rows(found: dict[str, Event], counts: dict[str, int]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE:
        event = found.get(marker)
        rows.append([
            marker,
            str(counts.get(marker, 0)),
            "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}",
            "missing" if event is None else event.line,
        ])
    return rows


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android"]
    native = manifest["native"]
    return [
        [
            "service-notifier 180",
            "reproduced in native",
            f"android={android['counts'].get('service_notifier_180', 0)} native={native['counts'].get('service_notifier_180', 0)}",
            "safe partial positive is stable enough for next lower gate",
        ],
        [
            "service-notifier 74",
            "missing in native",
            (
                f"android={android['counts'].get('service_notifier_74', 0)} "
                f"native={native['counts'].get('service_notifier_74', 0)} "
                f"android_180_to_74={android['deltas_ms'].get('service_notifier_180_to_service_notifier_74')}ms"
            ),
            "target post-180 service 74 publication before HAL/connect",
        ],
        [
            "WLAN-PD",
            "missing in native",
            (
                f"android={android['counts'].get('wlan_pd', 0)} native={native['counts'].get('wlan_pd', 0)} "
                f"android_180_to_wlan_pd={android['deltas_ms'].get('service_notifier_180_to_wlan_pd')}ms"
            ),
            "do not start Wi-Fi HAL until WLAN-PD or WLFW advances",
        ],
        [
            "CNSS timing",
            "not root for service 74",
            (
                f"android_180_to_74={android['deltas_ms'].get('service_notifier_180_to_service_notifier_74')}ms; "
                f"android_180_to_cnss_diag={android['deltas_ms'].get('service_notifier_180_to_cnss_diag_netlink')}ms; "
                f"native_180_to_cnss_diag={native['deltas_ms'].get('service_notifier_180_to_cnss_diag_netlink')}ms"
            ),
            "service 74 appears before Android CNSS userspace netlink",
        ],
        [
            "WLFW QRTR readback",
            "clean empty",
            (
                f"service_events={native['qrtr_readback'].get('service_events')} "
                f"end_of_list={native['qrtr_readback'].get('end_of_list')} "
                f"timeouts={native['qrtr_readback'].get('timeouts')} qmi_attempted={native['qrtr_readback'].get('qmi_attempted')}"
            ),
            "missing WLFW is publication absence, not readback timeout",
        ],
        [
            "mdm3 state",
            "still unresolved",
            f"native_mss={native['mss_after_companion']} native_mdm3={native['mdm3_after_companion']}",
            "keep mdm3/WLAN-PD lower publication as candidate surface",
        ],
        [
            "safety",
            "clean",
            f"native_kernel_warning={native['counts'].get('kernel_warning', 0)} wifi_bringup={manifest['native_v625'].get('wifi_bringup_executed')}",
            "continue bounded observer gates only",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    android = manifest["android"]
    native = manifest["native"]
    android_has_pair = android["counts"].get("service_notifier_180", 0) > 0 and android["counts"].get("service_notifier_74", 0) > 0
    native_has_180_only = native["counts"].get("service_notifier_180", 0) > 0 and native["counts"].get("service_notifier_74", 0) == 0
    native_clean = native["counts"].get("kernel_warning", 0) == 0
    readback_empty = native["qrtr_readback"].get("service_events") == 0 and native["qrtr_readback"].get("end_of_list") == 2
    android_74_before_cnss = (
        android["deltas_ms"].get("service_notifier_180_to_service_notifier_74") is not None
        and android["deltas_ms"].get("service_notifier_180_to_cnss_diag_netlink") is not None
        and android["deltas_ms"]["service_notifier_180_to_service_notifier_74"] < android["deltas_ms"]["service_notifier_180_to_cnss_diag_netlink"]
    )
    if android_has_pair and native_has_180_only and native_clean and readback_empty and android_74_before_cnss:
        return (
            "v626-post-180-service74-publication-gap-classified",
            True,
            (
                "V625 reproduces warning-free native service-notifier 180, but Android publishes service 74 "
                "6.561ms later and before CNSS userspace netlink while native never publishes 74/WLAN-PD/WLFW service 69."
            ),
            "V627 should implement a bounded post-180 service-74/WLAN-PD observer without DSP boot-node writes, service-manager, HAL, scan, connect, credentials, DHCP, routes, or external ping",
        )
    return (
        "v626-post-180-publication-evidence-gap",
        False,
        (
            f"android_has_pair={android_has_pair} native_has_180_only={native_has_180_only} "
            f"native_clean={native_clean} readback_empty={readback_empty} android_74_before_cnss={android_74_before_cnss}"
        ),
        "refresh V622/V625 evidence before another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_manifest = load_json(args.android_v622_manifest)
    native_manifest = load_json(args.native_v625_manifest)
    native_dmesg = read_text(args.native_v625_dmesg)
    android_events = android_first_events(android_manifest)
    native_events = parse_events(native_dmesg, "native-v625")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    android_summary = android_manifest.get("android_summary") or {}
    native_live = native_manifest.get("live") or {}
    native_marker_counts = ((native_live.get("markers") or {}).get("counts") or {})
    native_counts = count_by_marker(native_events)
    if native_marker_counts.get("service_notifier", 0) and not native_counts.get("service_notifier_180", 0):
        native_counts["service_notifier_180"] = int(native_marker_counts.get("service_notifier", 0))
    if native_marker_counts.get("kernel_warning", 0):
        native_counts["kernel_warning"] = int(native_marker_counts.get("kernel_warning", 0))
    android_counts = {**count_by_marker(android_events), **(android_summary.get("counts") or {})}
    android_deltas = dict(android_summary.get("deltas_ms") or {})
    android_deltas.update({
        "service_notifier_180_to_cnss_diag_netlink": delta_ms(android_found, "cnss_diag_netlink", "service_notifier_180"),
        "service_notifier_180_to_cnss_daemon_netlink": delta_ms(android_found, "cnss_daemon_netlink", "service_notifier_180"),
    })
    native_deltas = {
        "service_notifier_180_to_service_notifier_74": delta_ms(native_found, "service_notifier_74", "service_notifier_180"),
        "service_notifier_180_to_cnss_diag_netlink": delta_ms(native_found, "cnss_diag_netlink", "service_notifier_180"),
        "service_notifier_180_to_cnss_daemon_netlink": delta_ms(native_found, "cnss_daemon_netlink", "service_notifier_180"),
        "service_notifier_180_to_binder_failure": delta_ms(native_found, "cnss_daemon_binder_failure", "service_notifier_180"),
        "rmt_storage_ready_to_service_notifier_180": delta_ms(native_found, "service_notifier_180", "rmt_storage_ready"),
    }
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "android_v622_manifest": str(repo_path(args.android_v622_manifest)),
            "native_v625_manifest": str(repo_path(args.native_v625_manifest)),
            "native_v625_dmesg": str(repo_path(args.native_v625_dmesg)),
        },
        "android_v622": {
            "decision": android_manifest.get("decision"),
            "pass": android_manifest.get("pass"),
        },
        "native_v625": {
            "decision": native_manifest.get("decision"),
            "pass": native_manifest.get("pass"),
            "wifi_bringup_executed": native_manifest.get("wifi_bringup_executed"),
            "wifi_hal_start_executed": native_manifest.get("wifi_hal_start_executed"),
            "external_ping_executed": native_manifest.get("external_ping_executed"),
        },
        "android": {
            "counts": android_counts,
            "deltas_ms": android_deltas,
            "timeline_rows": timeline_rows(android_found, android_counts),
            "first_lines": {
                marker: first_line(android_found, marker)
                for marker in ("service_notifier_180", "service_notifier_74", "wlfw_start", "wlan_pd", "qmi_server_connected", "wlan0")
            },
        },
        "native": {
            "counts": native_counts,
            "deltas_ms": native_deltas,
            "qrtr_readback": native_live.get("qrtr_readback") or {},
            "mss_after_companion": native_live.get("mss_after_companion"),
            "mdm3_after_companion": native_live.get("mdm3_after_companion"),
            "timeline_rows": timeline_rows(native_found, native_counts),
            "first_lines": {
                marker: first_line(native_found, marker)
                for marker in ("service_notifier_180", "service_notifier_74", "cnss_diag_netlink", "cnss_daemon_netlink", "cnss_daemon_binder_failure")
            },
        },
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v626-post-180-publication-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V626 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["evidence_rows"] = evidence_rows(manifest)
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V626 Post-180 Publication Classifier",
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
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Android First Lines",
        "",
        markdown_table(["marker", "line"], [[key, value] for key, value in manifest["android"]["first_lines"].items()]),
        "",
        "## Native First Lines",
        "",
        markdown_table(["marker", "line"], [[key, value] for key, value in manifest["native"]["first_lines"].items()]),
        "",
        "## Android Deltas",
        "",
        markdown_table(["key", "ms"], [[key, str(value)] for key, value in manifest["android"]["deltas_ms"].items() if "service_notifier_180" in key]),
        "",
        "## Native Deltas",
        "",
        markdown_table(["key", "ms"], [[key, str(value)] for key, value in manifest["native"]["deltas_ms"].items()]),
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
