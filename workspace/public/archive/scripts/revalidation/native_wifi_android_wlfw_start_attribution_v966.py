#!/usr/bin/env python3
"""V966 host-only Android wlfw_start trigger attribution classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v966-android-wlfw-start-attribution")
LATEST_POINTER = Path("tmp/wifi/latest-v966-android-wlfw-start-attribution.txt")
DEFAULT_COLLECTOR_DIR = Path(
    "tmp/wifi/v913-android-esoc-gpio-timeline-handoff-live/v913-android-esoc-gpio-timeline-run"
)
DEFAULT_V963_POST_DMESG = Path("tmp/wifi/v963-post-provider-trigger-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V964 = Path("tmp/wifi/v964-v963-post-provider-trigger-classifier/manifest.json")
DEFAULT_V965 = Path("tmp/wifi/v965-v964-route-classifier/manifest.json")

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")

EVENT_PATTERNS: dict[str, str] = {
    "wlan_driver_loading": r"wlan: Loading driver",
    "vendor_wifi_hal_legacy_start": r"init: starting service 'vendor\.wifi_hal_legacy'",
    "vendor_wifi_hal_ext_start": r"init: starting service 'vendor\.wifi_hal_ext'",
    "vendor_per_mgr_start": r"init: starting service 'vendor\.per_mgr'",
    "service_notifier_180_connect": r"service_notifier_new_server: Connection established.*180 service",
    "service_notifier_74_connect": r"service_notifier_new_server: Connection established.*74 service",
    "vendor_mdm_launcher_start": r"init: starting service 'vendor\.mdm_launcher'",
    "cnss_diag_start": r"init: starting service 'cnss_diag'",
    "wificond_start": r"init: starting service 'wificond'",
    "vendor_mdm_helper_start": r"init: starting service 'vendor\.mdm_helper'",
    "vendor_mdm_helper_ctl_start": r"Processed ctl\.start for 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init: starting service 'cnss-daemon'",
    "cnss_daemon_netlink_first": r"netlink_create.*comm:\s*cnss-daemon",
    "cnss_daemon_genl_continue": r"cnss-daemon Failed to init genl between daemon and platform, continue",
    "wlfw_start": r"cnss-daemon wlfw_start: Starting",
    "wlfw_service_request": r"cnss-daemon wlfw_service_request: Start the pthread",
    "esoc0_subsystem_get": r"__subsystem_get\(\): __subsystem_get: esoc0 count:0",
    "wlan_pd_indication": r"msm/modem/wlan_pd, state:",
    "icnss_qmi_connected": r"icnss_qmi: QMI Server Connected",
    "bdf_regdb": r"BDF file\s*:\s*regdb\.bin",
    "bdf_bdwlan": r"BDF file\s*:\s*bdwlan\.bin",
    "fw_ready": r"icnss: WLAN FW is ready",
    "wlan0_event": r"dev\s*:\s*wlan0\s*:\s*event",
    "qcwlanstate": r"qcwlanstate|qcwlan",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--collector-dir", type=Path, default=DEFAULT_COLLECTOR_DIR)
    parser.add_argument("--v963-post-dmesg", type=Path, default=DEFAULT_V963_POST_DMESG)
    parser.add_argument("--v964", type=Path, default=DEFAULT_V964)
    parser.add_argument("--v965", type=Path, default=DEFAULT_V965)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line.strip())
    return float(match.group("time")) if match else None


def first_event(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            return {
                "present": True,
                "line_number": line_number,
                "time": dmesg_time(line),
                "line": line,
            }
    return {"present": False, "line_number": None, "time": None, "line": ""}


def all_matching_events(text: str, pattern: str, limit: int = 80) -> list[dict[str, Any]]:
    regex = re.compile(pattern, re.IGNORECASE)
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            events.append({"line_number": line_number, "time": dmesg_time(line), "line": line})
            if len(events) >= limit:
                break
    return events


def parse_events(text: str) -> dict[str, dict[str, Any]]:
    return {name: first_event(text, pattern) for name, pattern in EVENT_PATTERNS.items()}


def event_time(events: dict[str, dict[str, Any]], name: str) -> float | None:
    value = events.get(name, {}).get("time")
    return float(value) if isinstance(value, int | float) else None


def before(events: dict[str, dict[str, Any]], left: str, right: str) -> bool:
    left_time = event_time(events, left)
    right_time = event_time(events, right)
    return left_time is not None and right_time is not None and left_time < right_time


def after(events: dict[str, dict[str, Any]], left: str, right: str) -> bool:
    left_time = event_time(events, left)
    right_time = event_time(events, right)
    return left_time is not None and right_time is not None and left_time > right_time


def delta_ms(events: dict[str, dict[str, Any]], later: str, earlier: str) -> float | None:
    later_time = event_time(events, later)
    earlier_time = event_time(events, earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def count_before(events: list[dict[str, Any]], cutoff: float | None) -> int:
    if cutoff is None:
        return 0
    return sum(1 for event in events if isinstance(event.get("time"), int | float) and event["time"] <= cutoff)


def process_summary(text: str) -> dict[str, Any]:
    return {
        "android_wifi_hal_1_0_process": "android.hardware.wifi@1.0-service" in text,
        "samsung_wifi_hal_2_0_process": "vendor.samsung.hardware.wifi@2.0-service" in text,
        "wificond_process": bool(re.search(r"\bcomm=wificond\b|/system/bin/wificond", text)),
        "cnss_daemon_process": bool(re.search(r"\bcomm=cnss-daemon\b|/system/vendor/bin/cnss-daemon", text)),
        "mdm_helper_esoc0_fd": bool(re.search(r"comm=mdm_helper[\s\S]{0,240}-> /dev/esoc-0", text)),
        "pm_service_subsys_modem_fd": bool(re.search(r"comm=pm-service[\s\S]{0,240}-> /dev/subsys_modem", text)),
    }


def props_summary(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("init.svc."):
            continue
        key, _, value = line.partition("=")
        values[key.removeprefix("init.svc.")] = value
    return values


def timeline_rows(events: dict[str, dict[str, Any]]) -> list[tuple[str, str, str, str]]:
    selected = [
        "wlan_driver_loading",
        "vendor_wifi_hal_legacy_start",
        "vendor_wifi_hal_ext_start",
        "vendor_per_mgr_start",
        "service_notifier_180_connect",
        "service_notifier_74_connect",
        "vendor_mdm_launcher_start",
        "cnss_diag_start",
        "wificond_start",
        "vendor_mdm_helper_start",
        "vendor_mdm_helper_ctl_start",
        "cnss_daemon_start",
        "cnss_daemon_netlink_first",
        "cnss_daemon_genl_continue",
        "wlfw_start",
        "wlfw_service_request",
        "esoc0_subsystem_get",
        "wlan_pd_indication",
        "icnss_qmi_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "fw_ready",
        "wlan0_event",
    ]
    rows: list[tuple[str, str, str, str]] = []
    for name in selected:
        event = events[name]
        rows.append(
            (
                name,
                "" if event["time"] is None else f"{event['time']:.6f}",
                "" if event["line_number"] is None else str(event["line_number"]),
                "present" if event["present"] else "absent",
            )
        )
    return rows


def classify(args: argparse.Namespace) -> dict[str, Any]:
    collector_dir = repo_path(args.collector_dir)
    android_dmesg = read_text(collector_dir / "android" / "commands" / "dmesg-full.txt")
    android_focus = read_text(collector_dir / "android" / "commands" / "dmesg-focus.txt")
    process_fd = read_text(collector_dir / "android" / "commands" / "process-fd.txt")
    props = read_text(collector_dir / "android" / "commands" / "props.txt")
    v963_post_dmesg = read_text(args.v963_post_dmesg)
    v964 = load_json(args.v964)
    v965 = load_json(args.v965)

    timeline_text = android_dmesg if android_dmesg else android_focus
    events = parse_events(timeline_text)
    qcwlan_events = all_matching_events(timeline_text, EVENT_PATTERNS["qcwlanstate"])
    wlfw_time = event_time(events, "wlfw_start")

    native_patterns = {
        "cnss_netlink": len(all_matching_events(v963_post_dmesg, r"netlink_create.*comm:\s*cnss-daemon", 20)),
        "wlfw_start": len(all_matching_events(v963_post_dmesg, EVENT_PATTERNS["wlfw_start"], 20)),
        "sdx50m_queue_error": len(all_matching_events(v963_post_dmesg, r"unable to queue event for SDX50M", 20)),
        "esoc0_subsystem_get": len(all_matching_events(v963_post_dmesg, EVENT_PATTERNS["esoc0_subsystem_get"], 20)),
    }

    checks = {
        "android_dmesg_present": bool(timeline_text),
        "android_wlfw_start_present": events["wlfw_start"]["present"],
        "android_wlfw_after_cnss_daemon_start": after(events, "wlfw_start", "cnss_daemon_start"),
        "android_wlfw_after_wifi_hal_legacy": after(events, "wlfw_start", "vendor_wifi_hal_legacy_start"),
        "android_wlfw_after_wifi_hal_ext": after(events, "wlfw_start", "vendor_wifi_hal_ext_start"),
        "android_wlfw_after_wificond": after(events, "wlfw_start", "wificond_start"),
        "android_wlfw_before_esoc0_subsystem_get": before(events, "wlfw_start", "esoc0_subsystem_get"),
        "android_qcwlanstate_not_observed_before_wlfw": count_before(qcwlan_events, wlfw_time) == 0,
        "android_upper_wifi_positive_after_wlfw": all(
            events[name]["present"]
            for name in ("wlan_pd_indication", "icnss_qmi_connected", "bdf_regdb", "bdf_bdwlan", "fw_ready", "wlan0_event")
        ),
        "v963_native_cnss_netlink_without_wlfw": native_patterns["cnss_netlink"] > 0 and native_patterns["wlfw_start"] == 0,
        "v963_native_sdx50m_queue_or_esoc_stall": (
            native_patterns["sdx50m_queue_error"] > 0 or native_patterns["esoc0_subsystem_get"] > 0
        ),
        "v964_route_input_confirms_esoc_stall": (
            v964.get("decision") == "v964-post-provider-trigger-stalls-in-sdx50m-reset"
            and bool(v964.get("pass"))
        ),
        "v965_selected_this_attribution": (
            v965.get("decision") == "v965-select-wlfw-start-trigger-attribution"
            and bool(v965.get("pass"))
        ),
    }
    pass_ok = all(checks.values())
    deltas = {
        "wlfw_after_cnss_daemon_start_ms": delta_ms(events, "wlfw_start", "cnss_daemon_start"),
        "wlfw_after_mdm_helper_start_ms": delta_ms(events, "wlfw_start", "vendor_mdm_helper_start"),
        "wlfw_after_wificond_start_ms": delta_ms(events, "wlfw_start", "wificond_start"),
        "esoc0_after_wlfw_ms": delta_ms(events, "esoc0_subsystem_get", "wlfw_start"),
        "wlan_pd_after_wlfw_ms": delta_ms(events, "wlan_pd_indication", "wlfw_start"),
        "icnss_qmi_after_wlfw_ms": delta_ms(events, "icnss_qmi_connected", "wlfw_start"),
        "fw_ready_after_wlfw_ms": delta_ms(events, "fw_ready", "wlfw_start"),
        "wlan0_after_wlfw_ms": delta_ms(events, "wlan0_event", "wlfw_start"),
    }
    if pass_ok:
        decision = "v966-android-cnss-wlfw-start-window-attributed"
        reason = (
            "Android wlfw_start is a cnss-daemon service-window event after Wi-Fi HAL/wificond/mdm_helper startup "
            "and before esoc0 subsystem_get; no qcwlanstate marker appears before it, while V963 native shows CNSS netlink "
            "without wlfw_start and still stalls in the SDX50M/eSoC path."
        )
        next_step = (
            "plan V967 as a source/build-only Android init Wi-Fi service-window parity gate; do not repeat direct esoc0, "
            "qcwlanstate, HAL scan/connect, DHCP, or external ping."
        )
    else:
        decision = "v966-android-wlfw-start-attribution-incomplete"
        missing = ", ".join(name for name, passed in checks.items() if not passed)
        reason = f"missing checks: {missing}"
        next_step = "repair or recapture Android attribution evidence before selecting another native live gate"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "timeline": events,
        "timeline_rows": timeline_rows(events),
        "deltas_ms": deltas,
        "qcwlan_events_before_wlfw": count_before(qcwlan_events, wlfw_time),
        "qcwlan_events_total": len(qcwlan_events),
        "native_v963_patterns": native_patterns,
        "postboot_process_summary": process_summary(process_fd),
        "postboot_props": props_summary(props),
        "checks": checks,
        "guardrails": {
            "host_only": True,
            "device_commands_executed": False,
            "device_mutations": False,
            "wifi_hal_start_executed": False,
            "scan_connect_linkup": False,
            "credentials_used": False,
            "dhcp_routing": False,
            "external_ping": False,
            "boot_image_write": False,
            "partition_write": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    rows = [(name, "PASS" if passed else "FAIL") for name, passed in checks.items()]
    deltas = manifest["deltas_ms"]
    delta_rows = [(name, "" if value is None else str(value)) for name, value in deltas.items()]
    process_rows = [(name, str(value)) for name, value in manifest["postboot_process_summary"].items()]
    native_rows = [(name, str(value)) for name, value in manifest["native_v963_patterns"].items()]
    return "\n".join(
        [
            "# V966 Android WLFW Start Attribution",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "result"], rows),
            "",
            "## Timeline",
            "",
            markdown_table(["event", "time", "line", "status"], manifest["timeline_rows"]),
            "",
            "## Deltas",
            "",
            markdown_table(["delta", "ms"], delta_rows),
            "",
            "## Android Postboot Process Evidence",
            "",
            markdown_table(["signal", "value"], process_rows),
            "",
            "## Native V963 Comparator",
            "",
            markdown_table(["signal", "count"], native_rows),
            "",
            "## Guardrails",
            "",
            markdown_table(["guard", "value"], [(name, str(value)) for name, value in manifest["guardrails"].items()]),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    classification = classify(args)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "collector_dir": str(repo_path(args.collector_dir)),
            "v963_post_dmesg": str(repo_path(args.v963_post_dmesg)),
            "v964": str(repo_path(args.v964)),
            "v965": str(repo_path(args.v965)),
        },
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
