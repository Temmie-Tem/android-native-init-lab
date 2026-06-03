#!/usr/bin/env python3
"""V1808 one-run WLAN-PD PM-client return fetchargs handoff."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import native_wifi_post_pm_lower_state_observer_handoff_v1806 as prev1806
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1808"
V1807_OUT = REPO_ROOT / "tmp" / "wifi" / "v1807-pm-client-return-fetchargs-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1807/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1808-pm-client-return-fetchargs-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1808_PM_CLIENT_RETURN_FETCHARGS_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.152 (v1807-pm-client-return-fetchargs)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1807.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1807.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1807-helper.result"
DMESG_PATTERN = (
    "A90v1807|wlan_pd_post_pm_lower_state_observer|"
    "pm_init_pm_client_register|pm_init_pm_client_connect|pm_init_return_path|"
    "rc=|arg0=|wlan_pd_service_object_visible_trigger|private_node.subsys|"
    "devnode_access|devnode.sdx50m|devnode.modem|access_f_ok|lstat_ok|"
    "char_device|wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|"
    "pm_server_register|pm-service-init|pm_service_init|pm_service_add_peripheral|"
    "first_count=|second_count=|record=|devnode=|pm-server-register|pm-service|"
    "PeripheralManager|peripheral|vndservicemanager|vndbinder|service-manager|"
    "servicemanager|hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|"
    "rmt_storage|pd-mapper|qrtr|service 69|wlfw|wlfw_start|"
    "wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|Brought out of reset|modem: loading"
)
RC_RE = re.compile(r"\brc=(0x[0-9a-fA-F]+|\d+)\b")


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1807_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1807_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1807_OUT / "boot_linux_v1807_pm_client_return_fetchargs.img"
    )
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1807_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1796.intish(value)


def parse_rc(event: dict[str, str]) -> int | None:
    line = event.get("first_hit_line", "")
    match = RC_RE.search(line)
    if not match:
        return None
    try:
        return int(match.group(1), 0)
    except ValueError:
        return None


def rc_text(value: int | None) -> str:
    return "" if value is None else str(value)


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1806.collect_gate_fields(fields)
    register_rc = parse_rc(details.get("pm_init_pm_client_register_retcheck", {}))
    connect_rc = parse_rc(details.get("pm_init_pm_client_connect_retcheck", {}))
    return_path_rc = parse_rc(prev1806.prev1802.event(fields, "pm_init_return_path"))
    details.update(
        {
            "pm_client_register_rc": rc_text(register_rc),
            "pm_client_connect_rc": rc_text(connect_rc),
            "pm_init_return_path": prev1806.prev1802.event(fields, "pm_init_return_path"),
            "pm_init_return_path_rc": rc_text(return_path_rc),
            "pm_client_return_fetchargs_seen": register_rc is not None and connect_rc is not None,
            "pm_client_return_nonzero": (
                (register_rc is not None and register_rc != 0)
                or (connect_rc is not None and connect_rc != 0)
                or (return_path_rc is not None and return_path_rc != 0)
            ),
        }
    )
    return details


def lower_progress(details: dict[str, Any]) -> bool:
    return (
        prev1806.mdm3_left_offlining(details)
        or bool(details.get("lower_mdm_status_irq_increased"))
        or bool(details.get("lower_mhi_present"))
        or bool(details.get("lower_service69_progress"))
        or bool(details.get("lower_wlan0_present"))
    )


def stable_offlining(details: dict[str, Any]) -> bool:
    return (
        str(details.get("lower_mdm3_states") or "") == "OFFLINING"
        and not bool(details.get("lower_mdm_status_irq_increased"))
        and not bool(details.get("lower_mhi_present"))
        and not bool(details.get("lower_service69_progress"))
        and not bool(details.get("lower_wlan0_present"))
    )


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev1796.runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev1796.runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    nonlog_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_cnss_nonlog_control_flow.begin",
    )
    late_listener_contract_seen = prev1796.field_bool(
        helper_fields,
        "wifi_companion_service_notifier_late_listener.begin",
    )
    safety_ok = (
        prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
    )
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "nonlog_contract_seen": nonlog_contract_seen,
            "late_listener_contract_seen": late_listener_contract_seen,
            "safety_ok": safety_ok,
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1807 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not details.get("lower_contract_ok"):
        return f"{args.cycle.lower()}-lower-observer-contract-missing", False, "helper result missed V1807 lower-state observer fields", details
    if not safety_ok:
        details["pm_client_return_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif stable_offlining(details):
        details["post_pm_lower_state_label"] = "stable-mdm3-offlining"
    else:
        details["post_pm_lower_state_label"] = "lower-state-incomplete"

    if not prev1806.pm_vote_boundary_reached(details):
        label = "pm-vote-boundary-incomplete"
        reason = "PM list/register/client-connect boundary was not fully observed in this run"
    elif details["post_pm_lower_state_label"] == "lower-progress":
        label = "lower-progress"
        reason = "post-PM lower-state sampler observed mdm3/IRQ/MHI/WLFW/wlan0 progress"
    elif not bool(details.get("pm_client_return_fetchargs_seen")):
        label = "pm-client-return-fetchargs-missing"
        reason = "PM client retcheck hits were present but return-value fetchargs were missing or unparsable"
    elif bool(details.get("pm_client_return_nonzero")):
        label = "pm-client-return-error"
        reason = "PM client register/connect return-value fetchargs reported a non-zero return"
    elif details["post_pm_lower_state_label"] == "stable-mdm3-offlining":
        label = "pm-client-return-success-still-offlining"
        reason = "PM client register/connect returns were zero while mdm3 remained OFFLINING with no MHI, WLFW service 69, or wlan0"
    else:
        label = "pm-client-return-lower-state-incomplete"
        reason = "PM client return fetchargs and lower-state samples did not match a fixed label"

    details["pm_client_return_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lower = gate.get("lower_observer", {})
    lines = [
        f"# Native Init {cycle} PM-client Return Fetchargs Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM-client return fetcharg discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- post-PM lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- PM-service projection label: `{gate.get('pm_service_devnode_projection_label')}`",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- return fetchargs seen/nonzero: `{gate.get('pm_client_return_fetchargs_seen')}` / `{gate.get('pm_client_return_nonzero')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## PM-client Return Values",
        "",
        f"- register rc: `{gate.get('pm_client_register_rc')}`",
        f"- connect rc: `{gate.get('pm_client_connect_rc')}`",
        f"- PM init return-path rc: `{gate.get('pm_init_return_path_rc')}`",
        *prev1806.render_event("pm_init_pm_client_register_retcheck", gate.get("pm_init_pm_client_register_retcheck", {})),
        *prev1806.render_event("pm_init_pm_client_connect_retcheck", gate.get("pm_init_pm_client_connect_retcheck", {})),
        *prev1806.render_event("pm_init_return_path", gate.get("pm_init_return_path", {})),
        "",
        "## Lower-state Samples",
        "",
        f"- sample total: `{gate.get('lower_sample_total')}`",
        f"- mdm3 states: `{gate.get('lower_mdm3_states')}`",
        f"- mdm status IRQ totals/increased: `{gate.get('lower_mdm_status_irq_totals')}` / `{gate.get('lower_mdm_status_irq_increased')}`",
        f"- MHI counts/pipes/present: `{gate.get('lower_mhi_device_counts')}` / `{gate.get('lower_mhi_pipe_exists')}` / `{gate.get('lower_mhi_present')}`",
        f"- wlan0 samples/present: `{gate.get('lower_wlan0_exists')}` / `{gate.get('lower_wlan0_present')}`",
        f"- WLFW service69 progress: `{gate.get('lower_service69_progress')}`",
        *prev1806.render_phase("after_holder_start", lower.get("after_holder_start", {})),
        *prev1806.render_phase("post_listener_window", lower.get("post_listener_window", {})),
        "",
        "## Route Health",
        "",
        f"- list commit hits: `{gate.get('pm_service_add_peripheral_list_commit_hits')}`",
        f"- PM register success hits: `{gate.get('pm_server_success_return_hits')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- Uploaded files/bytes: `{property_deploy.get('file_count')}` / `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.",
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; do not proceed to Wi-Fi HAL/scan/connect unless lower progress reaches WLFW/wlan0 readiness first.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    prev1796.runner.deploy_property_root = prev1796.deploy_property_root_serial
    prev1796.runner.classify_gate = classify_gate
    prev1796.runner.render_report = render_report
    rc = prev1796.runner.main(argv)
    prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
