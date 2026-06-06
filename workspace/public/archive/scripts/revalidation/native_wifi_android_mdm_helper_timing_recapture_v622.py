#!/usr/bin/env python3
"""V622 Android same-boot MDM helper timing recapture.

This collector runs only while Android ADB is available. It captures Android
property boottimes and lower dmesg markers from the same boot so V621's
cross-boot `vendor.mdm_helper` timing gap can be closed. It is read-only: no
Wi-Fi enable, scan, connect, credentials, DHCP, route changes, sysfs writes,
daemon starts, HAL starts, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from dataclasses import asdict
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
from native_wifi_qmi_publication_precondition_v610 import (
    TIMELINE_MARKERS,
    count_by_marker,
    deltas,
    first_by_marker,
    parse_events,
    parse_key_values,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v622-android-mdm-helper-timing-recapture")
DEFAULT_TIMEOUT = 45.0
BOOTTIME_KEYS = [
    "ro.boottime.vendor.mdm_launcher",
    "ro.boottime.vendor.mdm_helper",
    "ro.boottime.vendor.qrtr-ns",
    "ro.boottime.vendor.rmt_storage",
    "ro.boottime.vendor.tftp_server",
    "ro.boottime.vendor.pd_mapper",
    "ro.boottime.cnss_diag",
    "ro.boottime.cnss-daemon",
]
PROP_KEYS = [
    "sys.boot_completed",
    "ro.baseband",
    "ro.boot.baseband",
    "init.svc.vendor.mdm_launcher",
    "init.svc.vendor.mdm_helper",
    "init.svc.vendor.qrtr-ns",
    "init.svc.vendor.rmt_storage",
    "init.svc.vendor.tftp_server",
    "init.svc.vendor.pd_mapper",
    "init.svc.cnss_diag",
    "init.svc.cnss-daemon",
    "persist.vendor.mdm_helper.fail_action",
    *BOOTTIME_KEYS,
]
LOWER_DMESG_PATTERN = (
    "qrtr: Modem QMI Readiness|sysmon-qmi|service-notifier|wlan_pd|"
    "icnss_qmi: QMI Server Connected|BDF file|regdb\\.bin|bdwlan\\.bin|"
    "WLAN FW is ready|wlan0|servloc|service_locator|QIPCRTR|rpmsg|"
    "rmt_storage|tftp|pd-mapper|cnss-daemon|cnss_diag"
)
FORBIDDEN_ACTIONS = [
    "Wi-Fi enable/scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs write or QMI payload",
    "native daemon/service-manager/Wi-Fi HAL start",
    "boot image or partition write",
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


def ns_to_ms(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    try:
        return round(int(raw_value) / 1_000_000.0, 3)
    except ValueError:
        return None


def event_ms(first: dict[str, Any], marker: str) -> float | None:
    event = first.get(marker)
    if event is None:
        return None
    timestamp = event.timestamp
    return round(timestamp * 1000.0, 3) if timestamp is not None else None


def ms_delta(newer: float | None, older: float | None) -> float | None:
    if newer is None or older is None:
        return None
    return round(newer - older, 3)


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def prop_command() -> str:
    props = " ".join(PROP_KEYS)
    return "; ".join([
        "echo A90_V622_PROPS_BEGIN",
        f"for p in {props}; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        "echo A90_V622_PROPS_END",
    ])


def dmesg_command() -> str:
    return f"dmesg 2>&1 | grep -Ei {LOWER_DMESG_PATTERN!r} | tail -n 800 || true"


def unfiltered_tail_command() -> str:
    return "dmesg 2>&1 | tail -n 1200 || true"


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    captures.append(capture_shell(args, store, "same-boot-props", prop_command(), 15.0))
    captures.append(capture_shell(args, store, "dmesg-lower-surface-tail", dmesg_command(), 30.0))
    captures.append(capture_shell(args, store, "dmesg-unfiltered-tail", unfiltered_tail_command(), 30.0))
    return captures


def capture_text(captures: list[Capture], *names: str) -> str:
    wanted = set(names)
    return "\n".join(capture.text for capture in captures if capture.name in wanted)


def timing_rows(timing: dict[str, float | None]) -> list[list[str]]:
    return [[key, "" if value is None else str(value)] for key, value in timing.items()]


def marker_rows(counts: dict[str, int], first: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE_MARKERS:
        event = first.get(marker)
        timestamp = "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}"
        rows.append([marker, str(counts.get(marker, 0)), timestamp])
    return rows


def summarize(captures: list[Capture], store: EvidenceStore) -> dict[str, Any]:
    props = parse_key_values(capture_text(captures, "same-boot-props"))
    dmesg_text = capture_text(captures, "dmesg-lower-surface-tail", "dmesg-unfiltered-tail")
    events = parse_events(dmesg_text, "android-v622")
    first = first_by_marker(events)
    counts = count_by_marker(events)
    timing: dict[str, float | None] = {
        "mdm_launcher_boottime_ms": ns_to_ms(props.get("ro.boottime.vendor.mdm_launcher")),
        "mdm_helper_boottime_ms": ns_to_ms(props.get("ro.boottime.vendor.mdm_helper")),
        "qrtr_ns_boottime_ms": ns_to_ms(props.get("ro.boottime.vendor.qrtr-ns")),
        "rmt_storage_boottime_ms": ns_to_ms(props.get("ro.boottime.vendor.rmt_storage")),
        "tftp_server_boottime_ms": ns_to_ms(props.get("ro.boottime.vendor.tftp_server")),
        "pd_mapper_boottime_ms": ns_to_ms(props.get("ro.boottime.vendor.pd_mapper")),
        "cnss_diag_boottime_ms": ns_to_ms(props.get("ro.boottime.cnss_diag")),
        "cnss_daemon_boottime_ms": ns_to_ms(props.get("ro.boottime.cnss-daemon")),
        "service_notifier_180_ms": event_ms(first, "service_notifier_180"),
        "service_notifier_74_ms": event_ms(first, "service_notifier_74"),
        "wlan_pd_ms": event_ms(first, "wlan_pd"),
        "sysmon_modem_ms": event_ms(first, "sysmon_modem"),
        "sysmon_esoc0_ms": event_ms(first, "sysmon_esoc0"),
    }
    timing.update({
        "launcher_to_service_notifier_180_ms": ms_delta(timing["service_notifier_180_ms"], timing["mdm_launcher_boottime_ms"]),
        "helper_to_service_notifier_180_ms": ms_delta(timing["service_notifier_180_ms"], timing["mdm_helper_boottime_ms"]),
        "cnss_diag_to_service_notifier_180_ms": ms_delta(timing["service_notifier_180_ms"], timing["cnss_diag_boottime_ms"]),
        "service_notifier_180_to_wlan_pd_ms": ms_delta(timing["wlan_pd_ms"], timing["service_notifier_180_ms"]),
        "service_notifier_180_to_sysmon_esoc0_ms": ms_delta(timing["sysmon_esoc0_ms"], timing["service_notifier_180_ms"]),
    })
    normalized_props = "\n".join(f"{key}={props.get(key, '')}" for key in PROP_KEYS).rstrip() + "\n"
    store.write_text("android-mdm-helper-same-boot-props.txt", normalized_props)
    return {
        "boot_completed": props.get("sys.boot_completed") == "1",
        "all_commands_ok": all(capture.ok for capture in captures),
        "props": {key: props.get(key, "") for key in PROP_KEYS},
        "event_count": len(events),
        "counts": {marker: counts.get(marker, 0) for marker in TIMELINE_MARKERS},
        "first": {marker: asdict(event) for marker, event in first.items() if marker in TIMELINE_MARKERS},
        "deltas_ms": deltas(first),
        "timing": timing,
        "has_mdm_helper_boottime": timing["mdm_helper_boottime_ms"] is not None,
        "has_mdm_launcher_boottime": timing["mdm_launcher_boottime_ms"] is not None,
        "has_service_notifier_180": counts.get("service_notifier_180", 0) > 0,
        "has_service_notifier_pair": counts.get("service_notifier_180", 0) > 0 and counts.get("service_notifier_74", 0) > 0,
        "has_wlan_pd": counts.get("wlan_pd", 0) > 0,
        "has_sysmon_esoc0": counts.get("sysmon_esoc0", 0) > 0,
    }


def decide(args: argparse.Namespace,
           devices: dict[str, Any],
           captures: list[Capture],
           summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v622-android-mdm-helper-timing-plan-ready",
            True,
            "plan-only; no adb command executed",
            "boot Android or run approved handoff, then execute V622 read-only collector",
        )
    if devices["device_count"] == 0:
        return (
            "v622-android-adb-unavailable",
            False,
            "no Android ADB device is currently visible",
            "run Android handoff before V622 live collection",
        )
    if not selected_device_available(args, devices):
        return (
            "v622-android-adb-selection-needed",
            False,
            f"device_count={devices['device_count']}",
            "rerun with --serial",
        )
    if args.command == "preflight":
        return (
            "v622-android-mdm-helper-timing-preflight-ready",
            True,
            "one Android ADB device is visible",
            "run V622 Android same-boot timing recapture",
        )
    if not captures:
        return "v622-capture-too-filtered", False, "run command produced no captures", "inspect collector failure"
    if not summary.get("boot_completed"):
        return (
            "v622-android-not-boot-complete",
            False,
            "Android ADB is visible but sys.boot_completed=1 was not captured",
            "wait for Android boot-complete and rerun V622",
        )
    if not summary.get("has_mdm_helper_boottime") or not summary.get("has_service_notifier_180"):
        return (
            "v622-same-boot-evidence-gap",
            False,
            "same-boot capture lacks mdm_helper boottime or service-notifier 180 dmesg marker",
            "recapture with root ADB and broader read-only dmesg/property access",
        )

    timing = summary["timing"]
    helper_delta = timing.get("helper_to_service_notifier_180_ms")
    launcher_delta = timing.get("launcher_to_service_notifier_180_ms")
    if helper_delta is not None and helper_delta >= 0:
        return (
            "v622-mdm-helper-pre-notifier-candidate",
            True,
            f"same-boot mdm_helper starts {helper_delta}ms before service-notifier 180",
            "design bounded native mdm_helper start-only proof; still no CNSS/HAL/scan/connect",
        )
    if launcher_delta is not None and launcher_delta >= 0:
        return (
            "v622-mdm-launcher-window-not-helper-classified",
            True,
            (
                f"same-boot mdm_launcher starts {launcher_delta}ms before service-notifier 180, "
                f"but mdm_helper starts {abs(helper_delta) if helper_delta is not None else 'unknown'}ms after it"
            ),
            "classify init.mdm.sh/property side effects before any native helper start-only proof",
        )
    return (
        "v622-mdm-helper-post-notifier-not-root-trigger",
        True,
        "same-boot mdm_helper and mdm_launcher boottimes are not before service-notifier 180",
        "do not test mdm_helper as first-notifier trigger; focus on earlier Android services or kernel publication state",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    summary = manifest.get("android_summary") or {}
    timing = summary.get("timing") or {}
    counts = summary.get("counts") or {}
    first_payload = summary.get("first") or {}
    first = {
        key: type("EventProxy", (), {"timestamp": value.get("timestamp")})()
        for key, value in first_payload.items()
        if isinstance(value, dict)
    }
    capture_rows = [[item["name"], item["status"], item["rc"], f"{item['duration_sec']:.3f}s", item["file"]] for item in captures]
    prop_rows = [[key, (summary.get("props") or {}).get(key, "")] for key in PROP_KEYS]
    return "\n".join([
        "# V622 Android MDM Helper Timing Recapture",
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
        "## Timing",
        "",
        markdown_table(["key", "ms"], timing_rows(timing)),
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count", "first_s"], marker_rows(counts, first)),
        "",
        "## Properties",
        "",
        markdown_table(["key", "value"], prop_rows),
        "",
        "## Captures",
        "",
        markdown_table(["capture", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["none", "-", "-", "-", "-"]]),
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
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
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
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
