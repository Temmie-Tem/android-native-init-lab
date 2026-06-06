#!/usr/bin/env python3
"""V2115 rollbackable handoff for V2113 dual-RFS bridge plus bounded DIAG session masks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_wlan_pd_memory_session_mask_handoff_v2074 as prev2074


prev2072 = prev2074.prev2072
prev2069 = prev2074.prev2069
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())

CYCLE = "V2115"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2115-dual-rfs-leaf-diag-session-handoff"
HANDOFF_DIR = OUT_DIR / "v2114-handoff"
HANDOFF_REPORT = OUT_DIR / "v2114-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2115_DUAL_RFS_LEAF_DIAG_SESSION_HANDOFF_2026-06-05.md"
)
V2114_OUT = REPO_ROOT / "tmp" / "wifi" / "v2114-dual-rfs-leaf-diag-session-test-boot"
V2114_INIT = V2114_OUT / "init_v2114_dual_rfs_leaf_diag_session"
V2114_BOOT = V2114_OUT / "boot_linux_v2114_dual_rfs_leaf_diag_session.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2114/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.232 (v2114-dual-rfs-leaf-diag-session)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2114.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2114.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2114-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v416"

ORIGINAL_COLLECT_DETAILS = prev2074.collect_details
ORIGINAL_CLASSIFY = prev2074.classify


def rel(path: Path) -> str:
    return prev2074.rel(path)


def intish(value: object) -> int:
    return prev2074.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2074.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "diag_wlan_pd_memory_device_probe.global_transport_switch=1",
        "diag_wlan_pd_memory_device_probe.usb_pcie_switch=1",
        "diag_wlan_pd_memory_device_probe.broad_mask=1",
        "diag_wlan_pd_memory_device_probe.restore_ioctl_attempted=1",
        "diag_wlan_pd_memory_device_probe.stream_config_attempted=1",
        "diag_wlan_pd_memory_device_probe.qmi_send=1",
        "diag_wlan_pd_memory_device_probe.ptraced=1",
        "diag_wlan_pd_memory_regular_mask_probe.broad_mask=1",
        "diag_wlan_pd_memory_regular_mask_probe.stream_config_attempted=1",
        "diag_wlan_pd_memory_regular_mask_probe.qmi_send=1",
        "diag_wlan_pd_memory_regular_mask_probe.ptraced=1",
        "diag_dci_register_read_probe.stream_config_attempted=1",
        "diag_dci_register_read_probe.qmi_send=1",
        "diag_dci_register_read_probe.ptraced=1",
        "diag_dci_canary_mask_probe.begin=1",
        "diag_remote_dev_poll_probe.begin=1",
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "post_bdf_boot_wlan_consumer_gate.begin=1",
        "ota_firewall/ruleset:",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2114",
        "v2114-dual-rfs-leaf-diag-session",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "android_parity=firmware_mnt_probe_present_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.enabled=%d",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.paths=/mnt/vendor/persist/rfs/mdm/mpss,/mnt/vendor/persist/rfs/apq/gnss",
        "wifi_companion_start.tftp_process_namespace_audit.compiled=%d",
        "persist_rfs_mdm_mpss",
        "persist_rfs_apq_gnss",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
        "diag_dci_register_read_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.cleanup.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.mode=query-gated-wlan-pd-memory-device-session-borrowed-dci-fd",
        "diag_wlan_pd_memory_device_probe.fd_borrowed=1",
        "diag_wlan_pd_memory_device_probe.node_created=0",
        "diag_wlan_pd_memory_device_probe.write_attempted=%d",
        "diag_wlan_pd_memory_device_probe.log_mask_write=%d",
        "diag_wlan_pd_memory_device_probe.event_mask_write=%d",
        "diag_wlan_pd_memory_device_probe.ioctl_query=DIAG_IOCTL_QUERY_PD_LOGGING",
        "diag_wlan_pd_memory_device_probe.ioctl_switch=DIAG_IOCTL_SWITCH_LOGGING",
        "diag_wlan_pd_memory_device_probe.switch_logging_scope=wlan-pd-memory-device-only",
        "diag_wlan_pd_memory_device_probe.req_mode=MEMORY_DEVICE_MODE",
        "diag_wlan_pd_memory_device_probe.pd_mask_name=DIAG_CON_UPD_WLAN",
        "diag_wlan_pd_memory_device_probe.global_transport_switch=0",
        "diag_wlan_pd_memory_device_probe.usb_pcie_switch=0",
        "diag_wlan_pd_memory_device_probe.broad_mask=0",
        "diag_wlan_pd_memory_device_probe.stream_config_attempted=0",
        "diag_wlan_pd_memory_device_probe.restore_ioctl_attempted=0",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.mode=session-scoped-user-space-nonhdlc-wlan-log-event-mask-hold-clear",
        "diag_wlan_pd_memory_regular_mask_probe.user_space_data_type_prefix=1",
        "diag_wlan_pd_memory_regular_mask_probe.diag_write_scope=three-wlan-log-three-wlan-event-session-mask-set-hold-clear",
        "diag_wlan_pd_memory_regular_mask_probe.%s.hdlc_toggle_attempted=1",
        "diag_wlan_pd_memory_regular_mask_probe.%s.hdlc_toggle_value=%u",
        "diag_wlan_pd_memory_regular_mask_probe.%s.%s_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.set_log_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.set_event_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.clear_log_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.clear_event_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.user_space_data_type_prefix=1",
        "diag_wlan_pd_memory_regular_mask_probe.summary.broad_mask=0",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2114_INIT, init_required, init_forbidden),
        (V2114_BOOT, boot_required, boot_forbidden),
    ):
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        present_forbidden = [token for token in forbidden if token.encode() in data]
        checks[rel(path)] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not present_forbidden,
            "missing": missing,
            "forbidden": present_forbidden,
        }
    return checks


def ns_path(fields: dict[str, str], name: str) -> dict[str, Any]:
    prefix = f"tftp_process_namespace_audit.path.{name}"
    return {
        "absolute": fields.get(f"{prefix}.absolute", ""),
        "proc_root_path": fields.get(f"{prefix}.proc_root_path", ""),
        "exists": intish(fields.get(f"{prefix}.exists")),
        "is_dir": intish(fields.get(f"{prefix}.is_dir")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "uid": intish(fields.get(f"{prefix}.uid")),
        "gid": intish(fields.get(f"{prefix}.gid")),
        "fs_type": fields.get(f"{prefix}.fs_type", ""),
        "errno": intish(fields.get(f"{prefix}.errno")),
        "error": fields.get(f"{prefix}.error", ""),
    }


def collect_namespace(fields: dict[str, str]) -> dict[str, Any]:
    paths = {
        name: ns_path(fields, name)
        for name in (
            "mnt",
            "mnt_vendor",
            "persist",
            "persist_rfs",
            "persist_rfs_shared",
            "persist_rfs_msm",
            "persist_rfs_msm_mpss",
            "persist_rfs_msm_adsp",
            "vendor_rfs_readwrite",
            "data_tombstones_rfs",
            "persist_rfs_mdm_mpss",
            "persist_rfs_apq_gnss",
        )
    }
    return {
        "compiled": intish(fields.get("wifi_companion_start.tftp_process_namespace_audit.compiled")),
        "begin": intish(fields.get("tftp_process_namespace_audit.begin")),
        "audit_ok": intish(fields.get("tftp_process_namespace_audit.audit_ok")),
        "pid": intish(fields.get("tftp_process_namespace_audit.pid")),
        "root_target": fields.get("tftp_process_namespace_audit.root.target", ""),
        "cwd_target": fields.get("tftp_process_namespace_audit.cwd.target", ""),
        "ns_mnt_target": fields.get("tftp_process_namespace_audit.ns_mnt.target", ""),
        "mountinfo_match_count": intish(fields.get("tftp_process_namespace_audit.mountinfo.match_count")),
        "paths": paths,
        "parents_traversable_for_tftp": all(
            paths[name]["mode"] == "0750" and paths[name]["uid"] == 0 and paths[name]["gid"] == 1000
            for name in ("mnt", "mnt_vendor", "persist")
        ),
        "persist_rfs_leaves_visible_for_tftp": all(
            paths[name]["exists"] == 1
            and paths[name]["is_dir"] == 1
            and paths[name]["mode"] == "0770"
            and paths[name]["uid"] == 2903
            and paths[name]["gid"] == 2903
            for name in ("persist_rfs_mdm_mpss", "persist_rfs_apq_gnss")
        ),
        "all_persist_targets_visible": all(
            paths[name]["exists"] == 1 and paths[name]["is_dir"] == 1
            for name in ("persist_rfs_shared", "persist_rfs_msm_mpss", "persist_rfs_msm_adsp")
        ),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev2069.prev2065.prev2063.prev2059.prev2057.parse_fields()
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    details["dual_rfs_bridge"] = {
        "android_parity": bridge.get("android_parity", ""),
        "probe_exists": intish(bridge.get("probe_exists")),
        "probe_nonzero": intish(bridge.get("probe_nonzero")),
        "probe_open_rc": str(bridge.get("probe_open_rc", "")),
        "fallback_exists": intish(bridge.get("fallback_exists")),
        "fallback_nonzero": intish(bridge.get("fallback_nonzero")),
        "fallback_open_rc": str(bridge.get("fallback_open_rc", "")),
        "rootfs_namespace_only": intish(bridge.get("rootfs_namespace_only")),
        "sda29_write": intish(bridge.get("sda29_write")),
    }
    details["leaf_precreate_marker"] = {
        "enabled": intish(fields.get("wifi_companion_start.tftp_persist_rfs_leaf_precreate.enabled")),
        "paths": fields.get("wifi_companion_start.tftp_persist_rfs_leaf_precreate.paths", ""),
        "owner": fields.get("wifi_companion_start.tftp_persist_rfs_leaf_precreate.owner", ""),
        "mode": fields.get("wifi_companion_start.tftp_persist_rfs_leaf_precreate.mode", ""),
    }
    details["tftp_process_namespace_audit"] = collect_namespace(fields)
    return details


def dual_rfs_ok(details: dict[str, Any]) -> bool:
    bridge = details.get("dual_rfs_bridge") if isinstance(details.get("dual_rfs_bridge"), dict) else {}
    return (
        bridge.get("android_parity") == "firmware_mnt_probe_present_firmware_fallback_present"
        and intish(bridge.get("probe_exists")) == 1
        and intish(bridge.get("probe_nonzero")) == 1
        and str(bridge.get("probe_open_rc")) == "0"
        and intish(bridge.get("fallback_exists")) == 1
        and intish(bridge.get("fallback_nonzero")) == 1
        and str(bridge.get("fallback_open_rc")) == "0"
        and intish(bridge.get("rootfs_namespace_only")) == 1
        and intish(bridge.get("sda29_write")) == 0
    )


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    bridge_ok = dual_rfs_ok(details)
    memory = details.get("diag_wlan_pd_memory_device") if isinstance(details.get("diag_wlan_pd_memory_device"), dict) else {}
    regular = details.get("diag_wlan_pd_memory_regular_mask") if isinstance(details.get("diag_wlan_pd_memory_regular_mask"), dict) else {}
    target = details.get("diag_dci_wlan_target_mask") if isinstance(details.get("diag_dci_wlan_target_mask"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}
    ns = details.get("tftp_process_namespace_audit") if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    marker = details.get("leaf_precreate_marker") if isinstance(details.get("leaf_precreate_marker"), dict) else {}
    leaves_ok = bool(ns.get("persist_rfs_leaves_visible_for_tftp"))
    marker_enabled = intish(marker.get("enabled")) == 1
    memory_safe = bool(memory.get("safe"))
    regular_safe = bool(regular.get("safe"))
    memory_switched = intish(memory.get("switched")) == 1
    regular_armed = intish(regular.get("armed")) == 1
    regular_cleared = intish(regular.get("clear_write_successes")) == 2 and intish(regular.get("hdlc_reenabled")) == 1
    target_clear_ok = bool(target.get("clear_ok"))
    memory_payload = intish(memory.get("payload_records")) > 0
    mask_response_only = intish(memory.get("mask_response_records")) > 0 and intish(memory.get("useful_payload_records")) == 0
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0 or intish(cascade.get("wlanmdsp_tftp")) > 0
    ota_seen = intish(summary.get("ota_firewall")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0

    if not hook_ok:
        label = "dual-rfs-leaf-diag-session-artifact-hook-regression"
        passed = False
        reason = "V2114 artifact does not contain the combined dual-RFS bridge plus bounded DIAG session contract"
    elif not bridge_ok:
        label = "dual-rfs-leaf-diag-session-bridge-missing"
        passed = False
        reason = "exact Android firmware_mnt WLAN image path or fallback path did not resolve in the private RFS bridge"
    elif not marker_enabled or not leaves_ok:
        label = "dual-rfs-leaf-diag-session-leaf-regression"
        passed = False
        reason = "persist-RFS leaf precreate marker or tftp process-root visibility regressed"
    elif not memory_safe or not regular_safe:
        label = "dual-rfs-leaf-diag-session-safety-regression"
        passed = False
        reason = "DIAG memory-device/session-mask safety markers were absent or unsafe"
    elif not memory_switched:
        label = "dual-rfs-leaf-diag-session-switch-missing"
        passed = True
        reason = "dual-RFS bridge held, but WLAN-PD memory-device switch did not complete"
    elif not regular_armed:
        label = "dual-rfs-leaf-diag-session-not-armed"
        passed = True
        reason = "dual-RFS bridge held, but normal WLAN session masks did not arm"
    elif not regular_cleared:
        label = "dual-rfs-leaf-diag-session-clear-failed"
        passed = False
        reason = "session masks were armed but not proven cleared/restored"
    elif not target_clear_ok:
        label = "dual-rfs-leaf-diag-session-target-clear-failed"
        passed = False
        reason = "bounded DCI WLAN target masks were not proven cleared after the memory-device session"
    elif wlan0:
        label = "dual-rfs-leaf-diag-session-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "dual-rfs-leaf-diag-session-fw-ready-progress"
        passed = True
        reason = "native reached WLAN firmware-ready progress"
    elif wlanmdsp_seen:
        label = "dual-rfs-leaf-diag-session-wlanmdsp-requested"
        passed = True
        reason = "native entered the WLAN image request branch with the combined bridge and bounded DIAG session active"
    elif ota_seen:
        label = "dual-rfs-leaf-diag-session-ota-no-wlanmdsp"
        passed = True
        reason = "native reached ota_firewall but still skipped wlanmdsp"
    elif mask_response_only:
        label = "dual-rfs-leaf-diag-session-mask-response-only-no-wlanmdsp"
        passed = True
        reason = "combined bridge held and session masks were acknowledged, but memory-device reads contained only app-side mask responses"
    elif memory_payload:
        label = "dual-rfs-leaf-diag-session-payload-no-wlanmdsp"
        passed = True
        reason = "combined bridge held and session masks yielded memory-device payload records, but native still made no wlanmdsp request"
    else:
        label = "dual-rfs-leaf-diag-session-no-payload-no-wlanmdsp"
        passed = True
        reason = "combined bridge held and bounded WLAN-PD session masks produced no payload and no wlanmdsp request"

    return {
        **base,
        "decision": f"v2115-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "dual_rfs_bridge_ok": bridge_ok,
        "leaf_precreate_marker_enabled": marker_enabled,
        "persist_rfs_leaves_visible_for_tftp": leaves_ok,
        "namespace_audit_ok": intish(ns.get("audit_ok")),
        "tftp_pid": intish(ns.get("pid")),
        "parents_traversable_for_tftp": bool(ns.get("parents_traversable_for_tftp")),
        "all_persist_targets_visible": bool(ns.get("all_persist_targets_visible")),
        "mountinfo_match_count": intish(ns.get("mountinfo_match_count")),
        "memory_safe": memory_safe,
        "regular_safe": regular_safe,
        "memory_switched": memory_switched,
        "regular_armed": regular_armed,
        "regular_cleared": regular_cleared,
        "memory_payload": memory_payload,
        "mask_response_only": mask_response_only,
        "target_clear_ok": target_clear_ok,
        "wlanmdsp_seen": wlanmdsp_seen,
        "ota_seen": ota_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    diag = details.get("diag_dci_register_read", {}) if isinstance(details.get("diag_dci_register_read"), dict) else {}
    target = details.get("diag_dci_wlan_target_mask", {}) if isinstance(details.get("diag_dci_wlan_target_mask"), dict) else {}
    memory = details.get("diag_wlan_pd_memory_device", {}) if isinstance(details.get("diag_wlan_pd_memory_device"), dict) else {}
    regular = details.get("diag_wlan_pd_memory_regular_mask", {}) if isinstance(details.get("diag_wlan_pd_memory_regular_mask"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    samples = memory.get("samples", []) if isinstance(memory.get("samples"), list) else []
    ns = details.get("tftp_process_namespace_audit", {}) if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    paths = ns.get("paths", {}) if isinstance(ns.get("paths"), dict) else {}
    marker = details.get("leaf_precreate_marker", {}) if isinstance(details.get("leaf_precreate_marker"), dict) else {}
    bridge = details.get("dual_rfs_bridge", {}) if isinstance(details.get("dual_rfs_bridge"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2115 Dual-RFS Leaf DIAG Session Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2115`",
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
                ["dual_rfs", classification.get("dual_rfs_bridge_ok"), f"bridge={bridge}"],
                ["leaf_precreate", classification.get("persist_rfs_leaves_visible_for_tftp"), f"marker={marker}"],
                ["namespace_audit", classification.get("namespace_audit_ok"), f"pid={classification.get('tftp_pid')} root={ns.get('root_target')}"],
                ["diag_register", diag.get("registered"), f"open={diag.get('open_ok')} proc={diag.get('selected_proc')} mask={diag.get('selected_mask')} rc={diag.get('register_rc')} client={diag.get('client_id')}"],
                ["memory_switch", memory.get("switched"), f"attempted={memory.get('switch_attempted')} rc={memory.get('switch_rc')} errno={memory.get('switch_errno')} scope={memory.get('switch_logging_scope')}"],
                ["regular_masks", regular.get("armed"), f"hdlc={regular.get('hdlc_disabled')} set={regular.get('set_write_successes')}/{regular.get('set_write_attempts')} clear={regular.get('clear_write_successes')}/{regular.get('clear_write_attempts')} restored={regular.get('hdlc_reenabled')} completed={regular.get('completed')}"],
                ["memory_reads", memory.get("useful_payload_records"), f"records={memory.get('read_records')} bytes={memory.get('read_bytes')} user={memory.get('user_space_records')} mask_response={memory.get('mask_response_records')} raw={memory.get('raw_user_space_records')} other={memory.get('other_records')} errors={memory.get('read_errors')} terminal={memory.get('read_terminal_error')}"],
                ["target_clear", classification.get("target_clear_ok"), f"attempts={target.get('clear_write_attempts')} success={target.get('clear_write_successes')} errors={target.get('clear_write_errors')} log_still_set={target.get('log_clear_set_count')} event_still_set={target.get('event_clear_set_count')} completed={target.get('completed')}"],
                ["tftp_branch", "", f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Process-Root Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "errno"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("errno")]
                for name, item in paths.items()
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Memory Samples",
        "",
        markdown_table(
            ["idx", "bytes", "type", "name", "num_data", "first_payload_len", "prefix_hex"],
            [[sample.get("index"), sample.get("bytes"), sample.get("data_type"), sample.get("data_type_name"), sample.get("num_data"), sample.get("first_payload_len"), sample.get("prefix_hex")] for sample in samples] or [["none", "", "", "", "", "", ""]],
        ),
        "",
        "## Branch",
        "",
        "- V2115 keeps the V2113 readonly/readwrite dual-RFS and persist-leaf bridge contract while replaying the bounded V2074 WLAN-PD memory-session DIAG observer.",
        "- If `wlanmdsp` appears, chase the normal BDF, FW-ready, and `wlan0` cascade.",
        "- If DIAG still shows only mask responses or no payload, the combined AP bridge is held and the remaining producer condition is modem-internal.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG mutation was limited to private rootfs `/dev/diag`, bounded DCI WLAN target masks, one query-gated WLAN-PD-only `DIAG_IOCTL_SWITCH_LOGGING` to `MEMORY_DEVICE_MODE`, session-local `DIAG_IOCTL_HDLC_TOGGLE`, and exactly three WLAN log masks plus three WLAN event masks set during the lower window and cleared during cleanup; no USB/PCIE restore, broad masks, DCI stream config, QMI send, AP-side strace, boot-time QRTR matrix, passive DIAG replay, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2114 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors and leaf precreate, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2074() -> None:
    prev2074.CYCLE = CYCLE
    prev2074.OUT_DIR = OUT_DIR
    prev2074.HANDOFF_DIR = HANDOFF_DIR
    prev2074.HANDOFF_REPORT = HANDOFF_REPORT
    prev2074.REPORT_PATH = REPORT_PATH
    prev2074.V2073_OUT = V2114_OUT
    prev2074.V2073_INIT = V2114_INIT
    prev2074.V2073_BOOT = V2114_BOOT
    prev2074.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2074.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2074.TEST_LOG_PATH = TEST_LOG_PATH
    prev2074.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2074.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2074.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2074.artifact_hook_check = artifact_hook_check
    prev2074.collect_details = collect_details
    prev2074.classify = classify
    prev2074.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2074()
    return prev2074.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
