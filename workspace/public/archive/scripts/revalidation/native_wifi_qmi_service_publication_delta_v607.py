#!/usr/bin/env python3
"""V607 host-only QMI service-publication delta classifier.

This classifier compares the V598 service-notifier-positive native baseline
with the V606 helper-v102 replay. It is intentionally host-only: it does not
contact the device, start daemons, send QRTR/QMI payloads, start Wi-Fi HAL,
write qcwlanstate, scan, connect, use credentials, run DHCP, change routes, or
ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v607-qmi-service-publication-delta")
DEFAULT_V598_DIR = Path("tmp/wifi/v598-modem-holder-wlfw-readback")
DEFAULT_V606_DIR = Path("tmp/wifi/v606-v102-baseline-wlfw-readback-live")
DEFAULT_V603_DIR = Path("tmp/wifi/v603-qrtr-first-service-manager-live")
DEFAULT_V604B_DIR = Path("tmp/wifi/v604b-cnss-first-service-manager-live")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
HELPER_RE = re.compile(r'A90_EXECNS_BEGIN\s+version="([^"]+)"')


@dataclass(frozen=True)
class CaseInput:
    label: str
    run_dir: Path
    required: bool = True


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("binder_ioctl_unsupported", re.compile(r"binder: .*ioctl .* returned -22|BINDER_ENABLE_ONEWAY", re.I)),
    ("binder_transaction_failed", re.compile(r"binder: .*transaction failed|binder transaction failed", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|wlfw_start", re.I)),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request|wlfw.*thread", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready|WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
)

MATRIX_MARKERS = [
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "service_notifier_180",
    "service_notifier_74",
    "wlan_pd",
    "cnss_diag_netlink",
    "cnss_daemon_netlink",
    "binder_ioctl_unsupported",
    "binder_transaction_failed",
    "wlfw_start",
    "wlfw_thread",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
]

FORBIDDEN_ACTIONS = [
    "device command",
    "QRTR/QMI payload",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "qcwlanstate write",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v598-dir", type=Path, default=DEFAULT_V598_DIR)
    parser.add_argument("--v606-dir", type=Path, default=DEFAULT_V606_DIR)
    parser.add_argument("--v603-dir", type=Path, default=DEFAULT_V603_DIR)
    parser.add_argument("--v604b-dir", type=Path, default=DEFAULT_V604B_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_binary_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def parse_events(text: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        match = TS_RE.match(line)
        timestamp = float(match.group("ts")) if match else None
        for marker, pattern in MARKERS:
            if pattern.search(line):
                events.append(Event(marker, timestamp, line))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    found: dict[str, Event] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def count_by_marker(events: list[Event]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def parse_keys(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def parse_helper_marker(text: str) -> str:
    match = HELPER_RE.search(text)
    return match.group(1) if match else ""


def parse_helper_version(marker: str) -> str:
    match = re.search(r"\bv([0-9]+)\b", marker)
    return match.group(1) if match else ""


def first_time(found: dict[str, Event], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    newer_time = first_time(found, newer)
    older_time = first_time(found, older)
    if newer_time is None or older_time is None:
        return None
    return round((newer_time - older_time) * 1000.0, 3)


def live_dict(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live")
    return live if isinstance(live, dict) else {}


def readback_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    readback = live_dict(manifest).get("qrtr_readback") or {}
    return {
        "send_attempted": str(readback.get("send_attempted", "")),
        "service_events": int(readback.get("service_events") or 0),
        "end_of_list": int(readback.get("end_of_list") or 0),
        "timeouts": int(readback.get("timeouts") or 0),
        "qmi_attempted": int(readback.get("qmi_attempted") or 0),
    }


def helper_keys(keys: dict[str, str]) -> dict[str, str]:
    wanted = [
        "wifi_companion_start.order",
        "wifi_companion_start.result",
        "wifi_companion_start.timed_out",
        "wifi_companion_start.child_started",
        "wifi_companion_start.with_service_manager",
        "wifi_companion_start.with_vnd_service_manager",
        "wifi_companion_start.service_manager",
        "wifi_companion_start.qrtr_nameservice_readback",
        "wifi_companion_start.qmi_payload",
        "wifi_companion_start.net_before.qipcrtr_sockets",
        "wifi_companion_start.net_after_spawn.qipcrtr_sockets",
        "wifi_companion_start.net_window.qipcrtr_sockets",
        "wifi_companion_start.net_after_cleanup.qipcrtr_sockets",
    ]
    return {key: keys.get(key, "") for key in wanted}


def surface_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    live = live_dict(manifest)
    markers = (live.get("markers") or {}).get("counts") or {}
    return {
        "helper_result": live.get("helper_result"),
        "mss_after_holder": live.get("mss_after_holder"),
        "mss_after_companion": live.get("mss_after_companion"),
        "mdm3_after_companion": live.get("mdm3_after_companion"),
        "firmware_class_path": live.get("firmware_class_path"),
        "mounted_hits": live.get("mounted_hits") or {},
        "modem_blob_visible": live.get("modem_blob_visible") or {},
        "manifest_marker_counts": markers,
    }


def summarize_case(case: CaseInput) -> dict[str, Any]:
    run_dir = repo_path(case.run_dir)
    manifest_path = run_dir / "manifest.json"
    dmesg_path = run_dir / "native" / "dmesg-delta.txt"
    companion_path = run_dir / "native" / "companion-start-only-with-holder.txt"
    manifest = load_json(manifest_path)
    dmesg = read_text(dmesg_path)
    companion_text = read_binary_text(companion_path)
    events = parse_events(dmesg)
    found = first_by_marker(events)
    counts = count_by_marker(events)
    keys = parse_keys(companion_text)
    helper_marker = parse_helper_marker(companion_text)
    return {
        "label": case.label,
        "required": case.required,
        "exists": run_dir.exists() and manifest_path.exists() and dmesg_path.exists(),
        "run_dir": str(run_dir),
        "manifest_path": str(manifest_path),
        "dmesg_path": str(dmesg_path),
        "companion_path": str(companion_path),
        "manifest_decision": manifest.get("decision"),
        "manifest_pass": manifest.get("pass"),
        "manifest_generated_at": manifest.get("generated_at"),
        "v490_manifest": manifest.get("v490_manifest") or {},
        "helper_marker": helper_marker,
        "helper_version": parse_helper_version(helper_marker),
        "helper": helper_keys(keys),
        "surface": surface_summary(manifest),
        "readback": readback_summary(manifest),
        "counts": {marker: counts.get(marker, 0) for marker in MATRIX_MARKERS},
        "first": {
            marker: asdict(event)
            for marker, event in found.items()
            if marker in MATRIX_MARKERS
        },
        "delta_ms": {
            "qrtr_rx_to_tx": delta_ms(found, "qrtr_tx", "qrtr_rx"),
            "qrtr_tx_to_sysmon": delta_ms(found, "sysmon_modem", "qrtr_tx"),
            "sysmon_to_service_notifier_180": delta_ms(found, "service_notifier_180", "sysmon_modem"),
            "sysmon_to_cnss_diag": delta_ms(found, "cnss_diag_netlink", "sysmon_modem"),
            "sysmon_to_cnss_daemon": delta_ms(found, "cnss_daemon_netlink", "sysmon_modem"),
            "service_notifier_180_to_cnss_diag": delta_ms(found, "cnss_diag_netlink", "service_notifier_180"),
            "cnss_daemon_to_binder_failed": delta_ms(found, "binder_transaction_failed", "cnss_daemon_netlink"),
        },
        "focus_tail": [asdict(event) for event in events[-80:]],
    }


def same_value(left: Any, right: Any) -> bool:
    return left == right


def near_ms(left: float | None, right: float | None, tolerance_ms: float) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= tolerance_ms


def classify(cases: dict[str, dict[str, Any]]) -> tuple[str, bool, str, str, dict[str, Any]]:
    v598 = cases.get("v598-positive", {})
    v606 = cases.get("v606-v102-replay", {})
    diagnostics: dict[str, Any] = {
        "required_inputs_present": bool(v598.get("exists")) and bool(v606.get("exists")),
    }
    if not diagnostics["required_inputs_present"]:
        return (
            "v607-evidence-insufficient",
            False,
            "required V598 or V606 evidence is missing",
            "restore required evidence before selecting another live gate",
            diagnostics,
        )

    v598_counts = v598.get("counts") or {}
    v606_counts = v606.get("counts") or {}
    v598_delta = v598.get("delta_ms") or {}
    v606_delta = v606.get("delta_ms") or {}
    v598_helper = v598.get("helper") or {}
    v606_helper = v606.get("helper") or {}
    v598_surface = v598.get("surface") or {}
    v606_surface = v606.get("surface") or {}
    v598_readback = v598.get("readback") or {}
    v606_readback = v606.get("readback") or {}

    service_regressed = v598_counts.get("service_notifier_180", 0) > 0 and v606_counts.get("service_notifier_180", 0) == 0
    lower_ready_same = all(
        v598_counts.get(marker, 0) > 0 and v606_counts.get(marker, 0) > 0
        for marker in ("qrtr_rx", "qrtr_tx", "sysmon_modem")
    )
    order_same = same_value(
        v598_helper.get("wifi_companion_start.order"),
        v606_helper.get("wifi_companion_start.order"),
    )
    no_service_manager_same = (
        v598_helper.get("wifi_companion_start.with_service_manager") == "0"
        and v606_helper.get("wifi_companion_start.with_service_manager") == "0"
        and v598_helper.get("wifi_companion_start.with_vnd_service_manager") == "0"
        and v606_helper.get("wifi_companion_start.with_vnd_service_manager") == "0"
    )
    readback_same_empty = v598_readback == v606_readback and v598_readback.get("service_events") == 0
    cnss_window_same = near_ms(
        v598_delta.get("sysmon_to_cnss_diag"),
        v606_delta.get("sysmon_to_cnss_diag"),
        250.0,
    )
    helper_diff = v598.get("helper_marker") != v606.get("helper_marker")
    binder_after_cnss = (
        v606_delta.get("cnss_daemon_to_binder_failed") is not None
        and float(v606_delta["cnss_daemon_to_binder_failed"]) >= 0
    )
    firmware_same = (
        v598_surface.get("firmware_class_path") == v606_surface.get("firmware_class_path")
        and v598_surface.get("mounted_hits") == v606_surface.get("mounted_hits")
        and v598_surface.get("modem_blob_visible") == v606_surface.get("modem_blob_visible")
    )
    diagnostics.update({
        "service_notifier_regressed": service_regressed,
        "lower_ready_same": lower_ready_same,
        "order_same": order_same,
        "no_service_manager_same": no_service_manager_same,
        "readback_same_empty": readback_same_empty,
        "cnss_window_same_250ms": cnss_window_same,
        "helper_marker_differs": helper_diff,
        "firmware_surface_same": firmware_same,
        "binder_failure_after_cnss_daemon": binder_after_cnss,
    })

    if service_regressed and lower_ready_same and order_same and no_service_manager_same and readback_same_empty and cnss_window_same and helper_diff:
        return (
            "v607-helper-version-delta",
            True,
            "V598 and V606 match lower modem readiness, no-service-manager order, QRTR readback result, and CNSS timing, but service-notifier 180 disappears after helper marker changed from v100 to v102",
            "run a bounded helper-v100 replay or audit helper v100-to-v102 companion deltas before another daemon-order live proof",
            diagnostics,
        )
    if service_regressed and lower_ready_same and order_same and no_service_manager_same and not helper_diff:
        return (
            "v607-modem-publication-nondeterministic",
            True,
            "V598 and V606 have matching helper/order/lower readiness but service-notifier 180 is not stable",
            "repeat the same bounded no-service-manager observation once before changing daemon behavior",
            diagnostics,
        )
    if service_regressed and (not lower_ready_same or not cnss_window_same or not firmware_same):
        return (
            "v607-boot-runtime-delta",
            True,
            "service-notifier 180 regressed and at least one lower readiness, firmware, or timing surface differs",
            "classify the differing precondition before replaying Wi-Fi daemons",
            diagnostics,
        )
    if binder_after_cnss:
        return (
            "v607-binder-side-effect-after-gap",
            True,
            "binder failures are observable only after CNSS daemon entry and do not explain the pre-CNSS service-notifier gap",
            "prioritize pre-CNSS service publication observation before binder repair",
            diagnostics,
        )
    return (
        "v607-evidence-insufficient",
        False,
        "available evidence does not isolate a deterministic next gate",
        "inspect V598/V606 manifests and dmesg manually",
        diagnostics,
    )


def matrix_rows(cases: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in MATRIX_MARKERS:
        row = [marker]
        for case in cases:
            row.append(str((case.get("counts") or {}).get(marker, 0)))
        rows.append(row)
    return rows


def timing_rows(cases: list[dict[str, Any]]) -> list[list[str]]:
    fields = [
        "qrtr_rx_to_tx",
        "qrtr_tx_to_sysmon",
        "sysmon_to_service_notifier_180",
        "sysmon_to_cnss_diag",
        "sysmon_to_cnss_daemon",
        "service_notifier_180_to_cnss_diag",
        "cnss_daemon_to_binder_failed",
    ]
    rows: list[list[str]] = []
    for field in fields:
        row = [field]
        for case in cases:
            row.append(str((case.get("delta_ms") or {}).get(field)))
        rows.append(row)
    return rows


def helper_rows(cases: list[dict[str, Any]]) -> list[list[str]]:
    fields = [
        ("helper_marker", "helper_marker"),
        ("order", "wifi_companion_start.order"),
        ("with_service_manager", "wifi_companion_start.with_service_manager"),
        ("with_vnd_service_manager", "wifi_companion_start.with_vnd_service_manager"),
        ("qmi_payload", "wifi_companion_start.qmi_payload"),
        ("qrtr_readback", "wifi_companion_start.qrtr_nameservice_readback"),
        ("child_started", "wifi_companion_start.child_started"),
        ("qipcrtr_before", "wifi_companion_start.net_before.qipcrtr_sockets"),
        ("qipcrtr_after_spawn", "wifi_companion_start.net_after_spawn.qipcrtr_sockets"),
        ("qipcrtr_window", "wifi_companion_start.net_window.qipcrtr_sockets"),
        ("qipcrtr_after_cleanup", "wifi_companion_start.net_after_cleanup.qipcrtr_sockets"),
    ]
    rows: list[list[str]] = []
    for label, key in fields:
        row = [label]
        for case in cases:
            if key == "helper_marker":
                row.append(str(case.get("helper_marker", "")))
            else:
                row.append(str((case.get("helper") or {}).get(key, "")))
        rows.append(row)
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    cases = manifest["cases"]
    labels = [case["label"] for case in cases]
    return "\n".join([
        "# V607 QMI Service-Publication Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Diagnostics",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["diagnostics"].items()]),
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", *labels], matrix_rows(cases)),
        "",
        "## Timing Deltas (ms)",
        "",
        markdown_table(["delta", *labels], timing_rows(cases)),
        "",
        "## Helper Surface",
        "",
        markdown_table(["field", *labels], helper_rows(cases)),
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    inputs = [
        CaseInput("v598-positive", args.v598_dir, True),
        CaseInput("v606-v102-replay", args.v606_dir, True),
        CaseInput("v603-qrtr-first-service-manager", args.v603_dir, False),
        CaseInput("v604b-cnss-first-service-manager", args.v604b_dir, False),
    ]
    cases = [summarize_case(case) for case in inputs]
    case_map = {case["label"]: case for case in cases}
    decision, pass_ok, reason, next_step, diagnostics = classify(case_map)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "diagnostics": diagnostics,
        "host": collect_host_metadata(),
        "cases": cases,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
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
    manifest = build_manifest(args)
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
