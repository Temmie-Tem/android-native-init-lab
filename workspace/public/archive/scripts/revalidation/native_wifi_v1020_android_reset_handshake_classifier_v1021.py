#!/usr/bin/env python3
"""V1021 host-only classifier after V1020 SDX50M reset-path stall.

Compares V1020 native upper-surface scoped `/dev/subsys_esoc0` evidence with
existing Android-good evidence and prior PeripheralManager classifiers. This
script does not contact the device and does not execute ADB.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1021-v1020-android-reset-handshake-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1021-v1020-android-reset-handshake-classifier.txt")

DEFAULT_V1020_MANIFEST = Path("tmp/wifi/v1020-after-fd-subsys-window-live/manifest.json")
DEFAULT_V1020_TRANSCRIPT = Path(
    "tmp/wifi/v1020-after-fd-subsys-window-live/native/mdm-helper-cnss-before-esoc.txt"
)
DEFAULT_V1020_DMESG = Path("tmp/wifi/v1020-after-fd-subsys-window-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V1000_MANIFEST = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/manifest.json"
)
DEFAULT_V1000_DMESG = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/dmesg-full.txt"
)
DEFAULT_V1000_PROCESS_FD = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/process-fd.txt"
)
DEFAULT_V968_MANIFEST = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json")
DEFAULT_V867_REPORT = Path("docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md")
DEFAULT_V868_REPORT = Path("docs/reports/NATIVE_INIT_V868_PM_ESOC_CONTRACT_CLASSIFIER_2026-05-25.md")
DEFAULT_V944_REPORT = Path("docs/reports/NATIVE_INIT_V944_V943_QUEUE_TIMING_CLASSIFIER_2026-05-26.md")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_PM_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
ANDROID_PATTERNS: dict[str, str] = {
    "per_proxy_helper_start": r"init:\s+starting service 'vendor\.per_proxy_helper'",
    "per_proxy_helper_exit": r"Service 'vendor\.per_proxy_helper'.*exited",
    "per_mgr_start": r"init:\s+starting service 'vendor\.per_mgr'",
    "per_proxy_start": r"init:\s+starting service 'vendor\.per_proxy'",
    "mdm_helper_start": r"init:\s+starting service 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init:\s+starting service 'cnss-daemon'",
    "subsys_esoc0_get": r"__subsystem_get\(\):\s+__subsystem_get:\s+esoc0 count:0",
    "wlfw_start": r"cnss-daemon wlfw_start:\s+Starting",
    "wlan_pd": r"msm/modem/wlan_pd, state:",
    "icnss_qmi_connected": r"icnss_qmi:\s+QMI Server Connected",
    "bdf_regdb": r"BDF file\s*:\s*regdb\.bin",
    "bdf_bdwlan": r"BDF file\s*:\s*bdwlan\.bin",
    "fw_ready": r"WLAN FW is ready",
    "wlan0_event": r"dev\s*:\s*wlan0\s*:\s*event",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1020-manifest", type=Path, default=DEFAULT_V1020_MANIFEST)
    parser.add_argument("--v1020-transcript", type=Path, default=DEFAULT_V1020_TRANSCRIPT)
    parser.add_argument("--v1020-dmesg", type=Path, default=DEFAULT_V1020_DMESG)
    parser.add_argument("--v1000-manifest", type=Path, default=DEFAULT_V1000_MANIFEST)
    parser.add_argument("--v1000-dmesg", type=Path, default=DEFAULT_V1000_DMESG)
    parser.add_argument("--v1000-process-fd", type=Path, default=DEFAULT_V1000_PROCESS_FD)
    parser.add_argument("--v968-manifest", type=Path, default=DEFAULT_V968_MANIFEST)
    parser.add_argument("--v867-report", type=Path, default=DEFAULT_V867_REPORT)
    parser.add_argument("--v868-report", type=Path, default=DEFAULT_V868_REPORT)
    parser.add_argument("--v944-report", type=Path, default=DEFAULT_V944_REPORT)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--pm-research", type=Path, default=DEFAULT_PM_RESEARCH)
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def parse_events(text: str) -> dict[str, dict[str, Any]]:
    return {name: first_event(text, pattern) for name, pattern in ANDROID_PATTERNS.items()}


def event_time(events: dict[str, dict[str, Any]], name: str) -> float | None:
    value = events.get(name, {}).get("time")
    if isinstance(value, int | float):
        return float(value)
    return None


def delta_ms(events: dict[str, dict[str, Any]], later: str, earlier: str) -> float | None:
    later_time = event_time(events, later)
    earlier_time = event_time(events, earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def manifest_contract(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def v968_event(v968: dict[str, Any], name: str) -> dict[str, Any]:
    events = ((v968.get("classification") or {}).get("events") or {})
    value = events.get(name) or {}
    return value if isinstance(value, dict) else {}


def text_has_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1020 = load_json(args.v1020_manifest)
    v1000 = load_json(args.v1000_manifest)
    v968 = load_json(args.v968_manifest)
    v1020_text = read_text(args.v1020_transcript)
    v1020_dmesg = read_text(args.v1020_dmesg)
    v1000_dmesg = read_text(args.v1000_dmesg)
    v1000_process_fd = read_text(args.v1000_process_fd)
    v867_report = read_text(args.v867_report)
    v868_report = read_text(args.v868_report)
    v944_report = read_text(args.v944_report)
    mdm3_research = read_text(args.mdm3_research)
    pm_research = read_text(args.pm_research)

    contract = manifest_contract(v1020)
    android_events = parse_events(v1000_dmesg)
    android_positive_v968 = all(
        bool(v968_event(v968, name).get("present"))
        for name in (
            "wlfw_start",
            "esoc0_subsystem_get",
            "wlan_pd_indication",
            "icnss_qmi_connected",
            "bdf_regdb",
            "bdf_bdwlan",
            "fw_ready",
            "wlan0_event",
        )
    )
    android_positive_v1000 = all(
        bool(android_events.get(name, {}).get("present"))
        for name in (
            "per_proxy_helper_start",
            "per_mgr_start",
            "per_proxy_start",
            "mdm_helper_start",
            "cnss_daemon_start",
            "subsys_esoc0_get",
            "wlfw_start",
            "wlan_pd",
            "icnss_qmi_connected",
        )
    )

    v1020_upper_surface_reached = (
        v1020.get("decision") == "v1020-reboot-required-cleaned"
        and bool(v1020.get("pass"))
        and contract.get("mdm_helper_esoc0_fd_seen") == "1"
        and contract.get("service_manager_started") == "1"
        and contract.get("wifi_hal_started") == "1"
        and contract.get("wificond_started") == "1"
        and contract.get("cnss_diag_started") == "1"
        and contract.get("cnss_daemon_started") == "1"
    )
    v1020_stall_is_sdx50m_soft_reset = text_has_all(
        v1020_text,
        (
            "sdx50m_toggle_soft_reset",
            "mdm4x_do_first_power_on",
            "mdm_subsys_powerup",
            "subsys_device_open",
            "State:\tD (disk sleep)",
        ),
    )
    v1020_guardrails_clean = all(
        v1020.get(key) is False
        for key in (
            "wifi_bringup_executed",
            "external_ping_executed",
            "live_esoc_ioctl_executed",
            "subsys_esoc0_controller_open_attempted",
            "notify_attempted",
            "boot_done_attempted",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
        )
    )
    v1020_no_wlfw_continuation = (
        v1020.get("wlfw_precondition_observed") is False
        and "WLAN FW is ready" not in v1020_dmesg
        and "BDF file" not in v1020_dmesg
        and "dev : wlan0" not in v1020_dmesg
    )
    v1020_proxy_gap = (
        contract.get("pm_proxy_started") == "0"
        and contract.get("pm_proxy_helper_start_executed") == "0"
        and contract.get("pm_proxy_helper_count") != "1"
    )
    android_peripheral_lifecycle = all(
        bool(android_events.get(name, {}).get("present"))
        for name in ("per_proxy_helper_start", "per_mgr_start", "per_proxy_start", "per_proxy_helper_exit")
    )
    android_fd_snapshot = {
        "mdm_helper_esoc0_fd": "comm=mdm_helper" in v1000_process_fd and "/dev/esoc-0" in v1000_process_fd,
        "pm_service_subsys_modem_fd": "comm=pm-service" in v1000_process_fd and "/dev/subsys_modem" in v1000_process_fd,
        "pm_proxy_helper_late_fd_visible": "comm=pm_proxy_helper" in v1000_process_fd,
        "pm_proxy_late_process_visible": "comm=pm-proxy" in v1000_process_fd or "/vendor/bin/pm-proxy" in v1000_process_fd,
    }
    prior_blind_pm_proxy_helper_closed = text_has_all(
        v867_report + "\n" + v868_report,
        (
            "pm_proxy_helper",
            "D-state",
            "should not be retried alone",
        ),
    )
    prior_provider_lifetime_gap = "v944-pm-provider-lifetime-gap-selected" in v944_report
    research_maps_soft_reset = text_has_all(
        mdm3_research,
        (
            "sdx50m_toggle_soft_reset",
            "PMIC pm8150l GPIO 9",
            "GPIO 135",
            "GPIO 142",
        ),
    )
    research_maps_pm_proxy_helper = text_has_all(
        pm_research,
        (
            "pm_proxy_helper",
            "/dev/subsys_esoc0",
            "ESOC_REG_REQ_ENG",
        ),
    )

    gaps = {
        "android_exact_per_proxy_helper_fd_timing_missing": not android_fd_snapshot["pm_proxy_helper_late_fd_visible"],
        "android_gpio_transition_timing_missing": (
            ((v968.get("classification") or {}).get("answers") or {}).get("ap2mdm_gpio135_assert_time") is None
            or ((v968.get("classification") or {}).get("answers") or {}).get("pmic_gpio9_deassert_time") is None
        ),
        "native_proxy_lifecycle_missing": v1020_proxy_gap,
    }
    checks = {
        "v1020_input_present": bool(v1020),
        "v1020_upper_surface_reached": v1020_upper_surface_reached,
        "v1020_subsys_open_attempted": v1020.get("subsys_esoc0_open_attempted") is True,
        "v1020_stall_is_sdx50m_soft_reset": v1020_stall_is_sdx50m_soft_reset,
        "v1020_no_wlfw_continuation": v1020_no_wlfw_continuation,
        "v1020_guardrails_clean": v1020_guardrails_clean,
        "android_v1000_peripheral_lifecycle_present": android_peripheral_lifecycle,
        "android_v1000_wlfw_chain_present": android_positive_v1000,
        "android_v968_full_positive_chain_present": android_positive_v968,
        "android_fd_snapshot_has_mdm_helper_esoc0": android_fd_snapshot["mdm_helper_esoc0_fd"],
        "prior_blind_pm_proxy_helper_retry_closed": prior_blind_pm_proxy_helper_closed,
        "prior_provider_lifetime_gap_present": prior_provider_lifetime_gap,
        "research_maps_soft_reset_to_pmic_gpio": research_maps_soft_reset,
        "research_maps_pm_proxy_helper_contract": research_maps_pm_proxy_helper,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    passed = not blockers
    if passed:
        decision = "v1021-select-android-pm-esoc-timing-recapture"
        reason = (
            "V1020 proves the upper-surface scoped subsystem open reaches "
            "sdx50m_toggle_soft_reset and stalls; Android has per_proxy_helper/"
            "per_mgr/per_proxy plus WLFW-positive evidence, but existing captures "
            "miss exact per_proxy_helper fd and GPIO/PMIC transition timing"
        )
        next_step = "V1022 Android read-only PM/eSoC timing recapture before any native retry"
    else:
        decision = "v1021-reset-handshake-classifier-incomplete"
        reason = "missing checks: " + ", ".join(blockers)
        next_step = "repair missing evidence before changing native live gates"

    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "gaps": gaps,
        "timing": {
            "android_per_proxy_helper_start_to_mdm_helper_start_ms": delta_ms(
                android_events, "mdm_helper_start", "per_proxy_helper_start"
            ),
            "android_mdm_helper_start_to_subsys_esoc0_get_ms": delta_ms(
                android_events, "subsys_esoc0_get", "mdm_helper_start"
            ),
            "android_subsys_esoc0_get_to_wlfw_start_ms": delta_ms(
                android_events, "wlfw_start", "subsys_esoc0_get"
            ),
            "android_wlfw_start_to_wlan_pd_ms": delta_ms(
                android_events, "wlan_pd", "wlfw_start"
            ),
        },
        "android_fd_snapshot": android_fd_snapshot,
        "selected_route": {
            "next_version": "V1022",
            "route": "android-readonly-pm-esoc-timing-recapture",
            "collect": [
                "full dmesg focused on per_proxy_helper, per_mgr, per_proxy, mdm_helper, subsys_esoc0, WLFW, PMIC/GPIO",
                "short repeated ps/fd snapshots during early Android Wi-Fi window if handoff script can capture before per_proxy_helper exits",
                "/proc/interrupts mdm status snapshots",
                "/sys/kernel/debug/gpio snapshots for GPIO135, GPIO142, and PMIC GPIO9 if readable",
                "init service state for vendor.per_proxy_helper, vendor.per_mgr, vendor.per_proxy, vendor.mdm_helper, cnss-daemon",
            ],
            "forbid": [
                "native /dev/subsys_esoc0 retry",
                "blind pm_proxy_helper native retry",
                "eSoC notify or BOOT_DONE",
                "GPIO/sysfs/debugfs writes",
                "IWifi.start, qcwlanstate, scan/connect, credentials, DHCP/routes, external ping",
            ],
            "defer": [
                "helper source changes until Android-positive timing identifies the missing native side condition",
                "Wi-Fi scan/connect until WLFW/BDF/wlan0 appears in native init",
            ],
        },
        "events": {
            "v1000_android": android_events,
            "v968_selected": {
                name: v968_event(v968, name)
                for name in (
                    "wlfw_start",
                    "esoc0_subsystem_get",
                    "wlan_pd_indication",
                    "icnss_qmi_connected",
                    "bdf_regdb",
                    "bdf_bdwlan",
                    "fw_ready",
                    "wlan0_event",
                )
            },
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    gap_rows = [[name, "YES" if value else "NO"] for name, value in manifest["gaps"].items()]
    timing_rows = [[name, value] for name, value in manifest["timing"].items()]
    fd_rows = [[name, "YES" if value else "NO"] for name, value in manifest["android_fd_snapshot"].items()]
    route = manifest["selected_route"]
    return "\n".join(
        [
            "# V1021 V1020 Android Reset Handshake Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "result"], check_rows),
            "",
            "## Gaps",
            "",
            markdown_table(["gap", "present"], gap_rows),
            "",
            "## Android Timing",
            "",
            markdown_table(["measurement", "ms"], timing_rows),
            "",
            "## Android FD Snapshot",
            "",
            markdown_table(["item", "visible"], fd_rows),
            "",
            "## Selected Route",
            "",
            f"- next_version: `{route['next_version']}`",
            f"- route: `{route['route']}`",
            "",
            "### Collect",
            "",
            *[f"- {item}" for item in route["collect"]],
            "",
            "### Forbid",
            "",
            *[f"- {item}" for item in route["forbid"]],
            "",
            "### Defer",
            "",
            *[f"- {item}" for item in route["defer"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    classification = classify(args)
    store = EvidenceStore(repo_path(args.out_dir))
    inputs = {
        "v1020_manifest": str(repo_path(args.v1020_manifest)),
        "v1020_manifest_sha256": sha256(args.v1020_manifest),
        "v1020_transcript": str(repo_path(args.v1020_transcript)),
        "v1020_transcript_sha256": sha256(args.v1020_transcript),
        "v1020_dmesg": str(repo_path(args.v1020_dmesg)),
        "v1000_manifest": str(repo_path(args.v1000_manifest)),
        "v1000_manifest_sha256": sha256(args.v1000_manifest),
        "v1000_dmesg": str(repo_path(args.v1000_dmesg)),
        "v1000_dmesg_sha256": sha256(args.v1000_dmesg),
        "v1000_process_fd": str(repo_path(args.v1000_process_fd)),
        "v1000_process_fd_sha256": sha256(args.v1000_process_fd),
        "v968_manifest": str(repo_path(args.v968_manifest)),
        "v968_manifest_sha256": sha256(args.v968_manifest),
        "v867_report": str(repo_path(args.v867_report)),
        "v868_report": str(repo_path(args.v868_report)),
        "v944_report": str(repo_path(args.v944_report)),
        "mdm3_research": str(repo_path(args.mdm3_research)),
        "pm_research": str(repo_path(args.pm_research)),
    }
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": inputs,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
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
