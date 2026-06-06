#!/usr/bin/env python3
"""V1744 one-run WLAN-PD pure-route non-log parity handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_output_source_handoff_v1740 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1744"
V1743_OUT = REPO_ROOT / "tmp" / "wifi" / "v1743-wlan-pd-pure-nonlog-parity-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1743/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1744-wlan-pd-pure-nonlog-parity-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1744_WLAN_PD_PURE_NONLOG_PARITY_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.141 (v1743-wlan-pd-pure-nonlog-parity)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1743.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1743.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1743-helper.result"
DMESG_PATTERN = (
    "A90v1743|wlan_pd_cnss_output_visibility|property_lookup|"
    "wlan_pd_cnss_nonlog_control_flow|wlan_pd_firmware_serve_gate|"
    "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)

WLFW_REACHED_PREFIXES = (
    "wlfw-",
    "pm-init-",
)
WLFW_REACHED_LABELS = {
    "peripheral-register-returned",
    "peripheral-success-path-no-return",
    "peripheral-manager-register-transaction-returned",
    "peripheral-manager-register-transaction-call-no-return",
    "peripheral-as-interface-no-register-transaction",
    "peripheral-service-lookup-returned-no-interface",
    "peripheral-service-manager-get-call-no-return",
    "peripheral-service-name-built-no-get",
    "peripheral-default-service-manager-call-no-return",
    "peripheral-vndbinder-init-call-no-return",
    "peripheral-register-connect-entry-no-vndbinder-init",
    "peripheral-client-register-entry-no-connect-entry",
}


def configure_base() -> None:
    prev.CYCLE = CYCLE
    prev.V1739_OUT = V1743_OUT
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev.TEST_LOG_PATH = TEST_LOG_PATH
    prev.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev.DMESG_PATTERN = DMESG_PATTERN
    prev.configure_base()
    prev.base.base.DEFAULT_SOURCE_MANIFEST = V1743_OUT / "manifest.json"
    prev.base.base.DEFAULT_TEST_IMAGE = V1743_OUT / "boot_linux_v1743_wlan_pd_pure_nonlog_parity.img"


def is_true(value: object) -> bool:
    return str(value) == "1"


def intish(value: object) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def nonlog_reached_wlfw(helper_fields: dict[str, str]) -> bool:
    label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    hit_count = intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count"))
    if hit_count > 0:
        return True
    if label in WLFW_REACHED_LABELS:
        return True
    return any(label.startswith(prefix) for prefix in WLFW_REACHED_PREFIXES)


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, pass_ok, reason, details = prev.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = prev.base.base.fwbase.parse_helper_fields(evidence_dir)
    nonlog_contract_seen = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1"
    tracefs_available = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available")
    uprobe_attempted = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted")
    uprobe_register_attempted = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.register_attempted")
    nonlog_label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    output_label = helper_fields.get("wlan_pd_cnss_output_visibility.label", "")
    route_safety_ok = all([
        helper_fields.get("wlan_pd_cnss_output_visibility.no_service_manager") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_pm_trio") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_esoc0") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_forced_rc1") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_fake_online") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_wifi_hal") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_scan_connect") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_credentials") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_dhcp_routes") == "1",
        helper_fields.get("wlan_pd_cnss_output_visibility.no_external_ping") == "1",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.service_manager") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.pm_trio") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.boot_wlan") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.subsys_esoc0") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.forced_rc1") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fake_online") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.wifi_hal") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.scan_connect") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.credentials") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.dhcp_routes") == "0",
        helper_fields.get("wlan_pd_cnss_nonlog_control_flow.external_ping") == "0",
    ])
    reached_wlfw = nonlog_reached_wlfw(helper_fields)
    details.update({
        "v1744_output_label": output_label,
        "v1744_nonlog_contract_seen": nonlog_contract_seen,
        "v1744_tracefs_available": tracefs_available,
        "v1744_tracefs_path": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.path"),
        "v1744_tracefs_errno": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.errno"),
        "v1744_uprobe_attempted": uprobe_attempted,
        "v1744_uprobe_register_attempted": uprobe_register_attempted,
        "v1744_uprobe_register_rc": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.register_rc"),
        "v1744_uprobe_registered": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.registered"),
        "v1744_uprobe_enabled": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.enabled"),
        "v1744_uprobe_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count"),
        "v1744_nonlog_label": nonlog_label,
        "v1744_reached_wlfw": reached_wlfw,
        "v1744_route_safety_ok": route_safety_ok,
    })
    if not pass_ok:
        return decision, pass_ok, reason, details
    if not nonlog_contract_seen:
        return (
            f"{args.cycle.lower()}-nonlog-contract-missing",
            False,
            "helper result did not include the non-log control-flow contract",
            details,
        )
    if not route_safety_ok:
        return (
            f"{args.cycle.lower()}-route-safety-violation",
            False,
            "helper result indicates an excluded actor or action was used",
            details,
        )
    if not is_true(tracefs_available) or not is_true(uprobe_attempted) or not is_true(uprobe_register_attempted):
        label = "tracefs-surface-unavailable"
    elif reached_wlfw:
        label = "pure-route-nonlog-wlfw-start"
    else:
        label = "pure-route-nonlog-no-wlfw-start"
    details["v1744_label"] = label
    return (
        f"{args.cycle.lower()}-{label}-rollback-pass",
        True,
        "one pure-route non-log parity run produced a fixed label and rollback verified",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    lines = [
        "# Native Init V1744 WLAN-PD Pure-route Non-log Parity Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1744`",
        "- Type: one-run rollbackable pure-route non-log parity gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Non-log Parity Decision",
        "",
        f"- V1744 label: `{gate.get('v1744_label')}`",
        f"- output label: `{gate.get('v1744_output_label')}`",
        f"- non-log label: `{gate.get('v1744_nonlog_label')}`",
        f"- non-log contract seen: `{gate.get('v1744_nonlog_contract_seen')}`",
        f"- tracefs available/path/errno: `{gate.get('v1744_tracefs_available')}` / `{gate.get('v1744_tracefs_path')}` / `{gate.get('v1744_tracefs_errno')}`",
        f"- uprobe attempted/register rc/enabled/hits: `{gate.get('v1744_uprobe_attempted')}` / `{gate.get('v1744_uprobe_register_rc')}` / `{gate.get('v1744_uprobe_enabled')}` / `{gate.get('v1744_uprobe_hit_count')}`",
        f"- reached wlfw by non-log evidence: `{gate.get('v1744_reached_wlfw')}`",
        f"- route safety ok: `{gate.get('v1744_route_safety_ok')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Uploaded files: `{property_deploy.get('file_count')}`",
        f"- Uploaded bytes: `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Output-source Supplemental Fields",
        "",
        f"- stdout/stderr bytes: `{gate.get('stdout_bytes')}` / `{gate.get('stderr_bytes')}`",
        f"- `wlfw_start` source: `{gate.get('wlfw_start_source')}`",
        f"- `wlfw_start` stdout/stderr/kmsg counts: `{gate.get('wlfw_start_stdout_count')}` / `{gate.get('wlfw_start_stderr_count')}` / `{gate.get('wlfw_start_kmsg_count')}`",
        f"- first init failure slug: `{gate.get('first_failure_slug')}`",
        f"- syslog available/errno/filtered: `{gate.get('syslog_available')}` / `{gate.get('syslog_errno')}` / `{gate.get('syslog_filtered_count')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Interpretation",
        "",
        "- This gate uses the V1743 artifact to close the V1740 tracefs measurement gap on the pure internal-modem route.",
        "- It does not add service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- One live run sets one label; stop and classify before adding actors.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_base()
    prev.base.base.classify_gate = classify_gate
    prev.base.base.render_report = render_report
    return prev.base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
