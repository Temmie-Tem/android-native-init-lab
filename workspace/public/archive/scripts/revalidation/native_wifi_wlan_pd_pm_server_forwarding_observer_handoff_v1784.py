#!/usr/bin/env python3
"""V1784 one-run WLAN-PD PM server forwarding observer handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_service_object_visible_handoff_v1772 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1784"
V1783_OUT = REPO_ROOT / "tmp" / "wifi" / "v1783-pm-server-forwarding-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1783/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1784-pm-server-forwarding-observer-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1784_PM_SERVER_FORWARDING_OBSERVER_HANDOFF_2026-06-03.md"
)


def configure_base() -> None:
    base.prev.CYCLE = CYCLE
    base.prev.V1735_OUT = V1783_OUT
    base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.prev.base.CYCLE = CYCLE
    base.prev.base.V1726_OUT = V1783_OUT
    base.prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.prev.base.prev.CYCLE = CYCLE
    base.prev.base.prev.V1687_OUT = V1783_OUT
    base.prev.base.prev.DEFAULT_SOURCE_MANIFEST = V1783_OUT / "manifest.json"
    base.prev.base.prev.DEFAULT_TEST_IMAGE = V1783_OUT / "boot_linux_v1783_pm_server_forwarding_observer.img"
    base.prev.base.prev.LOCAL_PROPERTY_ROOT = V1783_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.prev.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.prev.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.prev.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.prev.base.prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.144 (v1783-pm-server-forwarding-observer)"
    base.prev.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1783.log"
    base.prev.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1783.summary"
    base.prev.base.prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1783-helper.result"
    base.prev.base.prev.DMESG_PATTERN = (
        "A90v1783|wlan_pd_service_object_visible_trigger|wlan_pd_service_object_visible|"
        "wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|pm_server_register|"
        "pm-server-register|pm-service|PeripheralManager|peripheral|vndservicemanager|"
        "vndbinder|service-manager|servicemanager|hwservicemanager|pm_proxy_helper|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|wlfw|"
        "wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
        "4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def field_bool(fields: dict[str, str], key: str) -> bool:
    return fields.get(key) == "1"


def collect_pm_server_fields(fields: dict[str, str]) -> dict[str, str]:
    prefix = "wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe."
    return {
        "pm_server_label": fields.get(prefix + "label", ""),
        "pm_server_attempted": fields.get("wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe_attempted", ""),
        "pm_server_registered": fields.get(prefix + "registered", ""),
        "pm_server_enabled": fields.get(prefix + "enabled", ""),
        "pm_server_hit_count": fields.get(prefix + "hit_count", ""),
        "pm_server_first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "pm_server_selected_path": fields.get(prefix + "target.selected_path", ""),
        "pm_server_target_index": fields.get(prefix + "target.selected_index", ""),
        "pm_server_register_entry_hits": fields.get(prefix + "pm_server_register_entry.hit_count", ""),
        "pm_server_loop_node_hits": fields.get(prefix + "pm_server_register_loop_node.hit_count", ""),
        "pm_server_name_helper_call_hits": fields.get(prefix + "pm_server_register_name_helper_call.hit_count", ""),
        "pm_server_name_helper_return_hits": fields.get(prefix + "pm_server_register_name_helper_return.hit_count", ""),
        "pm_server_strcmp_call_hits": fields.get(prefix + "pm_server_register_strcmp_call.hit_count", ""),
        "pm_server_strcmp_result_hits": fields.get(prefix + "pm_server_register_strcmp_result.hit_count", ""),
        "pm_server_loop_advance_hits": fields.get(prefix + "pm_server_register_loop_advance.hit_count", ""),
        "pm_server_loop_compare_hits": fields.get(prefix + "pm_server_register_loop_compare.hit_count", ""),
        "pm_server_match_hits": fields.get(prefix + "pm_server_register_match.hit_count", ""),
        "pm_server_permission_ok_hits": fields.get(prefix + "pm_server_register_permission_ok.hit_count", ""),
        "pm_server_add_client_hits": fields.get(prefix + "pm_server_register_add_client_call.hit_count", ""),
        "pm_server_success_return_hits": fields.get(prefix + "pm_server_register_success_return.hit_count", ""),
        "pm_server_no_peripheral_hits": fields.get(prefix + "pm_server_register_no_peripheral.hit_count", ""),
    }


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
    null_branch_hits = intish(
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_null_peripheral_branch.hit_count")
    )
    requested_wlanmdsp = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.requested_wlanmdsp")
    wlfw_service69 = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.wlfw_service69_seen")
    wlan0_present = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.wlan0_present")
    policy_precondition_required = field_bool(helper_fields, "wlan_pd_service_object_visible.policy_load_precondition.required")
    policy_precondition_requested = field_bool(helper_fields, "wlan_pd_service_object_visible.policy_load_precondition.requested")
    policy_load_result = helper_fields.get("pm_service_trigger_observer.policy_load.result", "")
    policy_load_pass = policy_load_result.startswith("policy-load-pass")
    pm_server = collect_pm_server_fields(helper_fields)
    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "nonlog_contract_seen": nonlog_contract_seen,
        "late_listener_contract_seen": late_listener_contract_seen,
        "safety_ok": safety_ok,
        "policy_precondition_required": "1" if policy_precondition_required else "0",
        "policy_precondition_requested": "1" if policy_precondition_requested else "0",
        "policy_load_result": policy_load_result,
        "policy_load_pass": "1" if policy_load_pass else "0",
        "per_mgr_state": helper_fields.get("wlan_pd_service_object_visible.per_mgr.state"),
        "per_mgr_zombie": helper_fields.get("wlan_pd_service_object_visible.per_mgr.zombie"),
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
        **pm_server,
    }

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1783 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not safety_ok:
        return f"{args.cycle.lower()}-safety-contract-regression", False, "one or more hard-stop safety fields regressed", details
    if not policy_precondition_required or not policy_precondition_requested or not policy_load_pass:
        return (
            f"{args.cycle.lower()}-service-object-still-null-rollback-pass",
            True,
            "service-object helper did not complete the SELinux policy-load precondition; stop for route/helper fix",
            details,
        )
    if not provider_seen or as_interface_hits == 0:
        return (
            f"{args.cycle.lower()}-service-object-still-null-rollback-pass",
            True,
            "service-object helper failed to make vendor.qcom.PeripheralManager visible/non-null; stop for route/helper fix",
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
        "PeripheralManager object was non-null and register/vote TX was observed, but wlanmdsp was not requested; PM server label fixes the next boundary",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} PM Server Forwarding Observer Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM server forwarding observer discriminator",
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
        f"- client success path hits: `{gate.get('success_path_hits')}`",
        f"- null branch hits: `{gate.get('null_branch_hits')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        f"- late listener state: `{gate.get('late_listener_state')}`",
        f"- late listener indication seen: `{gate.get('late_listener_indication_seen')}`",
        "",
        "## PM Server Uprobes",
        "",
        f"- label: `{gate.get('pm_server_label')}`",
        f"- attempted/registered/enabled: `{gate.get('pm_server_attempted')}` / `{gate.get('pm_server_registered')}` / `{gate.get('pm_server_enabled')}`",
        f"- target: `{gate.get('pm_server_selected_path')}` (index `{gate.get('pm_server_target_index')}`)",
        f"- total hits: `{gate.get('pm_server_hit_count')}`",
        f"- first hit: `{gate.get('pm_server_first_hit_line')}`",
        f"- register entry hits: `{gate.get('pm_server_register_entry_hits')}`",
        f"- loop/match hits: loop=`{gate.get('pm_server_loop_node_hits')}`, strcmp=`{gate.get('pm_server_strcmp_result_hits')}`, match=`{gate.get('pm_server_match_hits')}`",
        f"- permission/add-client/success hits: `{gate.get('pm_server_permission_ok_hits')}` / `{gate.get('pm_server_add_client_hits')}` / `{gate.get('pm_server_success_return_hits')}`",
        f"- no-peripheral hits: `{gate.get('pm_server_no_peripheral_hits')}`",
        "",
        "## Route Health",
        "",
        f"- policy-load result: `{gate.get('policy_load_result')}`",
        f"- `pm_proxy_helper` ready: `{gate.get('pm_proxy_helper_ready')}`",
        f"- `pm-service` ready: `{gate.get('per_mgr_ready')}`",
        f"- `pm-service` state/zombie: `{gate.get('per_mgr_state')}` / `{gate.get('per_mgr_zombie')}`",
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
        "- Stop after this one label; do not autonomously chain into functional PM forwarding repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
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
