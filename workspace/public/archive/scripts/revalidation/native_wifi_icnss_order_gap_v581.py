#!/usr/bin/env python3
"""V581 host-only Android/native ICNSS order-gap classifier.

This classifier compares the Android boot-complete Wi-Fi/ICNSS sequence against
the latest native V580 evidence. It does not talk to the device and cannot
start daemons, write qcwlanstate, scan, connect, route, or ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v581-icnss-order-gap")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt")
DEFAULT_V519_MANIFEST = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/manifest.json")
DEFAULT_V571_MANIFEST = Path("tmp/wifi/v571-qrtr-modem-readiness-delta/manifest.json")
DEFAULT_V580_MANIFEST = Path("tmp/wifi/v580-v579-postflight-icnss/manifest.json")
DEFAULT_NATIVE_DMESG = Path("tmp/wifi/v580-v579-postflight-icnss/native/dmesg.txt")
DEFAULT_NATIVE_HELPER = Path("tmp/wifi/v579-v95-companion-driver-state/native/v579-helper-run.txt")
SOURCE_REFERENCES = (
    "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"\[\s*(?P<time>[0-9]+(?:\.[0-9]+)?)\]")


@dataclass(frozen=True)
class Marker:
    name: str
    pattern: re.Pattern[str]
    stage: str
    required_before_retry: bool
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
    Marker("firmware_mounts", re.compile(r"mount.*(?:firmware_mnt|apnhlos|firmware-modem).*Success", re.I), "storage", True,
           "Android mounts firmware/modem partitions before WLAN firmware activity"),
    Marker("wlan_driver_load", re.compile(r"wlan: Loading driver", re.I), "driver-load", True,
           "QCACLD driver load starts"),
    Marker("wlan_state_initialized", re.compile(r"wlan_hdd_state .* initialized", re.I), "driver-load", True,
           "qcwlanstate char-device class is registered"),
    Marker("qrtr_modem_readiness_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I), "qrtr-modem", True,
           "kernel receives modem QRTR readiness"),
    Marker("qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'|exec_target = /vendor/bin/qrtr-ns|exec_target=/vendor/bin/qrtr-ns", re.I), "qrtr-modem", True,
           "QRTR namespace service starts"),
    Marker("qrtr_modem_readiness_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I), "qrtr-modem", True,
           "kernel replies to modem QRTR readiness"),
    Marker("sysmon_qmi_ready", re.compile(r"sysmon-qmi: ssctl_new_server: Connection established", re.I), "modem-companion", True,
           "sysmon QMI connects to modem/subsystem control"),
    Marker("service_notifier_ready", re.compile(r"service-notifier: service_notifier_new_server: Connection established", re.I), "modem-companion", True,
           "service-notifier QMI service appears"),
    Marker("wlan_pd_indication", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I), "modem-companion", True,
           "WLAN protection-domain indication arrives"),
    Marker("cnss_diag_start", re.compile(r"starting service 'cnss_diag'|exec_target\s*=\s*/vendor/bin/cnss_diag", re.I), "cnss-userspace", True,
           "cnss_diag starts"),
    Marker("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag|comm:cnss_diag|cnss_diag.*ctrl_getfamily", re.I), "cnss-userspace", True,
           "cnss_diag reaches cld80211 netlink"),
    Marker("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'|exec_target\s*=\s*/vendor/bin/cnss-daemon", re.I), "cnss-userspace", True,
           "cnss-daemon starts"),
    Marker("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon|comm:cnss-daemon|cnss-daemon.*ctrl_getfamily", re.I), "cnss-userspace", True,
           "cnss-daemon reaches cld80211 netlink"),
    Marker("cnss_daemon_wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.I), "wlfw", True,
           "cnss-daemon starts WLFW"),
    Marker("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request", re.I), "wlfw", True,
           "WLFW service request thread starts"),
    Marker("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I), "wlfw", True,
           "ICNSS QMI server connects"),
    Marker("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I), "firmware", True,
           "regulatory BDF download is requested"),
    Marker("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I), "firmware", True,
           "board-data BDF download is requested"),
    Marker("wifi_turning_on", re.compile(r"Wifi Turning On from UI", re.I), "qcwlanstate", False,
           "qcwlanstate ON path is attempted"),
    Marker("timed_out", re.compile(r"Timed-out|Timed-out waiting", re.I), "qcwlanstate", False,
           "native qcwlanstate wait timed out"),
    Marker("modules_not_initialized", re.compile(r"Modules not initialized just return", re.I), "qcwlanstate", False,
           "QCACLD module state is still uninitialized"),
    Marker("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready|FW ready event received|wma_wait_for_ready_event", re.I), "ready", True,
           "ICNSS/WMA firmware readiness is observed"),
    Marker("wlan0_event", re.compile(r"dev\s*:\s*wlan0\s*:\s*event", re.I), "ready", False,
           "wlan0 netdev appears"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--native-dmesg", type=Path, default=DEFAULT_NATIVE_DMESG)
    parser.add_argument("--native-helper-transcript", type=Path, default=DEFAULT_NATIVE_HELPER)
    parser.add_argument("--v519-manifest", type=Path, default=DEFAULT_V519_MANIFEST)
    parser.add_argument("--v571-manifest", type=Path, default=DEFAULT_V571_MANIFEST)
    parser.add_argument("--v580-manifest", type=Path, default=DEFAULT_V580_MANIFEST)
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


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


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
    return {
        "counts": counts,
        "first": {name: asdict(event) for name, event in first_by_marker.items()},
        "ordered_first": [asdict(event) for event in sorted(first_by_marker.values(), key=lambda item: item.index)],
        "focus_tail": [asdict(event) for event in events[-180:]],
    }


def present(summary: dict[str, Any], name: str) -> bool:
    return int((summary.get("counts") or {}).get(name, 0) or 0) > 0


def first_line(summary: dict[str, Any], name: str) -> str:
    event = (summary.get("first") or {}).get(name) or {}
    return str(event.get("line") or "")


def first_time(summary: dict[str, Any], name: str) -> float | None:
    event = (summary.get("first") or {}).get(name) or {}
    value = event.get("time")
    return value if isinstance(value, float) else None


def marker_by_name(name: str) -> Marker:
    for marker in MARKERS:
        if marker.name == name:
            return marker
    raise KeyError(name)


def missing_required(android: dict[str, Any], native: dict[str, Any]) -> list[str]:
    missing = []
    for marker in MARKERS:
        if marker.required_before_retry and present(android, marker.name) and not present(native, marker.name):
            missing.append(marker.name)
    return missing


def stage_gaps(missing: list[str]) -> dict[str, list[str]]:
    gaps: dict[str, list[str]] = {}
    for name in missing:
        gaps.setdefault(marker_by_name(name).stage, []).append(name)
    return gaps


def ordered_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in MARKERS:
        android_has = present(android, marker.name)
        native_has = present(native, marker.name)
        if not android_has and not native_has:
            continue
        rows.append([
            marker.name,
            marker.stage,
            "yes" if android_has else "no",
            "" if first_time(android, marker.name) is None else f"{first_time(android, marker.name):.3f}",
            "yes" if native_has else "no",
            "" if first_time(native, marker.name) is None else f"{first_time(native, marker.name):.3f}",
            "yes" if marker.required_before_retry else "no",
            marker.description,
        ])
    return rows


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(command: str,
                 android_exists: bool,
                 native_exists: bool,
                 v519: dict[str, Any],
                 v571: dict[str, Any],
                 v580: dict[str, Any],
                 android: dict[str, Any],
                 native: dict[str, Any],
                 missing: list[str],
                 gaps: dict[str, list[str]]) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "host-only; no evidence parsed", [], "run V581 classifier")
        return checks

    add_check(
        checks,
        "android-reference-present",
        "pass" if android_exists and present(android, "wlan_fw_ready") and present(android, "wlan0_event") else "blocked",
        "blocker",
        f"android_exists={android_exists} fw_ready={present(android, 'wlan_fw_ready')} wlan0={present(android, 'wlan0_event')}",
        [first_line(android, "qmi_server_connected"), first_line(android, "wlan_fw_ready")],
        "refresh Android Wi-Fi boot-complete baseline",
    )
    add_check(
        checks,
        "native-v580-reference-present",
        "pass" if native_exists and v580.get("decision") == "v580-delayed-clean-icnss-module-init-blocker-confirmed" else "blocked",
        "blocker",
        f"native_exists={native_exists} v580={v580.get('decision')} pass={v580.get('pass')}",
        [str(v580.get("path"))],
        "run V580 current postflight classifier first",
    )
    add_check(
        checks,
        "v519-consistent",
        "pass" if v519.get("decision") == "v519-qrtr-companion-service-gap-classified" else "warn",
        "warning",
        f"decision={v519.get('decision')} pass={v519.get('pass')}",
        [str(v519.get("path"))],
        "refresh V519 if Android/native QRTR baseline is stale",
    )
    add_check(
        checks,
        "v571-consistent",
        "pass" if v571.get("decision") == "v571-modem-readiness-not-entered" else "warn",
        "warning",
        f"decision={v571.get('decision')} pass={v571.get('pass')}",
        [str(v571.get("path"))],
        "refresh V571 if native QRTR readiness evidence changed",
    )
    add_check(
        checks,
        "native-qcwlanstate-reaches-driver",
        "pass" if present(native, "wifi_turning_on") and present(native, "timed_out") and present(native, "modules_not_initialized") else "blocked",
        "blocker",
        f"wifi_turning_on={present(native, 'wifi_turning_on')} timed_out={present(native, 'timed_out')} modules_not_initialized={present(native, 'modules_not_initialized')}",
        [first_line(native, "wifi_turning_on"), first_line(native, "timed_out"), first_line(native, "modules_not_initialized")],
        "do not pursue HAL retry until qcwlanstate lower dependency changes",
    )
    add_check(
        checks,
        "native-missing-modem-companion-readiness",
        "pass" if any(stage in gaps for stage in ("qrtr-modem", "modem-companion", "wlfw", "firmware")) else "blocked",
        "blocker",
        f"missing_required={missing}",
        [", ".join(f"{stage}:{','.join(names)}" for stage, names in sorted(gaps.items()))],
        "focus next work on Android/native QRTR modem companion ordering, not scan/connect",
    )
    add_check(
        checks,
        "ready-surface-absent-native",
        "pass" if not present(native, "wlan_fw_ready") and not present(native, "wlan0_event") else "blocked",
        "blocker",
        f"native_fw_ready={present(native, 'wlan_fw_ready')} native_wlan0={present(native, 'wlan0_event')}",
        [],
        "if native readiness appears, switch to scan-only gate",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], gaps: dict[str, list[str]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v581-icnss-order-gap-plan-ready", True, "plan-only; host-only comparator is ready", "run V581 classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v581-icnss-order-gap-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence before next Wi-Fi work"
    if "modem-companion" in gaps or "qrtr-modem" in gaps:
        return (
            "v581-native-missing-modem-qrtr-readiness-before-qcwlanstate",
            True,
            "Android reaches QRTR modem readiness and service-notifier/WLAN-PD before QMI/BDF/FW-ready; native reaches qcwlanstate/CNSS netlink but lacks those modem companion readiness markers",
            "plan V582 around QRTR modem readiness/service-notifier/sysmon gap; keep qcwlanstate/IWifi/scan/connect blocked",
        )
    if "wlfw" in gaps or "firmware" in gaps:
        return (
            "v581-native-missing-wlfw-firmware-stage",
            True,
            "native reaches early QRTR/CNSS markers but still lacks WLFW/QMI/BDF/FW-ready",
            "inspect cnss-daemon WLFW prerequisites before qcwlanstate retry",
        )
    return (
        "v581-icnss-order-gap-review",
        True,
        "order comparison captured but no canonical missing stage was selected",
        "inspect marker table before next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    marker_rows = manifest.get("marker_rows") or []
    gap_rows = [[stage, ", ".join(names)] for stage, names in sorted((manifest.get("stage_gaps") or {}).items())]
    android = manifest.get("android_summary") or {}
    native = manifest.get("native_summary") or {}
    return "\n".join([
        "# V581 ICNSS Order Gap Classifier",
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
        "## Stage Gaps",
        "",
        markdown_table(["stage", "missing native markers"], gap_rows) if gap_rows else "- none",
        "",
        "## Marker Order",
        "",
        markdown_table(["marker", "stage", "android", "android_time", "native", "native_time", "required", "description"], marker_rows),
        "",
        "## Android Counts",
        "",
        markdown_table(["marker", "count"], [[k, v] for k, v in sorted((android.get("counts") or {}).items()) if v]),
        "",
        "## Native Counts",
        "",
        markdown_table(["marker", "count"], [[k, v] for k, v in sorted((native.get("counts") or {}).items()) if v]),
        "",
        "## Source References",
        "",
        *[f"- {item}" for item in manifest["source_references"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v519 = load_json_if_exists(args.v519_manifest)
    v571 = load_json_if_exists(args.v571_manifest)
    v580 = load_json_if_exists(args.v580_manifest)
    android_exists, android_path, android_text = read_text_if_exists(args.android_dmesg)
    native_exists, native_path, native_text = read_text_if_exists(args.native_dmesg)
    helper_exists, helper_path, helper_text = read_text_if_exists(args.native_helper_transcript)
    native_combined_text = native_text + "\n" + helper_text
    android = extract_events(android_text) if args.command == "run" else extract_events("")
    native = extract_events(native_combined_text) if args.command == "run" else extract_events("")
    missing = missing_required(android, native) if args.command == "run" else []
    gaps = stage_gaps(missing)
    checks = build_checks(args.command, android_exists, native_exists, v519, v571, v580, android, native, missing, gaps)
    decision, pass_ok, reason, next_step = decide(args.command, checks, gaps)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": android_path,
            "native_dmesg": native_path,
            "native_helper_transcript": helper_path,
            "native_helper_transcript_exists": helper_exists,
            "v519_manifest": v519.get("path"),
            "v571_manifest": v571.get("path"),
            "v580_manifest": v580.get("path"),
        },
        "checks": [asdict(check) for check in checks],
        "missing_required_markers": missing,
        "stage_gaps": gaps,
        "marker_rows": ordered_rows(android, native) if args.command == "run" else [],
        "android_summary": android,
        "native_summary": native,
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
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
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
