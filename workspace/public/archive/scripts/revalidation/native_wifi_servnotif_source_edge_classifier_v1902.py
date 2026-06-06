#!/usr/bin/env python3
"""V1902 host-only classifier for the service-notifier servreg state-up edge."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1902"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1902-servnotif-source-edge-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1902_SERVNOTIF_SOURCE_EDGE_CLASSIFIER_2026-06-03.md"
)
LATEST_POINTER = REPO_ROOT / "tmp" / "wifi" / "latest-v1902-servnotif-source-edge-classifier.txt"
DEFAULT_SERVICE_NOTIFIER = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "drivers"
    / "soc"
    / "qcom"
    / "service-notifier.c"
)
DEFAULT_SERVICE_NOTIFIER_PRIVATE = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "drivers"
    / "soc"
    / "qcom"
    / "service-notifier-private.h"
)
DEFAULT_SERVICE_NOTIFIER_HEADER = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "include"
    / "soc"
    / "qcom"
    / "service-notifier.h"
)
DEFAULT_V1901_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1901-servnotif-publication-absent-classifier" / "manifest.json"
)
DEFAULT_V1898_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1898-servnotif-stateup-not-msg22-classifier" / "manifest.json"
DEFAULT_V1899_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1899-android-cnss-qrtr-stateup-live2-20260603-200642" / "manifest.json"
)


SOURCE_MARKERS = {
    "new_server_cb": r"static int service_notifier_new_server",
    "new_server_print": r"Connection established between QMI handle and %d service",
    "new_server_work": r"static void new_server_work",
    "register_listener_wrapper": r"static int register_notif_listener",
    "listener_send_request": r"qmi_send_request\(&data->clnt_handle, &data->s_addr,\s*$",
    "state_ind_handler_table": r"\.msg_id = SERVREG_NOTIF_STATE_UPDATED_IND_MSG",
    "state_ind_callback": r"static void root_service_service_ind_cb",
    "state_ind_print": r"Indication received from %s, state:",
    "ack_worker": r"static void send_ind_ack",
    "ack_send_request": r"SERVREG_NOTIF_SET_ACK_REQ",
    "add_lookup": r"qmi_add_lookup\(&qmi_data->clnt_handle,",
    "pd_restart_export": r"EXPORT_SYMBOL\(service_notif_pd_restart\)",
    "pd_restart_send": r"QMI_SERVREG_NOTIF_RESTART_PD_REQ_V01",
}

PRIVATE_MARKERS = {
    "servreg_service_id": r"#define SERVREG_NOTIF_SERVICE_ID_V01\s+0x42",
    "register_listener_msg": r"#define QMI_SERVREG_NOTIF_REGISTER_LISTENER_REQ_V01\s+0x0020",
    "query_state_msg": r"#define QMI_SERVREG_NOTIF_QUERY_STATE_REQ_V01\s+0x0021",
    "state_updated_ind_msg": r"#define QMI_SERVREG_NOTIF_STATE_UPDATED_IND_V01\s+0x0022",
    "state_updated_ack_msg": r"#define QMI_SERVREG_NOTIF_STATE_UPDATED_IND_ACK_REQ_V01\s+0x0023",
    "restart_pd_msg": r"#define QMI_SERVREG_NOTIF_RESTART_PD_REQ_V01\s+0x0024",
}

HEADER_MARKERS = {
    "state_down": r"SERVREG_NOTIF_SERVICE_STATE_DOWN_V01\s+=\s+0x0FFFFFFF",
    "state_up": r"SERVREG_NOTIF_SERVICE_STATE_UP_V01\s+=\s+0x1FFFFFFF",
    "state_uninit": r"SERVREG_NOTIF_SERVICE_STATE_UNINIT_V01\s+=\s+0x7FFFFFFF",
    "register_notifier_api": r"service_notif_register_notifier",
    "restart_pd_api": r"service_notif_pd_restart",
}


def rel(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(REPO_ROOT))
    except (OSError, ValueError):
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except (TypeError, ValueError):
        return 0


def positive_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and any(intish(part) > 0 for part in parts)


def zero_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(intish(part) == 0 for part in parts)


def line_markers(path: Path, markers: dict[str, str]) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    lines = text.splitlines()
    result: dict[str, dict[str, Any]] = {}
    for name, pattern in markers.items():
        regex = re.compile(pattern)
        line_no = 0
        line_text = ""
        for index, line in enumerate(lines, start=1):
            if regex.search(line):
                line_no = index
                line_text = line.strip()
                break
        result[name] = {
            "present": line_no > 0,
            "line": line_no,
            "file": rel(path),
            "text": line_text,
        }
    return result


def source_summary(service_notifier: Path, private_header: Path, public_header: Path) -> dict[str, Any]:
    source = line_markers(service_notifier, SOURCE_MARKERS)
    private = line_markers(private_header, PRIVATE_MARKERS)
    public = line_markers(public_header, HEADER_MARKERS)
    passive_edge_present = all(
        source[key]["present"]
        for key in (
            "new_server_cb",
            "new_server_print",
            "new_server_work",
            "register_listener_wrapper",
            "state_ind_handler_table",
            "state_ind_callback",
            "state_ind_print",
            "ack_worker",
            "add_lookup",
        )
    )
    message_ids_present = all(private[key]["present"] for key in PRIVATE_MARKERS)
    state_values_present = all(public[key]["present"] for key in ("state_up", "state_uninit", "state_down"))
    restart_path_present = (
        source["pd_restart_export"]["present"]
        and source["pd_restart_send"]["present"]
        and private["restart_pd_msg"]["present"]
        and public["restart_pd_api"]["present"]
    )
    return {
        "service_notifier": rel(service_notifier),
        "private_header": rel(private_header),
        "public_header": rel(public_header),
        "source_markers": source,
        "private_markers": private,
        "header_markers": public,
        "passive_servreg_edge_present": passive_edge_present,
        "message_ids_present": message_ids_present,
        "state_values_present": state_values_present,
        "restart_path_present": restart_path_present,
        "passive_sequence": [
            "qmi_add_lookup service 0x42 instance",
            "service_notifier_new_server",
            "register listener request msg 0x20",
            "state updated indication msg 0x22",
            "state-up curr_state 0x1fffffff",
            "ack request msg 0x23",
        ],
        "forbidden_mutating_sequence": [
            "service_notif_pd_restart",
            "restart-PD request msg 0x24",
        ],
    }


def evidence_summary(v1901_path: Path, v1898_path: Path, v1899_path: Path) -> dict[str, Any]:
    v1901 = read_json(v1901_path)
    v1898 = read_json(v1898_path)
    v1899 = read_json(v1899_path)
    v1901_summaries = v1901.get("summaries") or {}
    v1901_v1834 = v1901_summaries.get("v1834") or {}
    v1901_v1803 = v1901_summaries.get("v1803") or {}
    android_1898 = v1898.get("android") or {}
    native_1898 = v1898.get("native") or {}
    analysis_1899 = (v1899.get("context") or {}).get("analysis") or {}
    dmesg_1899 = analysis_1899.get("dmesg") or {}
    return {
        "v1901_manifest": rel(v1901_path),
        "v1901_decision": v1901.get("decision", ""),
        "v1901_label": v1901.get("label", ""),
        "v1901_pass": boolish(v1901.get("pass")),
        "v1898_manifest": rel(v1898_path),
        "v1898_decision": v1898.get("decision", ""),
        "v1898_label": v1898.get("label", ""),
        "v1898_pass": boolish(v1898.get("pass")),
        "v1899_manifest": rel(v1899_path),
        "v1899_decision": v1899.get("decision", ""),
        "v1899_label": v1899.get("label", ""),
        "v1899_pass": boolish(v1899.get("pass")),
        "android_ordered_internal_stateup": boolish(android_1898.get("ordered_internal_stateup")),
        "android_service74_count": intish(android_1898.get("service74_count")),
        "android_wlan_pd_count": intish(android_1898.get("wlan_pd_count")),
        "android_wlanmdsp_count": intish(android_1898.get("wlanmdsp_count")),
        "android_wlan0_time_s": android_1898.get("wlan0_time_s"),
        "android_pm_msg22_hits": intish(android_1898.get("pm_msg22_hits")),
        "android_pcie_mhi_before_wlan0": intish(android_1898.get("pcie_mhi_before_wlan0")),
        "android_degraded_257s_like": boolish(android_1898.get("degraded_257s_like")),
        "android_v1899_pm_msg22_count": intish(analysis_1899.get("pm_msg22_count")),
        "android_v1899_pending_qmi_client_count": intish(analysis_1899.get("pending_qmi_client_count")),
        "android_v1899_wlan0_time_s": dmesg_1899.get("wlan0_time_s"),
        "native_service180_counts": str(native_1898.get("v1885_service180_counts", "")),
        "native_service74_counts": str(native_1898.get("v1816_service74_counts", "")),
        "native_wlan_pd_counts": str(native_1898.get("v1885_wlan_pd_counts", "")),
        "native_servnotif_late_state": str(native_1898.get("late_servnotif_state", "")),
        "native_wlfw_service69_seen": str(native_1898.get("wlfw_service69_seen", "")),
        "native_requested_wlanmdsp": str(native_1898.get("requested_wlanmdsp", "")),
        "native_wlan0_present": str(native_1898.get("wlan0_present", "")),
        "qipcrtr_packet_received": boolish(v1901_v1834.get("qipcrtr_packet_received")),
        "qipcrtr_poll_timeout": boolish(v1901_v1834.get("qipcrtr_poll_timeout")),
        "wlfw_readback_service69_seen": str(v1901_v1803.get("wlfw_service69_seen", "")),
        "wlfw_readback_case0_service_events": intish(v1901_v1803.get("qrtr_case_0_service_events")),
        "wlfw_readback_case1_service_events": intish(v1901_v1803.get("qrtr_case_1_service_events")),
    }


def classify(source: dict[str, Any], evidence: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, bool]]:
    source_passive_edge_ok = (
        source["passive_servreg_edge_present"]
        and source["message_ids_present"]
        and source["state_values_present"]
        and source["restart_path_present"]
    )
    android_edge_observed = (
        evidence["v1898_pass"]
        and evidence["android_ordered_internal_stateup"]
        and evidence["android_service74_count"] > 0
        and evidence["android_wlan_pd_count"] > 0
        and evidence["android_wlanmdsp_count"] > 0
        and evidence["android_wlan0_time_s"] is not None
        and evidence["android_pm_msg22_hits"] == 0
        and evidence["android_pcie_mhi_before_wlan0"] == 0
        and not evidence["android_degraded_257s_like"]
        and evidence["v1899_pass"]
        and evidence["android_v1899_pm_msg22_count"] == 0
        and evidence["android_v1899_pending_qmi_client_count"] == 0
    )
    native_edge_absent = (
        evidence["v1901_pass"]
        and evidence["v1901_label"] == "servnotif-publication-absent-not-socket-mechanics"
        and positive_csv(evidence["native_service180_counts"])
        and zero_csv(evidence["native_service74_counts"])
        and zero_csv(evidence["native_wlan_pd_counts"])
        and evidence["native_servnotif_late_state"] == "uninit"
        and evidence["native_wlfw_service69_seen"] == "0"
        and evidence["native_requested_wlanmdsp"] == "0"
        and evidence["native_wlan0_present"] == "0"
        and evidence["qipcrtr_poll_timeout"]
        and not evidence["qipcrtr_packet_received"]
        and evidence["wlfw_readback_service69_seen"] == "0"
        and evidence["wlfw_readback_case0_service_events"] == 0
        and evidence["wlfw_readback_case1_service_events"] == 0
    )
    restart_pd_forbidden_not_triggered = True
    checks = {
        "source_passive_edge_ok": source_passive_edge_ok,
        "android_edge_observed_without_pmservice_msg22": android_edge_observed,
        "native_servreg_edge_absent": native_edge_absent,
        "restart_pd_is_mutating_forbidden_path": restart_pd_forbidden_not_triggered,
    }
    if all(checks.values()):
        return (
            "v1902-servnotif-root-service-indication-edge-host-pass",
            True,
            "service-notifier source maps the passive WLAN-PD state-up edge to SERVREG 0x42 instance new_server plus register-listener 0x20 and state-up indication 0x22; native lacks that edge while Android reaches it without pm-service msg22",
            "servnotif-root-service-indication-edge-not-pmservice-msg22",
            checks,
        )
    failing = ",".join(key for key, value in checks.items() if not value)
    return (
        "v1902-servnotif-source-edge-mismatch",
        False,
        f"source/evidence checks did not prove the service-notifier root-service indication edge: {failing}",
        "servnotif-source-edge-unproven",
        checks,
    )


def marker_row(markers: dict[str, dict[str, Any]], name: str) -> str:
    item = markers[name]
    location = f"{item['file']}:{item['line']}" if item["present"] else item["file"]
    return f"| `{name}` | `{item['present']}` | `{location}` |"


def render_report(result: dict[str, Any]) -> str:
    source = result["source"]
    evidence = result["evidence"]
    checks = result["checks"]
    source_markers = source["source_markers"]
    private_markers = source["private_markers"]
    header_markers = source["header_markers"]
    return "\n".join(
        [
            "# Native Init V1902 Service-notifier Source Edge Classifier",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            "- Type: host-only source/evidence classifier for the internal WLAN-PD servreg state-up edge",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Gate Checks",
            "",
            "| check | result |",
            "| --- | --- |",
            *[f"| `{key}` | `{value}` |" for key, value in checks.items()],
            "",
            "## Source Edge",
            "",
            "- Passive path: `qmi_add_lookup` for SERVREG service `0x42` at a target instance, `service_notifier_new_server`, listener registration request `0x20`, state-up indication `0x22`, and indication ACK `0x23`.",
            "- Mutating path: `service_notif_pd_restart` sends restart-PD request `0x24`; this is classified only as a forbidden/non-observation path.",
            "",
            "| marker | present | location |",
            "| --- | --- | --- |",
            marker_row(source_markers, "add_lookup"),
            marker_row(source_markers, "new_server_cb"),
            marker_row(source_markers, "new_server_print"),
            marker_row(source_markers, "new_server_work"),
            marker_row(source_markers, "register_listener_wrapper"),
            marker_row(source_markers, "state_ind_handler_table"),
            marker_row(source_markers, "state_ind_callback"),
            marker_row(source_markers, "state_ind_print"),
            marker_row(source_markers, "ack_worker"),
            marker_row(source_markers, "pd_restart_export"),
            "",
            "## Servreg IDs",
            "",
            "| marker | present | location |",
            "| --- | --- | --- |",
            marker_row(private_markers, "servreg_service_id"),
            marker_row(private_markers, "register_listener_msg"),
            marker_row(private_markers, "query_state_msg"),
            marker_row(private_markers, "state_updated_ind_msg"),
            marker_row(private_markers, "state_updated_ack_msg"),
            marker_row(private_markers, "restart_pd_msg"),
            marker_row(header_markers, "state_up"),
            marker_row(header_markers, "state_uninit"),
            marker_row(header_markers, "restart_pd_api"),
            "",
            "## Retained Evidence",
            "",
            f"- V1901 decision/label/pass: `{evidence['v1901_decision']}` / `{evidence['v1901_label']}` / `{evidence['v1901_pass']}`",
            f"- Android normal service74/wlan_pd/wlanmdsp/wlan0: `{evidence['android_service74_count']}` / `{evidence['android_wlan_pd_count']}` / `{evidence['android_wlanmdsp_count']}` / `{evidence['android_wlan0_time_s']}`",
            f"- Android pm-service msg22/pending-client: `{evidence['android_pm_msg22_hits']}` / `{evidence['android_v1899_pending_qmi_client_count']}`",
            f"- Native service180/service74/wlan_pd: `{evidence['native_service180_counts']}` / `{evidence['native_service74_counts']}` / `{evidence['native_wlan_pd_counts']}`",
            f"- Native servnotif/WLFW69/wlanmdsp/wlan0: `{evidence['native_servnotif_late_state']}` / `{evidence['native_wlfw_service69_seen']}` / `{evidence['native_requested_wlanmdsp']}` / `{evidence['native_wlan0_present']}`",
            f"- Passive QRTR/WLFW readback: poll_timeout=`{evidence['qipcrtr_poll_timeout']}`, packet_received=`{evidence['qipcrtr_packet_received']}`, service69=`{evidence['wlfw_readback_service69_seen']}`",
            "",
            "## Selected Boundary",
            "",
            "- The remaining edge is not `pm-service` msg22. It is the kernel `service-notifier` root-service state-up indication path for `msm/modem/wlan_pd`.",
            "- The next live unit, if run, should observe `service_notifier_new_server`, `new_server_work`, `root_service_service_ind_cb`, and `send_ind_ack` around native post-open without sending restart-PD.",
            "- Do not send `service_notif_pd_restart` or SERVREG restart-PD request `0x24`; that is a mutating trigger candidate, not read-only observation.",
            "",
            "## Safety Scope",
            "",
            "V1902 is host-only. It reads kernel source and retained manifests and writes local classifier artifacts only. "
            "It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, "
            "scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, "
            "forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, "
            "PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.",
            "",
            "## Next",
            "",
            "- Build one bounded native read-only observer for the kernel service-notifier passive edge, preferably tracefs/klog-only with explicit `restart_pd_executed=0`.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--service-notifier", type=Path, default=DEFAULT_SERVICE_NOTIFIER)
    parser.add_argument("--service-notifier-private", type=Path, default=DEFAULT_SERVICE_NOTIFIER_PRIVATE)
    parser.add_argument("--service-notifier-header", type=Path, default=DEFAULT_SERVICE_NOTIFIER_HEADER)
    parser.add_argument("--v1901-manifest", type=Path, default=DEFAULT_V1901_MANIFEST)
    parser.add_argument("--v1898-manifest", type=Path, default=DEFAULT_V1898_MANIFEST)
    parser.add_argument("--v1899-manifest", type=Path, default=DEFAULT_V1899_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = source_summary(
        REPO_ROOT / args.service_notifier,
        REPO_ROOT / args.service_notifier_private,
        REPO_ROOT / args.service_notifier_header,
    )
    evidence = evidence_summary(
        REPO_ROOT / args.v1901_manifest,
        REPO_ROOT / args.v1898_manifest,
        REPO_ROOT / args.v1899_manifest,
    )
    decision, passed, reason, label, checks = classify(source, evidence)
    store = EvidenceStore(REPO_ROOT / args.out_dir)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(store.run_dir),
        "report": rel(REPO_ROOT / args.report_path),
        "source": source,
        "evidence": evidence,
        "checks": checks,
        "safety": {
            "host_only": True,
            "device_command": False,
            "wifi_hal_scan_connect_ping": False,
            "restart_pd_request": False,
            "subsys_esoc0_open": False,
            "pcie_esoc_gdsc_path": False,
            "secret_material_written": False,
        },
    }
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(LATEST_POINTER, rel(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(REPO_ROOT / args.report_path, report)
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"label:    {label}")
    print(f"reason:   {reason}")
    print(f"evidence: {rel(store.run_dir)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
