#!/usr/bin/env python3
"""V1793 one-run WLAN-PD PM register request string observer handoff."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_server_forwarding_observer_handoff_v1784 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1793"
V1792_OUT = REPO_ROOT / "tmp" / "wifi" / "v1792-pm-register-request-string-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1792/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1793-pm-register-request-string-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1793_PM_REGISTER_REQUEST_STRING_HANDOFF_2026-06-03.md"
)

DEVNODE_RE = re.compile(r'\bdevnode="?([^"\s]+)"?')
NAME_RE = re.compile(r'\bname="?([^"\s]+)"?')


def configure_base() -> None:
    base.base.prev.CYCLE = CYCLE
    base.base.prev.V1735_OUT = V1792_OUT
    base.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.prev.base.CYCLE = CYCLE
    base.base.prev.base.V1726_OUT = V1792_OUT
    base.base.prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.prev.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.prev.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.prev.base.prev.CYCLE = CYCLE
    base.base.prev.base.prev.V1687_OUT = V1792_OUT
    base.base.prev.base.prev.DEFAULT_SOURCE_MANIFEST = V1792_OUT / "manifest.json"
    base.base.prev.base.prev.DEFAULT_TEST_IMAGE = (
        V1792_OUT / "boot_linux_v1792_pm_register_request_string_observer.img"
    )
    base.base.prev.base.prev.LOCAL_PROPERTY_ROOT = (
        V1792_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )
    base.base.prev.base.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.prev.base.prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.prev.base.prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.prev.base.prev.TEST_EXPECT_VERSION = (
        "A90 Linux init 0.9.147 (v1792-pm-register-request-string-observer)"
    )
    base.base.prev.base.prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1792.log"
    base.base.prev.base.prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1792.summary"
    base.base.prev.base.prev.TEST_HELPER_RESULT_PATH = (
        "/cache/native-init-wifi-test-boot-v1792-helper.result"
    )
    base.base.prev.base.prev.DMESG_PATTERN = (
        "A90v1792|wlan_pd_service_object_visible_trigger|wlan_pd_service_object_visible|"
        "wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|pm_server_register|"
        "pm-service-init|pm_service_init|pm_service_add_peripheral|"
        "record=|devnode=|pm-server-register|pm-service|PeripheralManager|"
        "peripheral|vndservicemanager|vndbinder|service-manager|servicemanager|"
        "hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|rmt_storage|"
        "pd-mapper|qrtr|service 69|wlfw|wlfw_start|wlfw_service_request|"
        "icnss|FW ready|BDF|wlan0|cnss-daemon|4080000.qcom,mss|"
        "Brought out of reset|modem: loading"
    )


def intish(value: object) -> int:
    return base.intish(value)


def parse_token(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text or "")
    return match.group(1) if match else ""


def parse_field(key: str, text: str) -> str:
    quoted = re.search(rf'\b{re.escape(key)}="([^"]*)"', text or "")
    if quoted:
        return reliable_observed_string(quoted.group(1))
    bare = re.search(rf'\b{re.escape(key)}=([^\s]+)', text or "")
    return reliable_observed_string(bare.group(1)) if bare else ""


def reliable_observed_string(value: str) -> str:
    if not value or "\ufffd" in value:
        return ""
    if any(ord(ch) < 32 for ch in value):
        return ""
    return value


def report_value(value: object) -> str:
    text = str(value or "")
    if reliable_observed_string(text):
        return text
    return "unreliable-entry-fetcharg"


def collect_pm_server_fields(fields: dict[str, str]) -> dict[str, str]:
    result = base.collect_pm_server_fields(fields)
    prefix = "wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe."
    for key in (
        "pm_server_register_entry",
        "pm_server_register_strcmp_call",
        "pm_server_register_no_peripheral",
        "pm_service_main_supported_list_init",
        "pm_service_init_helper_entry",
        "pm_service_init_get_system_info_call",
        "pm_service_init_get_system_info_fail",
        "pm_service_init_first_count_load",
        "pm_service_init_first_add_peripheral_call",
        "pm_service_init_first_add_peripheral_fail_log",
        "pm_service_init_second_count_load",
        "pm_service_init_second_add_peripheral_call",
        "pm_service_init_second_add_peripheral_fail_log",
        "pm_service_add_peripheral_entry",
        "pm_service_add_peripheral_known_name",
        "pm_service_add_peripheral_init_fail",
        "pm_service_add_peripheral_list_commit",
        "pm_service_pre_binder_init_done",
    ):
        result[f"{key}_hits"] = fields.get(prefix + f"{key}.hit_count", "")
        result[f"{key}_first_hit_line"] = fields.get(prefix + f"{key}.first_hit_line", "")
        result[f"{key}_fetch_args"] = fields.get(prefix + f"{key}.fetch_args", "")
    for key in (
        "pm_server_register_entry",
        "pm_server_register_strcmp_call",
        "pm_server_register_no_peripheral",
        "pm_service_add_peripheral_entry",
        "pm_service_add_peripheral_known_name",
        "pm_service_add_peripheral_init_fail",
    ):
        line = result.get(f"{key}_first_hit_line", "")
        result[f"{key}_name"] = parse_token(NAME_RE, line)
        result[f"{key}_devnode"] = parse_token(DEVNODE_RE, line)
    result["pm_server_register_entry_peripheral"] = parse_field(
        "peripheral",
        result.get("pm_server_register_entry_first_hit_line", ""),
    )
    result["pm_server_register_entry_client"] = parse_field(
        "client",
        result.get("pm_server_register_entry_first_hit_line", ""),
    )
    result["pm_server_register_strcmp_candidate"] = parse_field(
        "candidate",
        result.get("pm_server_register_strcmp_call_first_hit_line", ""),
    )
    result["pm_server_register_strcmp_requested"] = parse_field(
        "requested",
        result.get("pm_server_register_strcmp_call_first_hit_line", ""),
    )
    result["pm_server_register_no_peripheral_name"] = parse_field(
        "peripheral",
        result.get("pm_server_register_no_peripheral_first_hit_line", ""),
    )
    return result


def choose_devnode(details: dict[str, Any]) -> tuple[str, str]:
    for key in (
        "pm_service_add_peripheral_init_fail",
        "pm_service_add_peripheral_known_name",
        "pm_service_add_peripheral_entry",
    ):
        devnode = str(details.get(f"{key}_devnode") or "")
        name = str(details.get(f"{key}_name") or "")
        if devnode:
            return name, devnode
    return "", ""


def choose_requested_peripheral(details: dict[str, Any]) -> str:
    for key in (
        "pm_server_register_no_peripheral_name",
        "pm_server_register_entry_peripheral",
        "pm_server_register_strcmp_requested",
    ):
        value = str(details.get(key) or "")
        if value:
            return value
    return ""


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
    register_entry_hits = intish(details.get("pm_server_register_entry_hits"))
    register_success_hits = intish(details.get("pm_server_success_return_hits"))
    register_match_hits = intish(details.get("pm_server_match_hits"))
    register_no_peripheral_hits = intish(details.get("pm_server_no_peripheral_hits"))
    list_commit_hits = intish(details.get("pm_service_add_peripheral_list_commit_hits"))
    requested_peripheral = choose_requested_peripheral(details)
    name, devnode = choose_devnode(details)
    details["pm_service_devnode_candidate_name"] = name
    details["pm_service_devnode_candidate_path"] = devnode
    details["pm_register_requested_peripheral"] = requested_peripheral
    label = "pm-register-unclassified"

    if not pass_ok:
        details["pm_register_request_label"] = label
        return decision, pass_ok, reason, details
    if list_commit_hits > 0 or register_match_hits > 0 or register_success_hits > 0:
        label = "pm-register-list-commit-progress"
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = "PM-service register path progressed past the previous empty-list/no-peripheral boundary; stop before any PM repair or WLAN-PD cascade"
    elif register_entry_hits > 0 and not requested_peripheral:
        label = "pm-register-fetcharg-unavailable"
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = "PM-service register ran, but tracefs fetchargs did not expose the requested peripheral string; stop for observer repair"
    elif requested_peripheral == "SDX50M":
        label = "pm-register-request-sdx50m"
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = "CNSS PM register requested SDX50M; stop before any private /dev/subsys_esoc0 existence-parity repair"
    elif requested_peripheral:
        label = "pm-register-request-modem-or-other"
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = f"CNSS PM register requested {requested_peripheral}; classify request/candidate mismatch before any devnode repair"
    elif register_entry_hits == 0:
        label = "pm-register-entry-missing"
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = "PM-service register entry was not observed; stop for route or observer repair"
    elif register_no_peripheral_hits > 0:
        label = "pm-register-fetcharg-unavailable"
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = "PM-service no-peripheral path was observed, but the requested peripheral string was not recovered"
    details["pm_register_request_label"] = label
    return decision, pass_ok, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} PM Register Request String Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM register request string discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- PM register request label: `{gate.get('pm_register_request_label')}`",
        f"- requested peripheral: `{gate.get('pm_register_requested_peripheral')}`",
        f"- register entry peripheral/client: `{report_value(gate.get('pm_server_register_entry_peripheral'))}` / `{report_value(gate.get('pm_server_register_entry_client'))}`",
        f"- register strcmp candidate/requested: `{gate.get('pm_server_register_strcmp_candidate')}` / `{gate.get('pm_server_register_strcmp_requested')}`",
        f"- no-peripheral requested: `{gate.get('pm_server_register_no_peripheral_name')}`",
        f"- candidate name: `{gate.get('pm_service_devnode_candidate_name')}`",
        f"- candidate devnode: `{gate.get('pm_service_devnode_candidate_path')}`",
        f"- provider seen: `{gate.get('provider_seen')}`",
        f"- asInterface hits: `{gate.get('as_interface_hits')}`",
        f"- register/vote TX hits: `{gate.get('register_tx_hits')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        "",
        "## PM Register Request Uprobes",
        "",
        f"- register entry hits: `{gate.get('pm_server_register_entry_hits')}`",
        f"- register entry fetchargs: `{gate.get('pm_server_register_entry_fetch_args')}`",
        f"- register entry first hit: `{report_value(gate.get('pm_server_register_entry_first_hit_line'))}`",
        f"- strcmp hits: `{gate.get('pm_server_strcmp_call_hits')}`",
        f"- strcmp fetchargs: `{gate.get('pm_server_register_strcmp_call_fetch_args')}`",
        f"- strcmp first hit: `{gate.get('pm_server_register_strcmp_call_first_hit_line')}`",
        f"- no-peripheral hits: `{gate.get('pm_server_no_peripheral_hits')}`",
        f"- no-peripheral fetchargs: `{gate.get('pm_server_register_no_peripheral_fetch_args')}`",
        f"- no-peripheral first hit: `{gate.get('pm_server_register_no_peripheral_first_hit_line')}`",
        f"- loop/match/success hits: `{gate.get('pm_server_loop_node_hits')}` / `{gate.get('pm_server_match_hits')}` / `{gate.get('pm_server_success_return_hits')}`",
        "",
        "## PM-service Devnode Uprobes",
        "",
        f"- entry hits: `{gate.get('pm_service_add_peripheral_entry_hits')}`",
        f"- entry fetchargs: `{gate.get('pm_service_add_peripheral_entry_fetch_args')}`",
        f"- entry first hit: `{gate.get('pm_service_add_peripheral_entry_first_hit_line')}`",
        f"- entry parsed name/devnode: `{gate.get('pm_service_add_peripheral_entry_name')}` / `{gate.get('pm_service_add_peripheral_entry_devnode')}`",
        f"- known-name hits: `{gate.get('pm_service_add_peripheral_known_name_hits')}`",
        f"- known-name fetchargs: `{gate.get('pm_service_add_peripheral_known_name_fetch_args')}`",
        f"- known-name first hit: `{gate.get('pm_service_add_peripheral_known_name_first_hit_line')}`",
        f"- known-name parsed name/devnode: `{gate.get('pm_service_add_peripheral_known_name_name')}` / `{gate.get('pm_service_add_peripheral_known_name_devnode')}`",
        f"- init-fail hits: `{gate.get('pm_service_add_peripheral_init_fail_hits')}`",
        f"- init-fail fetchargs: `{gate.get('pm_service_add_peripheral_init_fail_fetch_args')}`",
        f"- init-fail first hit: `{gate.get('pm_service_add_peripheral_init_fail_first_hit_line')}`",
        f"- init-fail parsed name/devnode: `{gate.get('pm_service_add_peripheral_init_fail_name')}` / `{gate.get('pm_service_add_peripheral_init_fail_devnode')}`",
        f"- list commit hits: `{gate.get('pm_service_add_peripheral_list_commit_hits')}`",
        "",
        "## PM-service Init-discovery Uprobes",
        "",
        f"- get_system_info call/fail hits: `{gate.get('pm_service_init_get_system_info_call_hits')}` / `{gate.get('pm_service_init_get_system_info_fail_hits')}`",
        f"- first add-peripheral call/fail hits: `{gate.get('pm_service_init_first_add_peripheral_call_hits')}` / `{gate.get('pm_service_init_first_add_peripheral_fail_log_hits')}`",
        f"- second add-peripheral call/fail hits: `{gate.get('pm_service_init_second_add_peripheral_call_hits')}` / `{gate.get('pm_service_init_second_add_peripheral_fail_log_hits')}`",
        f"- pre-Binder init-done hits: `{gate.get('pm_service_pre_binder_init_done_hits')}`",
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
        "- Stop after this one label; do not repair PM-service devnodes, chase WLAN-PD cascade, start Wi-Fi HAL, scan/connect, DHCP/routes, or external ping in this run.",
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
