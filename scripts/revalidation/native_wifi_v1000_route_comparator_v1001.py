#!/usr/bin/env python3
"""V1001 host-only comparator for V1000 Android timing versus native gates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1001-v1000-route-comparator")
LATEST_POINTER = Path("tmp/wifi/latest-v1001-v1000-route-comparator.txt")

DEFAULT_V1000_HANDOFF = Path("tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/manifest.json")
DEFAULT_V1000_DMESG = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/dmesg-full.txt"
)
DEFAULT_V1000_GPIO = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/gpio.txt"
)
DEFAULT_V1000_PROCESS = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/process-fd.txt"
)
DEFAULT_V998_REPORT = Path("docs/reports/NATIVE_INIT_V998_ANDROID_SERVICE_WINDOW_POST_SELINUX_2026-05-26.md")
DEFAULT_V998_TRANSCRIPT = Path(
    "tmp/wifi/v998-android-service-window-live-v169-post-selinux/native/mdm-helper-cnss-before-esoc.txt"
)
DEFAULT_V923_REPORT = Path("docs/reports/NATIVE_INIT_V923_CNSS_BEFORE_ESOC_LIVE_2026-05-26.md")
DEFAULT_V964_REPORT = Path("docs/reports/NATIVE_INIT_V964_V963_POST_PROVIDER_TRIGGER_CLASSIFIER_2026-05-26.md")
DEFAULT_V965_REPORT = Path("docs/reports/NATIVE_INIT_V965_V964_ROUTE_CLASSIFIER_2026-05-26.md")

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")

EVENT_PATTERNS: dict[str, str] = {
    "mdm3_probe": r"ext-mdm\s+soc:qcom,mdm3",
    "gpio135_request": r"msm_gpio_request:\s+off\[135\]",
    "gpio142_request": r"msm_gpio_request:\s+off\[142\]",
    "wifi_hal_legacy_start": r"init: starting service 'vendor\.wifi_hal_legacy'",
    "wifi_hal_ext_start": r"init: starting service 'vendor\.wifi_hal_ext'",
    "wificond_start": r"init: starting service 'wificond'",
    "mdm_helper_start": r"init: starting service 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init: starting service 'cnss-daemon'",
    "esoc0_get": r"__subsystem_get\(\):\s+__subsystem_get:\s+esoc0 count:0",
    "wlfw_start": r"cnss-daemon wlfw_start:\s+Starting",
    "wlan_pd": r"service-notifier: .*msm/modem/wlan_pd",
    "icnss_qmi_connected": r"icnss_qmi:\s+QMI Server Connected",
    "bdf": r"BDF file\s*:",
    "wlan0": r"dev\s*:\s*wlan0\s*:\s*event|\bwlan0\b",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1000-handoff", type=Path, default=DEFAULT_V1000_HANDOFF)
    parser.add_argument("--v1000-dmesg", type=Path, default=DEFAULT_V1000_DMESG)
    parser.add_argument("--v1000-gpio", type=Path, default=DEFAULT_V1000_GPIO)
    parser.add_argument("--v1000-process", type=Path, default=DEFAULT_V1000_PROCESS)
    parser.add_argument("--v998-report", type=Path, default=DEFAULT_V998_REPORT)
    parser.add_argument("--v998-transcript", type=Path, default=DEFAULT_V998_TRANSCRIPT)
    parser.add_argument("--v923-report", type=Path, default=DEFAULT_V923_REPORT)
    parser.add_argument("--v964-report", type=Path, default=DEFAULT_V964_REPORT)
    parser.add_argument("--v965-report", type=Path, default=DEFAULT_V965_REPORT)
    return parser.parse_args()


def read_text(path: Path, limit: int = 3_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def line_time(line: str) -> float | None:
    match = TIME_RE.search(line.strip())
    return float(match.group("time")) if match else None


def first_event(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if regex.search(line):
            return {
                "present": True,
                "line_number": line_number,
                "time": line_time(line),
                "line": line,
            }
    return {"present": False, "line_number": None, "time": None, "line": ""}


def parse_events(text: str) -> dict[str, dict[str, Any]]:
    return {name: first_event(text, pattern) for name, pattern in EVENT_PATTERNS.items()}


def delta_ms(events: dict[str, dict[str, Any]], later: str, earlier: str) -> float | None:
    later_time = events.get(later, {}).get("time")
    earlier_time = events.get(earlier, {}).get("time")
    if not isinstance(later_time, int | float) or not isinstance(earlier_time, int | float):
        return None
    return round((float(later_time) - float(earlier_time)) * 1000.0, 3)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1000 = load_json(args.v1000_handoff)
    dmesg = read_text(args.v1000_dmesg)
    gpio = read_text(args.v1000_gpio)
    process = read_text(args.v1000_process)
    v998_report = read_text(args.v998_report)
    v998_transcript = read_text(args.v998_transcript)
    v923_report = read_text(args.v923_report)
    v964_report = read_text(args.v964_report)
    v965_report = read_text(args.v965_report)

    events = parse_events(dmesg)
    comparison = v1000.get("context", {}).get("comparison", {})
    positive_markers = comparison.get("positive_markers") or {}

    v1000_rollback_complete = (
        v1000.get("decision") == "v913-handoff-collector-failed-rollback-complete"
        and v1000.get("device_commands_executed") is True
        and v1000.get("wifi_bringup_executed") is False
        and v1000.get("external_ping_executed") is False
    )
    v1000_android_reached_lower_wlfw = all(
        events[name]["present"] for name in ("esoc0_get", "wlfw_start", "wlan_pd", "icnss_qmi_connected")
    )
    v1000_esoc_before_wlfw = (
        events["esoc0_get"]["present"]
        and events["wlfw_start"]["present"]
        and delta_ms(events, "wlfw_start", "esoc0_get") is not None
        and float(delta_ms(events, "wlfw_start", "esoc0_get") or 0.0) >= 0.0
    )
    v1000_mdm_helper_fd = "/dev/esoc-0" in process and "comm=mdm_helper" in process
    v1000_actor_contexts = all(
        marker in process
        for marker in (
            "u:r:vendor_mdm_helper:s0",
            "u:r:vendor_wcnss_service:s0",
            "u:r:wificond:s0",
            "u:r:hal_wifi_default:s0",
        )
    )
    v1000_gpio_surface = all(marker in gpio for marker in ("GPIO_DEBUG readable=1", "gpio135", "gpio142"))
    v1000_no_full_wifi_required = (
        positive_markers.get("bdf") is False
        and positive_markers.get("wlan0") is False
        and positive_markers.get("wlfw") is True
    )

    v998_service_window_clean_no_wlfw = all(
        marker in v998_report
        for marker in (
            "all_observable_at_timeout=1",
            "WLFW precondition | MISSING",
            "`wificond` post-exec context",
        )
    ) or all(
        marker in v998_transcript
        for marker in (
            "android_wifi_service_window.all_observable_at_timeout=1",
            "wlfw_precondition_observed=0",
            "wifi_hal_composite_child.wificond.selinux.exec=u:r:wificond:s0",
        )
    )
    v998_did_not_try_subsys = (
        "no `/dev/subsys_esoc0` open" in v998_report
        or "android_wifi_service_window.subsys_esoc0_open_attempted=0" in v998_transcript
    )
    v923_wlfw_gate_too_strict = all(
        marker in v923_report
        for marker in (
            "`subsys_esoc0_open_attempted` | `false`",
            "fail-closed gate kept `/dev/subsys_esoc0` closed",
        )
    )
    v964_warns_blind_stall = all(
        marker in v964_report
        for marker in (
            "`sdx50m_toggle_soft_reset`",
            "The child blocks in `sdx50m_toggle_soft_reset`",
        )
    )
    v965_rejects_stale_routes = all(
        marker in v965_report
        for marker in (
            "blind `/dev/subsys_esoc0` open",
            "`qcwlanstate ON` retry",
            "`IWifi.start` retry",
        )
    )

    checks = {
        "v1000_rollback_complete": v1000_rollback_complete,
        "v1000_android_reached_lower_wlfw": v1000_android_reached_lower_wlfw,
        "v1000_esoc_before_wlfw": v1000_esoc_before_wlfw,
        "v1000_mdm_helper_fd": v1000_mdm_helper_fd,
        "v1000_actor_contexts": v1000_actor_contexts,
        "v1000_gpio_surface": v1000_gpio_surface,
        "v1000_no_full_wifi_required": v1000_no_full_wifi_required,
        "v998_service_window_clean_no_wlfw": v998_service_window_clean_no_wlfw,
        "v998_did_not_try_subsys": v998_did_not_try_subsys,
        "v923_wlfw_gate_too_strict": v923_wlfw_gate_too_strict,
        "v964_warns_blind_stall": v964_warns_blind_stall,
        "v965_rejects_stale_routes": v965_rejects_stale_routes,
    }

    if all(checks.values()):
        decision = "v1001-select-service-window-scoped-subsys-trigger-support"
        passed = True
        route = "source-build-helper-for-service-window-scoped-subsys-trigger"
        reason = (
            "V1000 shows Android reaches esoc0 get, wlfw_start, WLAN-PD, and ICNSS QMI inside the actor window; "
            "V998 had the actor window but never tried subsys_esoc0, while V923's wlfw-precondition gate is now circular"
        )
        next_step = (
            "V1002 should be source/build-only: add a fail-closed helper mode that opens /dev/subsys_esoc0 only after "
            "current-boot SELinux proof, service-window actors, mdm_helper /dev/esoc-0 fd, and cleanup/D-state capture are ready"
        )
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1001-route-evidence-incomplete"
        passed = False
        route = "repair-comparator-evidence-before-live"
        reason = f"required comparator evidence missing: {missing}"
        next_step = "refresh V1000/V998/V923/V964/V965 evidence before selecting another native lower trigger"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "event_times": {name: events[name] for name in events},
        "deltas_ms": {
            "esoc0_get_to_wlfw_start": delta_ms(events, "wlfw_start", "esoc0_get"),
            "wlfw_start_to_wlan_pd": delta_ms(events, "wlan_pd", "wlfw_start"),
            "wlan_pd_to_icnss_qmi": delta_ms(events, "icnss_qmi_connected", "wlan_pd"),
            "cnss_daemon_start_to_esoc0_get": delta_ms(events, "esoc0_get", "cnss_daemon_start"),
            "mdm_helper_start_to_esoc0_get": delta_ms(events, "esoc0_get", "mdm_helper_start"),
        },
        "inputs": {
            "v1000_handoff": str(repo_path(args.v1000_handoff)),
            "v1000_dmesg": str(repo_path(args.v1000_dmesg)),
            "v1000_gpio": str(repo_path(args.v1000_gpio)),
            "v1000_process": str(repo_path(args.v1000_process)),
            "v998_report": str(repo_path(args.v998_report)),
            "v998_transcript": str(repo_path(args.v998_transcript)),
            "v923_report": str(repo_path(args.v923_report)),
            "v964_report": str(repo_path(args.v964_report)),
            "v965_report": str(repo_path(args.v965_report)),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "subsys_esoc0_open_executed": False,
        "esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_linkup": False,
        "credentials_used": False,
        "dhcp_routing": False,
        "external_ping": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    delta_rows = [[name, str(value)] for name, value in manifest["deltas_ms"].items()]
    event_rows = [
        [name, str(event["present"]), str(event["time"]), event["line"]]
        for name, event in manifest["event_times"].items()
    ]
    input_rows = [[name, path] for name, path in manifest["inputs"].items()]
    return "\n".join(
        [
            "# V1001 V1000 Route Comparator",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- route: `{manifest['route']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "result"], check_rows),
            "",
            "## Deltas",
            "",
            markdown_table(["delta", "ms"], delta_rows),
            "",
            "## Events",
            "",
            markdown_table(["event", "present", "time", "line"], event_rows),
            "",
            "## Inputs",
            "",
            markdown_table(["name", "path"], input_rows),
            "",
            "## Guardrails",
            "",
            "- Host-only comparator.",
            "- No device command, actor start, eSoC ioctl, `/dev/subsys_esoc0` open, Wi-Fi bring-up, scan/connect, credentials, DHCP, external ping, boot image write, or partition write.",
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
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"route: {manifest['route']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
