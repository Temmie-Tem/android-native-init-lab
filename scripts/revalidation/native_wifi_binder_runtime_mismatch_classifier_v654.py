#!/usr/bin/env python3
"""V654 host-only binder/runtime mismatch classifier.

This classifier compares V653 service-74-gated service-manager evidence with
Android V649/V651 references. It does not contact the device, write sysfs,
start daemons, start service-manager, start Wi-Fi HAL, scan, connect, use
credentials, run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v654-binder-runtime-mismatch-classifier")
DEFAULT_V651_MANIFEST = Path("tmp/wifi/v651-cnss-wlfw-continuation/manifest.json")
DEFAULT_V652_MANIFEST = Path("tmp/wifi/v652-service74-binder-parity-live-20260523-082200/manifest.json")
DEFAULT_V653_MANIFEST = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json")
DEFAULT_V653_DMESG = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/native/dmesg-delta.txt")
DEFAULT_V653_HELPER = Path(
    "tmp/wifi/v653-service74-gated-live-20260523-085337/native/companion-start-only-with-holder.txt"
)
DEFAULT_ANDROID_AUDIO_DMESG = Path("tmp/wifi/v649-final-live-replay-classifier/android/replay/dmesg-audio-wifi-tail.txt")
DEFAULT_ANDROID_UNFILTERED_DMESG = Path("tmp/wifi/v649-final-live-replay-classifier/android/replay/dmesg-unfiltered-tail.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_genl_fail_continue", re.compile(r"cnss-daemon Failed to init genl.*continue", re.I)),
    ("cnss_wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|\bwlfw_start\b", re.I)),
    ("cnss_wlfw_service_request", re.compile(r"cnss-daemon wlfw_service_request", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("servicemanager_binder_ioctl_unsupported", re.compile(r"\bservicemanager:.*binder:.*ioctl .* returned -22", re.I)),
    ("hwservicemanager_binder_ioctl_unsupported", re.compile(r"\bhwservicemanage:.*binder:.*ioctl .* returned -22", re.I)),
    ("vndservicemanager_binder_ioctl_unsupported", re.compile(r"\bvndservicemanag:.*binder:.*ioctl .* returned -22", re.I)),
    ("generic_binder_ioctl_unsupported", re.compile(r"binder: .*ioctl .* returned -22", re.I)),
    ("cnss_binder_ioctl_unsupported", re.compile(r"cnss-daemon.*binder:.*ioctl .* returned -22", re.I)),
    ("cnss_binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
    ("generic_binder_transaction_failed", re.compile(r"binder: .*transaction failed .*?-22", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put", re.I)),
)

TIMELINE = (
    "service_notifier_180",
    "service_notifier_74",
    "cnss_daemon_netlink",
    "cnss_daemon_cld80211",
    "cnss_genl_fail_continue",
    "cnss_wlfw_start",
    "cnss_wlfw_service_request",
    "wlan_pd",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
    "servicemanager_binder_ioctl_unsupported",
    "hwservicemanager_binder_ioctl_unsupported",
    "vndservicemanager_binder_ioctl_unsupported",
    "generic_binder_ioctl_unsupported",
    "cnss_binder_ioctl_unsupported",
    "cnss_binder_transaction_failed",
    "generic_binder_transaction_failed",
    "kernel_warning",
)

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)

SERVICE_CHILDREN = ("servicemanager", "hwservicemanager", "vndservicemanager")


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
    parser.add_argument("--v651-manifest", type=Path, default=DEFAULT_V651_MANIFEST)
    parser.add_argument("--v652-manifest", type=Path, default=DEFAULT_V652_MANIFEST)
    parser.add_argument("--v653-manifest", type=Path, default=DEFAULT_V653_MANIFEST)
    parser.add_argument("--v653-dmesg", type=Path, default=DEFAULT_V653_DMESG)
    parser.add_argument("--v653-helper", type=Path, default=DEFAULT_V653_HELPER)
    parser.add_argument("--android-audio-dmesg", type=Path, default=DEFAULT_ANDROID_AUDIO_DMESG)
    parser.add_argument("--android-unfiltered-dmesg", type=Path, default=DEFAULT_ANDROID_UNFILTERED_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


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
        for marker, pattern in MARKERS:
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
    rows = []
    for marker in TIMELINE:
        event = first.get(marker)
        rows.append([
            marker,
            str(counts.get(marker, 0)),
            "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}",
            "missing" if event is None else event.line,
        ])
    return {
        "counts": counts,
        "first_times": {marker: event_time(first, marker) for marker in TIMELINE},
        "first_lines": {
            marker: first.get(marker, Event(marker, None, "missing", "")).line for marker in TIMELINE
        },
        "deltas_ms": {
            "service74_to_cnss_daemon_netlink": delta_ms(first, "cnss_daemon_netlink", "service_notifier_74"),
            "service74_to_servicemanager_ioctl": delta_ms(
                first, "servicemanager_binder_ioctl_unsupported", "service_notifier_74"
            ),
            "service74_to_cnss_binder_transaction": delta_ms(
                first, "cnss_binder_transaction_failed", "service_notifier_74"
            ),
            "cnss_daemon_netlink_to_servicemanager_ioctl": delta_ms(
                first, "servicemanager_binder_ioctl_unsupported", "cnss_daemon_netlink"
            ),
            "cnss_daemon_netlink_to_cnss_binder_transaction": delta_ms(
                first, "cnss_binder_transaction_failed", "cnss_daemon_netlink"
            ),
            "servicemanager_ioctl_to_cnss_binder_transaction": delta_ms(
                first, "cnss_binder_transaction_failed", "servicemanager_binder_ioctl_unsupported"
            ),
            "cnss_daemon_netlink_to_genl_fail": delta_ms(first, "cnss_genl_fail_continue", "cnss_daemon_netlink"),
            "cnss_daemon_netlink_to_wlfw_start": delta_ms(first, "cnss_wlfw_start", "cnss_daemon_netlink"),
            "genl_fail_to_wlfw_start": delta_ms(first, "cnss_wlfw_start", "cnss_genl_fail_continue"),
            "wlfw_start_to_wlan_pd": delta_ms(first, "wlan_pd", "cnss_wlfw_start"),
        },
        "timeline_rows": rows,
    }


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(clean_line(raw_line))
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def bool_key(keys: dict[str, str], key: str) -> bool:
    return keys.get(key) == "1"


def int_key(keys: dict[str, str], key: str) -> int | None:
    try:
        return int(keys[key])
    except (KeyError, ValueError):
        return None


def service_manager_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for child in SERVICE_CHILDREN:
        rows.append([
            child,
            keys.get(f"wifi_companion_start.child.{child}.start_order", ""),
            keys.get(f"wifi_companion_start.child.{child}.observable", ""),
            keys.get(f"wifi_companion_start.child.{child}.exited", ""),
            keys.get(f"wifi_companion_start.child.{child}.signal", ""),
            keys.get(f"wifi_companion_start.child.{child}.postflight_safe", ""),
            keys.get(f"wifi_hal_composite_child.{child}.selinux.exec", ""),
            keys.get(f"wifi_hal_composite_start.child.{child}.target", ""),
        ])
    return rows


def binder_surface_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for dev in ("binder", "hwbinder", "vndbinder"):
        rows.append([
            f"/dev/{dev}",
            keys.get(f"context.dev_{dev}.exists", ""),
            keys.get(f"context.dev_{dev}.access_r", ""),
            keys.get(f"context.dev_{dev}.mode", ""),
            keys.get(f"context.dev_{dev}.rdev", ""),
        ])
    return rows


def process_surface(keys: dict[str, str]) -> dict[str, Any]:
    cnss_order = int_key(keys, "wifi_companion_start.child.cnss_daemon.start_order")
    vnd_order = int_key(keys, "wifi_companion_start.child.vndservicemanager.start_order")
    return {
        "order": keys.get("wifi_companion_start.order", ""),
        "cnss_daemon_start_order": cnss_order,
        "vndservicemanager_start_order": vnd_order,
        "cnss_daemon_before_vndservicemanager": (
            cnss_order is not None and vnd_order is not None and cnss_order < vnd_order
        ),
        "cnss_daemon_vndbinder_fd": "/dev/vndbinder" in keys.get(
            "capture.wifi_hal_composite_cnss_daemon.fd_links.entry_15.target", ""
        ),
        "vndservicemanager_vndbinder_fd": "/dev/vndbinder" in keys.get(
            "capture.wifi_hal_composite_vndservicemanager.fd_links.entry_03.target", ""
        ),
        "property_service_shim_started": keys.get("wifi_hal_composite_start.property_service_shim.started", ""),
        "property_service_shim_mode": keys.get("wifi_hal_composite_start.property_service_shim.mode", ""),
        "target_profile": keys.get("target_profile", ""),
        "linkerconfig_mode": keys.get("linkerconfig_mode", ""),
        "service74_gate_status": keys.get("wifi_companion_start.service74_gate.status", ""),
        "service74_gate_wait_ms": keys.get("wifi_companion_start.service74_gate.wait_ms", ""),
        "service74_gate_seen": keys.get("wifi_companion_start.service74_gate.seen", ""),
        "service_manager_start_order_rows": service_manager_rows(keys),
        "binder_surface_rows": binder_surface_rows(keys),
    }


def rows_to_dicts(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    return [dict(zip(headers, row, strict=True)) for row in rows]


def matrix_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in (
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_genl_fail_continue",
        "cnss_wlfw_start",
        "wlan_pd",
        "qmi_server_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "servicemanager_binder_ioctl_unsupported",
        "hwservicemanager_binder_ioctl_unsupported",
        "generic_binder_ioctl_unsupported",
        "cnss_binder_transaction_failed",
    ):
        rows.append([
            marker,
            str(android["counts"].get(marker, 0)),
            str(android["first_times"].get(marker)),
            str(native["counts"].get(marker, 0)),
            str(native["first_times"].get(marker)),
        ])
    return rows


def build_checks(v651: dict[str, Any],
                 v652: dict[str, Any],
                 v653: dict[str, Any],
                 android: dict[str, Any],
                 native: dict[str, Any],
                 surface: dict[str, Any],
                 keys: dict[str, str]) -> dict[str, bool]:
    service_manager_ok = all(
        bool_key(keys, f"wifi_companion_start.child.{child}.observable")
        and bool_key(keys, f"wifi_companion_start.child.{child}.postflight_safe")
        for child in SERVICE_CHILDREN
    )
    return {
        "v651_binder_blocker_classified": v651.get("decision")
        == "v651-cnss-daemon-binder-blocks-wlfw-continuation",
        "v652_delayed_service_manager_regressed_service74": v652.get("decision") == "v652-service74-regressed",
        "v653_service74_gate_preserved": surface["service74_gate_status"] == "open"
        and native["counts"].get("service_notifier_74", 0) > 0,
        "v653_service_manager_trio_observable": service_manager_ok,
        "v653_cnss_reaches_vndbinder": bool(surface["cnss_daemon_vndbinder_fd"]),
        "v653_vndservicemanager_reaches_vndbinder": bool(surface["vndservicemanager_vndbinder_fd"]),
        "v653_binder_devnodes_present": all(row[1] == "1" and row[2] == "1" for row in surface["binder_surface_rows"]),
        "v653_selinux_exec_contexts_set": all(
            keys.get(f"wifi_hal_composite_child.{child}.selinux_exec.ok") == "1"
            for child in ("cnss_daemon", "servicemanager", "hwservicemanager", "vndservicemanager")
        ),
        "android_cnss_reaches_wlfw": android["counts"].get("cnss_wlfw_start", 0) > 0,
        "android_cnss_binder_transaction_absent": android["counts"].get("cnss_binder_transaction_failed", 0) == 0,
        "android_generic_binder_ioctl_nonfatal": android["counts"].get("generic_binder_ioctl_unsupported", 0) > 0
        and android["counts"].get("cnss_wlfw_start", 0) > 0,
        "native_cnss_binder_transaction_blocks_wlfw": native["counts"].get("cnss_binder_transaction_failed", 0) > 0
        and native["counts"].get("cnss_wlfw_start", 0) == 0,
        "cnss_started_before_vndservicemanager": bool(surface["cnss_daemon_before_vndservicemanager"]),
        "vndservicemanager_readiness_unproven": (
            bool(surface["vndservicemanager_vndbinder_fd"])
            and "vndservicemanager_ready" not in keys
            and "vndservicemanager_list" not in keys
        ),
    }


def inference_rows(manifest: dict[str, Any]) -> list[list[str]]:
    checks = manifest["checks"]
    native = manifest["native_v653"]
    android = manifest["android_v649"]
    surface = manifest["v653_process_surface"]
    return [
        [
            "service74 gate",
            "working",
            f"status={surface['service74_gate_status']}; wait_ms={surface['service74_gate_wait_ms']}; native_count={native['counts'].get('service_notifier_74', 0)}",
            "preserve this gate in the next live proof",
        ],
        [
            "binder device namespace",
            "unlikely root cause",
            f"devnodes_present={checks['v653_binder_devnodes_present']}; cnss_fd_vnd={surface['cnss_daemon_vndbinder_fd']}; vndsm_fd_vnd={surface['vndservicemanager_vndbinder_fd']}",
            "do not spend the next live cycle on devnode remount alone",
        ],
        [
            "SELinux exec contexts",
            "unlikely root cause",
            f"contexts_set={checks['v653_selinux_exec_contexts_set']}",
            "retain V490/policy setup, but classify binder ordering first",
        ],
        [
            "generic binder ioctl -22",
            "non-fatal class",
            f"android_generic_ioctl={android['counts'].get('generic_binder_ioctl_unsupported', 0)}; android_wlfw={android['counts'].get('cnss_wlfw_start', 0)}; native_manager_ioctl={native['counts'].get('servicemanager_binder_ioctl_unsupported', 0) + native['counts'].get('hwservicemanager_binder_ioctl_unsupported', 0)}",
            "do not treat service-manager ioctl 40046210 -22 alone as the blocker",
        ],
        [
            "cnss-daemon vndbinder transaction",
            "active blocker",
            f"native_cnss_tx_fail={native['counts'].get('cnss_binder_transaction_failed', 0)}; android_cnss_tx_fail={android['counts'].get('cnss_binder_transaction_failed', 0)}; native_wlfw={native['counts'].get('cnss_wlfw_start', 0)}",
            "next proof should verify vndservicemanager readiness before a fresh cnss-daemon binder attempt",
        ],
        [
            "process order",
            "readiness/order gap",
            f"cnss_order={surface['cnss_daemon_start_order']}; vndsm_order={surface['vndservicemanager_start_order']}; cnss_before_vndsm={surface['cnss_daemon_before_vndservicemanager']}",
            "prefer vndservicemanager-ready plus cnss-daemon restart over widening to HAL",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    if (
        checks["v653_service74_gate_preserved"]
        and checks["v653_service_manager_trio_observable"]
        and checks["v653_cnss_reaches_vndbinder"]
        and checks["v653_vndservicemanager_reaches_vndbinder"]
        and checks["v653_binder_devnodes_present"]
        and checks["v653_selinux_exec_contexts_set"]
        and checks["android_generic_binder_ioctl_nonfatal"]
        and checks["native_cnss_binder_transaction_blocks_wlfw"]
        and checks["cnss_started_before_vndservicemanager"]
    ):
        return (
            "v654-vndbinder-readiness-gap-classified",
            True,
            (
                "V653 preserved service 74 and mounted the binder/SELinux runtime surface, but "
                "cnss-daemon opened vndbinder before vndservicemanager readiness was proven and "
                "then hit a cnss-specific binder transaction -22. Generic binder ioctl -22 is "
                "not sufficient as a root cause because Android logs that class while still "
                "reaching WLFW."
            ),
            (
                "plan V655 as a bounded vndservicemanager-readiness plus fresh cnss-daemon "
                "binder attempt proof; keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, "
                "and external ping blocked"
            ),
        )

    return (
        "v654-binder-runtime-review-required",
        False,
        "V653/Android binder-runtime evidence did not match the expected readiness/order gap",
        "inspect V653 helper and dmesg manually before another live retry",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v651 = load_json(args.v651_manifest)
    v652 = load_json(args.v652_manifest)
    v653 = load_json(args.v653_manifest)
    helper_text = read_text(args.v653_helper)
    keys = parse_key_values(helper_text)
    android_text = read_text(args.android_audio_dmesg) + "\n" + read_text(args.android_unfiltered_dmesg)
    android = source_summary(parse_events(android_text, "android-v649"))
    native = source_summary(parse_events(read_text(args.v653_dmesg), "native-v653"))
    surface = process_surface(keys)
    checks = build_checks(v651, v652, v653, android, native, surface, keys)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v651_manifest": str(repo_path(args.v651_manifest)),
            "v652_manifest": str(repo_path(args.v652_manifest)),
            "v653_manifest": str(repo_path(args.v653_manifest)),
            "v653_dmesg": str(repo_path(args.v653_dmesg)),
            "v653_helper": str(repo_path(args.v653_helper)),
            "android_audio_dmesg": str(repo_path(args.android_audio_dmesg)),
            "android_unfiltered_dmesg": str(repo_path(args.android_unfiltered_dmesg)),
        },
        "prior": {
            "v651": {"decision": v651.get("decision"), "pass": v651.get("pass")},
            "v652": {"decision": v652.get("decision"), "pass": v652.get("pass")},
            "v653": {"decision": v653.get("decision"), "pass": v653.get("pass")},
        },
        "android_v649": android,
        "native_v653": native,
        "v653_process_surface": surface,
        "checks": checks,
        "matrix_rows": matrix_rows(android, native),
        "service_manager_rows": surface["service_manager_start_order_rows"],
        "binder_surface_rows": surface["binder_surface_rows"],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v654-binder-runtime-mismatch-classifier-plan-ready",
            True,
            "plan-only; no device contact, no daemon start, no Wi-Fi bring-up",
            "run V654 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)

    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["inference_rows"] = inference_rows(manifest)
    manifest["inferences"] = rows_to_dicts(
        ["subject", "classification", "evidence", "next"],
        manifest["inference_rows"],
    )
    manifest["matrix"] = rows_to_dicts(
        ["marker", "android_count", "android_first_time", "native_count", "native_first_time"],
        manifest["matrix_rows"],
    )
    manifest["service_managers"] = rows_to_dicts(
        ["child", "start_order", "observable", "exited", "signal", "postflight_safe", "selinux_exec", "target"],
        manifest["service_manager_rows"],
    )
    manifest["binder_surface"] = rows_to_dicts(
        ["device", "exists", "access_r", "mode", "rdev"],
        manifest["binder_surface_rows"],
    )
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V654 Binder Runtime Mismatch Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## Key Deltas",
        "",
        markdown_table(
            ["source", "delta", "ms"],
            [["android-v649", key, str(value)] for key, value in manifest["android_v649"]["deltas_ms"].items()]
            + [["native-v653", key, str(value)] for key, value in manifest["native_v653"]["deltas_ms"].items()],
        ),
        "",
        "## Inferences",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["inference_rows"]),
        "",
        "## Service Managers",
        "",
        markdown_table(
            ["child", "start_order", "observable", "exited", "signal", "postflight_safe", "selinux_exec", "target"],
            manifest["service_manager_rows"],
        ),
        "",
        "## Binder Surface",
        "",
        markdown_table(["device", "exists", "access_r", "mode", "rdev"], manifest["binder_surface_rows"]),
        "",
        "## Marker Matrix",
        "",
        markdown_table(
            ["marker", "android_count", "android_first_time", "native_count", "native_first_time"],
            manifest["matrix_rows"],
        ),
        "",
        "## Interpretation",
        "",
        "- V653 solved the previous `service 74` preservation problem.",
        "- Binder devnodes, service-manager child processes, and SELinux exec contexts are present.",
        "- Android also logs generic binder ioctl `-22` while continuing to WLFW, so that class is not the final stop condition.",
        "- The native-only stop condition is the `cnss-daemon` vndbinder transaction `-22` before WLFW.",
        "- The next proof should make vndservicemanager readiness explicit and trigger a fresh `cnss-daemon` binder attempt before any Wi-Fi HAL or connect step.",
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
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
