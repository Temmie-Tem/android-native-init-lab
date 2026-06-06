#!/usr/bin/env python3
"""V589 host-only Android/native subsystem state-gap classifier.

This classifier compares the Android QRTR/sysmon/service-notifier/WLAN-PD
timeline against the V588 native companion-window modem/esoc subsystem values.
It does not talk to the device, start daemons, write sysfs/qcwlanstate, scan,
connect, route, or ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v589-android-subsys-state-gap")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_STATE_SAMPLE = Path("tmp/wifi/v589-android-subsys-state-sample/android-subsys-state.txt")
DEFAULT_V519_MANIFEST = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/manifest.json")
DEFAULT_V582_MANIFEST = Path("tmp/wifi/v582-modem-companion-classifier/manifest.json")
DEFAULT_V588_MANIFEST = Path("tmp/wifi/v588-modem-subsys-window-values/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"\[\s*(?P<time>[0-9]+(?:\.[0-9]+)?)\]")
STATE_RE = re.compile(r"(?P<name>mss|modem|mdm3|esoc0)[^=\n:]*[:=]\s*(?P<state>ONLINE|OFFLINE|OFFLINING|RUNNING|BOOTING)", re.I)


@dataclass(frozen=True)
class Marker:
    name: str
    pattern: re.Pattern[str]
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
    Marker("qrtr_modem_readiness_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
           "Android receives modem QRTR readiness"),
    Marker("qrtr_modem_readiness_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
           "Android replies to modem QRTR readiness"),
    Marker("sysmon_qmi_modem", re.compile(r"sysmon-qmi: .*modem's SSCTL service", re.I),
           "sysmon QMI connects to modem SSCTL"),
    Marker("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server: .* 180 service", re.I),
           "service-notifier appears for WLAN-PD service id 180"),
    Marker("wlan_pd_indication", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I),
           "WLAN protection-domain indication arrives"),
    Marker("sysmon_qmi_esoc0", re.compile(r"sysmon-qmi: .*esoc0's SSCTL service", re.I),
           "sysmon QMI connects to esoc0 SSCTL"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-state-sample", type=Path, default=DEFAULT_ANDROID_STATE_SAMPLE)
    parser.add_argument("--v519-manifest", type=Path, default=DEFAULT_V519_MANIFEST)
    parser.add_argument("--v582-manifest", type=Path, default=DEFAULT_V582_MANIFEST)
    parser.add_argument("--v588-manifest", type=Path, default=DEFAULT_V588_MANIFEST)
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
    }


def present(summary: dict[str, Any], name: str) -> bool:
    return int((summary.get("counts") or {}).get(name, 0) or 0) > 0


def first_time(summary: dict[str, Any], name: str) -> float | None:
    value = ((summary.get("first") or {}).get(name) or {}).get("time")
    return value if isinstance(value, float) else None


def first_line(summary: dict[str, Any], name: str) -> str:
    return str(((summary.get("first") or {}).get(name) or {}).get("line") or "")


def marker_rows(summary: dict[str, Any]) -> list[list[str]]:
    rows = []
    for marker in MARKERS:
        time = first_time(summary, marker.name)
        rows.append([
            marker.name,
            "yes" if present(summary, marker.name) else "no",
            "" if time is None else f"{time:.3f}",
            marker.description,
            first_line(summary, marker.name),
        ])
    return rows


def parse_state_sample(text: str) -> dict[str, str]:
    states: dict[str, str] = {}
    for line in strip_ansi(text).splitlines():
        match = STATE_RE.search(line)
        if match:
            states[match.group("name").lower()] = match.group("state").upper()
    return states


def v588_values(v588: dict[str, Any]) -> dict[str, str]:
    live = v588.get("live_result") or {}
    values = live.get("window_subsys_values") or {}
    return {
        "mss_state": str(values.get("mss_state") or live.get("mss_state") or ""),
        "mdm3_state": str(values.get("mdm3_state") or live.get("mdm3_state") or ""),
        "mss_name": str(values.get("mss_name") or ""),
        "mdm3_name": str(values.get("mdm3_name") or ""),
        "rpmsg_drivers_autoprobe": str(values.get("rpmsg_drivers_autoprobe") or ""),
        "subsys_value_captures": str((live.get("keys") or {}).get("wifi_companion_start.surface_window.subsys_value_captures") or ""),
    }


def lower_marker_counts(v588: dict[str, Any]) -> dict[str, int]:
    counts = ((v588.get("dmesg_summary") or {}).get("counts") or {})
    names = (
        "qrtr_modem_readiness",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_thread",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0_event",
        "wma_service_ready",
    )
    return {name: int(counts.get(name, 0) or 0) for name in names}


def all_zero(counts: dict[str, int]) -> bool:
    return all(value == 0 for value in counts.values())


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(command: str,
                 android_dmesg_exists: bool,
                 android_state_exists: bool,
                 android: dict[str, Any],
                 android_states: dict[str, str],
                 v519: dict[str, Any],
                 v582: dict[str, Any],
                 v588: dict[str, Any],
                 values: dict[str, str],
                 marker_counts: dict[str, int]) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "host-only; no evidence parsed", [], "run V589 classifier")
        return checks

    add_check(
        checks,
        "android-readiness-timeline-present",
        "pass" if android_dmesg_exists and present(android, "qrtr_modem_readiness_rx") and present(android, "sysmon_qmi_modem") and present(android, "service_notifier_180") and present(android, "wlan_pd_indication") else "blocked",
        "blocker",
        f"dmesg={android_dmesg_exists} qrtr_rx={present(android, 'qrtr_modem_readiness_rx')} sysmon_modem={present(android, 'sysmon_qmi_modem')} service180={present(android, 'service_notifier_180')} wlan_pd={present(android, 'wlan_pd_indication')}",
        [first_line(android, "qrtr_modem_readiness_rx"), first_line(android, "service_notifier_180"), first_line(android, "wlan_pd_indication")],
        "refresh Android QRTR/modem readiness baseline",
    )
    add_check(
        checks,
        "v519-reference-consistent",
        "pass" if v519.get("decision") == "v519-qrtr-companion-service-gap-classified" and v519.get("pass") is True else "warn",
        "warning",
        f"decision={v519.get('decision')} pass={v519.get('pass')}",
        [str(v519.get("path"))],
        "refresh V519 if Android/native QRTR baseline is stale",
    )
    add_check(
        checks,
        "v582-kernel-path-classification-present",
        "pass" if v582.get("decision") == "v582-kernel-modem-companion-readiness-gap-classified" and v582.get("pass") is True else "warn",
        "warning",
        f"decision={v582.get('decision')} pass={v582.get('pass')}",
        [str(v582.get("path"))],
        "refresh V582 if sysmon/service-notifier classification is stale",
    )
    add_check(
        checks,
        "v588-native-window-present",
        "pass" if v588.get("decision") == "v588-modem-subsys-offline-window" and v588.get("pass") is True else "blocked",
        "blocker",
        f"decision={v588.get('decision')} pass={v588.get('pass')}",
        [str(v588.get("path"))],
        "run V588 before classifying subsystem state gap",
    )
    add_check(
        checks,
        "native-subsys-offlining-captured",
        "pass" if values.get("mss_state") == "OFFLINING" and values.get("mdm3_state") == "OFFLINING" else "blocked",
        "blocker",
        f"mss_state={values.get('mss_state')} mdm3_state={values.get('mdm3_state')}",
        [f"mss={values.get('mss_state')}", f"mdm3={values.get('mdm3_state')}"],
        "refresh V588 if native subsystem values changed",
    )
    add_check(
        checks,
        "native-lower-markers-absent",
        "pass" if all_zero(marker_counts) else "blocked",
        "blocker",
        str(marker_counts),
        [],
        "if any lower marker appears, advance to bounded qcwlanstate/HAL retry",
    )
    add_check(
        checks,
        "android-direct-subsys-state-sample",
        "pass" if android_state_exists and android_states else "warn",
        "warning",
        f"exists={android_state_exists} states={android_states}",
        [],
        "boot Android and capture read-only subsystem state sample if this remains absent",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str,
           checks: list[Check],
           android_states: dict[str, str],
           values: dict[str, str]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v589-android-subsys-state-gap-plan-ready", True, "plan-only; host-only classifier is ready", "run V589 classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v589-android-subsys-state-gap-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence before next Wi-Fi work"

    native_offlining = values.get("mss_state") == "OFFLINING" and values.get("mdm3_state") == "OFFLINING"
    android_non_offline = any(state not in {"OFFLINE", "OFFLINING"} for state in android_states.values())
    if native_offlining and android_non_offline:
        return (
            "v589-android-native-subsys-state-delta-confirmed",
            True,
            f"native V588 window is OFFLINING while Android state sample has non-offline states: {android_states}",
            "plan the smallest safe subsystem-readiness trigger; keep HAL/scan/connect blocked until lower markers change",
        )
    if native_offlining and not android_states:
        return (
            "v589-android-subsys-state-sample-needed",
            True,
            "native V588 window captured modem/esoc OFFLINING and Android reaches QRTR/sysmon/service-notifier/WLAN-PD, but current Android evidence lacks direct subsystem state values",
            "collect Android read-only subsystem state around boot/Wi-Fi readiness, then decide whether a subsystem readiness trigger is justified",
        )
    if native_offlining:
        return (
            "v589-subsys-offlining-not-decisive",
            True,
            f"native is OFFLINING, but Android state sample does not prove a non-offline delta: {android_states}",
            "refresh Android state sampling with timestamps before live readiness triggers",
        )
    return (
        "v589-subsys-state-gap-review",
        True,
        "comparison completed but native subsystem state no longer matches the expected OFFLINING blocker",
        "inspect V588/V589 evidence before choosing next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    values = manifest.get("v588_values") or {}
    marker_counts = manifest.get("v588_lower_marker_counts") or {}
    return "\n".join([
        "# V589 Android/Native Subsystem State Gap Classifier",
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
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Android Readiness Timeline",
        "",
        markdown_table(["marker", "present", "time", "description", "line"], manifest.get("android_marker_rows") or []),
        "",
        "## Native V588 Window Values",
        "",
        markdown_table(["name", "value"], [[key, value] for key, value in values.items()]),
        "",
        "## Native Lower Marker Counts",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in marker_counts.items()]),
        "",
        "## Android Direct State Sample",
        "",
        markdown_table(["name", "state"], [[key, value] for key, value in (manifest.get("android_state_sample") or {}).items()]) if manifest.get("android_state_sample") else "- none in current evidence",
        "",
        "## Evidence",
        "",
        *[f"- `{item}`" for item in manifest["evidence_paths"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v519 = load_json_if_exists(args.v519_manifest)
    v582 = load_json_if_exists(args.v582_manifest)
    v588 = load_json_if_exists(args.v588_manifest)
    android_exists, android_path, android_text = read_text_if_exists(args.android_dmesg)
    android_state_exists, android_state_path, android_state_text = read_text_if_exists(args.android_state_sample)
    android = extract_events(android_text) if args.command == "run" else extract_events("")
    android_states = parse_state_sample(android_state_text) if args.command == "run" else {}
    values = v588_values(v588) if args.command == "run" else {}
    marker_counts = lower_marker_counts(v588) if args.command == "run" else {}
    checks = build_checks(args.command, android_exists, android_state_exists, android, android_states, v519, v582, v588, values, marker_counts)
    decision, pass_ok, reason, next_step = decide(args.command, checks, android_states, values)
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
            "android_state_sample": android_state_path,
            "android_state_sample_exists": android_state_exists,
            "v519_manifest": v519.get("path"),
            "v582_manifest": v582.get("path"),
            "v588_manifest": v588.get("path"),
        },
        "checks": [asdict(check) for check in checks],
        "android_summary": android,
        "android_marker_rows": marker_rows(android) if args.command == "run" else [],
        "android_state_sample": android_states,
        "v588_values": values,
        "v588_lower_marker_counts": marker_counts,
        "evidence_paths": [android_path, android_state_path, str(v519.get("path")), str(v582.get("path")), str(v588.get("path"))],
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
