#!/usr/bin/env python3
"""V1017 host-only classifier after V1016 upper-surface/no-WLFW result.

Compares V1016 native evidence with existing Android-positive dmesg evidence to
decide whether the current WLFW-precondition-gated `/dev/subsys_esoc0` open is a
circular gate. This script does not contact the device and does not execute ADB.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1017-v1016-android-lower-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1017-v1016-android-lower-gap-classifier.txt")
DEFAULT_V1016 = Path("tmp/wifi/v1016-after-fd-wifi-surface-matrix-live/manifest.json")
DEFAULT_V1000_DMESG = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/dmesg-full.txt"
)
DEFAULT_V1000_MANIFEST = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/manifest.json"
)
DEFAULT_V968 = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json")
DEFAULT_V1016_REPORT = Path("docs/reports/NATIVE_INIT_V1016_AFTER_FD_WIFI_SURFACE_MATRIX_LIVE_2026-05-26.md")
DEFAULT_V968_REPORT = Path("docs/reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md")

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
EVENT_PATTERNS: dict[str, str] = {
    "wifi_hal_legacy_start": r"init: starting service 'vendor\.wifi_hal_legacy'",
    "wifi_hal_ext_start": r"init: starting service 'vendor\.wifi_hal_ext'",
    "wificond_start": r"init: starting service 'wificond'",
    "mdm_helper_start": r"init: starting service 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init: starting service 'cnss-daemon'",
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
    parser.add_argument("--v1016", type=Path, default=DEFAULT_V1016)
    parser.add_argument("--v1000-manifest", type=Path, default=DEFAULT_V1000_MANIFEST)
    parser.add_argument("--v1000-android-dmesg", type=Path, default=DEFAULT_V1000_DMESG)
    parser.add_argument("--v968", type=Path, default=DEFAULT_V968)
    parser.add_argument("--v1016-report", type=Path, default=DEFAULT_V1016_REPORT)
    parser.add_argument("--v968-report", type=Path, default=DEFAULT_V968_REPORT)
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
    return {name: first_event(text, pattern) for name, pattern in EVENT_PATTERNS.items()}


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


def v968_answers(v968: dict[str, Any]) -> dict[str, Any]:
    answers = ((v968.get("classification") or {}).get("answers") or {})
    return answers if isinstance(answers, dict) else {}


def all_present(events: dict[str, dict[str, Any]], names: tuple[str, ...]) -> bool:
    return all(bool(events.get(name, {}).get("present")) for name in names)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1016 = load_json(args.v1016)
    v1000 = load_json(args.v1000_manifest)
    v968 = load_json(args.v968)
    v1016_report = read_text(args.v1016_report)
    v968_report = read_text(args.v968_report)
    android_dmesg = read_text(args.v1000_android_dmesg)
    v1016_contract = manifest_contract(v1016)
    android_events = parse_events(android_dmesg)
    answers = v968_answers(v968)

    android_wlfw_chain_names = (
        "wifi_hal_legacy_start",
        "wifi_hal_ext_start",
        "wificond_start",
        "mdm_helper_start",
        "cnss_daemon_start",
        "subsys_esoc0_get",
        "wlfw_start",
        "wlan_pd",
        "icnss_qmi_connected",
    )
    android_full_positive_names = (
        "bdf_regdb",
        "bdf_bdwlan",
        "fw_ready",
        "wlan0_event",
    )
    v968_full_positive = all(
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
    v1000_chain = all_present(android_events, android_wlfw_chain_names)
    v1000_partial_or_full_wlfw = v1000_chain or all_present(android_events, ("wlfw_start", "wlan_pd", "icnss_qmi_connected"))
    v1000_full_positive = all_present(android_events, android_full_positive_names)
    v1000_subsys_to_wlfw_ms = delta_ms(android_events, "wlfw_start", "subsys_esoc0_get")
    v1000_wlfw_to_subsys_ms = delta_ms(android_events, "subsys_esoc0_get", "wlfw_start")
    v968_wlfw_to_subsys_ms = answers.get("wlfw_start_to_esoc0_get_ms")
    if isinstance(v968_wlfw_to_subsys_ms, str):
        try:
            v968_wlfw_to_subsys_ms = float(v968_wlfw_to_subsys_ms)
        except ValueError:
            v968_wlfw_to_subsys_ms = None

    v1016_upper_started = (
        v1016.get("decision") == "v1016-upper-surface-started-wlfw-missing-no-open"
        and bool(v1016.get("pass"))
        and v1016.get("mdm_helper_start_executed") is True
        and v1016.get("service_manager_start_executed") is True
        and v1016.get("wifi_hal_start_executed") is True
        and v1016.get("wificond_start_executed") is True
    )
    v1016_lower_fd_positive = v1016_contract.get("mdm_helper_esoc0_fd_seen") == "1"
    v1016_no_wlfw_no_subsys = (
        v1016.get("wlfw_precondition_observed") is False
        and v1016.get("subsys_esoc0_open_attempted") is False
        and v1016_contract.get("subsys_esoc0_open_gate") == "wlfw-precondition"
    )
    v1016_guardrails_clean = all(
        v1016.get(key) is False
        for key in (
            "live_esoc_ioctl_executed",
            "wifi_bringup_executed",
            "external_ping_executed",
            "cleanup_reboot_executed",
        )
    )
    android_subsys_near_wlfw = (
        isinstance(v1000_subsys_to_wlfw_ms, int | float)
        and abs(float(v1000_subsys_to_wlfw_ms)) <= 100.0
    ) or (
        isinstance(v1000_wlfw_to_subsys_ms, int | float)
        and abs(float(v1000_wlfw_to_subsys_ms)) <= 100.0
    ) or (
        isinstance(v968_wlfw_to_subsys_ms, int | float)
        and abs(float(v968_wlfw_to_subsys_ms)) <= 100.0
    )
    gpio_transition_gap_is_secondary = all(
        key in answers
        for key in (
            "ap2mdm_gpio135_assert_time",
            "pmic_gpio9_deassert_time",
            "mdm2ap_gpio142_level_snapshot",
        )
    ) and all(
        token in v968_report
        for token in (
            "GPIO level-transition timing is not directly visible",
            "Magisk or adb early sampler is justified only if",
            "not required just to continue the Android service-window parity route",
        )
    )
    v1016_report_matches = all(
        token in v1016_report
        for token in (
            "combined after-fd upper Wi-Fi surface",
            "WLFW precondition still did not appear",
            "upper userspace surface",
        )
    ) or all(
        token in v1016_report
        for token in (
            "combined after-fd upper Wi-Fi surface can be started",
            "WLFW precondition still did not appear",
            "upper userspace surface",
        )
    )

    checks = {
        "v1016_input_present": bool(v1016),
        "v1016_upper_surface_started": v1016_upper_started,
        "v1016_mdm_helper_fd_positive": v1016_lower_fd_positive,
        "v1016_wlfw_missing_and_subsys_not_opened": v1016_no_wlfw_no_subsys,
        "v1016_guardrails_clean": v1016_guardrails_clean,
        "android_v1000_wlfw_chain_present": v1000_partial_or_full_wlfw,
        "android_v1000_service_window_chain_present": v1000_chain,
        "android_subsys_get_near_wlfw": android_subsys_near_wlfw,
        "android_v968_full_positive_chain_present": v968_full_positive,
        "gpio_transition_gap_secondary": gpio_transition_gap_is_secondary,
        "v1016_report_matches": v1016_report_matches,
    }
    optional = {
        "android_v1000_full_positive_chain_present": v1000_full_positive,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    passed = not blockers
    if passed:
        decision = "v1017-select-after-fd-upper-surface-subsys-window"
        reason = (
            "V1016 proves fd-positive upper-surface parity without WLFW while the WLFW-gated "
            "subsys child never opens; Android evidence places /dev/subsys_esoc0 get in the "
            "same narrow window as cnss-daemon wlfw_start and has a full WLFW/BDF/wlan0 positive chain"
        )
        next_step = "V1018 helper v173 source/build support for after-fd upper-surface scoped /dev/subsys_esoc0 window"
    else:
        decision = "v1017-lower-gap-classifier-incomplete"
        reason = "missing checks: " + ", ".join(blockers)
        next_step = "repair missing evidence or run Android read-only recapture before changing the live gate"

    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "optional_checks": optional,
        "timing": {
            "v1000_subsys_esoc0_get_to_wlfw_start_ms": v1000_subsys_to_wlfw_ms,
            "v1000_wlfw_start_to_subsys_esoc0_get_ms": v1000_wlfw_to_subsys_ms,
            "v968_wlfw_start_to_esoc0_get_ms": v968_wlfw_to_subsys_ms,
        },
        "selected_route": {
            "next_version": "V1018",
            "helper_version": "v173",
            "order_candidate": "after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window",
            "allow": [
                "same current-boot SELinux refresh",
                "mdm_helper /dev/esoc-0 fd predicate",
                "service-manager trio",
                "Wi-Fi HAL legacy/ext and wificond",
                "CNSS actors",
                "bounded child open of /dev/subsys_esoc0 after upper surface",
                "strict timeout and cleanup reboot if holder blocks",
            ],
            "forbid": [
                "raw eSoC controller ioctl path",
                "GPIO/sysfs/debugfs write",
                "IWifi.start",
                "qcwlanstate write",
                "scan/connect/link-up",
                "credential use",
                "DHCP/routes/external ping",
                "boot image or firmware mutation",
            ],
            "defer": [
                "Magisk early sampler until scoped subsystem window still fails and exact GPIO transition timing becomes necessary",
                "Wi-Fi scan/connect until WLFW/BDF/wlan0 or equivalent lower surface is proven",
            ],
        },
        "events": {
            "v1000": android_events,
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
    optional_rows = [[name, "PASS" if ok else "MISS"] for name, ok in manifest["optional_checks"].items()]
    timing_rows = [[name, value] for name, value in manifest["timing"].items()]
    route = manifest["selected_route"]
    return "\n".join(
        [
            "# V1017 V1016 Android Lower Gap Classifier",
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
            "## Optional Checks",
            "",
            markdown_table(["check", "result"], optional_rows),
            "",
            "## Timing",
            "",
            markdown_table(["measurement", "ms"], timing_rows),
            "",
            "## Selected Route",
            "",
            f"- next_version: `{route['next_version']}`",
            f"- helper_version: `{route['helper_version']}`",
            f"- order_candidate: `{route['order_candidate']}`",
            "",
            "### Allow",
            "",
            *[f"- {item}" for item in route["allow"]],
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
        "v1016": str(repo_path(args.v1016)),
        "v1016_sha256": sha256(args.v1016),
        "v1000_manifest": str(repo_path(args.v1000_manifest)),
        "v1000_manifest_sha256": sha256(args.v1000_manifest),
        "v1000_android_dmesg": str(repo_path(args.v1000_android_dmesg)),
        "v1000_android_dmesg_sha256": sha256(args.v1000_android_dmesg),
        "v968": str(repo_path(args.v968)),
        "v968_sha256": sha256(args.v968),
        "v1016_report": str(repo_path(args.v1016_report)),
        "v968_report": str(repo_path(args.v968_report)),
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
