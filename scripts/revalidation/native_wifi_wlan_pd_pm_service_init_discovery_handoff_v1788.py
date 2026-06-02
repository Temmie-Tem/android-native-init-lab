#!/usr/bin/env python3
"""V1788 one-run WLAN-PD PM-service init-discovery observer handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_server_forwarding_observer_handoff_v1784 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1788"
V1787_OUT = REPO_ROOT / "tmp" / "wifi" / "v1787-pm-service-init-discovery-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1787/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1788-pm-service-init-discovery-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1788_PM_SERVICE_INIT_DISCOVERY_HANDOFF_2026-06-03.md"
)


def configure_base() -> None:
    base.base.prev.CYCLE = CYCLE
    base.base.prev.V1735_OUT = V1787_OUT
    base.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.prev.base.CYCLE = CYCLE
    base.base.prev.base.V1726_OUT = V1787_OUT
    base.base.prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.prev.base.prev.CYCLE = CYCLE
    base.base.prev.base.prev.V1687_OUT = V1787_OUT
    base.base.prev.base.prev.DEFAULT_SOURCE_MANIFEST = V1787_OUT / "manifest.json"
    base.base.prev.base.prev.DEFAULT_TEST_IMAGE = (
        V1787_OUT / "boot_linux_v1787_pm_service_init_discovery_observer.img"
    )
    base.base.prev.base.prev.LOCAL_PROPERTY_ROOT = (
        V1787_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )
    base.base.prev.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.prev.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.prev.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.prev.base.prev.TEST_EXPECT_VERSION = (
        "A90 Linux init 0.9.145 (v1787-pm-service-init-discovery-observer)"
    )
    base.base.prev.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1787.log"
    base.base.prev.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1787.summary"
    base.base.prev.base.prev.TEST_HELPER_RESULT_PATH = (
        "/cache/native-init-wifi-test-boot-v1787-helper.result"
    )
    base.base.prev.base.prev.DMESG_PATTERN = (
        "A90v1787|wlan_pd_service_object_visible_trigger|wlan_pd_service_object_visible|"
        "wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|pm_server_register|"
        "pm-service-init|pm_service_init|pm_service_add_peripheral|"
        "pm-server-register|pm-service|PeripheralManager|peripheral|vndservicemanager|"
        "vndbinder|service-manager|servicemanager|hwservicemanager|pm_proxy_helper|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|wlfw|"
        "wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
        "4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def intish(value: object) -> int:
    return base.intish(value)


def field_bool(fields: dict[str, str], key: str) -> bool:
    return base.field_bool(fields, key)


def collect_pm_server_fields(fields: dict[str, str]) -> dict[str, str]:
    result = base.collect_pm_server_fields(fields)
    prefix = "wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe."
    result.update(
        {
            "pm_service_main_supported_list_init_hits": fields.get(
                prefix + "pm_service_main_supported_list_init.hit_count", ""
            ),
            "pm_service_init_helper_entry_hits": fields.get(
                prefix + "pm_service_init_helper_entry.hit_count", ""
            ),
            "pm_service_init_get_system_info_call_hits": fields.get(
                prefix + "pm_service_init_get_system_info_call.hit_count", ""
            ),
            "pm_service_init_get_system_info_fail_hits": fields.get(
                prefix + "pm_service_init_get_system_info_fail.hit_count", ""
            ),
            "pm_service_init_first_count_load_hits": fields.get(
                prefix + "pm_service_init_first_count_load.hit_count", ""
            ),
            "pm_service_init_first_add_peripheral_call_hits": fields.get(
                prefix + "pm_service_init_first_add_peripheral_call.hit_count", ""
            ),
            "pm_service_init_first_add_peripheral_fail_log_hits": fields.get(
                prefix + "pm_service_init_first_add_peripheral_fail_log.hit_count", ""
            ),
            "pm_service_init_second_count_load_hits": fields.get(
                prefix + "pm_service_init_second_count_load.hit_count", ""
            ),
            "pm_service_init_second_add_peripheral_call_hits": fields.get(
                prefix + "pm_service_init_second_add_peripheral_call.hit_count", ""
            ),
            "pm_service_init_second_add_peripheral_fail_log_hits": fields.get(
                prefix + "pm_service_init_second_add_peripheral_fail_log.hit_count", ""
            ),
            "pm_service_add_peripheral_entry_hits": fields.get(
                prefix + "pm_service_add_peripheral_entry.hit_count", ""
            ),
            "pm_service_add_peripheral_known_name_hits": fields.get(
                prefix + "pm_service_add_peripheral_known_name.hit_count", ""
            ),
            "pm_service_add_peripheral_init_fail_hits": fields.get(
                prefix + "pm_service_add_peripheral_init_fail.hit_count", ""
            ),
            "pm_service_add_peripheral_list_commit_hits": fields.get(
                prefix + "pm_service_add_peripheral_list_commit.hit_count", ""
            ),
            "pm_service_pre_binder_init_done_hits": fields.get(
                prefix + "pm_service_pre_binder_init_done.hit_count", ""
            ),
        }
    )
    return result


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, pass_ok, reason, details = base.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = base.base.prev.base.prev.fwbase.parse_helper_fields(evidence_dir)
    details.update(collect_pm_server_fields(helper_fields))
    pm_label = str(details.get("pm_server_label") or "")
    get_system_info_hits = intish(details.get("pm_service_init_get_system_info_call_hits"))
    get_system_info_fail_hits = intish(details.get("pm_service_init_get_system_info_fail_hits"))
    add_peripheral_hits = intish(details.get("pm_service_add_peripheral_list_commit_hits"))
    register_success_hits = intish(details.get("pm_server_success_return_hits"))
    no_peripheral_hits = intish(details.get("pm_server_no_peripheral_hits"))
    register_tx_hits = intish(details.get("register_tx_hits"))
    requested_wlanmdsp = details.get("requested_wlanmdsp") == "1"
    details["pm_service_discovery_get_system_info_hits"] = str(get_system_info_hits)
    details["pm_service_discovery_fail_hits"] = str(get_system_info_fail_hits)
    details["pm_service_discovery_list_commit_hits"] = str(add_peripheral_hits)
    discovery_label = "pm-service-discovery-unclassified"

    if not pass_ok:
        details["pm_service_discovery_label"] = discovery_label
        return decision, pass_ok, reason, details
    if get_system_info_fail_hits > 0:
        discovery_label = "pm-service-discovery-get-system-info-failed"
        decision = f"{args.cycle.lower()}-{discovery_label}-rollback-pass"
        reason = "PM-service init reached get_system_info but hit the immediate failure path; stop for sysfs discovery input classification"
    elif get_system_info_hits > 0 and add_peripheral_hits == 0:
        discovery_label = "pm-service-discovery-zero-list-commit"
        decision = f"{args.cycle.lower()}-{discovery_label}-rollback-pass"
        reason = "PM-service init reached get_system_info but no supported-list insertion was observed; stop for private sysfs discovery parity"
    elif add_peripheral_hits > 0 and no_peripheral_hits > 0:
        discovery_label = "pm-service-discovery-list-populated-register-no-peripheral"
        decision = f"{args.cycle.lower()}-{discovery_label}-rollback-pass"
        reason = "PM-service populated at least one supported-list node but CNSS register still took the no-peripheral branch; stop for PM server object/timing mismatch analysis"
    elif add_peripheral_hits > 0 and register_success_hits > 0 and register_tx_hits > 0:
        discovery_label = "pm-service-discovery-success-register-success"
        if requested_wlanmdsp:
            decision = (
                f"{args.cycle.lower()}-service-object-nonnull-vote-sent-"
                "wlanmdsp-requested-rollback-pass"
            )
            reason = "PM-service discovery and register succeeded, and wlanmdsp was requested; stop before WLAN-PD cascade"
        else:
            decision = f"{args.cycle.lower()}-{discovery_label}-no-wlanmdsp-rollback-pass"
            reason = "PM-service discovery and register succeeded, but wlanmdsp was still not requested; stop for functional vote-to-modem forwarding analysis"
    elif pm_label in {"pm-service-init-list-populated-no-register", "pm-service-init-no-list-insert"}:
        discovery_label = pm_label
        decision = f"{args.cycle.lower()}-{discovery_label}-rollback-pass"
        reason = "PM-service init-discovery observer produced its internal label before a server register conclusion; stop after one discriminator"
    details["pm_service_discovery_label"] = discovery_label
    return decision, pass_ok, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} PM-service Init-discovery Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM-service init-discovery discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- PM-service discovery label: `{gate.get('pm_service_discovery_label')}`",
        f"- provider seen: `{gate.get('provider_seen')}`",
        f"- asInterface hits: `{gate.get('as_interface_hits')}`",
        f"- register/vote TX hits: `{gate.get('register_tx_hits')}`",
        f"- client success path hits: `{gate.get('success_path_hits')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        f"- late listener state: `{gate.get('late_listener_state')}`",
        "",
        "## PM-service Init-discovery Uprobes",
        "",
        f"- list init hits: `{gate.get('pm_service_main_supported_list_init_hits')}`",
        f"- init helper entry hits: `{gate.get('pm_service_init_helper_entry_hits')}`",
        f"- get_system_info call hits: `{gate.get('pm_service_init_get_system_info_call_hits')}`",
        f"- get_system_info fail hits: `{gate.get('pm_service_init_get_system_info_fail_hits')}`",
        f"- first count/load hits: `{gate.get('pm_service_init_first_count_load_hits')}`",
        f"- first add-peripheral call/fail hits: `{gate.get('pm_service_init_first_add_peripheral_call_hits')}` / `{gate.get('pm_service_init_first_add_peripheral_fail_log_hits')}`",
        f"- second count/load hits: `{gate.get('pm_service_init_second_count_load_hits')}`",
        f"- second add-peripheral call/fail hits: `{gate.get('pm_service_init_second_add_peripheral_call_hits')}` / `{gate.get('pm_service_init_second_add_peripheral_fail_log_hits')}`",
        f"- add-peripheral entry hits: `{gate.get('pm_service_add_peripheral_entry_hits')}`",
        f"- known-name hits: `{gate.get('pm_service_add_peripheral_known_name_hits')}`",
        f"- add-peripheral init-fail hits: `{gate.get('pm_service_add_peripheral_init_fail_hits')}`",
        f"- list commit hits: `{gate.get('pm_service_add_peripheral_list_commit_hits')}`",
        f"- pre-Binder init-done hits: `{gate.get('pm_service_pre_binder_init_done_hits')}`",
        "",
        "## PM Server Register Uprobes",
        "",
        f"- attempted/registered/enabled: `{gate.get('pm_server_attempted')}` / `{gate.get('pm_server_registered')}` / `{gate.get('pm_server_enabled')}`",
        f"- target: `{gate.get('pm_server_selected_path')}` (index `{gate.get('pm_server_target_index')}`)",
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
        "- Stop after this one label; do not autonomously chain into sysfs repair, functional PM forwarding repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    base.base.configure_base = configure_base
    base.base.classify_gate = classify_gate
    base.base.render_report = render_report
    return base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
