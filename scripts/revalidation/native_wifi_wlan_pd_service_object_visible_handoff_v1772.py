#!/usr/bin/env python3
"""V1772 one-run WLAN-PD service-object-visible discriminator handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_timestamped_observer_handoff_v1736 as prev


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1772"
V1771_OUT = REPO_ROOT / "tmp" / "wifi" / "v1771-wlan-pd-service-object-visible-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1771/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1772-wlan-pd-service-object-visible-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1772_WLAN_PD_SERVICE_OBJECT_VISIBLE_HANDOFF_2026-06-03.md"
)


def configure_base() -> None:
    prev.CYCLE = CYCLE
    prev.V1735_OUT = V1771_OUT
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.CYCLE = CYCLE
    prev.base.V1728_OUT = V1771_OUT
    prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.base.CYCLE = CYCLE
    prev.base.base.V1726_OUT = V1771_OUT
    prev.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.base.prev.CYCLE = CYCLE
    prev.base.base.prev.V1687_OUT = V1771_OUT
    prev.base.base.prev.DEFAULT_SOURCE_MANIFEST = V1771_OUT / "manifest.json"
    prev.base.base.prev.DEFAULT_TEST_IMAGE = V1771_OUT / "boot_linux_v1771_wlan_pd_service_object_visible.img"
    prev.base.base.prev.LOCAL_PROPERTY_ROOT = V1771_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    prev.base.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.base.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.base.base.prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.140 (v1771-wlan-pd-service-object-visible)"
    prev.base.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1771.log"
    prev.base.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1771.summary"
    prev.base.base.prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1771-helper.result"
    prev.base.base.prev.DMESG_PATTERN = (
        "A90v1771|wlan_pd_service_object_visible_trigger|wlan_pd_service_object_visible|"
        "wlan_pd_cnss_nonlog_control_flow|wifi_companion_service_notifier_late_probe|"
        "wifi_companion_service_notifier_late_listener|wlan_pd_firmware_serve_gate|"
        "service-manager|servicemanager|vndservicemanager|vndbinder|PeripheralManager|"
        "peripheral|pm-service|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|rmt_storage|"
        "pd-mapper|qrtr|service 69|wlfw|wlfw_start|wlfw_service_request|icnss|"
        "FW ready|BDF|wlan0|cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def field_bool(fields: dict[str, str], key: str) -> bool:
    return fields.get(key) == "1"


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev.base.base.prev.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev.base.base.prev.fwbase.parse_helper_fields(evidence_dir)
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
    null_branch_hits = intish(
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_null_peripheral_branch.hit_count")
    )
    requested_wlanmdsp = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.requested_wlanmdsp")
    wlfw_service69 = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.wlfw_service69_seen")
    wlan0_present = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.wlan0_present")
    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "nonlog_contract_seen": nonlog_contract_seen,
        "late_listener_contract_seen": late_listener_contract_seen,
        "safety_ok": safety_ok,
        "helper_label": helper_fields.get("wlan_pd_service_object_visible_trigger.label"),
        "provider_seen": "1" if provider_seen else "0",
        "as_interface_hits": str(as_interface_hits),
        "register_tx_hits": str(register_tx_hits),
        "success_path_hits": str(success_hits),
        "null_branch_hits": str(null_branch_hits),
        "requested_wlanmdsp": "1" if requested_wlanmdsp else "0",
        "wlfw_service69_seen": "1" if wlfw_service69 else "0",
        "wlan0_present": "1" if wlan0_present else "0",
        "late_listener_result": helper_fields.get("wifi_companion_service_notifier_late_listener.result"),
        "late_listener_state": helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name"),
        "late_listener_indication_seen": helper_fields.get("wifi_companion_service_notifier_late_listener.indication_seen"),
        "wlfw_start_hits": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.hit_count"),
        "wlfw_service_request_hits": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.hit_count"),
        "wlfw_worker_create_success_hits": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_worker_pthread_create_success.hit_count"),
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1771 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not safety_ok:
        return f"{args.cycle.lower()}-safety-contract-regression", False, "one or more hard-stop safety fields regressed", details
    if as_interface_hits > 0 and register_tx_hits > 0 and requested_wlanmdsp:
        return (
            f"{args.cycle.lower()}-service-object-nonnull-vote-sent-wlanmdsp-requested-rollback-pass",
            True,
            "PeripheralManager object was non-null, register/vote TX was observed, and wlanmdsp was requested; stop before cascade",
            details,
        )
    if as_interface_hits > 0 and register_tx_hits > 0:
        return (
            f"{args.cycle.lower()}-service-object-nonnull-vote-sent-no-request-rollback-pass",
            True,
            "PeripheralManager object was non-null and register/vote TX was observed, but wlanmdsp was not requested; stop for functional PM forwarding plan",
            details,
        )
    if as_interface_hits > 0:
        return (
            f"{args.cycle.lower()}-service-object-nonnull-no-vote-rollback-pass",
            True,
            "PeripheralManager object became non-null, but cnss-daemon did not reach register/vote TX; stop for host-only branch classification",
            details,
        )
    if not provider_seen or null_branch_hits > 0 or as_interface_hits == 0:
        return (
            f"{args.cycle.lower()}-service-object-still-null-rollback-pass",
            True,
            "service-object visibility did not make cnss-daemon reach asInterface/register; stop for route/helper fix",
            details,
        )
    return (
        f"{args.cycle.lower()}-service-object-unclassified-rollback-pass",
        True,
        "one service-object-visible run produced an unclassified but rollback-verified discriminator result",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD Service-object Visible Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD service-object visible discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- provider seen: `{gate.get('provider_seen')}`",
        f"- asInterface hits: `{gate.get('as_interface_hits')}`",
        f"- register/vote TX hits: `{gate.get('register_tx_hits')}`",
        f"- success path hits: `{gate.get('success_path_hits')}`",
        f"- null branch hits: `{gate.get('null_branch_hits')}`",
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
        f"- WLFW start hits: `{gate.get('wlfw_start_hits')}`",
        f"- WLFW service request hits: `{gate.get('wlfw_service_request_hits')}`",
        f"- WLFW worker create success hits: `{gate.get('wlfw_worker_create_success_hits')}`",
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
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; do not autonomously chain into PM survival or WLAN cascade gates.",
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
