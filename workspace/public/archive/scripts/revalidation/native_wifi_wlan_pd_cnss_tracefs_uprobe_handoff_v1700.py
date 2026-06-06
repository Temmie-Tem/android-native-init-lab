#!/usr/bin/env python3
"""V1700 one-run WLAN-PD cnss-daemon tracefs-uprobe handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_property_lookup_handoff_v1691 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1700"
V1699_OUT = REPO_ROOT / "tmp" / "wifi" / "v1699-wlan-pd-cnss-tracefs-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1699/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1700-wlan-pd-cnss-tracefs-uprobe-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1700_WLAN_PD_CNSS_TRACEFS_UPROBE_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.127 (v1699-wlan-pd-cnss-tracefs-uprobe)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1699.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1699.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1699-helper.result"
DMESG_PATTERN = (
    "A90v1699|wlan_pd_cnss_nonlog_control_flow|uprobe|tracefs|"
    "wlan_pd_cnss_output_visibility|property_lookup|wlan_pd_firmware_serve_gate|"
    "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)
VALID_NONLOG_LABELS = {
    "cnss-process-exited-before-wlfw",
    "cnss-wlfw-entry-hit-downstream-wait",
    "cnss-wlfw-entry-not-hit-init-stall",
    "cnss-uprobe-unavailable-fallback-needed",
}

ORIGINAL_CLASSIFY_GATE = base.classify_gate
ORIGINAL_RENDER_REPORT = base.render_report


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.base.CYCLE = CYCLE
    base.V1690_OUT = V1699_OUT
    base.base.V1687_OUT = V1699_OUT
    base.base.DEFAULT_SOURCE_MANIFEST = V1699_OUT / "manifest.json"
    base.base.DEFAULT_TEST_IMAGE = V1699_OUT / "boot_linux_v1699_wlan_pd_cnss_tracefs_uprobe.img"
    base.base.LOCAL_PROPERTY_ROOT = V1699_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.base.TEST_LOG_PATH = TEST_LOG_PATH
    base.base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.base.DMESG_PATTERN = DMESG_PATTERN
    base.V1690_OUT = V1699_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = DMESG_PATTERN


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, pass_ok, reason, details = ORIGINAL_CLASSIFY_GATE(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = base.base.fwbase.parse_helper_fields(evidence_dir)
    nonlog_label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    nonlog_contract_seen = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1"
    nonlog_label_ok = nonlog_label in VALID_NONLOG_LABELS
    details.update({
        "nonlog_contract_seen": nonlog_contract_seen,
        "nonlog_label": nonlog_label,
        "nonlog_label_ok": nonlog_label_ok,
        "nonlog_mode": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.mode"),
        "nonlog_uprobe_attempted": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted"),
        "nonlog_tracefs_write_attempted": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs_write_attempted"),
        "nonlog_tracefs_available": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available"),
        "nonlog_tracefs_path": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.path"),
        "nonlog_uprobe_register_rc": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.register_rc"),
        "nonlog_uprobe_registered": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.registered"),
        "nonlog_uprobe_enable_rc": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.enable_rc"),
        "nonlog_uprobe_enabled": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.enabled"),
        "nonlog_uprobe_hit_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count"),
        "nonlog_uprobe_first_hit_line": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.first_hit_line"),
        "nonlog_uprobe_cleanup_done": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.cleanup_done"),
        "nonlog_cnss_pid": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_pid"),
        "nonlog_cnss_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "nonlog_maps_text_seen": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.maps.text_seen"),
        "nonlog_wlfw_start_pc": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.runtime.wlfw_start_pc"),
        "nonlog_socket_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.socket_count"),
        "nonlog_kmsg_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.kmsg_count"),
        "nonlog_mhi_pipe_fd_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.global.mhi_pipe_fd_count"),
        "nonlog_ks_process_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.global.ks_process_count"),
        "nonlog_no_service_manager": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.service_manager"),
        "nonlog_no_pm_trio": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.pm_trio"),
        "nonlog_no_boot_wlan": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.boot_wlan"),
        "nonlog_no_esoc0": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.subsys_esoc0"),
        "nonlog_no_forced_rc1": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.forced_rc1"),
        "nonlog_no_wifi_hal": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.wifi_hal"),
        "nonlog_no_scan_connect": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.scan_connect"),
        "nonlog_no_credentials": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.credentials"),
        "nonlog_no_dhcp_routes": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.dhcp_routes"),
        "nonlog_no_external_ping": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.external_ping"),
    })
    if not pass_ok:
        return decision, pass_ok, reason, details
    if not nonlog_contract_seen:
        return (
            f"{args.cycle.lower()}-cnss-tracefs-uprobe-contract-missing",
            False,
            "helper result did not include cnss tracefs/non-log contract",
            details,
        )
    if not nonlog_label_ok:
        return (
            f"{args.cycle.lower()}-cnss-tracefs-uprobe-label-missing",
            False,
            "helper result did not produce a fixed cnss tracefs/non-log label",
            details,
        )
    return (
        f"{args.cycle.lower()}-{nonlog_label}-rollback-pass",
        True,
        reason + f"; nonlog_label={nonlog_label}",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    base_text = ORIGINAL_RENDER_REPORT(result)
    base_text = base_text.replace(
        "# Native Init V1700 WLAN-PD cnss-daemon Output Visibility Handoff",
        "# Native Init V1700 WLAN-PD cnss-daemon Tracefs Uprobe Handoff",
    )
    base_text = base_text.replace(
        "- Type: one-run rollbackable WLAN-PD cnss-daemon output-visibility gate",
        "- Type: one-run rollbackable WLAN-PD cnss-daemon tracefs uprobe/non-log gate",
    )
    extra = "\n".join([
        "## Tracefs / Non-log Control Flow",
        "",
        f"- contract seen: `{gate.get('nonlog_contract_seen')}`",
        f"- label: `{gate.get('nonlog_label')}`",
        f"- mode: `{gate.get('nonlog_mode')}`",
        f"- tracefs path/available: `{gate.get('nonlog_tracefs_path')}` / `{gate.get('nonlog_tracefs_available')}`",
        f"- uprobe register rc/registered: `{gate.get('nonlog_uprobe_register_rc')}` / `{gate.get('nonlog_uprobe_registered')}`",
        f"- uprobe enable rc/enabled: `{gate.get('nonlog_uprobe_enable_rc')}` / `{gate.get('nonlog_uprobe_enabled')}`",
        f"- uprobe hit count: `{gate.get('nonlog_uprobe_hit_count')}`",
        f"- first hit line: `{gate.get('nonlog_uprobe_first_hit_line')}`",
        f"- cleanup done: `{gate.get('nonlog_uprobe_cleanup_done')}`",
        f"- cnss pid/running: `{gate.get('nonlog_cnss_pid')}` / `{gate.get('nonlog_cnss_running')}`",
        f"- maps text seen / runtime PC: `{gate.get('nonlog_maps_text_seen')}` / `{gate.get('nonlog_wlfw_start_pc')}`",
        f"- socket/kmsg fd counts: `{gate.get('nonlog_socket_count')}` / `{gate.get('nonlog_kmsg_count')}`",
        f"- MHI pipe fd count / ks process count: `{gate.get('nonlog_mhi_pipe_fd_count')}` / `{gate.get('nonlog_ks_process_count')}`",
        "",
        "## Interpretation",
        "",
        "- V1700 is a one-run classifier for stock `cnss-daemon+0xec00` entry, not a Wi-Fi HAL or connect attempt.",
        "- A `cnss-wlfw-entry-hit-downstream-wait` label means stock `cnss-daemon` did reach `wlfw_start`, so the blocker moves downstream to WLAN-PD/WLFW service publication.",
        "- A `cnss-wlfw-entry-not-hit-init-stall` label means stock `cnss-daemon` stayed alive but did not enter `wlfw_start` during the bounded window.",
        "- `cnss-uprobe-unavailable-fallback-needed` means this boot could not use tracefs/uprobe and only `/proc` fallback evidence is available.",
        "",
    ])
    return base_text + "\n" + extra


def main(argv: list[str] | None = None) -> int:
    configure_base()
    base.base.classify_gate = classify_gate
    base.base.render_report = render_report
    return base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
