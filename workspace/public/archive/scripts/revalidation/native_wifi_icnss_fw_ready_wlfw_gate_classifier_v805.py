#!/usr/bin/env python3
"""V805 host-only ICNSS FW_READY/WLFW service-arrival gate classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v805-icnss-fw-ready-wlfw-gate-classifier")
DEFAULT_V804_MANIFEST = Path("tmp/wifi/v804-pld-icnss-register-probe-prereq-classifier/manifest.json")
DEFAULT_V802_MANIFEST = Path("tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/manifest.json")
DEFAULT_V800_MANIFEST = Path("tmp/wifi/v800-provider-first-icnss-edge-v124-live/manifest.json")
DEFAULT_V797_MANIFEST = Path("tmp/wifi/v797-pil-trace-payload/manifest.json")
DEFAULT_V776_MANIFEST = Path("tmp/wifi/v776-tracepoint-inventory/manifest.json")
DEFAULT_V777_MANIFEST = Path("tmp/wifi/v777-tracepoint-format-classifier/manifest.json")
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")

ICNSS = "drivers/soc/qcom/icnss.c"
ICNSS_QMI = "drivers/soc/qcom/icnss_qmi.c"
WLFW_HEADER = "drivers/soc/qcom/wlan_firmware_service_v01.h"

ANCHORS = {
    "wlfw_service_id": ("wlfw_header", r"#define\s+WLFW_SERVICE_ID_V01\s+0x45"),
    "wlfw_service_version": ("wlfw_header", r"#define\s+WLFW_SERVICE_VERS_V01\s+0x01"),
    "wlfw_fw_ready_ind_id": ("wlfw_header", r"#define\s+QMI_WLFW_FW_READY_IND_V01\s+0x0021"),
    "wlfw_bdf_download_req": ("wlfw_header", r"#define\s+QMI_WLFW_BDF_DOWNLOAD_REQ_V01\s+0x0025"),
    "icnss_probe_register_fw_service": ("icnss", r"ret = icnss_register_fw_service\(priv\);"),
    "icnss_platform_probe_success": ("icnss", r"Platform driver probed successfully"),
    "icnss_server_arrive": ("icnss", r"static int icnss_driver_event_server_arrive"),
    "icnss_server_arrive_sets_wlfw_exists": ("icnss", r"set_bit\(ICNSS_WLFW_EXISTS"),
    "icnss_server_arrive_connects_qmi": ("icnss", r"ret = icnss_connect_to_fw_server\(penv, data\);"),
    "icnss_qmi_server_connected_log": ("icnss_qmi", r"QMI Server Connected"),
    "icnss_ind_register": ("icnss", r"ret = wlfw_ind_register_send_sync_msg\(penv\);"),
    "icnss_msa_mem_info": ("icnss", r"ret = wlfw_msa_mem_info_send_sync_msg\(penv\);"),
    "icnss_msa_ready": ("icnss", r"ret = wlfw_msa_ready_send_sync_msg\(penv\);"),
    "icnss_cap_req": ("icnss", r"ret = wlfw_cap_send_sync_msg\(penv\);"),
    "icnss_fw_ready_event": ("icnss", r"static int icnss_driver_event_fw_ready_ind"),
    "icnss_fw_ready_sets_bit": ("icnss", r"set_bit\(ICNSS_FW_READY"),
    "icnss_fw_ready_calls_probe": ("icnss", r"ret = icnss_call_driver_probe\(penv\);"),
    "icnss_call_driver_probe": ("icnss", r"static int icnss_call_driver_probe"),
    "icnss_call_driver_probe_calls_hdd": ("icnss", r"ret = priv->ops->probe\(&priv->pdev->dev\);"),
    "qmi_fw_ready_callback": ("icnss_qmi", r"static void fw_ready_ind_cb"),
    "qmi_fw_ready_posts_event": ("icnss_qmi", r"ICNSS_DRIVER_EVENT_FW_READY_IND"),
    "qmi_new_server_callback": ("icnss_qmi", r"static int wlfw_new_server"),
    "qmi_new_server_posts_arrive": ("icnss_qmi", r"ICNSS_DRIVER_EVENT_SERVER_ARRIVE"),
    "qmi_ops_new_server": ("icnss_qmi", r"\.new_server\s*=\s*wlfw_new_server"),
    "qmi_handle_init": ("icnss_qmi", r"ret = qmi_handle_init\(&priv->qmi"),
    "qmi_add_lookup_wlfw": ("icnss_qmi", r"qmi_add_lookup\(&priv->qmi,\s*WLFW_SERVICE_ID_V01"),
}

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash or boot image write",
    "partition write or reboot",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate or boot_wlan write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v804-manifest", type=Path, default=DEFAULT_V804_MANIFEST)
    parser.add_argument("--v802-manifest", type=Path, default=DEFAULT_V802_MANIFEST)
    parser.add_argument("--v800-manifest", type=Path, default=DEFAULT_V800_MANIFEST)
    parser.add_argument("--v797-manifest", type=Path, default=DEFAULT_V797_MANIFEST)
    parser.add_argument("--v776-manifest", type=Path, default=DEFAULT_V776_MANIFEST)
    parser.add_argument("--v777-manifest", type=Path, default=DEFAULT_V777_MANIFEST)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def contains(text: str, pattern: str, flags: int = re.MULTILINE | re.DOTALL) -> bool:
    return re.search(pattern, text, flags) is not None


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def path_info(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    return {
        "path": str(resolved),
        "exists": resolved.exists(),
        "is_file": resolved.is_file(),
        "size": resolved.stat().st_size if resolved.exists() and resolved.is_file() else None,
    }


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def load_sources(source_root: Path) -> dict[str, str]:
    root = repo_path(source_root)
    return {
        "icnss": read_text(root / ICNSS),
        "icnss_qmi": read_text(root / ICNSS_QMI),
        "wlfw_header": read_text(root / WLFW_HEADER),
    }


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources(args.source_root)
    anchors = {
        name: {
            "source": source_key,
            "line": line_of(sources.get(source_key, ""), pattern),
            "pattern": pattern,
        }
        for name, (source_key, pattern) in ANCHORS.items()
    }
    header = sources["wlfw_header"]
    service_match = re.search(r"#define\s+WLFW_SERVICE_ID_V01\s+(0x[0-9A-Fa-f]+|\d+)", header)
    version_match = re.search(r"#define\s+WLFW_SERVICE_VERS_V01\s+(0x[0-9A-Fa-f]+|\d+)", header)
    service_value = int(service_match.group(1), 0) if service_match else None
    version_value = int(version_match.group(1), 0) if version_match else None
    icnss = sources["icnss"]
    qmi = sources["icnss_qmi"]
    return {
        "source_root": str(repo_path(args.source_root)),
        "source_files": {
            ICNSS: path_info(args.source_root / ICNSS),
            ICNSS_QMI: path_info(args.source_root / ICNSS_QMI),
            WLFW_HEADER: path_info(args.source_root / WLFW_HEADER),
        },
        "anchors": anchors,
        "derived": {
            "wlfw_service_id": service_value,
            "wlfw_service_version": version_value,
            "lookup_armed_in_platform_probe": all(
                anchors[name]["line"]
                for name in ("icnss_probe_register_fw_service", "qmi_handle_init", "qmi_add_lookup_wlfw")
            ),
            "lookup_targets_service69": service_value == 0x45,
            "new_server_posts_server_arrive": all(
                anchors[name]["line"]
                for name in ("qmi_ops_new_server", "qmi_new_server_callback", "qmi_new_server_posts_arrive")
            ),
            "server_arrive_connects_and_registers_indications": all(
                anchors[name]["line"]
                for name in (
                    "icnss_server_arrive_sets_wlfw_exists",
                    "icnss_server_arrive_connects_qmi",
                    "icnss_ind_register",
                    "icnss_msa_mem_info",
                    "icnss_msa_ready",
                    "icnss_cap_req",
                )
            ),
            "fw_ready_qmi_indication_posts_probe_event": all(
                anchors[name]["line"]
                for name in (
                    "qmi_fw_ready_callback",
                    "qmi_fw_ready_posts_event",
                    "icnss_fw_ready_event",
                    "icnss_fw_ready_sets_bit",
                    "icnss_fw_ready_calls_probe",
                    "icnss_call_driver_probe_calls_hdd",
                )
            ),
            "service_arrival_precedes_fw_ready": contains(
                qmi,
                r"wlfw_new_server.*?ICNSS_DRIVER_EVENT_SERVER_ARRIVE",
            )
            and contains(
                icnss,
                r"icnss_driver_event_server_arrive.*?wlfw_ind_register_send_sync_msg.*?wlfw_msa_ready_send_sync_msg.*?wlfw_cap_send_sync_msg",
            ),
        },
    }


def analyze_v804(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v804_manifest)
    return {
        "manifest": str(repo_path(args.v804_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "next_step": manifest.get("next_step", ""),
        "selected_fw_ready_gate": bool(manifest.get("pass")) and "fw-ready" in str(manifest.get("decision", "")).replace("_", "-"),
    }


def analyze_v802(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v802_manifest)
    counts = nested(manifest, "arm_v802", "counts")
    counts = counts if isinstance(counts, dict) else {}
    return {
        "manifest": str(repo_path(args.v802_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "counts": counts,
        "signals": {
            "wlan_loading": int_value(counts.get("wlan_loading")),
            "wlan_driver_loaded": int_value(counts.get("wlan_driver_loaded")),
            "icnss_qmi_connected": int_value(counts.get("icnss_qmi_connected")),
            "fw_ready": int_value(counts.get("fw_ready")),
            "wlfw": int_value(counts.get("wlfw")),
            "bdf": int_value(counts.get("bdf")),
            "wiphy": int_value(counts.get("wiphy")),
            "wlan0": int_value(counts.get("wlan0")),
        },
    }


def analyze_v800(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v800_manifest)
    counts = nested(manifest, "arm_v700", "counts")
    markers = nested(manifest, "arm_v700", "markers")
    counts = counts if isinstance(counts, dict) else {}
    markers = markers if isinstance(markers, dict) else {}
    marker_counts = markers.get("counts") if isinstance(markers.get("counts"), dict) else {}
    if not marker_counts:
        marker_counts = markers
    return {
        "manifest": str(repo_path(args.v800_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "counts": counts,
        "markers": markers,
        "signals": {
            "qmi_server_connected": int_value(counts.get("qmi_server_connected")),
            "wlan_fw_ready": int_value(counts.get("wlan_fw_ready")),
            "wlfw_service_request": int_value(counts.get("wlfw_service_request")),
            "wlfw_start": int_value(counts.get("wlfw_start")),
            "service_notifier_74": int_value(counts.get("service_notifier_74")),
            "service_notifier_180": int_value(counts.get("service_notifier_180")),
            "qrtr_rx": int_value(marker_counts.get("qrtr_rx")),
            "qrtr_tx": int_value(marker_counts.get("qrtr_tx")),
            "wlfw": int_value(marker_counts.get("wlfw")),
            "bdf": int_value(marker_counts.get("bdf")),
            "wlan0": int_value(marker_counts.get("wlan0")),
        },
    }


def analyze_v797(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v797_manifest)
    trace_payload = nested(manifest, "live", "trace_payload")
    markers = nested(manifest, "live", "markers", "counts")
    trace_payload = trace_payload if isinstance(trace_payload, dict) else {}
    markers = markers if isinstance(markers, dict) else {}
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    trace_check: dict[str, Any] = {}
    for check in checks:
        if isinstance(check, dict) and check.get("name") == "trace-payload":
            detail = check.get("detail")
            if isinstance(detail, str):
                try:
                    trace_check = json.loads(detail)
                except json.JSONDecodeError:
                    trace_check = {}
            elif isinstance(detail, dict):
                trace_check = detail
    return {
        "manifest": str(repo_path(args.v797_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "trace_payload": trace_payload,
        "trace_check": trace_check,
        "markers": markers,
        "signals": {
            "pil_notif_event_count": int_value(trace_payload.get("event_count") or trace_check.get("event_count")),
            "pil_codes": trace_check.get("codes", []),
            "qrtr_rx": int_value(markers.get("qrtr_rx")),
            "qrtr_tx": int_value(markers.get("qrtr_tx")),
            "sysmon_qmi": int_value(markers.get("sysmon_qmi")),
            "service_notifier": int_value(markers.get("service_notifier")),
            "wlfw": int_value(markers.get("wlfw")),
            "bdf": int_value(markers.get("bdf")),
            "wlan0": int_value(markers.get("wlan0")),
        },
    }


def analyze_trace_observability(args: argparse.Namespace) -> dict[str, Any]:
    v776 = load_json(args.v776_manifest)
    v777 = load_json(args.v777_manifest)
    candidates = nested(v776, "analysis", "proof", "candidate_counts")
    events = nested(v777, "analysis", "proof", "events")
    candidates = candidates if isinstance(candidates, dict) else {}
    events = events if isinstance(events, dict) else {}
    useful = {
        name: {
            "tracepoint": data.get("tracepoint"),
            "id": data.get("id"),
            "format_readable": data.get("format_readable"),
            "non_common_fields": [field.get("name") for field in data.get("non_common_fields", []) if isinstance(field, dict)],
        }
        for name, data in events.items()
        if isinstance(data, dict)
    }
    return {
        "v776_manifest": str(repo_path(args.v776_manifest)),
        "v777_manifest": str(repo_path(args.v777_manifest)),
        "v776_pass": bool(v776.get("pass")),
        "v777_pass": bool(v777.get("pass")),
        "candidate_counts": candidates,
        "events": useful,
        "pil_notif_payload_observable": bool(nested(events, "msm_pil_event.pil_notif", "format_readable")),
        "dfc_qmi_observable": bool(nested(events, "dfc.dfc_qmi_tc", "format_readable")),
    }


def build_checks(command: str,
                 v804: dict[str, Any],
                 v802: dict[str, Any],
                 v800: dict[str, Any],
                 v797: dict[str, Any],
                 trace: dict[str, Any],
                 source: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command, flash, reboot, Wi-Fi HAL, or connect action",
            "next_step": "run V805 host-only classifier",
        }]
    derived = source.get("derived") if isinstance(source.get("derived"), dict) else {}
    v802_signals = v802.get("signals") if isinstance(v802.get("signals"), dict) else {}
    v800_signals = v800.get("signals") if isinstance(v800.get("signals"), dict) else {}
    v797_signals = v797.get("signals") if isinstance(v797.get("signals"), dict) else {}
    return [
        {
            "name": "v804-fw-ready-gate-ready",
            "status": "pass" if v804.get("selected_fw_ready_gate") else "blocked",
            "detail": {"decision": v804.get("decision"), "pass": v804.get("pass")},
            "next_step": "rerun/fix V804 if PLD/ICNSS register classification is not ready",
        },
        {
            "name": "wlfw-source-chain-verified",
            "status": "pass"
            if derived.get("lookup_armed_in_platform_probe")
            and derived.get("lookup_targets_service69")
            and derived.get("new_server_posts_server_arrive")
            and derived.get("server_arrive_connects_and_registers_indications")
            and derived.get("fw_ready_qmi_indication_posts_probe_event")
            else "blocked",
            "detail": derived,
            "next_step": "refresh OSRC source staging before selecting the WLFW gate",
        },
        {
            "name": "provider-first-still-no-wlfw",
            "status": "pass"
            if v800.get("pass")
            and v800_signals.get("service_notifier_74")
            and v800_signals.get("service_notifier_180")
            and not any(int_value(v800_signals.get(name)) for name in ("qmi_server_connected", "wlan_fw_ready", "wlfw_service_request", "wlfw_start", "wlfw", "bdf", "wlan0"))
            else "blocked",
            "detail": v800_signals,
            "next_step": "if WLFW appears in V800 evidence, route to ICNSS-QMI connect/FW_READY classifier",
        },
        {
            "name": "boot-wlan-still-pre-fw-ready",
            "status": "pass"
            if v802.get("pass")
            and v802_signals.get("wlan_loading")
            and not any(int_value(v802_signals.get(name)) for name in ("icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wiphy", "wlan0"))
            else "blocked",
            "detail": v802_signals,
            "next_step": "if FW_READY/WLFW/netdev appears, route to driver-ready-to-netdev classifier",
        },
        {
            "name": "pil-transition-observed-without-wlfw",
            "status": "pass"
            if v797.get("pass")
            and v797_signals.get("pil_notif_event_count")
            and not any(int_value(v797_signals.get(name)) for name in ("wlfw", "bdf", "wlan0"))
            else "finding",
            "detail": v797_signals,
            "next_step": "treat PIL completion as necessary but insufficient for WLFW service publication",
        },
        {
            "name": "stock-observability-available",
            "status": "pass" if trace.get("v776_pass") and trace.get("v777_pass") and trace.get("pil_notif_payload_observable") else "finding",
            "detail": {
                "candidate_counts": trace.get("candidate_counts"),
                "pil_notif_payload_observable": trace.get("pil_notif_payload_observable"),
                "dfc_qmi_observable": trace.get("dfc_qmi_observable"),
            },
            "next_step": "use stock tracefs/BPF only as supporting evidence; direct WLFW service69 readback remains the primary gate",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v805-icnss-fw-ready-wlfw-gate-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V805 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v805-icnss-fw-ready-wlfw-gate-classifier-blocked", False, "blocked by " + ", ".join(blocked), "clear host evidence blocker"
    return (
        "v805-wlfw-service69-arrival-gate-selected",
        True,
        "ICNSS arms a QMI lookup for WLFW service 0x45/69 and FW_READY only follows WLFW server arrival; existing provider-first and boot_wlan evidence still has service74/180 and PIL activity but no WLFW/QMI-connected/FW_READY/BDF/netdev",
        "run a bounded V806 stock-kernel live gate that directly observes QRTR WLFW service69 publication and ICNSS-QMI/FW_READY after provider-first boot_wlan, with no HAL/scan/connect",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v804 = analyze_v804(args)
    v802 = analyze_v802(args)
    v800 = analyze_v800(args)
    v797 = analyze_v797(args)
    trace = analyze_trace_observability(args)
    source = analyze_source(args)
    checks = build_checks(args.command, v804, v802, v800, v797, trace, source)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v805",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v804_manifest": str(repo_path(args.v804_manifest)),
            "v802_manifest": str(repo_path(args.v802_manifest)),
            "v800_manifest": str(repo_path(args.v800_manifest)),
            "v797_manifest": str(repo_path(args.v797_manifest)),
            "v776_manifest": str(repo_path(args.v776_manifest)),
            "v777_manifest": str(repo_path(args.v777_manifest)),
            "source_root": str(repo_path(args.source_root)),
        },
        "v804": v804,
        "v802": v802,
        "v800": v800,
        "v797": v797,
        "trace_observability": trace,
        "source": source,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    source = manifest["source"]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    source_rows = [
        [name, data["source"], str(data["line"]), data["pattern"]]
        for name, data in source["anchors"].items()
    ]
    derived_rows = [[key, str(value)] for key, value in source["derived"].items()]
    signal_rows = [
        ["V804", json.dumps({"decision": manifest["v804"].get("decision"), "pass": manifest["v804"].get("pass")}, sort_keys=True)],
        ["V802", json.dumps(manifest["v802"].get("signals", {}), sort_keys=True)],
        ["V800", json.dumps(manifest["v800"].get("signals", {}), sort_keys=True)],
        ["V797", json.dumps(manifest["v797"].get("signals", {}), sort_keys=True)],
        ["trace", json.dumps({
            "pil_notif_payload_observable": manifest["trace_observability"].get("pil_notif_payload_observable"),
            "dfc_qmi_observable": manifest["trace_observability"].get("dfc_qmi_observable"),
            "candidate_counts": manifest["trace_observability"].get("candidate_counts"),
        }, sort_keys=True)],
    ]
    return "\n".join([
        "# V805 ICNSS FW_READY/WLFW Gate Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- custom_kernel_flash_executed: `{manifest['custom_kernel_flash_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Evidence Signals",
        "",
        markdown_table(["source", "signals"], signal_rows),
        "",
        "## Source Derived Facts",
        "",
        markdown_table(["fact", "value"], derived_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["anchor", "source", "line", "pattern"], source_rows),
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
    print(f"custom_kernel_flash_executed: {manifest['custom_kernel_flash_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
