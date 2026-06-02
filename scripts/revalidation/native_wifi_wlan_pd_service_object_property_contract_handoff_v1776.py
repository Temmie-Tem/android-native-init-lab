#!/usr/bin/env python3
"""V1776 one-run WLAN-PD service-object property-contract handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_service_object_visible_handoff_v1772 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1776"
V1775_OUT = REPO_ROOT / "tmp" / "wifi" / "v1775-service-object-property-contract-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1775/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1776-service-object-property-contract-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1776_SERVICE_OBJECT_PROPERTY_CONTRACT_HANDOFF_2026-06-03.md"
)


def configure_base() -> None:
    base.prev.CYCLE = CYCLE
    base.prev.V1735_OUT = V1775_OUT
    base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.prev.base.CYCLE = CYCLE
    base.prev.base.V1726_OUT = V1775_OUT
    base.prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.prev.base.prev.CYCLE = CYCLE
    base.prev.base.prev.V1687_OUT = V1775_OUT
    base.prev.base.prev.DEFAULT_SOURCE_MANIFEST = V1775_OUT / "manifest.json"
    base.prev.base.prev.DEFAULT_TEST_IMAGE = V1775_OUT / "boot_linux_v1775_service_object_property_contract.img"
    base.prev.base.prev.LOCAL_PROPERTY_ROOT = V1775_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.prev.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.prev.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.prev.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.prev.base.prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.141 (v1775-service-object-property-contract)"
    base.prev.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1775.log"
    base.prev.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1775.summary"
    base.prev.base.prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1775-helper.result"
    base.prev.base.prev.DMESG_PATTERN = (
        "A90v1775|wlan_pd_service_object_visible_trigger|wlan_pd_service_object_visible|"
        "wlan_pd_cnss_nonlog_control_flow|wifi_companion_service_notifier_late_probe|"
        "wifi_companion_service_notifier_late_listener|wlan_pd_firmware_serve_gate|"
        "property_service_shim|shutdown_critical_list|service-manager|servicemanager|"
        "vndservicemanager|vndbinder|PeripheralManager|peripheral|pm-service|"
        "pm_proxy_helper|wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|"
        "service 69|wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|"
        "wlan0|cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def field_bool(fields: dict[str, str], key: str) -> bool:
    return fields.get(key) == "1"


def shutdown_values(fields: dict[str, str]) -> list[str]:
    values: list[str] = []
    prefix = "wifi_hal_composite_start.property_service_shim.request."
    for key, value in fields.items():
        if not key.startswith(prefix) or not key.endswith(".name"):
            continue
        if value != "vendor.peripheral.shutdown_critical_list":
            continue
        values.append(fields.get(key[: -len(".name")] + ".value", ""))
    return values


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = base.prev.base.prev.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = base.prev.base.prev.fwbase.parse_helper_fields(evidence_dir)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.begin")
    nonlog_contract_seen = field_bool(helper_fields, "wlan_pd_cnss_nonlog_control_flow.begin")
    late_listener_contract_seen = field_bool(helper_fields, "wifi_companion_service_notifier_late_listener.begin")
    safety_ok = all(
        field_bool(helper_fields, key)
        for key in (
            "wlan_pd_service_object_visible_trigger.no_esoc0",
            "wlan_pd_service_object_visible_trigger.no_forced_rc1",
            "wlan_pd_service_object_visible_trigger.no_fake_online",
            "wlan_pd_service_object_visible_trigger.no_per_proxy",
            "wlan_pd_service_object_visible_trigger.no_wifi_hal",
            "wlan_pd_service_object_visible_trigger.no_scan_connect",
            "wlan_pd_service_object_visible_trigger.no_credentials",
            "wlan_pd_service_object_visible_trigger.no_dhcp_routes",
            "wlan_pd_service_object_visible_trigger.no_external_ping",
        )
    )
    provider_seen = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.provider_seen")
    as_interface_hits = intish(
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_as_interface_call.hit_count")
    )
    register_tx_hits = intish(
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_call.hit_count")
    )
    success_hits = intish(
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_success_path.hit_count")
    )
    requested_wlanmdsp = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.requested_wlanmdsp")
    wlfw_service69 = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.wlfw_service69_seen")
    wlan0_present = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.wlan0_present")
    property_contract = field_bool(helper_fields, "wifi_companion_start.peripheral_manager.property_contract")
    allow_shutdown = field_bool(helper_fields, "wifi_hal_composite_start.property_service_shim.allow_peripheral_shutdown_list")
    values = shutdown_values(helper_fields)

    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "nonlog_contract_seen": nonlog_contract_seen,
        "late_listener_contract_seen": late_listener_contract_seen,
        "safety_ok": safety_ok,
        "property_contract": "1" if property_contract else "0",
        "allow_peripheral_shutdown_list": "1" if allow_shutdown else "0",
        "shutdown_critical_list_values": ",".join(values),
        "helper_label": helper_fields.get("wlan_pd_service_object_visible_trigger.label"),
        "provider_seen": "1" if provider_seen else "0",
        "as_interface_hits": str(as_interface_hits),
        "register_tx_hits": str(register_tx_hits),
        "success_path_hits": str(success_hits),
        "requested_wlanmdsp": "1" if requested_wlanmdsp else "0",
        "wlfw_service69_seen": "1" if wlfw_service69 else "0",
        "wlan0_present": "1" if wlan0_present else "0",
        "late_listener_result": helper_fields.get("wifi_companion_service_notifier_late_listener.result"),
        "late_listener_state": helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name"),
        "late_listener_indication_seen": helper_fields.get("wifi_companion_service_notifier_late_listener.indication_seen"),
        "pm_proxy_helper_ready": helper_fields.get("wlan_pd_service_object_visible_trigger.pm_proxy_helper_ready"),
        "per_mgr_ready": helper_fields.get("wlan_pd_service_object_visible_trigger.per_mgr_ready"),
        "tftp_running": helper_fields.get("wlan_pd_service_object_visible_trigger.tftp_running"),
        "cnss_daemon_running": helper_fields.get("wlan_pd_service_object_visible_trigger.cnss_daemon_running"),
        "no_esoc0": helper_fields.get("wlan_pd_service_object_visible_trigger.no_esoc0"),
        "no_forced_rc1": helper_fields.get("wlan_pd_service_object_visible_trigger.no_forced_rc1"),
        "no_per_proxy": helper_fields.get("wlan_pd_service_object_visible_trigger.no_per_proxy"),
        "no_scan_connect": helper_fields.get("wlan_pd_service_object_visible_trigger.no_scan_connect"),
        "no_credentials": helper_fields.get("wlan_pd_service_object_visible_trigger.no_credentials"),
        "no_dhcp_routes": helper_fields.get("wlan_pd_service_object_visible_trigger.no_dhcp_routes"),
        "no_external_ping": helper_fields.get("wlan_pd_service_object_visible_trigger.no_external_ping"),
    }

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1775 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not safety_ok:
        return f"{args.cycle.lower()}-safety-contract-regression", False, "one or more hard-stop safety fields regressed", details
    if not property_contract or not allow_shutdown or len(values) < 2:
        return (
            f"{args.cycle.lower()}-property-contract-not-materialized-rollback-pass",
            True,
            "V1775 booted and rolled back, but the PM shutdown-critical-list values did not materialize in helper output",
            details,
        )
    if not provider_seen:
        return (
            f"{args.cycle.lower()}-service-object-route-provider-still-hidden-rollback-pass",
            True,
            "PM property contract materialized but vendor.qcom.PeripheralManager remained hidden after per_mgr; stop for route/lifetime fix",
            details,
        )
    if as_interface_hits == 0:
        return (
            f"{args.cycle.lower()}-service-object-route-provider-visible-no-asinterface-rollback-pass",
            True,
            "provider became visible, but cnss-daemon did not reach asInterface; stop for host-only branch classification",
            details,
        )
    if register_tx_hits == 0:
        return (
            f"{args.cycle.lower()}-service-object-nonnull-no-vote-rollback-pass",
            True,
            "PeripheralManager object became non-null, but cnss-daemon did not reach register/vote TX; stop for host-only branch classification",
            details,
        )
    if requested_wlanmdsp:
        return (
            f"{args.cycle.lower()}-service-object-nonnull-vote-sent-wlanmdsp-requested-rollback-pass",
            True,
            "PeripheralManager object was non-null, register/vote TX was observed, and wlanmdsp was requested; stop before cascade",
            details,
        )
    return (
        f"{args.cycle.lower()}-service-object-nonnull-vote-sent-no-request-rollback-pass",
        True,
        "PeripheralManager object was non-null and register/vote TX was observed, but wlanmdsp was not requested; stop for functional PM forwarding plan",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} Service-object Property-contract Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD service-object property-contract discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Property Contract",
        "",
        f"- Property contract flag: `{gate.get('property_contract')}`",
        f"- Shutdown-list allow flag: `{gate.get('allow_peripheral_shutdown_list')}`",
        f"- Shutdown-list values: `{gate.get('shutdown_critical_list_values')}`",
        "",
        "Interpretation: the repaired V1775 route did enable the property-contract flags,",
        "but it still did not surface the actual",
        "`vendor.peripheral.shutdown_critical_list` values. The provider therefore",
        "remained hidden and this is a route/helper-materialization result, not a modem",
        "or WLAN-PD response result.",
        "",
        "## Gate Label",
        "",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- provider seen: `{gate.get('provider_seen')}`",
        f"- asInterface hits: `{gate.get('as_interface_hits')}`",
        f"- register/vote TX hits: `{gate.get('register_tx_hits')}`",
        f"- success path hits: `{gate.get('success_path_hits')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        f"- late listener state: `{gate.get('late_listener_state')}`",
        f"- late listener indication seen: `{gate.get('late_listener_indication_seen')}`",
        "",
        "## Route Health",
        "",
        f"- `pm_proxy_helper` ready: `{gate.get('pm_proxy_helper_ready')}`",
        f"- `pm-service` ready: `{gate.get('per_mgr_ready')}`",
        f"- `tftp_server` running: `{gate.get('tftp_running')}`",
        f"- `cnss-daemon` running: `{gate.get('cnss_daemon_running')}`",
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
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; do not autonomously chain into PM forwarding, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    base.configure_base = configure_base
    base.classify_gate = classify_gate
    base.render_report = render_report
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
