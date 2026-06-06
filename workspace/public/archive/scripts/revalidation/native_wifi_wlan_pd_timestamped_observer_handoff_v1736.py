#!/usr/bin/env python3
"""V1736 one-run WLAN-PD timestamped observer handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_servnotif_late_endpoint_handoff_v1729 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1736"
V1735_OUT = REPO_ROOT / "tmp" / "wifi" / "v1735-wlan-pd-timestamped-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1735/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1736_WLAN_PD_TIMESTAMPED_OBSERVER_HANDOFF_2026-06-03.md"
)


def configure_base() -> None:
    prev.CYCLE = CYCLE
    prev.V1728_OUT = V1735_OUT
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.CYCLE = CYCLE
    prev.base.V1726_OUT = V1735_OUT
    prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.prev.CYCLE = CYCLE
    prev.base.prev.V1687_OUT = V1735_OUT
    prev.base.prev.DEFAULT_SOURCE_MANIFEST = V1735_OUT / "manifest.json"
    prev.base.prev.DEFAULT_TEST_IMAGE = V1735_OUT / "boot_linux_v1735_wlan_pd_timestamped_observer.img"
    prev.base.prev.LOCAL_PROPERTY_ROOT = V1735_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    prev.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.139 (v1735-wlan-pd-timestamped-observer)"
    prev.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1735.log"
    prev.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1735.summary"
    prev.base.prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1735-helper.result"
    prev.base.prev.DMESG_PATTERN = (
        "A90v1735|wlan_pd_service_window_trigger|wlan_pd_cnss_nonlog_control_flow|"
        "wifi_companion_service_notifier_late_probe|wifi_companion_service_notifier_late_listener|"
        "wifi_companion_service_notifier_listener|wlan_pd_firmware_serve_gate|"
        "service-manager|servicemanager|vndservicemanager|vndbinder|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
        "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
        "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev.base.prev.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev.base.prev.fwbase.parse_helper_fields(evidence_dir)
    service_window_label = helper_fields.get("wlan_pd_service_window_trigger.label", "")
    nonlog_label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_service_window_trigger.begin") == "1"
    timestamped_seen = helper_fields.get("wlan_pd_service_window_trigger.timestamped_observer_compatible") == "1"
    nonlog_contract_seen = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1"
    late_endpoint_contract_seen = helper_fields.get("wifi_companion_service_notifier_late_probe.begin") == "1"
    late_listener_contract_seen = helper_fields.get("wifi_companion_service_notifier_late_listener.begin") == "1"
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    wlfw_start_hit_count = intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.hit_count"))
    wlfw_service_request_hit_count = intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.hit_count"))
    wlfw_worker_success_hit_count = intish(
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_worker_pthread_create_success.hit_count")
    )
    wlfw_start_seen = (
        helper_fields.get("wlan_pd_service_window_trigger.wlfw_start_seen") == "1" or
        helper_fields.get("wlan_pd_service_window_trigger.wlfw_service_request_seen") == "1" or
        wlfw_start_hit_count > 0 or
        wlfw_service_request_hit_count > 0
    )
    service69_seen = helper_fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen") == "1"
    requested_wlanmdsp = helper_fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp") == "1"
    late_listener_state = helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name", "")
    late_listener_indication = helper_fields.get("wifi_companion_service_notifier_late_listener.indication_seen", "")
    child_failed = service_window_label in {"service-window-child-failed", "modem-holder-regression"}

    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "timestamped_observer_seen": timestamped_seen,
        "observer_monotonic_ms": helper_fields.get("wlan_pd_service_window_trigger.observer_monotonic_ms"),
        "nonlog_contract_seen": nonlog_contract_seen,
        "late_endpoint_contract_seen": late_endpoint_contract_seen,
        "late_listener_contract_seen": late_listener_contract_seen,
        "service_window_label": service_window_label,
        "nonlog_label": nonlog_label,
        "old_firmware_serve_label": helper_fields.get("wlan_pd_firmware_serve_gate.label"),
        "service_manager": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.service_manager"),
        "tftp_running": helper_fields.get("wlan_pd_service_window_trigger.tftp_running"),
        "cnss_daemon_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "wlfw_start_seen": "1" if wlfw_start_seen else "0",
        "wlfw_service69_seen": "1" if service69_seen else "0",
        "requested_wlanmdsp": "1" if requested_wlanmdsp else "0",
        "wlfw_start_hit_count": str(wlfw_start_hit_count),
        "wlfw_service_request_hit_count": str(wlfw_service_request_hit_count),
        "wlfw_worker_create_success_hit_count": str(wlfw_worker_success_hit_count),
        "wlfw_ind_register_qmi_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_ind_register_qmi.hit_count"),
        "wlfw_cap_qmi_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_cap_qmi.hit_count"),
        "late_endpoint_result": helper_fields.get("wifi_companion_service_notifier_late_probe.result"),
        "late_listener_result": helper_fields.get("wifi_companion_service_notifier_late_listener.result"),
        "late_listener_state": late_listener_state,
        "late_listener_indication_seen": late_listener_indication,
        "late_listener_hold_ms": helper_fields.get("wifi_companion_service_notifier_late_listener.timing.hold_ms"),
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1735 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not timestamped_seen:
        return f"{args.cycle.lower()}-timestamped-observer-contract-missing", False, "helper result did not include timestamped observer fields", details
    if not nonlog_contract_seen:
        return f"{args.cycle.lower()}-cnss-nonlog-contract-missing", False, "helper result did not include CNSS non-log evidence", details
    if child_failed:
        return f"{args.cycle.lower()}-{service_window_label}", False, "required internal-modem companion actor failed", details
    if not late_endpoint_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-servnotif-listener-contract-missing", False, "late service-notifier listener evidence missing", details
    if wlfw_start_seen and not service69_seen and not requested_wlanmdsp:
        return (
            f"{args.cycle.lower()}-wlfw-start-reached-downstream-block-rollback-pass",
            True,
            "cnss-daemon reached WLFW start/request path, but WLAN-PD stayed uninit with no WLFW service 69 or wlanmdsp request; rollback verified",
            details,
        )
    if service69_seen or requested_wlanmdsp:
        return (
            f"{args.cycle.lower()}-wlan-pd-progress-before-connect-rollback-pass",
            True,
            "WLAN-PD/WLFW progressed beyond the current blocker; stop before scan/connect",
            details,
        )
    return (
        f"{args.cycle.lower()}-service-window-still-no-wlfw-rollback-pass",
        True,
        "bounded observer produced a fixed no-WLFW label and rollback verified",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD Timestamped Observer Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable read-only WLAN-PD timestamped observer gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- service-window label: `{gate.get('service_window_label')}`",
        f"- timestamped observer seen: `{gate.get('timestamped_observer_seen')}`",
        f"- observer monotonic ms: `{gate.get('observer_monotonic_ms')}`",
        f"- nonlog label: `{gate.get('nonlog_label')}`",
        f"- old firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- service_manager: `{gate.get('service_manager')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- wlfw start seen: `{gate.get('wlfw_start_seen')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- late listener result: `{gate.get('late_listener_result')}`",
        f"- late listener state: `{gate.get('late_listener_state')}`",
        f"- late listener indication seen: `{gate.get('late_listener_indication_seen')}`",
        f"- late listener hold ms: `{gate.get('late_listener_hold_ms')}`",
        "",
        "## Uprobe Fields",
        "",
        f"- wlfw_start hits: `{gate.get('wlfw_start_hit_count')}`",
        f"- wlfw_service_request hits: `{gate.get('wlfw_service_request_hit_count')}`",
        f"- wlfw worker create success hits: `{gate.get('wlfw_worker_create_success_hit_count')}`",
        f"- wlfw indication-register QMI hits: `{gate.get('wlfw_ind_register_qmi_hit_count')}`",
        f"- wlfw capability QMI hits: `{gate.get('wlfw_cap_qmi_hit_count')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Uploaded files: `{property_deploy.get('file_count')}`",
        f"- Uploaded bytes: `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Next",
        "",
        "- Stop after this label. Do not spin timing/window variants from this gate.",
        "- If label is `wlfw-start-reached-downstream-block`, the next work is modem-side WLAN-PD image/start trigger analysis, not PM actors or QCACLD registration.",
        "- If label is `wlan-pd-progress-before-connect`, plan the next bounded WLFW/BDF/wlan0 gate before any credentialed connection attempt.",
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
