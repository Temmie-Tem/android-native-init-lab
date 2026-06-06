#!/usr/bin/env python3
"""V725 host-only service-locator to modem/QMI readiness gap classifier.

This classifier compares Android lower Wi-Fi evidence against V724 native
boot-window evidence. It does not contact the device, start daemons, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, ping
externally, write sysfs, or write boot partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v725-servloc-modem-gap")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_ANDROID_V612_MANIFEST = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/manifest.json"
)
DEFAULT_NATIVE_V724_SOURCE = Path("tmp/wifi/latest-v724-armed-boot-proof.txt")
DEFAULT_LIVE_READONLY_SOURCE = Path("tmp/wifi/latest-v725-live-readonly.txt")

FORBIDDEN_ACTIONS = (
    "device command",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "sysfs/debugfs write",
    "esoc0 open/hold",
    "subsys state write",
    "boot image or partition write",
)

DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0|sysmon_esoc0", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server|Service locator initialized", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier:.*74 service", re.I)),
    ("servloc_timeout", re.compile(r"service_locator.*timed out|servloc.*timed out", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|\bwlan_pd\b", re.I)),
    ("pd_notifier", re.compile(r"pd_notifier|pd notifier|service_state.*up", re.I)),
    ("qca6390", re.compile(r"qca6390|wcn3990|wcnss", re.I)),
    ("wlfw", re.compile(r"\bwlfw\b|wlfw_start|QMI Server Connected", re.I)),
    ("bdf", re.compile(r"\bBDF\b|regdb\.bin|bdwlan\.bin", re.I)),
    ("fw_ready", re.compile(r"WLAN FW is ready|fw_ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:.*Done with init", re.I)),
)

EXECNS_BEGIN_RE = re.compile(r"^A90_EXECNS_(?:PATH|DIR)_(?P<name>.+)_BEGIN\b")
EXECNS_END_RE = re.compile(r"^A90_EXECNS_(?:PATH|DIR)_(?P<name>.+)_END\b(?P<tail>.*)")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--android-v612-manifest", type=Path, default=DEFAULT_ANDROID_V612_MANIFEST)
    parser.add_argument("--native-v724-source", type=Path, default=DEFAULT_NATIVE_V724_SOURCE)
    parser.add_argument("--live-readonly-source", type=Path, default=DEFAULT_LIVE_READONLY_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path | str) -> str:
    resolved = repo_path(path)
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path | str) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready", "ok"}


def resolve_source(source: Path) -> Path:
    resolved = repo_path(source)
    if resolved.is_file() and resolved.name != "manifest.json":
        text = resolved.read_text(encoding="utf-8").strip()
        if text:
            return repo_path(Path(text))
    return resolved


def resolve_run_dir(source: Path) -> Path:
    resolved = resolve_source(source)
    if resolved.name == "manifest.json":
        return resolved.parent
    return resolved


def dmesg_ts(line: str) -> float | None:
    match = TS_RE.match(line.strip())
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in DMESG_PATTERNS}
    focus: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for name, pattern in DMESG_PATTERNS:
            if pattern.search(line):
                events[name].append({"ts": dmesg_ts(line), "line": line[:360]})
                matched = True
        if matched:
            focus.append(line[:360])
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "focus_tail": focus[-120:],
    }


def manifest_counts(manifest: dict[str, Any]) -> dict[str, int]:
    counts = manifest.get("counts") if isinstance(manifest.get("counts"), dict) else {}
    return {str(key): intish(value) for key, value in counts.items()}


def android_counts(summary: dict[str, Any]) -> dict[str, int]:
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    keys = (
        "qrtr_rx",
        "qrtr_tx",
        "sysmon_modem",
        "sysmon_esoc0",
        "service_locator",
        "service_notifier_180",
        "service_notifier_74",
        "wlan_pd",
        "wlan_pd_ack_180",
        "wlfw_start",
        "qmi_server_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
        "rmt_storage_ready",
        "rmt_storage_open",
    )
    return {key: intish(counts.get(key)) for key in keys}


def path_capture_value(log: str, name: str) -> str:
    capture = False
    values: list[str] = []
    for raw_line in log.splitlines():
        line = raw_line.rstrip("\n")
        begin = EXECNS_BEGIN_RE.match(line)
        if begin and begin.group("name") == name:
            capture = True
            values = []
            continue
        end = EXECNS_END_RE.match(line)
        if capture and end and end.group("name") == name:
            return "\n".join(value for value in values if value.strip()).strip()
        if capture:
            values.append(line)
    return ""


def dir_capture_count(log: str, name: str) -> int:
    capture = False
    for raw_line in log.splitlines():
        line = raw_line.strip()
        begin = EXECNS_BEGIN_RE.match(line)
        if begin and begin.group("name") == name:
            capture = True
            continue
        end = EXECNS_END_RE.match(line)
        if capture and end and end.group("name") == name:
            match = re.search(r"\bcount=(\d+)", end.group("tail"))
            return intish(match.group(1) if match else 0)
    return 0


def kv(log: str, key: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$", re.MULTILINE)
    match = pattern.search(log)
    return match.group(1).strip() if match else ""


def android_v622_surface(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    summary = manifest.get("android_summary") if isinstance(manifest.get("android_summary"), dict) else {}
    props = summary.get("props") if isinstance(summary.get("props"), dict) else {}
    timing = summary.get("timing") if isinstance(summary.get("timing"), dict) else {}
    deltas = summary.get("deltas_ms") if isinstance(summary.get("deltas_ms"), dict) else {}
    counts = android_counts(summary)
    return {
        "manifest": str(repo_path(path)),
        "exists": bool(manifest),
        "pass": boolish(manifest.get("pass")),
        "decision": manifest.get("decision", ""),
        "counts": counts,
        "timing_ms": {
            key: timing.get(key)
            for key in (
                "qrtr_ns_boottime_ms",
                "pd_mapper_boottime_ms",
                "sysmon_modem_ms",
                "service_notifier_180_ms",
                "service_notifier_74_ms",
                "rmt_storage_boottime_ms",
                "tftp_server_boottime_ms",
                "mdm_helper_boottime_ms",
                "cnss_daemon_boottime_ms",
                "wlan_pd_ms",
                "sysmon_esoc0_ms",
            )
        },
        "deltas_ms": {
            key: deltas.get(key)
            for key in (
                "qrtr_rx_to_qrtr_tx",
                "qrtr_tx_to_sysmon_modem",
                "sysmon_modem_to_service_locator",
                "sysmon_modem_to_service_notifier_180",
                "service_notifier_180_to_service_notifier_74",
                "service_notifier_180_to_wlfw_start",
                "service_notifier_180_to_wlan_pd",
                "wlan_pd_to_qmi_server_connected",
                "wlan_pd_to_bdf_regdb",
            )
        },
        "service_props": {
            key: props.get(key, "")
            for key in (
                "init.svc.vendor.qrtr-ns",
                "init.svc.vendor.pd_mapper",
                "init.svc.vendor.rmt_storage",
                "init.svc.vendor.tftp_server",
                "init.svc.vendor.mdm_helper",
                "init.svc.cnss_diag",
                "init.svc.cnss-daemon",
            )
        },
        "has_modem_qmi_chain": all(
            counts.get(key, 0) > 0
            for key in ("qrtr_rx", "qrtr_tx", "sysmon_modem", "service_locator", "service_notifier_180", "service_notifier_74")
        ),
        "has_wlanpd_wlfw_chain": all(
            counts.get(key, 0) > 0
            for key in ("wlan_pd", "wlfw_start", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")
        ),
    }


def android_v612_surface(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    summary = manifest.get("android_summary") if isinstance(manifest.get("android_summary"), dict) else {}
    initial = summary.get("initial_values") if isinstance(summary.get("initial_values"), dict) else {}
    delayed = summary.get("delayed_values") if isinstance(summary.get("delayed_values"), dict) else {}
    return {
        "manifest": str(repo_path(path)),
        "exists": bool(manifest),
        "pass": boolish(manifest.get("pass")),
        "decision": manifest.get("decision", ""),
        "mss_state": summary.get("mss_state", ""),
        "mdm3_state": summary.get("mdm3_state", ""),
        "initial_mss_state": initial.get("mss_state", ""),
        "initial_mdm3_state": initial.get("mdm3_state", ""),
        "delayed_mss_state": delayed.get("mss_state", ""),
        "delayed_mdm3_state": delayed.get("mdm3_state", ""),
        "has_qipcrtr_protocol": boolish(summary.get("has_qipcrtr_protocol")),
        "has_rpmsg_ipcrtr": boolish(summary.get("has_rpmsg_ipcrtr")),
        "has_sibling_sysmon": boolish(summary.get("has_sibling_sysmon")),
        "has_service_notifier_pair": boolish(summary.get("has_service_notifier_pair")),
        "state_values_ready": boolish(summary.get("state_values_ready")),
        "selected_values": summary.get("selected_values") if isinstance(summary.get("selected_values"), dict) else {},
    }


def native_v724_surface(source: Path) -> dict[str, Any]:
    run_dir = resolve_run_dir(source)
    manifest_path = run_dir / "manifest.json"
    manifest = load_json(manifest_path)
    cache_log = read_text(run_dir / "native/v724-cache-log-after-hide.txt") or read_text(run_dir / "native/v724-cache-log.txt")
    dmesg_text = read_text(run_dir / "native/dmesg-after-330s.txt") or read_text(run_dir / "native/dmesg-after-hide.txt")
    parsed_dmesg = parse_dmesg(dmesg_text)
    counts = parsed_dmesg["counts"] | manifest_counts(manifest)
    mss_state = path_capture_value(cache_log, "wifi_window_soc_mss_subsys0_state")
    mdm3_state = path_capture_value(cache_log, "wifi_window_soc_mdm3_subsys9_state")
    return {
        "source": str(repo_path(source)),
        "run_dir": str(run_dir),
        "manifest": str(manifest_path),
        "exists": bool(manifest),
        "pass": boolish(manifest.get("status_has_v724")) and not boolish(manifest.get("guardrail_crossed")),
        "decision": manifest.get("decision", ""),
        "counts": counts,
        "first_ts": parsed_dmesg["first_ts"] | (manifest.get("first_ts") if isinstance(manifest.get("first_ts"), dict) else {}),
        "first_lines": parsed_dmesg["first_lines"] | (manifest.get("first_line") if isinstance(manifest.get("first_line"), dict) else {}),
        "helper": {
            "mode": kv(cache_log, "mode"),
            "order": kv(cache_log, "wifi_companion_start.order"),
            "child_started": intish(kv(cache_log, "wifi_companion_start.child_started")),
            "all_observable": boolish(kv(cache_log, "wifi_companion_start.all_observable")),
            "all_postflight_safe": boolish(kv(cache_log, "wifi_companion_start.all_postflight_safe")),
            "result": kv(cache_log, "wifi_companion_start.result"),
            "service_manager": intish(kv(cache_log, "wifi_companion_start.service_manager_started")),
            "scan_connect_linkup": intish(kv(cache_log, "wifi_companion_start.scan_connect_linkup")),
            "external_ping": intish(kv(cache_log, "wifi_companion_start.external_ping")),
        },
        "subsys": {
            "mss_name": path_capture_value(cache_log, "wifi_window_soc_mss_subsys0_name"),
            "mss_state": mss_state,
            "mss_restart_level": path_capture_value(cache_log, "wifi_window_soc_mss_subsys0_restart_level"),
            "mss_firmware_name": path_capture_value(cache_log, "wifi_window_soc_mss_subsys0_firmware_name"),
            "mss_crash_count": path_capture_value(cache_log, "wifi_window_soc_mss_subsys0_crash_count"),
            "mdm3_name": path_capture_value(cache_log, "wifi_window_soc_mdm3_subsys9_name"),
            "mdm3_state": mdm3_state,
            "mdm3_restart_level": path_capture_value(cache_log, "wifi_window_soc_mdm3_subsys9_restart_level"),
            "mdm3_firmware_name": path_capture_value(cache_log, "wifi_window_soc_mdm3_subsys9_firmware_name"),
            "mdm3_crash_count": path_capture_value(cache_log, "wifi_window_soc_mdm3_subsys9_crash_count"),
        },
        "surface": {
            "qipcrtr_present": boolish(kv(cache_log, "wifi_companion_start.net_window.qipcrtr_present")),
            "qipcrtr_sockets": intish(kv(cache_log, "wifi_companion_start.net_window.qipcrtr_sockets")),
            "rpmsg_devices_count": dir_capture_count(cache_log, "wifi_window_rpmsg_devices"),
            "service_notifier_debug_count": dir_capture_count(cache_log, "wifi_window_service_notifier"),
            "proc_qrtr_captured": boolish(kv(cache_log, "wifi_companion_start.surface_window.proc_qrtr_captured")),
            "mss_state_captured": boolish(kv(cache_log, "wifi_companion_start.surface_window.mss_subsys0_state_captured")),
            "mdm3_state_captured": boolish(kv(cache_log, "wifi_companion_start.surface_window.mdm3_subsys9_state_captured")),
        },
        "guardrail_crossed": boolish(manifest.get("guardrail_crossed")),
        "service_locator_connected": counts.get("service_locator_connected", 0) > 0 or counts.get("service_locator", 0) > 0,
        "servloc_timeout": counts.get("servloc_timeout", 0) > 0,
        "modem_qmi_ready": counts.get("qrtr_rx", 0) > 0 and counts.get("qrtr_tx", 0) > 0 and counts.get("sysmon_modem", 0) > 0,
        "service_pair_present": counts.get("service_notifier_180", 0) > 0 and counts.get("service_notifier_74", 0) > 0,
    }


def live_readonly_surface(source: Path) -> dict[str, Any]:
    run_dir = resolve_run_dir(source)
    if not run_dir.exists():
        return {"exists": False, "run_dir": str(run_dir)}
    subsys = read_text(run_dir / "msm_subsys-busybox.txt")
    dmesg = read_text(run_dir / "dmesg-focus-busybox.txt")
    qrtr = read_text(run_dir / "qrtr-rpmsg-surface.txt")
    ps_text = read_text(run_dir / "ps.txt")
    parsed = parse_dmesg(dmesg)
    return {
        "exists": True,
        "run_dir": str(run_dir),
        "counts": parsed["counts"],
        "first_lines": parsed["first_lines"],
        "qrtr_ns_process": bool(re.search(r"\bqrtr-ns\b", ps_text)),
        "cnss_process": bool(re.search(r"\bcnss(?:_diag|-daemon)\b", ps_text)),
        "mss_offlining": bool(re.search(r"modem\s+OFFLINING", subsys, re.I)),
        "mdm3_offlining": bool(re.search(r"esoc0\s+OFFLINING", subsys, re.I)),
        "rpmsg_devices_zero": bool(re.search(r"\b0\b", qrtr)),
        "qipcrtr_present": bool(re.search(r"\bQIPCRTR\b", qrtr)),
    }


def build_checks(android_v622: dict[str, Any], android_v612: dict[str, Any], native: dict[str, Any], live: dict[str, Any]) -> list[dict[str, Any]]:
    native_counts = native.get("counts") or {}
    native_subsys = native.get("subsys") or {}
    native_surface_data = native.get("surface") or {}
    checks: list[dict[str, Any]] = [
        {
            "name": "input-evidence-ready",
            "status": "pass" if android_v622["exists"] and android_v622["pass"] and android_v612["exists"] and android_v612["pass"] and native["exists"] and native["pass"] else "blocked",
            "detail": {
                "android_v622": android_v622["decision"],
                "android_v612": android_v612["decision"],
                "native_v724": native["decision"],
            },
            "next_step": "refresh Android V612/V622 or native V724 evidence before routing V725",
        },
        {
            "name": "driver-model-recentered-on-cnss2",
            "status": "finding",
            "detail": {
                "platform": "SM8250-class target",
                "analysis_path": "CNSS2 service-notifier/SERVREG path, not SDM845 ICNSS-only model",
                "note": "kernel log labels may still include icnss strings",
            },
            "next_step": "treat service 180 userspace visibility and kernel SERVREG listener indications as separate edges",
        },
        {
            "name": "android-modem-qmi-preconditions-present",
            "status": "pass" if android_v622["has_modem_qmi_chain"] and android_v612["mss_state"] == "ONLINE" and android_v612["mdm3_state"] == "ONLINE" else "blocked",
            "detail": {
                "counts": {key: android_v622["counts"].get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_modem", "service_locator", "service_notifier_180", "service_notifier_74")},
                "mss_state": android_v612["mss_state"],
                "mdm3_state": android_v612["mdm3_state"],
                "has_qipcrtr_protocol": android_v612["has_qipcrtr_protocol"],
                "has_rpmsg_ipcrtr": android_v612["has_rpmsg_ipcrtr"],
            },
            "next_step": "Android reference remains valid for the lower modem/QMI prerequisite chain",
        },
        {
            "name": "android-wlanpd-wlfw-continuation-present",
            "status": "pass" if android_v622["has_wlanpd_wlfw_chain"] else "blocked",
            "detail": {
                "counts": {key: android_v622["counts"].get(key, 0) for key in ("wlan_pd", "wlfw_start", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")},
            },
            "next_step": "use Android continuation only after native reaches modem QMI readiness",
        },
        {
            "name": "native-service-locator-timing-fixed",
            "status": "pass" if native["service_locator_connected"] and not native["servloc_timeout"] else "blocked",
            "detail": {
                "service_locator": native_counts.get("service_locator", native_counts.get("service_locator_connected", 0)),
                "service_locator_connected": native_counts.get("service_locator_connected", 0),
                "servloc_timeout": native_counts.get("servloc_timeout", 0),
                "helper_order": (native.get("helper") or {}).get("order", ""),
            },
            "next_step": "do not return to late qrtr-ns rearm as the main blocker",
        },
        {
            "name": "native-modem-qmi-readiness-missing",
            "status": "finding" if (
                not native["modem_qmi_ready"]
                and native_subsys.get("mss_state") == "OFFLINING"
                and native_subsys.get("mdm3_state") == "OFFLINING"
                and intish(native_surface_data.get("rpmsg_devices_count")) == 0
            ) else "review",
            "detail": {
                "qrtr_rx": native_counts.get("qrtr_rx", 0),
                "qrtr_tx": native_counts.get("qrtr_tx", 0),
                "sysmon_modem": native_counts.get("sysmon_modem", 0),
                "sysmon_esoc0": native_counts.get("sysmon_esoc0", 0),
                "mss_state": native_subsys.get("mss_state", ""),
                "mdm3_state": native_subsys.get("mdm3_state", ""),
                "rpmsg_devices_count": native_surface_data.get("rpmsg_devices_count", 0),
                "qipcrtr_sockets": native_surface_data.get("qipcrtr_sockets", 0),
            },
            "next_step": "test a bounded modem firmware/subsys_modem holder path before CNSS daemon/HAL/connect",
        },
        {
            "name": "native-servreg-publication-blocked-below-service180",
            "status": "finding" if native["service_locator_connected"] and not native["service_pair_present"] and not native["modem_qmi_ready"] else "review",
            "detail": {
                "service_notifier_180": native_counts.get("service_notifier_180", 0),
                "service_notifier_74": native_counts.get("service_notifier_74", 0),
                "pd_notifier": native_counts.get("pd_notifier", 0),
                "wlan_pd": native_counts.get("wlan_pd", 0),
                "wlfw": native_counts.get("wlfw", 0),
                "wlan0": native_counts.get("wlan0", 0),
            },
            "next_step": "do not retry qcwlanstate, CNSS daemon, HAL, scan, or connect until QRTR RX/TX and sysmon are present",
        },
        {
            "name": "live-readonly-spot-check",
            "status": "pass" if not live.get("exists") or (live.get("mss_offlining") and live.get("mdm3_offlining") and live.get("qipcrtr_present")) else "review",
            "detail": {
                "used": bool(live.get("exists")),
                "run_dir": live.get("run_dir", ""),
                "mss_offlining": live.get("mss_offlining"),
                "mdm3_offlining": live.get("mdm3_offlining"),
                "qipcrtr_present": live.get("qipcrtr_present"),
                "qrtr_ns_process": live.get("qrtr_ns_process"),
                "cnss_process": live.get("cnss_process"),
            },
            "next_step": "live spot check is corroborative only; V725 decision stays host-evidence based",
        },
    ]
    return checks


def decide(command: str, checks: list[dict[str, Any]], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v725-servloc-modem-gap-plan-ready",
            True,
            "plan-only; no device command executed",
            "run the V725 host-only classifier over Android V612/V622 and native V724 evidence",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v725-servloc-modem-gap-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing input evidence before live work",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "driver-model-recentered-on-cnss2",
        "native-modem-qmi-readiness-missing",
        "native-servreg-publication-blocked-below-service180",
    }
    if required <= findings and native.get("service_locator_connected") and not native.get("servloc_timeout"):
        return (
            "v725-servloc-live-modem-qmi-readiness-gap-classified",
            True,
            "V724 moved lower companion startup early enough for service-locator, but native still lacks QRTR RX/TX, sysmon, ONLINE modem/mdm3, rpmsg devices, and service 180/74. The blocker is below SERVREG/WLAN-PD publication.",
            "plan V726 as a bounded post-ACM modem firmware/subsys_modem holder plus lower companion proof; do not touch esoc0 and do not start CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, DHCP, credentials, or external ping",
        )
    return (
        "v725-servloc-modem-gap-review",
        True,
        "evidence is valid but does not match the expected V724 modem/QMI readiness gap",
        "inspect V725 summary before choosing a live gate",
    )


def render_counts(title: str, counts: dict[str, int]) -> str:
    rows = [[key, str(value)] for key, value in sorted(counts.items())]
    return "\n".join([f"## {title}", "", markdown_table(["marker", "count"], rows)])


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    sources = [
        ["android_v622", manifest.get("android_v622", {}).get("manifest", "")],
        ["android_v612", manifest.get("android_v612", {}).get("manifest", "")],
        ["native_v724", manifest.get("native_v724", {}).get("run_dir", "")],
        ["live_readonly", manifest.get("live_readonly", {}).get("run_dir", "")],
    ]
    android_counts = manifest.get("android_v622", {}).get("counts") or {}
    native_counts = manifest.get("native_v724", {}).get("counts") or {}
    native_subsys = manifest.get("native_v724", {}).get("subsys") or {}
    timing_rows = [
        [key, str(value)]
        for key, value in (manifest.get("android_v622", {}).get("deltas_ms") or {}).items()
        if value is not None
    ]
    subsys_rows = [[key, str(value)] for key, value in native_subsys.items()]
    return "\n".join([
        "# V725 Service-Locator to Modem/QMI Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Sources",
        "",
        markdown_table(["source", "path"], sources),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], checks) if checks else "- plan only",
        "",
        "## Android Timing Deltas",
        "",
        markdown_table(["delta", "ms"], timing_rows) if timing_rows else "- plan only",
        "",
        "## Native Subsystem Values",
        "",
        markdown_table(["key", "value"], subsys_rows) if subsys_rows else "- unavailable",
        "",
        render_counts("Android V622 Counts", android_counts),
        "",
        render_counts("Native V724 Counts", native_counts),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_v622: dict[str, Any] = {}
    android_v612: dict[str, Any] = {}
    native_v724: dict[str, Any] = {}
    live_readonly: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    if args.command == "run":
        android_v622 = android_v622_surface(args.android_v622_manifest)
        android_v612 = android_v612_surface(args.android_v612_manifest)
        native_v724 = native_v724_surface(args.native_v724_source)
        live_readonly = live_readonly_surface(args.live_readonly_source)
        checks = build_checks(android_v622, android_v612, native_v724, live_readonly)
    decision, pass_ok, reason, next_step = decide(args.command, checks, native_v724)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v725",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "android_v622": android_v622,
        "android_v612": android_v612,
        "native_v724": native_v724,
        "live_readonly": live_readonly,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "sysfs_writes_executed": False,
        "boot_partition_write_executed": False,
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
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
