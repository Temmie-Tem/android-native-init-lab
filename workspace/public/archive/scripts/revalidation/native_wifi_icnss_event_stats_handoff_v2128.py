#!/usr/bin/env python3
"""V2128 rollbackable handoff for ICNSS event stats."""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Any

import native_wifi_shared_server_info_post_cal_indication_handoff_v2122 as prev2122


CYCLE = "V2128"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2128-icnss-event-stats-handoff"
HANDOFF_DIR = OUT_DIR / "v2127-handoff"
HANDOFF_REPORT = OUT_DIR / "v2127-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2128_ICNSS_EVENT_STATS_HANDOFF_2026-06-05.md"
)
V2127_OUT = REPO_ROOT / "tmp" / "wifi" / "v2127-icnss-event-stats-test-boot"
V2127_INIT = V2127_OUT / "init_v2127_icnss_event_stats"
V2127_BOOT = V2127_OUT / "boot_linux_v2127_icnss_event_stats.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2127/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.238 (v2127-icnss-event-stats)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2127.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2127.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2127-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v422"
V422_IND_EVENTS = (
    "wlfw_qmi_ind_msa_ready_flag",
    "wlfw_qmi_ind_fw_mem_ready_flag",
)
ICNSS_STATS_PHASES = (
    "after_post_listener_window",
    "after_early_listener",
    "after_holder_start",
)
ICNSS_STATS_KEYS = (
    "open",
    "numeric",
    "ind_register_req",
    "ind_register_resp",
    "ind_register_err",
    "msa_info_req",
    "msa_info_resp",
    "msa_info_err",
    "msa_ready_req",
    "msa_ready_resp",
    "msa_ready_err",
    "msa_ready_ind",
    "cap_req",
    "cap_resp",
    "cap_err",
    "pin_connect_result",
    "cfg_req",
    "cfg_resp",
    "cfg_req_err",
    "mode_req",
    "mode_resp",
    "mode_req_err",
    "ini_req",
    "ini_resp",
    "ini_req_err",
    "event_summary",
    "event.server_arrive.posted",
    "event.server_arrive.processed",
    "event.fw_ready.posted",
    "event.fw_ready.processed",
    "event.register_driver.posted",
    "event.register_driver.processed",
    "state.seen",
)
CAP_EVENTS = (
    "wlfw_fw_mem_wait_return",
    "wlfw_cap_send_ret",
    "wlfw_cap_send_or_result_error_branch",
    "wlfw_cap_invalid_0x77_branch",
    "wlfw_cap_success_branch",
    "wlfw_cap_rsp_result_error_branch",
    "wlfw_cap_return",
)
BDF_EVENTS = (
    "wlfw_bdf_entry",
    "wlfw_bdf_named_path_ready",
    "wlfw_bdf_open_success",
    "wlfw_bdf_not_found",
    "wlfw_bdf_read_complete",
    "wlfw_bdf_send_call",
    "wlfw_bdf_send_ret",
    "wlfw_bdf_send_error_branch",
    "wlfw_bdf_result_log",
    "wlfw_bdf_return",
)
TAIL_EVENTS = (
    "wlfw_cal_report_entry",
    "wlfw_cal_report_send_ret",
    "wlfw_cal_report_error_branch",
    "wlfw_cal_report_success_branch",
    "wlfw_cal_report_return",
    "dms_get_wlan_address_entry",
    "dms_get_wlan_address_send_ret",
    "dms_get_wlan_address_valid_mac",
    "dms_get_wlan_address_return",
    "dms_service_request_init_ret",
    "dms_service_request_cond_wait",
    "dms_service_request_send_ret",
    "dms_service_request_success_branch",
    "wlan_send_status_entry",
    "wlan_send_status_send_ret",
    "wlan_send_status_return",
    "wlan_send_version_entry",
    "wlan_send_version_open_success",
    "wlan_send_version_not_found",
    "wlan_send_version_send_ret",
    "wlan_send_version_return",
)
IND_EVENTS = (
    "wlfw_worker_second_bdf_branch",
    "wlfw_worker_cal_only_call",
    "wlfw_worker_cal_only_retcheck",
    "wlfw_worker_done_signal",
    "wlfw_worker_post_done_wait",
    "wlfw_worker_handle_ind_call",
    "wlfw_qmi_ind_cb_entry",
    "wlfw_qmi_ind_msg_unknown",
    "wlfw_qmi_ind_decode_0x28_ok",
    "wlfw_qmi_ind_decode_0x2a_ok",
    "wlfw_qmi_ind_decode_0x41_ok",
    *V422_IND_EVENTS,
    "wlfw_qmi_ind_queue_link",
    "wlfw_qmi_ind_cond_signal",
    "wlfw_handle_ind_entry",
    "wlfw_handle_ind_type",
    "wlfw_handle_ind_type_0x28",
    "wlfw_handle_ind_type_0x2a",
    "wlfw_handle_ind_type_0x41",
)

prev2121 = prev2122.prev2121
prev2113 = prev2122.prev2113


def rel(path: Path) -> str:
    return prev2122.rel(path)


def intish(value: object) -> int:
    return prev2122.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2122.markdown_table(headers, rows)


def read_helper_text() -> str:
    parts: list[str] = []
    for path in (
        HANDOFF_DIR / "test-v1393-helper-result.stdout.txt",
        HANDOFF_DIR / "test-v1393-helper-result.stderr.txt",
        HANDOFF_DIR / "test-v1393-log.stdout.txt",
        HANDOFF_DIR / "test-v1393-summary.stdout.txt",
    ):
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        line = line.replace("\x00", "")
        if "=" not in line or line.startswith("A90_EXECNS_PATH_"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def focused_int(fields: dict[str, str], suffix: str) -> int:
    return intish(fields.get(f"wlfw_late_msg21_focused.{suffix}", ""))


def focused_int_any(fields: dict[str, str], *suffixes: str) -> int:
    for suffix in suffixes:
        key = f"wlfw_late_msg21_focused.{suffix}"
        if key in fields:
            return intish(fields.get(key, ""))
    return 0


def collect_icnss_stats_numeric(fields: dict[str, str]) -> dict[str, Any]:
    phases: dict[str, dict[str, int]] = {}
    best_phase = ""
    for phase in ICNSS_STATS_PHASES:
        prefix = f"wlan_pd_icnss_ipc_snapshot.{phase}.icnss_stats."
        values = {key: intish(fields.get(prefix + key, "")) for key in ICNSS_STATS_KEYS}
        values["state_hex"] = fields.get(prefix + "state.hex", "")
        values["state_line"] = fields.get(prefix + "state.line", "")
        phases[phase] = values
        if not best_phase and values.get("open", 0) > 0 and values.get("numeric", 0) > 0:
            best_phase = phase

    max_values: dict[str, int] = {}
    for key in ICNSS_STATS_KEYS:
        observed = [values.get(key, -1) for values in phases.values() if values.get(key, -1) >= 0]
        max_values[key] = max(observed) if observed else -1

    if not best_phase:
        best_phase = ICNSS_STATS_PHASES[0]
    best_values = phases.get(best_phase, {})
    return {
        "best_phase": best_phase,
        "phases": phases,
        "max": max_values,
        "state_hex": best_values.get("state_hex", ""),
        "state_line": best_values.get("state_line", ""),
        **max_values,
    }


def stats_rows(stats: dict[str, Any]) -> list[list[object]]:
    max_values = stats.get("max", {}) if isinstance(stats.get("max"), dict) else {}
    phases = stats.get("phases", {}) if isinstance(stats.get("phases"), dict) else {}
    rows: list[list[object]] = [
        ["selected", stats.get("best_phase", ""), f"open={max_values.get('open')} numeric={max_values.get('numeric')}"],
        ["ind_register", "", f"req={max_values.get('ind_register_req')} resp={max_values.get('ind_register_resp')} err={max_values.get('ind_register_err')}"],
        ["msa_info", "", f"req={max_values.get('msa_info_req')} resp={max_values.get('msa_info_resp')} err={max_values.get('msa_info_err')}"],
        ["msa_ready", "", f"req={max_values.get('msa_ready_req')} resp={max_values.get('msa_ready_resp')} err={max_values.get('msa_ready_err')} ind={max_values.get('msa_ready_ind')}"],
        ["cap", "", f"req={max_values.get('cap_req')} resp={max_values.get('cap_resp')} err={max_values.get('cap_err')}"],
        ["event_summary", max_values.get("event_summary"), f"state={stats.get('state_hex')} {stats.get('state_line')}"],
        ["event_server_arrive", "", f"posted={max_values.get('event.server_arrive.posted')} processed={max_values.get('event.server_arrive.processed')}"],
        ["event_fw_ready", "", f"posted={max_values.get('event.fw_ready.posted')} processed={max_values.get('event.fw_ready.processed')}"],
        ["event_register_driver", "", f"posted={max_values.get('event.register_driver.posted')} processed={max_values.get('event.register_driver.processed')}"],
        ["cfg_mode_ini", "", f"cfg={max_values.get('cfg_req')}/{max_values.get('cfg_resp')}/{max_values.get('cfg_req_err')} mode={max_values.get('mode_req')}/{max_values.get('mode_resp')}/{max_values.get('mode_req_err')} ini={max_values.get('ini_req')}/{max_values.get('ini_resp')}/{max_values.get('ini_req_err')}"],
        ["pin_connect", max_values.get("pin_connect_result"), ""],
    ]
    for phase in ICNSS_STATS_PHASES:
        values = phases.get(phase, {}) if isinstance(phases.get(phase), dict) else {}
        rows.append([
            phase,
            f"open={values.get('open')} numeric={values.get('numeric')}",
            f"fw_event={values.get('event.fw_ready.posted')}/{values.get('event.fw_ready.processed')} state={values.get('state_hex')} ind_reg={values.get('ind_register_resp')} msa_ind={values.get('msa_ready_ind')} cap={values.get('cap_resp')}",
        ])
    return rows


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}."
    return {
        "name": name,
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "fetch_args": fields.get(prefix + "fetch_args", ""),
        "sample_line_0": fields.get(prefix + "sample_line_0", ""),
        "sample_line_1": fields.get(prefix + "sample_line_1", ""),
    }


def first_value(line: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}=(0x[0-9a-fA-F]+|-?[0-9]+)", line)
    return match.group(1) if match else ""


def first_event_value(data: dict[str, str], *keys: str) -> str:
    line = data.get("first_hit_line", "")
    for key in keys:
        value = first_value(line, key)
        if value:
            return value
    return ""


def collect_post_cal(fields: dict[str, str]) -> dict[str, Any]:
    cap_events = {name: event(fields, name) for name in CAP_EVENTS}
    bdf_events = {name: event(fields, name) for name in BDF_EVENTS}
    tail_events = {name: event(fields, name) for name in TAIL_EVENTS}
    ind_events = {name: event(fields, name) for name in IND_EVENTS}
    cal_success = tail_events["wlfw_cal_report_success_branch"]
    cal_send = tail_events["wlfw_cal_report_send_ret"]
    return {
        "cap_events": cap_events,
        "bdf_events": bdf_events,
        "tail_events": tail_events,
        "ind_events": ind_events,
        "cap_return_rc": first_event_value(cap_events["wlfw_cap_return"], "rc"),
        "bdf_return_rc": first_event_value(bdf_events["wlfw_bdf_return"], "rc"),
        "bdf_send_rc": first_event_value(bdf_events["wlfw_bdf_send_ret"], "send_rc"),
        "bdf_qmi_result": first_event_value(bdf_events["wlfw_bdf_result_log"], "qmi_result"),
        "bdf_qmi_error": first_event_value(bdf_events["wlfw_bdf_result_log"], "qmi_error"),
        "cal_send_rc": first_event_value(tail_events["wlfw_cal_report_send_ret"], "send_rc"),
        "cal_qmi_result": first_event_value(cal_success, "qmi_result") or first_event_value(cal_send, "qmi_result"),
        "cal_qmi_error": first_event_value(cal_success, "qmi_error") or first_event_value(cal_send, "qmi_error"),
        "cal_return_rc": first_event_value(tail_events["wlfw_cal_report_return"], "rc"),
        "dms_addr_send_rc": first_event_value(tail_events["dms_get_wlan_address_send_ret"], "send_rc"),
        "dms_addr_qmi_result": first_event_value(tail_events["dms_get_wlan_address_send_ret"], "qmi_result"),
        "dms_addr_return_rc": first_event_value(tail_events["dms_get_wlan_address_return"], "rc"),
        "dms_req_init_rc": first_event_value(tail_events["dms_service_request_init_ret"], "rc"),
        "dms_req_send_rc": first_event_value(tail_events["dms_service_request_send_ret"], "send_rc"),
        "dms_req_qmi_result": first_event_value(tail_events["dms_service_request_send_ret"], "qmi_result"),
        "dms_req_qmi_error": first_event_value(tail_events["dms_service_request_send_ret"], "qmi_error"),
        "status_send_rc": first_event_value(tail_events["wlan_send_status_send_ret"], "send_rc"),
        "status_qmi_result": first_event_value(tail_events["wlan_send_status_send_ret"], "qmi_result"),
        "status_return_rc": first_event_value(tail_events["wlan_send_status_return"], "rc"),
        "version_send_rc": first_event_value(tail_events["wlan_send_version_send_ret"], "send_rc"),
        "version_qmi_result": first_event_value(tail_events["wlan_send_version_send_ret"], "qmi_result"),
        "version_return_rc": first_event_value(tail_events["wlan_send_version_return"], "rc"),
    }


def collect_focused_indication(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlfw_late_msg21_focused."
    samples = [
        fields.get(prefix + "qmi_cb.sample_0", ""),
        fields.get(prefix + "qmi_cb.sample_1", ""),
        fields.get(prefix + "qmi_cb.sample_2", ""),
        fields.get(prefix + "qmi_cb.sample_3", ""),
    ]
    return {
        "begin": focused_int(fields, "begin"),
        "mode": fields.get(prefix + "mode", ""),
        "qmi_cb_hit_count": focused_int(fields, "qmi_cb.hit_count"),
        "qmi_cb_sample_count": focused_int(fields, "qmi_cb.sample_count"),
        "saw_msg21": focused_int(fields, "qmi_cb.saw_msg21"),
        "saw_msg2b": focused_int(fields, "qmi_cb.saw_msg2b"),
        "saw_msg37": focused_int(fields, "qmi_cb.saw_msg37"),
        "first": fields.get(prefix + "qmi_cb.first", ""),
        "samples": samples,
        "queue_link_hit_count": focused_int(fields, "queue_link.hit_count"),
        "cond_signal_hit_count": focused_int(fields, "cond_signal.hit_count"),
        "msa_ready_flag_hit_count": focused_int_any(
            fields,
            "msa_ready_flag.hit_count",
            "fw_mem_flag.hit_count",
        ),
        "fw_mem_ready_flag_hit_count": focused_int_any(
            fields,
            "fw_mem_ready_flag.hit_count",
            "msa_flag.hit_count",
        ),
        "handle_ind_hit_count": focused_int(fields, "handle_ind.hit_count"),
        "wlan_status_hit_count": focused_int(fields, "wlan_status.hit_count"),
        "wlan_version_hit_count": focused_int(fields, "wlan_version.hit_count"),
        "cal_return_hit_count": focused_int(fields, "cal_return.hit_count"),
    }


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    return prev2122.event_rows(events)


def focused_rows(focused: dict[str, Any]) -> list[list[object]]:
    return [
        ["qmi_cb", focused.get("qmi_cb_hit_count"), focused.get("first", "")],
        ["samples", focused.get("qmi_cb_sample_count"), " | ".join(str(item) for item in focused.get("samples", []) if item and item != "none")],
        ["msg21", focused.get("saw_msg21"), "QMI_WLFW_FW_READY_IND_V01 userspace callback observed"],
        ["msg2b", focused.get("saw_msg2b"), "QMI_WLFW_MSA_READY_IND_V01 callback observed"],
        ["msg37", focused.get("saw_msg37"), "QMI_WLFW_MEM_READY_IND_V01 callback observed"],
        ["msa_ready_flag", focused.get("msa_ready_flag_hit_count"), "`cnss-daemon` offset 0xe2f0"],
        ["fw_mem_ready_flag", focused.get("fw_mem_ready_flag_hit_count"), "`cnss-daemon` offset 0xe328"],
        ["queue_link", focused.get("queue_link_hit_count"), "decoded indication queue edge"],
        ["cond_signal", focused.get("cond_signal_hit_count"), "callback condition signal"],
        ["handle_ind", focused.get("handle_ind_hit_count"), "worker indication handler"],
        ["wlan_status", focused.get("wlan_status_hit_count"), "WLAN status send path"],
        ["wlan_version", focused.get("wlan_version_hit_count"), "WLAN version send path"],
    ]


def post_cal_value(details: dict[str, Any], key: str) -> str:
    return prev2122.post_cal_value(details, key)


def post_cal_hit(details: dict[str, Any], group: str, event: str) -> int:
    return prev2122.post_cal_hit(details, group, event)


def cap_bdf_cal_success(details: dict[str, Any]) -> bool:
    return prev2122.cap_bdf_cal_success(details)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2127",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "android_parity=firmware_mnt_probe_present_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "shared_server_info.tmpfs_requested=1",
        "shared_server_info.absolute=/vendor/rfs/msm/mpss/shared/server_info.txt",
        "shared_server_info.rootfs_namespace_only=1",
        "shared_server_info.sda29_write=0",
        "wifi_companion_start.tftp_shared_server_info_tmpfs.enabled=%d",
        "wifi_companion_start.tftp_shared_server_info_tmpfs.path=/vendor/rfs/msm/mpss/shared/server_info.txt",
        "vendor_rfs_shared_server_info",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.enabled=%d",
        "wifi_companion_start.tftp_process_namespace_audit.compiled=%d",
        "persist_rfs_mdm_mpss",
        "persist_rfs_apq_gnss",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "wlfw_late_msg21_focused.qmi_cb.saw_msg37=%d",
        "wlfw_late_msg21_focused.msa_ready_flag.hit_count=%d",
        "wlfw_late_msg21_focused.fw_mem_ready_flag.hit_count=%d",
        "wlfw_qmi_ind_msa_ready_flag",
        "wlfw_qmi_ind_fw_mem_ready_flag",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.numeric=1",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.ind_register_req=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.ind_register_resp=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.msa_ready_resp=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.msa_ready_ind=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.cap_resp=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event_summary=1",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event.fw_ready.posted=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event.fw_ready.processed=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event.register_driver.posted=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.state.hex=%s",
        "icnss_qcacld_post_bdf_focused",
    )
    boot_forbidden = (
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "post_bdf_boot_wlan_consumer_gate.begin=1",
        "ota_firewall/ruleset:",
        "tftp_server-android-runtime",
        "wlfw_qmi_ind_fw_mem_flag",
        "wlfw_qmi_ind_msa_flag",
        "wlfw_late_msg21_focused.fw_mem_flag.hit_count",
        "wlfw_late_msg21_focused.msa_flag.hit_count",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2127_INIT, init_required), (V2127_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2127_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2121.collect_details(handoff)
    fields = parse_fields(read_helper_text())
    focused = collect_focused_indication(fields)
    post_cal = collect_post_cal(fields)
    icnss_stats = collect_icnss_stats_numeric(fields)
    cond = post_cal["ind_events"].get("wlfw_qmi_ind_cond_signal", {})
    if not cond.get("hit_count") and focused.get("cond_signal_hit_count"):
        cond["hit_count"] = str(focused["cond_signal_hit_count"])
    details["wlfw_late_msg21_focused"] = focused
    details["post_cal_indication"] = post_cal
    details["icnss_stats_numeric"] = icnss_stats
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2121.classify(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused") if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    stats = details.get("icnss_stats_numeric") if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    wlan0 = intish(cascade.get("wlan0")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    status_hits = intish(focused.get("wlan_status_hit_count"))
    version_hits = intish(focused.get("wlan_version_hit_count"))
    qmi_hits = intish(focused.get("qmi_cb_hit_count"))
    saw_msg21 = intish(focused.get("saw_msg21")) > 0
    saw_msg2b = intish(focused.get("saw_msg2b")) > 0
    saw_msg37 = intish(focused.get("saw_msg37")) > 0
    msa_ready_hits = intish(focused.get("msa_ready_flag_hit_count"))
    fw_mem_ready_hits = intish(focused.get("fw_mem_ready_flag_hit_count"))
    queue_hits = intish(focused.get("queue_link_hit_count"))
    handle_hits = intish(focused.get("handle_ind_hit_count"))
    stats_open = intish(stats.get("open"))
    stats_numeric = intish(stats.get("numeric"))
    event_summary = intish(stats.get("event_summary"))
    fw_ready_posted = intish(stats.get("event.fw_ready.posted"))
    fw_ready_processed = intish(stats.get("event.fw_ready.processed"))
    register_driver_posted = intish(stats.get("event.register_driver.posted"))
    register_driver_processed = intish(stats.get("event.register_driver.processed"))
    server_arrive_posted = intish(stats.get("event.server_arrive.posted"))
    server_arrive_processed = intish(stats.get("event.server_arrive.processed"))
    ind_register_resp = intish(stats.get("ind_register_resp"))
    ind_register_err = intish(stats.get("ind_register_err"))
    msa_ready_resp = intish(stats.get("msa_ready_resp"))
    msa_ready_err = intish(stats.get("msa_ready_err"))
    msa_ready_ind = intish(stats.get("msa_ready_ind"))
    cap_resp = intish(stats.get("cap_resp"))
    cap_err = intish(stats.get("cap_err"))
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("shared_server_info_bridge_ok"))
        and intish(base.get("server_info_startup_error_count")) == 0
        and intish(cascade.get("wlan_pd_up")) > 0
        and intish(cascade.get("icnss_qmi_connected")) > 0
        and cap_bdf_cal_success(details)
        and all(bool(step.get("ok")) for step in steps)
    )

    if not route_ok:
        label = "icnss-stats-route-regression"
        passed = False
        reason = "V2128 did not preserve shared-server-info, wlan_pd UP, ICNSS QMI, cap/BDF/cal, or rollback prerequisites"
    elif stats_open <= 0 or stats_numeric <= 0:
        label = "icnss-event-stats-numeric-missing"
        passed = False
        reason = "helper v422 ran but did not return readable numeric `/sys/kernel/debug/icnss/stats` counters"
    elif event_summary <= 0:
        label = "icnss-event-stats-missing"
        passed = False
        reason = "helper v422 ran but did not return ICNSS event-table counters"
    elif wlan0:
        label = "icnss-event-stats-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "icnss-event-stats-fw-ready-progress"
        passed = True
        reason = "native reached kernel FW_READY; chase wlan0 next"
    elif ind_register_resp <= 0 or ind_register_err > 0:
        label = "icnss-kernel-ind-register-failed"
        passed = True
        reason = "kernel ICNSS indication registration did not complete cleanly before the post-cal WLFW edge"
    elif msa_ready_resp <= 0 or msa_ready_err > 0:
        label = "icnss-kernel-msa-ready-req-failed"
        passed = True
        reason = "kernel ICNSS MSA-ready request did not complete cleanly, so WLFW FW_READY cannot be trusted downstream"
    elif cap_resp <= 0 or cap_err > 0:
        label = "icnss-kernel-cap-req-failed"
        passed = True
        reason = "kernel ICNSS capability request counters did not complete cleanly despite userspace BDF/cal progress"
    elif qmi_hits > 0 and msa_ready_ind <= 0:
        label = "wlfw-userspace-indications-kernel-msa-ind-missing"
        passed = True
        reason = "cnss-daemon saw WLFW indications, but kernel ICNSS stats did not record MSA-ready indication delivery"
    elif msa_ready_ind > 0 and saw_msg21 and fw_ready_posted <= 0:
        label = "wlfw-fw-ready-userspace-msg21-kernel-event-not-posted"
        passed = True
        reason = "cnss-daemon saw FW_READY msg 0x21, but ICNSS event stats show no kernel FW_READY event was posted"
    elif fw_ready_posted > 0 and fw_ready_processed <= 0:
        label = "wlfw-fw-ready-event-posted-not-processed"
        passed = True
        reason = "kernel ICNSS FW_READY event was posted but not processed by the event worker"
    elif fw_ready_processed > 0 and register_driver_posted <= 0:
        label = "wlfw-fw-ready-processed-register-driver-not-posted"
        passed = True
        reason = "kernel ICNSS FW_READY event processed, but driver registration/probe event did not post"
    elif fw_ready_processed > 0 and register_driver_processed > 0 and not wlan0:
        label = "wlfw-register-driver-processed-no-wlan0"
        passed = True
        reason = "kernel ICNSS FW_READY and register-driver events processed, but wlan0 did not appear"
    elif qmi_hits == 0:
        label = "icnss-event-stats-none-from-wlfw"
        passed = True
        reason = "cap/BDF/cal succeeded, but cnss-daemon received no WLFW QMI indication from the WLAN PD"
    elif status_hits > 0 or version_hits > 0:
        label = "icnss-event-stats-status-version-no-fw-ready"
        passed = True
        reason = "post-cal status/version path ran but did not produce kernel FW_READY/wlan0"
    elif saw_msg2b and msa_ready_hits > 0 and not saw_msg37 and fw_mem_ready_hits == 0:
        label = "icnss-event-stats-msa-ready-no-fw-mem-ready"
        passed = True
        reason = "MSA-ready msg 0x2b reached cnss-daemon, but FW-memory-ready msg 0x37 did not appear"
    elif queue_hits == 0:
        label = "icnss-event-stats-indication-callback-not-queued"
        passed = True
        reason = "WLFW QMI callback ran, but no decoded indication was queued for the worker"
    elif handle_hits == 0:
        label = "icnss-event-stats-indication-queued-not-drained"
        passed = True
        reason = "WLFW indication was queued, but the worker did not drain it"
    else:
        label = "icnss-event-stats-unresolved-no-fw-ready"
        passed = True
        reason = "ICNSS counters and WLFW indications advanced, but kernel FW_READY/wlan0 still did not appear"

    return {
        **base,
        "decision": f"v2128-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "cap_bdf_cal_success": cap_bdf_cal_success(details),
        "focused_qmi_hits": qmi_hits,
        "focused_saw_msg21": 1 if saw_msg21 else 0,
        "focused_saw_msg2b": 1 if saw_msg2b else 0,
        "focused_saw_msg37": 1 if saw_msg37 else 0,
        "focused_msa_ready_hits": msa_ready_hits,
        "focused_fw_mem_ready_hits": fw_mem_ready_hits,
        "focused_queue_hits": queue_hits,
        "focused_handle_hits": handle_hits,
        "focused_status_hits": status_hits,
        "focused_version_hits": version_hits,
        "icnss_stats_phase": stats.get("best_phase", ""),
        "icnss_stats_open": stats_open,
        "icnss_stats_numeric": stats_numeric,
        "icnss_event_summary": event_summary,
        "icnss_server_arrive_posted": server_arrive_posted,
        "icnss_server_arrive_processed": server_arrive_processed,
        "icnss_fw_ready_posted": fw_ready_posted,
        "icnss_fw_ready_processed": fw_ready_processed,
        "icnss_register_driver_posted": register_driver_posted,
        "icnss_register_driver_processed": register_driver_processed,
        "icnss_state_hex": stats.get("state_hex", ""),
        "icnss_state_line": stats.get("state_line", ""),
        "icnss_ind_register_resp": ind_register_resp,
        "icnss_ind_register_err": ind_register_err,
        "icnss_msa_ready_resp": msa_ready_resp,
        "icnss_msa_ready_err": msa_ready_err,
        "icnss_msa_ready_ind": msa_ready_ind,
        "icnss_cap_resp": cap_resp,
        "icnss_cap_err": cap_err,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    shared = details.get("shared_server_info_bridge", {}) if isinstance(details.get("shared_server_info_bridge"), dict) else {}
    post = details.get("post_cal_indication", {}) if isinstance(details.get("post_cal_indication"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused", {}) if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    stats = details.get("icnss_stats_numeric", {}) if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    tail = post.get("tail_events", {}) if isinstance(post.get("tail_events"), dict) else {}
    ind = post.get("ind_events", {}) if isinstance(post.get("ind_events"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2128 ICNSS Event Stats Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2128`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["artifact", classification.get("hook_ok"), f"helper={EXPECTED_HELPER_VERSION}"],
                ["shared_server_info", classification.get("shared_server_info_bridge_ok"), f"mode={shared.get('mode')} uid_gid={shared.get('uid')}:{shared.get('gid')} errno={shared.get('stat_errno')}"],
                ["tftp_branch", "", f"server_check={branch.get('server_check')} ota={classification.get('ota_seen')} wlanmdsp={classification.get('wlanmdsp_seen')}"],
                ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post.get('cap_return_rc')} bdf={post.get('bdf_return_rc')} bdf_qmi={post.get('bdf_qmi_result')} cal={post.get('cal_return_rc')}"],
                ["icnss_stats", "", f"phase={classification.get('icnss_stats_phase')} open={classification.get('icnss_stats_open')} numeric={classification.get('icnss_stats_numeric')} ind_reg_resp={classification.get('icnss_ind_register_resp')} msa_ready_resp={classification.get('icnss_msa_ready_resp')} msa_ready_ind={classification.get('icnss_msa_ready_ind')} cap_resp={classification.get('icnss_cap_resp')}"],
                ["icnss_events", "", f"summary={classification.get('icnss_event_summary')} server={classification.get('icnss_server_arrive_posted')}/{classification.get('icnss_server_arrive_processed')} fw_ready={classification.get('icnss_fw_ready_posted')}/{classification.get('icnss_fw_ready_processed')} register_driver={classification.get('icnss_register_driver_posted')}/{classification.get('icnss_register_driver_processed')} state={classification.get('icnss_state_hex')}"],
                ["focused_msg", "", f"qmi={classification.get('focused_qmi_hits')} msg21={classification.get('focused_saw_msg21')} msg2b={classification.get('focused_saw_msg2b')} msg37={classification.get('focused_saw_msg37')}"],
                ["focused_flags", "", f"msa_ready={classification.get('focused_msa_ready_hits')} fw_mem_ready={classification.get('focused_fw_mem_ready_hits')} queue={classification.get('focused_queue_hits')} handle={classification.get('focused_handle_hits')}"],
                ["status_version", "", f"status={classification.get('focused_status_hits')} version={classification.get('focused_version_hits')} dms_addr_qmi={post.get('dms_addr_qmi_result')} dms_addr_rc={post.get('dms_addr_return_rc')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Focused Indication",
        "",
        markdown_table(["edge", "hits", "detail"], focused_rows(focused)),
        "",
        "## ICNSS Stats",
        "",
        markdown_table(["area", "value", "detail"], stats_rows(stats)),
        "",
        "## Tail Events",
        "",
        markdown_table(["event", "hits", "fetch", "first"], event_rows(tail)),
        "",
        "## Indication Events",
        "",
        markdown_table(["event", "hits", "fetch", "first"], event_rows(ind)),
        "",
        "## Interpretation",
        "",
        "- V2128 keeps the V2120/V2123 route and adds only `/sys/kernel/debug/icnss/stats` event-table parsing in helper v422.",
        "- Correct focused mapping remains: `0xe2f0` is `Received MSA Ready Ind` / msg `0x2b`; `0xe328` is `Received FW memory ready indication` / msg `0x37`; msg `0x21` is `QMI_WLFW_FW_READY_IND_V01`.",
        "- The discriminator is after `wlfw_cal_report_return rc=0x0`: ICNSS `FW_READY` posted/processed counters, state bits, WLFW QMI msg ids, kernel FW_READY, and `wlan0`.",
        "- Android reference stays the normal V1982/V1753 baseline: ICNSS QMI server connected around 9.57s, BDF around 9.72s, kernel FW_READY around 14.62s, and `wlan0` around 14.87s.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2127 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_modules() -> None:
    prev2121.HANDOFF_DIR = HANDOFF_DIR
    prev2121.HANDOFF_REPORT = HANDOFF_REPORT
    prev2121.V2120_OUT = V2127_OUT
    prev2121.V2120_INIT = V2127_INIT
    prev2121.V2120_BOOT = V2127_BOOT
    prev2121.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2121.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2121.TEST_LOG_PATH = TEST_LOG_PATH
    prev2121.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2121.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2121.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION

    prev2113.CYCLE = CYCLE
    prev2113.OUT_DIR = OUT_DIR
    prev2113.HANDOFF_DIR = HANDOFF_DIR
    prev2113.HANDOFF_REPORT = HANDOFF_REPORT
    prev2113.REPORT_PATH = REPORT_PATH
    prev2113.V2112_OUT = V2127_OUT
    prev2113.V2112_INIT = V2127_INIT
    prev2113.V2112_BOOT = V2127_BOOT
    prev2113.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2113.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2113.TEST_LOG_PATH = TEST_LOG_PATH
    prev2113.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2113.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2113.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2113.BRIDGE_CAPTURE = OUT_DIR / "host" / "v2128-autostart-bridge.log"
    prev2113.BRIDGE_STDOUT = OUT_DIR / "host" / "v2128-autostart-bridge.stdout.txt"
    prev2113.BRIDGE_STDERR = OUT_DIR / "host" / "v2128-autostart-bridge.stderr.txt"
    prev2113.BRIDGE_PID = OUT_DIR / "host" / "v2128-autostart-bridge.pid"
    prev2113.artifact_hook_check = artifact_hook_check
    prev2113.collect_details = collect_details
    prev2113.classify = classify
    prev2113.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_modules()
    return prev2113.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
