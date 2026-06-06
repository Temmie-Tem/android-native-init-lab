#!/usr/bin/env python3
"""V2124 rollbackable handoff for corrected WLFW indication labels."""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Any

import native_wifi_shared_server_info_post_cal_indication_handoff_v2122 as prev2122


CYCLE = "V2124"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2124-wlfw-indication-label-fix-handoff"
HANDOFF_DIR = OUT_DIR / "v2123-handoff"
HANDOFF_REPORT = OUT_DIR / "v2123-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2124_WLFW_INDICATION_LABEL_FIX_HANDOFF_2026-06-05.md"
)
V2123_OUT = REPO_ROOT / "tmp" / "wifi" / "v2123-wlfw-indication-label-fix-test-boot"
V2123_INIT = V2123_OUT / "init_v2123_wlfw_indication_label_fix"
V2123_BOOT = V2123_OUT / "boot_linux_v2123_wlfw_indication_label_fix.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2123/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.236 (v2123-wlfw-indication-label-fix)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2123.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2123.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2123-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v420"
V420_IND_EVENTS = (
    "wlfw_qmi_ind_msa_ready_flag",
    "wlfw_qmi_ind_fw_mem_ready_flag",
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
    *V420_IND_EVENTS,
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
        "A90v2123",
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
    for path, required in ((V2123_INIT, init_required), (V2123_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2123_INIT else boot_forbidden
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
    cond = post_cal["ind_events"].get("wlfw_qmi_ind_cond_signal", {})
    if not cond.get("hit_count") and focused.get("cond_signal_hit_count"):
        cond["hit_count"] = str(focused["cond_signal_hit_count"])
    details["wlfw_late_msg21_focused"] = focused
    details["post_cal_indication"] = post_cal
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2121.classify(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused") if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
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
        label = "wlfw-label-fix-route-regression"
        passed = False
        reason = "V2124 did not preserve shared-server-info, wlan_pd UP, ICNSS QMI, cap/BDF/cal, or rollback prerequisites"
    elif wlan0:
        label = "wlfw-label-fix-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "wlfw-label-fix-fw-ready-progress"
        passed = True
        reason = "native reached kernel FW_READY; chase wlan0 next"
    elif status_hits > 0 or version_hits > 0:
        label = "wlfw-label-fix-status-version-no-fw-ready"
        passed = True
        reason = "post-cal status/version path ran but did not produce kernel FW_READY/wlan0"
    elif qmi_hits == 0:
        label = "wlfw-label-fix-none-from-wlfw"
        passed = True
        reason = "cap/BDF/cal succeeded, but cnss-daemon received no WLFW QMI indication from the WLAN PD"
    elif saw_msg21 and not fw_ready:
        label = "wlfw-fw-ready-msg21-userspace-seen-kernel-missing"
        passed = True
        reason = "cnss-daemon saw QMI WLFW FW_READY indication msg 0x21, but Samsung userspace takes the no-op branch and kernel FW_READY/wlan0 did not follow"
    elif saw_msg2b and msa_ready_hits > 0 and not saw_msg37 and fw_mem_ready_hits == 0:
        label = "wlfw-msa-ready-no-fw-mem-ready"
        passed = True
        reason = "MSA-ready msg 0x2b reached cnss-daemon, but FW-memory-ready msg 0x37 did not appear"
    elif queue_hits == 0:
        label = "wlfw-indication-callback-not-queued"
        passed = True
        reason = "WLFW QMI callback ran, but no decoded indication was queued for the worker"
    elif handle_hits == 0:
        label = "wlfw-indication-queued-not-drained"
        passed = True
        reason = "WLFW indication was queued, but the worker did not drain it"
    else:
        label = "wlfw-indication-handled-no-fw-ready"
        passed = True
        reason = "WLFW indication was delivered and handled, but kernel FW_READY/wlan0 still did not appear"

    return {
        **base,
        "decision": f"v2124-{label}-rollback-{'pass' if passed else 'blocked'}",
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
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    shared = details.get("shared_server_info_bridge", {}) if isinstance(details.get("shared_server_info_bridge"), dict) else {}
    post = details.get("post_cal_indication", {}) if isinstance(details.get("post_cal_indication"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused", {}) if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    tail = post.get("tail_events", {}) if isinstance(post.get("tail_events"), dict) else {}
    ind = post.get("ind_events", {}) if isinstance(post.get("ind_events"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2124 WLFW Indication Label Fix Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2124`",
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
        "- V2124 keeps the V2120/V2122 route and only corrects WLFW indication names using the Samsung `cnss-daemon` disassembly.",
        "- Correct mapping: `0xe2f0` is `Received MSA Ready Ind` / msg `0x2b`; `0xe328` is `Received FW memory ready indication` / msg `0x37`; msg `0x21` is `QMI_WLFW_FW_READY_IND_V01` and returns without the decoded queue path in this userspace.",
        "- The discriminator is after `wlfw_cal_report_return rc=0x0`: WLFW QMI callback, msg ids 0x21/0x2b/0x37, decode/queue, worker handle, status/version, kernel FW_READY, and `wlan0`.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2123 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_modules() -> None:
    prev2121.HANDOFF_DIR = HANDOFF_DIR
    prev2121.HANDOFF_REPORT = HANDOFF_REPORT
    prev2121.V2120_OUT = V2123_OUT
    prev2121.V2120_INIT = V2123_INIT
    prev2121.V2120_BOOT = V2123_BOOT
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
    prev2113.V2112_OUT = V2123_OUT
    prev2113.V2112_INIT = V2123_INIT
    prev2113.V2112_BOOT = V2123_BOOT
    prev2113.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2113.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2113.TEST_LOG_PATH = TEST_LOG_PATH
    prev2113.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2113.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2113.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2113.BRIDGE_CAPTURE = OUT_DIR / "host" / "v2124-autostart-bridge.log"
    prev2113.BRIDGE_STDOUT = OUT_DIR / "host" / "v2124-autostart-bridge.stdout.txt"
    prev2113.BRIDGE_STDERR = OUT_DIR / "host" / "v2124-autostart-bridge.stderr.txt"
    prev2113.BRIDGE_PID = OUT_DIR / "host" / "v2124-autostart-bridge.pid"
    prev2113.artifact_hook_check = artifact_hook_check
    prev2113.collect_details = collect_details
    prev2113.classify = classify
    prev2113.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_modules()
    return prev2113.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
