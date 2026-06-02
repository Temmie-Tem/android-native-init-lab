#!/usr/bin/env python3
"""V1731 one-run WLAN-PD service-notifier late listener handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_servnotif_late_endpoint_handoff_v1729 as prev


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1731"
V1730_OUT = REPO_ROOT / "tmp" / "wifi" / "v1730-wlan-pd-servnotif-late-listener-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1730/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1731-wlan-pd-servnotif-late-listener-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1731_WLAN_PD_SERVNOTIF_LATE_LISTENER_HANDOFF_2026-06-03.md"
)


def configure_base() -> None:
    prev.CYCLE = CYCLE
    prev.V1728_OUT = V1730_OUT
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.CYCLE = CYCLE
    prev.base.V1726_OUT = V1730_OUT
    prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.prev.CYCLE = CYCLE
    prev.base.prev.V1687_OUT = V1730_OUT
    prev.base.prev.DEFAULT_SOURCE_MANIFEST = V1730_OUT / "manifest.json"
    prev.base.prev.DEFAULT_TEST_IMAGE = V1730_OUT / "boot_linux_v1730_wlan_pd_servnotif_late_listener.img"
    prev.base.prev.LOCAL_PROPERTY_ROOT = V1730_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    prev.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.138 (v1730-wlan-pd-servnotif-late-listener)"
    prev.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1730.log"
    prev.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1730.summary"
    prev.base.prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1730-helper.result"
    prev.base.prev.DMESG_PATTERN = (
        "A90v1730|wlan_pd_service_window_trigger|wlan_pd_cnss_nonlog_control_flow|"
        "wifi_companion_service_notifier_late_probe|wifi_companion_service_notifier_late_listener|"
        "wifi_companion_service_notifier_listener|wlan_pd_firmware_serve_gate|"
        "service-manager|servicemanager|vndservicemanager|vndbinder|peripheral|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
        "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
        "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def late_listener_label(gate: dict[str, Any]) -> tuple[str, str]:
    late_result = str(gate.get("late_listener_result") or "")
    state_name = str(gate.get("late_listener_response_state_name") or "")
    indication_seen = str(gate.get("late_listener_indication_seen") or "")
    indication_state_name = str(gate.get("late_listener_indication_state_name") or "")
    response_success = str(gate.get("late_listener_response_success") or "")

    if late_result == "no-response":
        return "late-listener-no-response", "late endpoint did not answer the bounded listener register request"
    if late_result == "listener-response-success" and state_name == "uninit" and indication_seen == "0":
        return "late-listener-uninit-no-indication", "late listener response was success/uninit and no state indication arrived"
    if late_result == "listener-response-success" and indication_seen == "1":
        return (
            f"late-listener-response-success-indication-{indication_state_name or 'unknown'}",
            "late listener received a response and a state indication",
        )
    if late_result == "listener-response-success":
        return (
            f"late-listener-response-success-{state_name or 'unknown'}",
            "late listener response succeeded with a bounded current-state value",
        )
    if response_success == "0" and late_result == "listener-response-error":
        return "late-listener-response-error", "late listener returned a QMI response error"
    if late_result:
        return f"late-listener-{late_result}", "late listener produced a fixed diagnostic result"
    return "late-listener-label-missing", "late listener result was missing"


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev.base.prev.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev.base.prev.fwbase.parse_helper_fields(evidence_dir)
    service_window_label = helper_fields.get("wlan_pd_service_window_trigger.label", "")
    nonlog_label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_service_window_trigger.begin") == "1"
    nonlog_contract_seen = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1"
    late_endpoint_contract_seen = helper_fields.get("wifi_companion_service_notifier_late_probe.begin") == "1"
    late_listener_contract_seen = helper_fields.get("wifi_companion_service_notifier_late_listener.begin") == "1"
    late_endpoint_result = helper_fields.get("wifi_companion_service_notifier_late_probe.result", "")
    late_listener_result = helper_fields.get("wifi_companion_service_notifier_late_listener.result", "")
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
        "late_endpoint_contract_seen": late_endpoint_contract_seen,
        "late_listener_contract_seen": late_listener_contract_seen,
        "late_endpoint_result": late_endpoint_result,
        "late_endpoint_found": helper_fields.get("wifi_companion_service_notifier_late_probe.endpoint.found"),
        "late_endpoint_node": helper_fields.get("wifi_companion_service_notifier_late_probe.endpoint.node"),
        "late_endpoint_port": helper_fields.get("wifi_companion_service_notifier_late_probe.endpoint.port"),
        "late_listener_result": late_listener_result,
        "late_listener_endpoint_found": helper_fields.get("wifi_companion_service_notifier_late_listener.endpoint.found"),
        "late_listener_endpoint_node": helper_fields.get("wifi_companion_service_notifier_late_listener.endpoint.node"),
        "late_listener_endpoint_port": helper_fields.get("wifi_companion_service_notifier_late_listener.endpoint.port"),
        "late_listener_send_attempted": helper_fields.get("wifi_companion_service_notifier_late_listener.send_attempted"),
        "late_listener_response_seen": helper_fields.get("wifi_companion_service_notifier_late_listener.response_seen"),
        "late_listener_response_success": helper_fields.get("wifi_companion_service_notifier_late_listener.response_success"),
        "late_listener_response_state_valid": helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_valid"),
        "late_listener_response_state": helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state"),
        "late_listener_response_state_name": helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name"),
        "late_listener_indication_seen": helper_fields.get("wifi_companion_service_notifier_late_listener.indication_seen"),
        "late_listener_indication_valid": helper_fields.get("wifi_companion_service_notifier_late_listener.indication_valid"),
        "late_listener_indication_state": helper_fields.get("wifi_companion_service_notifier_late_listener.indication_curr_state"),
        "late_listener_indication_state_name": helper_fields.get("wifi_companion_service_notifier_late_listener.indication_curr_state_name"),
        "late_listener_ack_sent": helper_fields.get("wifi_companion_service_notifier_late_listener.ack_sent"),
        "late_listener_ack_success": helper_fields.get("wifi_companion_service_notifier_late_listener.ack_success"),
        "late_listener_poll_timeout": helper_fields.get("wifi_companion_service_notifier_late_listener.timing.poll_timeout"),
        "late_listener_hold_ms": helper_fields.get("wifi_companion_service_notifier_late_listener.timing.hold_ms"),
        "early_listener_result": helper_fields.get("wifi_companion_service_notifier_listener.result"),
        "early_listener_status": helper_fields.get("wifi_companion_service_notifier_listener.endpoint.status"),
        "service_window_label": service_window_label,
        "nonlog_label": nonlog_label,
        "diagnostic_label": diagnostic_label,
        "old_firmware_serve_label": helper_fields.get("wlan_pd_firmware_serve_gate.label"),
        "servloc_domain_result": helper_fields.get("wifi_companion_servloc_domain_list.result"),
        "servloc_domain_name": helper_fields.get("wifi_companion_servloc_domain_list.domain.0.name"),
        "service_manager": service_manager_value,
        "cnss_daemon_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "tftp_running": helper_fields.get("wlan_pd_service_window_trigger.tftp_running"),
        "wlfw_service69_seen": helper_fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen"),
        "requested_wlanmdsp": helper_fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp"),
        "wlfw_start_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.hit_count"),
        "wlfw_service_request_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.hit_count"),
        "wlfw_worker_create_success_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_worker_pthread_create_success.hit_count"),
        "wlfw_ind_register_qmi_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_ind_register_qmi.hit_count"),
        "wlfw_cap_qmi_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_cap_qmi.hit_count"),
        "tracefs_available": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available"),
        "tracefs_errno": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.errno"),
        "no_esoc0": helper_fields.get("wlan_pd_service_window_trigger.no_esoc0"),
        "no_forced_rc1": helper_fields.get("wlan_pd_service_window_trigger.no_forced_rc1"),
        "no_fake_online": helper_fields.get("wlan_pd_service_window_trigger.no_fake_online"),
        "no_scan_connect": helper_fields.get("wlan_pd_service_window_trigger.no_scan_connect"),
        "no_credentials": helper_fields.get("wlan_pd_service_window_trigger.no_credentials"),
        "no_dhcp_routes": helper_fields.get("wlan_pd_service_window_trigger.no_dhcp_routes"),
        "no_external_ping": helper_fields.get("wlan_pd_service_window_trigger.no_external_ping"),
    }
    fixed_label, fixed_reason = late_listener_label(details)
    details["late_listener_label"] = fixed_label
    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1730 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen:
        return f"{args.cycle.lower()}-service-window-contract-missing", False, "helper result did not include both service-window and nonlog contracts", details
    if not service_manager_ok:
        return f"{args.cycle.lower()}-service-manager-not-started", False, "service-manager bootstrap did not report service_manager=1", details
    if not diagnostic_label:
        return f"{args.cycle.lower()}-cnss-nonlog-label-nondiagnostic", False, "nonlog classifier did not produce a diagnostic label", details
    if not late_endpoint_contract_seen or late_endpoint_result != "endpoint-found":
        return f"{args.cycle.lower()}-servnotif-late-endpoint-not-found", False, "late endpoint prerequisite was not reproduced", details
    if not late_listener_contract_seen or fixed_label == "late-listener-label-missing":
        return f"{args.cycle.lower()}-servnotif-late-listener-label-missing", False, "late listener did not produce a fixed label", details
    return f"{args.cycle.lower()}-{fixed_label}-rollback-pass", True, fixed_reason + "; rollback verified", details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD Service-notifier Late Listener Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD service-notifier late listener gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- late listener label: `{gate.get('late_listener_label')}`",
        f"- late listener result: `{gate.get('late_listener_result')}`",
        f"- late listener endpoint found: `{gate.get('late_listener_endpoint_found')}`",
        f"- late listener endpoint node: `{gate.get('late_listener_endpoint_node')}`",
        f"- late listener endpoint port: `{gate.get('late_listener_endpoint_port')}`",
        f"- late listener response seen: `{gate.get('late_listener_response_seen')}`",
        f"- late listener response success: `{gate.get('late_listener_response_success')}`",
        f"- late listener response state: `{gate.get('late_listener_response_state')}` / `{gate.get('late_listener_response_state_name')}`",
        f"- late listener indication seen: `{gate.get('late_listener_indication_seen')}`",
        f"- late listener indication state: `{gate.get('late_listener_indication_state')}` / `{gate.get('late_listener_indication_state_name')}`",
        f"- late listener hold ms: `{gate.get('late_listener_hold_ms')}`",
        f"- late endpoint result: `{gate.get('late_endpoint_result')}`",
        f"- early listener result: `{gate.get('early_listener_result')}`",
        f"- nonlog label: `{gate.get('nonlog_label')}`",
        f"- service-window label: `{gate.get('service_window_label')}`",
        f"- service-locator domain result: `{gate.get('servloc_domain_result')}`",
        f"- service-locator domain name: `{gate.get('servloc_domain_name')}`",
        f"- service_manager: `{gate.get('service_manager')}`",
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
        "## Interpretation",
        "",
        "- `late-listener-uninit-no-indication` means the service-notifier endpoint is reachable but WLAN-PD still stays UNINIT in the bounded listener window.",
        "- `late-listener-no-response` means endpoint discovery is not enough; listener register does not get a QMI response in this namespace/window.",
        "- Any late indication label means the next gate can move from service-notifier timing to WLFW service 69 / ICNSS QMI readiness.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    prev.configure_base = configure_base
    prev.classify_gate = classify_gate
    prev.render_report = render_report
    return prev.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
