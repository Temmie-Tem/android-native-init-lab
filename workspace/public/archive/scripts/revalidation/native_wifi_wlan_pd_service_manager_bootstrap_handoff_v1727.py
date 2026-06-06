#!/usr/bin/env python3
"""V1727 one-run WLAN-PD service-manager-only bootstrap handoff."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_output_visibility_handoff_v1688 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1727"
V1726_OUT = REPO_ROOT / "tmp" / "wifi" / "v1726-wlan-pd-service-manager-bootstrap-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1726/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1727-wlan-pd-service-manager-bootstrap-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1727_WLAN_PD_SERVICE_MANAGER_BOOTSTRAP_HANDOFF_2026-06-03.md"
)

SENSITIVE_VERSION_CREATOR_RE = re.compile(r"(made by )[^\s\r\n]+")


def configure_base() -> None:
    prev.CYCLE = CYCLE
    prev.V1687_OUT = V1726_OUT
    prev.DEFAULT_SOURCE_MANIFEST = V1726_OUT / "manifest.json"
    prev.DEFAULT_TEST_IMAGE = V1726_OUT / "boot_linux_v1726_wlan_pd_service_manager_bootstrap.img"
    prev.LOCAL_PROPERTY_ROOT = V1726_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.136 (v1726-wlan-pd-service-manager-bootstrap)"
    prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1726.log"
    prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1726.summary"
    prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1726-helper.result"
    prev.DMESG_PATTERN = (
        "A90v1726|wlan_pd_service_window_trigger|wlan_pd_cnss_nonlog_control_flow|"
        "wlan_pd_firmware_serve_gate|service-manager|servicemanager|vndservicemanager|"
        "vndbinder|peripheral|wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|"
        "service 69|wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
        "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def sanitize_evidence_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sanitized = SENSITIVE_VERSION_CREATOR_RE.sub(r"\1[redacted]", text)
        if sanitized != text:
            item.write_text(sanitized, encoding="utf-8")


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev.fwbase.parse_helper_fields(evidence_dir)
    service_window_label = helper_fields.get("wlan_pd_service_window_trigger.label", "")
    nonlog_label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_service_window_trigger.begin") == "1"
    nonlog_contract_seen = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1"
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    service_manager_value = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.service_manager")
    service_manager_ok = service_manager_value == "1"
    diagnostic_label = bool(nonlog_label) and nonlog_label != "cnss-target-unavailable"
    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "nonlog_contract_seen": nonlog_contract_seen,
        "service_window_label": service_window_label,
        "nonlog_label": nonlog_label,
        "diagnostic_label": diagnostic_label,
        "old_firmware_serve_label": helper_fields.get("wlan_pd_firmware_serve_gate.label"),
        "service_manager": service_manager_value,
        "service_manager_started": helper_fields.get("wifi_companion_start.service_manager_started"),
        "companion_service_manager": helper_fields.get("wifi_companion_start.service_manager"),
        "companion_order": helper_fields.get("wifi_companion_start.order"),
        "cnss_daemon_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "cnss_daemon_present": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_present"),
        "tftp_running": helper_fields.get("wlan_pd_service_window_trigger.tftp_running"),
        "wlfw_service69_seen": helper_fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen"),
        "requested_wlanmdsp": helper_fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp"),
        "wlfw_start_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.hit_count"),
        "wlfw_service_request_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.hit_count"),
        "wlfw_worker_create_success_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_worker_pthread_create_success.hit_count"),
        "wlfw_ind_register_qmi_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_ind_register_qmi.hit_count"),
        "wlfw_cap_qmi_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_cap_qmi.hit_count"),
        "peripheral_default_service_manager_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.default_service_manager_call.hit_count"),
        "peripheral_manager_name_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.manager_name_string16_call.hit_count"),
        "peripheral_service_manager_get_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.service_manager_get_call.hit_count"),
        "peripheral_target_path": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.target.selected_path"),
        "tracefs_available": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available"),
        "tracefs_errno": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.errno"),
        "fd_vndbinder_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.vndbinder_count"),
        "fd_socket_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.socket_count"),
        "no_esoc0": helper_fields.get("wlan_pd_service_window_trigger.no_esoc0"),
        "no_forced_rc1": helper_fields.get("wlan_pd_service_window_trigger.no_forced_rc1"),
        "no_fake_online": helper_fields.get("wlan_pd_service_window_trigger.no_fake_online"),
        "no_scan_connect": helper_fields.get("wlan_pd_service_window_trigger.no_scan_connect"),
        "no_credentials": helper_fields.get("wlan_pd_service_window_trigger.no_credentials"),
        "no_dhcp_routes": helper_fields.get("wlan_pd_service_window_trigger.no_dhcp_routes"),
        "no_external_ping": helper_fields.get("wlan_pd_service_window_trigger.no_external_ping"),
    }
    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1726 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen:
        return f"{args.cycle.lower()}-service-manager-contract-missing", False, "helper result did not include both service-window and nonlog contracts", details
    if not service_manager_ok:
        return f"{args.cycle.lower()}-service-manager-not-started", False, "service-manager-only bootstrap did not report service_manager=1", details
    if not diagnostic_label:
        return f"{args.cycle.lower()}-cnss-nonlog-label-nondiagnostic", False, "nonlog classifier did not produce a diagnostic label", details
    return f"{args.cycle.lower()}-{nonlog_label}-rollback-pass", True, "one service-manager-only WLAN-PD gate produced a fixed nonlog label and rollback verified", details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD Service-manager Bootstrap Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD service-manager-only bootstrap gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- nonlog label: `{gate.get('nonlog_label')}`",
        f"- service-window label: `{gate.get('service_window_label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- service_manager: `{gate.get('service_manager')}`",
        f"- service_manager_started: `{gate.get('service_manager_started')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        "",
        "## Uprobe Fields",
        "",
        f"- tracefs available: `{gate.get('tracefs_available')}` (`errno={gate.get('tracefs_errno')}`)",
        f"- wlfw_start hits: `{gate.get('wlfw_start_hit_count')}`",
        f"- wlfw_service_request hits: `{gate.get('wlfw_service_request_hit_count')}`",
        f"- wlfw worker create success hits: `{gate.get('wlfw_worker_create_success_hit_count')}`",
        f"- wlfw indication-register QMI hits: `{gate.get('wlfw_ind_register_qmi_hit_count')}`",
        f"- wlfw capability QMI hits: `{gate.get('wlfw_cap_qmi_hit_count')}`",
        f"- peripheral defaultServiceManager hits: `{gate.get('peripheral_default_service_manager_hit_count')}`",
        f"- peripheral service name hits: `{gate.get('peripheral_manager_name_hit_count')}`",
        f"- peripheral service-manager get hits: `{gate.get('peripheral_service_manager_get_hit_count')}`",
        f"- peripheral target path: `{gate.get('peripheral_target_path')}`",
        f"- cnss fd counts: `vndbinder={gate.get('fd_vndbinder_count')}`, `socket={gate.get('fd_socket_count')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Uploaded files: `{property_deploy.get('file_count')}`",
        f"- Uploaded bytes: `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label.",
        "- If the label is `wlfw-worker-thread-started-waiting-for-qmi-service`, classify the blocker as downstream of cnss-daemon: the modem still does not publish WLFW service 69 / request `wlanmdsp`.",
        "- Do not add PM trio or `boot_wlan` from this result; the next unit should return to WLAN-PD image request / modem-side WLFW service publication evidence.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_base()
    prev.classify_gate = classify_gate
    prev.render_report = render_report
    rc = prev.main(argv)
    sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
