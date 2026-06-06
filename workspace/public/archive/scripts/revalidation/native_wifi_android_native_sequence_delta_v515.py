#!/usr/bin/env python3
"""V515 host-only Android/native ICNSS sequence comparator.

This tool does not talk to the device. It compares an Android boot-complete
Wi-Fi/ICNSS evidence log against the latest native-init V514 readiness evidence
and classifies the next safe gate before any additional qcwlanstate retry,
scan, connect, DHCP, route change, or external ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v515-android-native-sequence-delta")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt")
DEFAULT_NATIVE_DMESG = Path("tmp/wifi/v514-icnss-module-readiness/native/dmesg.txt")
DEFAULT_V514_MANIFEST = Path("tmp/wifi/v514-icnss-module-readiness/manifest.json")
SOURCE_REFERENCES = (
    "https://android.googlesource.com/device/google/marlin/+/e8ea1d15b6e35e4ba0c1eeeba47fe712af0fba92/init.common.rc",
    "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m2/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"\[\s*(?P<time>[0-9]+(?:\.[0-9]+)?)\]")


@dataclass(frozen=True)
class Marker:
    name: str
    pattern: re.Pattern[str]
    required_for_fw_ready: bool
    description: str


@dataclass(frozen=True)
class Event:
    marker: str
    index: int
    time: float | None
    line: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


MARKERS: tuple[Marker, ...] = (
    Marker("firmware_mounts", re.compile(r"mount.*apnhlos.*?/vendor/firmware_mnt.*Success", re.IGNORECASE), True,
           "Android mounts firmware partitions before WLAN firmware/BDF activity"),
    Marker("wlan_loading_driver", re.compile(r"wlan: Loading driver", re.IGNORECASE), True,
           "QCACLD driver load starts"),
    Marker("wlan_state_initialized", re.compile(r"wlan_hdd_state .* initialized", re.IGNORECASE), True,
           "qcwlanstate/dev_wlan layer is present"),
    Marker("qrtr_modem_readiness", re.compile(r"qrtr: Modem QMI Readiness", re.IGNORECASE), True,
           "QRTR/modem readiness is observed before WLFW connection"),
    Marker("macloader_mac", re.compile(r"icnss: Assigning MAC from Macloader", re.IGNORECASE), False,
           "Android obtains WLAN MAC from Macloader"),
    Marker("wifi_hal_legacy_start", re.compile(r"starting service 'vendor\.wifi_hal_legacy'", re.IGNORECASE), False,
           "Samsung/Qualcomm legacy Wi-Fi HAL starts"),
    Marker("wifi_hal_ext_start", re.compile(r"starting service 'vendor\.wifi_hal_ext'", re.IGNORECASE), False,
           "Samsung Wi-Fi extension HAL starts"),
    Marker("qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'", re.IGNORECASE), True,
           "QRTR namespace service starts"),
    Marker("cnss_diag_start", re.compile(r"starting service 'cnss_diag'", re.IGNORECASE), True,
           "cnss_diag starts before cnss-daemon"),
    Marker("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag|comm:cnss_diag", re.IGNORECASE), True,
           "cnss_diag opens the CNSS generic netlink path"),
    Marker("wificond_start", re.compile(r"starting service 'wificond'", re.IGNORECASE), False,
           "Android Wi-Fi framework support process starts"),
    Marker("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'", re.IGNORECASE), True,
           "cnss-daemon service starts"),
    Marker("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon|comm:cnss-daemon|cnss-daemon.*ctrl_getfamily", re.IGNORECASE), True,
           "cnss-daemon opens CNSS/cld80211 netlink"),
    Marker("cnss_daemon_wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.IGNORECASE), True,
           "cnss-daemon starts WLFW"),
    Marker("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request", re.IGNORECASE), True,
           "cnss-daemon starts the WLFW service request thread"),
    Marker("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE), True,
           "kernel ICNSS QMI server connects"),
    Marker("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE), True,
           "regulatory BDF download is requested"),
    Marker("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE), True,
           "board-data BDF download is requested"),
    Marker("wifi_turning_on", re.compile(r"Wifi Turning On from UI", re.IGNORECASE), True,
           "qcwlanstate ON path is attempted"),
    Marker("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE), True,
           "ICNSS reports firmware readiness"),
    Marker("wcnss_cfg_request", re.compile(r"WCNSS_qcom_cfg\.ini", re.IGNORECASE), True,
           "firmware_class requests WCNSS_qcom_cfg.ini"),
    Marker("wma_service_ready", re.compile(r"wma_rx_service_ready_event|FW ready event received", re.IGNORECASE), True,
           "WMA target firmware ready event is observed"),
    Marker("wlan0_event", re.compile(r"dev\s*:\s*wlan0\s*:\s*event", re.IGNORECASE), True,
           "wlan0 netdev appears"),
    Marker("swlan0_event", re.compile(r"dev\s*:\s*swlan0\s*:\s*event", re.IGNORECASE), False,
           "secondary Samsung WLAN interface appears"),
    Marker("timed_out", re.compile(r"Timed-out!!", re.IGNORECASE), False,
           "native qcwlanstate/ICNSS wait timed out"),
    Marker("modules_not_initialized", re.compile(r"Modules not initialized just return", re.IGNORECASE), False,
           "QCACLD module state is still uninitialized"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--native-dmesg", type=Path, default=DEFAULT_NATIVE_DMESG)
    parser.add_argument("--v514-manifest", type=Path, default=DEFAULT_V514_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def dmesg_time(line: str) -> float | None:
    match = DMESG_TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("time"))
    except ValueError:
        return None


def read_text_if_exists(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def extract_events(text: str) -> dict[str, Any]:
    events: list[Event] = []
    first_by_marker: dict[str, Event] = {}
    counts = {marker.name: 0 for marker in MARKERS}
    for index, raw_line in enumerate(text.splitlines()):
        line = strip_ansi(raw_line).strip()
        if not line:
            continue
        for marker in MARKERS:
            if marker.pattern.search(line):
                event = Event(marker.name, index, dmesg_time(line), line)
                events.append(event)
                counts[marker.name] += 1
                first_by_marker.setdefault(marker.name, event)
    ordered = [asdict(event) for event in sorted(first_by_marker.values(), key=lambda item: item.index)]
    return {
        "counts": counts,
        "first": {name: asdict(event) for name, event in first_by_marker.items()},
        "ordered_first": ordered,
        "focus_tail": [asdict(event) for event in events[-160:]],
    }


def load_v514(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "exists": True,
        "path": str(resolved),
        "decision": data.get("decision"),
        "pass": data.get("pass"),
        "reason": data.get("reason"),
        "next_step": data.get("next_step"),
        "device_mutations": data.get("device_mutations"),
        "wifi_bringup_executed": data.get("wifi_bringup_executed"),
    }


def present(summary: dict[str, Any], name: str) -> bool:
    return (summary.get("counts") or {}).get(name, 0) > 0


def first_line(summary: dict[str, Any], name: str) -> str:
    event = (summary.get("first") or {}).get(name) or {}
    return str(event.get("line") or "")


def first_time(summary: dict[str, Any], name: str) -> float | None:
    event = (summary.get("first") or {}).get(name) or {}
    value = event.get("time")
    return value if isinstance(value, float) else None


def missing_required(android: dict[str, Any], native: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for marker in MARKERS:
        if marker.required_for_fw_ready and present(android, marker.name) and not present(native, marker.name):
            missing.append(marker.name)
    return missing


def ordered_delta_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for marker in MARKERS:
        android_has = present(android, marker.name)
        native_has = present(native, marker.name)
        if not android_has and not native_has:
            continue
        rows.append([
            marker.name,
            "yes" if android_has else "no",
            "" if first_time(android, marker.name) is None else f"{first_time(android, marker.name):.3f}",
            "yes" if native_has else "no",
            "" if first_time(native, marker.name) is None else f"{first_time(native, marker.name):.3f}",
            "required" if marker.required_for_fw_ready else "context",
            marker.description,
        ])
    return rows


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(command: str,
                 android_exists: bool,
                 native_exists: bool,
                 v514: dict[str, Any],
                 android: dict[str, Any],
                 native: dict[str, Any],
                 missing: list[str]) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "host-only; no log parsing required", [], "run V515 comparator")
        return checks

    add_check(checks, "android-reference-present", "pass" if android_exists else "blocked", "blocker",
              f"android_events={len(android.get('ordered_first') or [])}",
              [first_line(android, "wlan_fw_ready"), first_line(android, "wlan0_event")],
              "refresh Android baseline before deriving native order")
    add_check(checks, "native-reference-present", "pass" if native_exists else "blocked", "blocker",
              f"native_events={len(native.get('ordered_first') or [])}",
              [first_line(native, "wifi_turning_on"), first_line(native, "timed_out")],
              "run V514 read-only readiness classifier first")
    add_check(checks, "v514-timeout-classified", "pass" if v514.get("decision") == "v514-wlan-module-init-timeout-classified" else "blocked", "blocker",
              f"decision={v514.get('decision')}", [str(v514.get("path"))],
              "obtain canonical V514 timeout classification before planning V516")
    add_check(checks, "android-fw-ready-sequence", "pass" if present(android, "wlan_fw_ready") and present(android, "wlan0_event") else "blocked", "blocker",
              f"fw_ready={present(android, 'wlan_fw_ready')} wlan0={present(android, 'wlan0_event')}",
              [first_line(android, "wlan_fw_ready"), first_line(android, "wlan0_event")],
              "capture Android boot-complete Wi-Fi evidence with firmware-ready and wlan0 markers")
    add_check(checks, "native-no-fw-ready", "pass" if not present(native, "wlan_fw_ready") and not present(native, "wlan0_event") else "warn", "warning",
              f"fw_ready={present(native, 'wlan_fw_ready')} wlan0={present(native, 'wlan0_event')}",
              [first_line(native, "wlan_fw_ready"), first_line(native, "wlan0_event")],
              "if native already exposes wlan0, skip to scan-only")
    add_check(checks, "native-timeout-pattern", "pass" if present(native, "wifi_turning_on") and present(native, "timed_out") and present(native, "modules_not_initialized") else "blocked", "blocker",
              f"wifi_on={present(native, 'wifi_turning_on')} timeout={present(native, 'timed_out')} modules_uninit={present(native, 'modules_not_initialized')}",
              [first_line(native, "wifi_turning_on"), first_line(native, "timed_out"), first_line(native, "modules_not_initialized")],
              "keep qcwlanstate retry blocked until userspace readiness markers appear")
    add_check(checks, "required-marker-gap", "pass" if missing else "warn", "warning",
              "missing_native_required=" + ",".join(missing[:16]),
              [first_line(android, name) for name in missing[:8]],
              "build V516 bounded cnss_diag/cnss-daemon WLFW readiness proof")
    add_check(checks, "cnss-userspace-gap", "pass" if {"cnss_diag_start", "cnss_daemon_wlfw_start", "qmi_server_connected", "bdf_bdwlan"}.issubset(set(missing)) else "review", "info",
              f"cnss_diag={present(native, 'cnss_diag_start')} wlfw={present(native, 'cnss_daemon_wlfw_start')} qmi={present(native, 'qmi_server_connected')} bdf={present(native, 'bdf_bdwlan')}",
              [first_line(android, "cnss_diag_start"), first_line(android, "cnss_daemon_wlfw_start"), first_line(android, "qmi_server_connected"), first_line(android, "bdf_bdwlan")],
              "start with userspace sequence, not scan/connect")
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], missing: list[str], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v515-android-native-sequence-delta-plan-ready", True, "host-only plan; no device command executed", "run V515 comparator"
    blockers = blocking_checks(checks)
    if blockers:
        return "v515-android-native-sequence-delta-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing baseline evidence"
    if missing and present(native, "wifi_turning_on") and present(native, "timed_out"):
        return (
            "v515-android-native-sequence-gap-classified",
            True,
            "Android reaches CNSS/WLFW/QMI/BDF/FW-ready before wlan0, while native reaches qcwlanstate ON then times out without those markers",
            "implement V516 bounded cnss_diag + cnss-daemon WLFW readiness proof before any scan/connect",
        )
    return "v515-android-native-sequence-delta-review", True, "baseline comparison completed but gap shape is not canonical", "inspect marker table before live work"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in checks]
    marker_rows = manifest.get("marker_delta_rows") or []
    missing_rows = [[name, first_line(manifest["android_summary"], name)] for name in manifest.get("missing_required_native_markers") or []]
    android_order = manifest.get("android_summary", {}).get("ordered_first") or []
    native_order = manifest.get("native_summary", {}).get("ordered_first") or []
    return "\n".join([
        "# V515 Android/Native ICNSS Sequence Delta",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Marker Delta",
        "",
        markdown_table(["marker", "android", "android_t", "native", "native_t", "class", "description"], marker_rows),
        "",
        "## Missing Native Required Markers",
        "",
        markdown_table(["marker", "android evidence"], missing_rows) if missing_rows else "- none",
        "",
        "## Android Ordered First Markers",
        "",
        "\n".join(f"- `{item['marker']}` `{item.get('time')}` {item['line'][:220]}" for item in android_order[:40]) if android_order else "- none",
        "",
        "## Native Ordered First Markers",
        "",
        "\n".join(f"- `{item['marker']}` `{item.get('time')}` {item['line'][:220]}" for item in native_order[:40]) if native_order else "- none",
        "",
        "## Source References",
        "",
        *[f"- {item}" for item in manifest["source_references"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "plan":
        android_exists, android_path, android_text = True, str(repo_path(args.android_dmesg)), ""
        native_exists, native_path, native_text = True, str(repo_path(args.native_dmesg)), ""
        v514 = {"exists": True, "path": str(repo_path(args.v514_manifest)), "decision": "plan-only"}
    else:
        android_exists, android_path, android_text = read_text_if_exists(args.android_dmesg)
        native_exists, native_path, native_text = read_text_if_exists(args.native_dmesg)
        v514 = load_v514(args.v514_manifest)
        if android_exists:
            store.write_text("inputs/android-dmesg-wifi-cnss-tail.txt", android_text.rstrip() + "\n")
        if native_exists:
            store.write_text("inputs/native-v514-dmesg.txt", native_text.rstrip() + "\n")

    android_summary = extract_events(android_text)
    native_summary = extract_events(native_text)
    missing = missing_required(android_summary, native_summary)
    checks = build_checks(args.command, android_exists, native_exists, v514, android_summary, native_summary, missing)
    decision, pass_ok, reason, next_step = decide(args.command, checks, missing, native_summary)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": {"exists": android_exists, "path": android_path},
            "native_dmesg": {"exists": native_exists, "path": native_path},
            "v514_manifest": v514,
        },
        "checks": [asdict(check) for check in checks],
        "android_summary": android_summary,
        "native_summary": native_summary,
        "missing_required_native_markers": missing,
        "marker_delta_rows": ordered_delta_rows(android_summary, native_summary),
        "source_references": list(SOURCE_REFERENCES),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("inputs")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
