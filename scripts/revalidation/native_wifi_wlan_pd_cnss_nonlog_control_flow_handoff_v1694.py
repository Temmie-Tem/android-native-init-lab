#!/usr/bin/env python3
"""V1694 one-run WLAN-PD cnss-daemon non-log control-flow handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_property_lookup_handoff_v1691 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1694"
V1693_OUT = REPO_ROOT / "tmp" / "wifi" / "v1693-wlan-pd-cnss-nonlog-control-flow-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1693/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1694-wlan-pd-cnss-nonlog-control-flow-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1694_WLAN_PD_CNSS_NONLOG_CONTROL_FLOW_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.125 (v1693-wlan-pd-cnss-nonlog-control-flow)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1693.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1693.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1693-helper.result"
DMESG_PATTERN = (
    "A90v1693|wlan_pd_cnss_nonlog_control_flow|"
    "wlan_pd_cnss_output_visibility|property_lookup|wlan_pd_firmware_serve_gate|"
    "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)
VALID_NONLOG_LABELS = {
    "cnss-process-exited-before-wlfw",
    "cnss-uprobe-unavailable-fallback-needed",
}

ORIGINAL_CLASSIFY_GATE = base.classify_gate
ORIGINAL_RENDER_REPORT = base.render_report


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.base.CYCLE = CYCLE
    base.V1690_OUT = V1693_OUT
    base.base.V1687_OUT = V1693_OUT
    base.base.DEFAULT_SOURCE_MANIFEST = V1693_OUT / "manifest.json"
    base.base.DEFAULT_TEST_IMAGE = V1693_OUT / "boot_linux_v1693_wlan_pd_cnss_nonlog_control_flow.img"
    base.base.LOCAL_PROPERTY_ROOT = V1693_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.base.TEST_LOG_PATH = TEST_LOG_PATH
    base.base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.base.DMESG_PATTERN = DMESG_PATTERN
    base.V1690_OUT = V1693_OUT
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
    decision, pass_ok, reason, details = ORIGINAL_CLASSIFY_GATE(args, test_flash, rollback_result, evidence_dir)
    helper_fields = base.base.fwbase.parse_helper_fields(evidence_dir)
    nonlog_label = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    nonlog_contract_seen = helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1"
    nonlog_label_ok = nonlog_label in VALID_NONLOG_LABELS
    details.update({
        "nonlog_contract_seen": nonlog_contract_seen,
        "nonlog_label": nonlog_label,
        "nonlog_label_ok": nonlog_label_ok,
        "nonlog_uprobe_attempted": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted"),
        "nonlog_tracefs_write_attempted": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs_write_attempted"),
        "nonlog_cnss_pid": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_pid"),
        "nonlog_cnss_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "nonlog_cnss_process_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.process_scan.cnss_daemon_count"),
        "nonlog_maps_text_seen": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.maps.text_seen"),
        "nonlog_wlfw_start_pc": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.runtime.wlfw_start_pc"),
        "nonlog_socket_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.socket_count"),
        "nonlog_vndbinder_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.vndbinder_count"),
        "nonlog_kmsg_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.kmsg_count"),
        "nonlog_mhi_pipe_fd_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.global.mhi_pipe_fd_count"),
        "nonlog_ks_process_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.global.ks_process_count"),
        "nonlog_no_service_manager": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.service_manager"),
        "nonlog_no_pm_trio": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.pm_trio"),
        "nonlog_no_boot_wlan": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.boot_wlan"),
        "nonlog_no_esoc0": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.subsys_esoc0"),
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
            f"{args.cycle.lower()}-cnss-nonlog-contract-missing",
            False,
            "helper result did not include cnss non-log control-flow contract",
            details,
        )
    if not nonlog_label_ok:
        return (
            f"{args.cycle.lower()}-cnss-nonlog-label-missing",
            False,
            "helper result did not produce a fixed cnss non-log label",
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
    extra = "\n".join([
        "## Non-log Control Flow",
        "",
        f"- contract seen: `{gate.get('nonlog_contract_seen')}`",
        f"- non-log label: `{gate.get('nonlog_label')}`",
        f"- uprobe attempted: `{gate.get('nonlog_uprobe_attempted')}`",
        f"- tracefs write attempted: `{gate.get('nonlog_tracefs_write_attempted')}`",
        f"- cnss pid/running: `{gate.get('nonlog_cnss_pid')}` / `{gate.get('nonlog_cnss_running')}`",
        f"- cnss process count: `{gate.get('nonlog_cnss_process_count')}`",
        f"- maps text seen: `{gate.get('nonlog_maps_text_seen')}`",
        f"- computed `wlfw_start` PC: `{gate.get('nonlog_wlfw_start_pc')}`",
        f"- socket/vndbinder/kmsg fd counts: `{gate.get('nonlog_socket_count')}` / `{gate.get('nonlog_vndbinder_count')}` / `{gate.get('nonlog_kmsg_count')}`",
        f"- MHI pipe fd count / ks process count: `{gate.get('nonlog_mhi_pipe_fd_count')}` / `{gate.get('nonlog_ks_process_count')}`",
        "",
        "## Interpretation",
        "",
        "- V1694 does not rely on Android log output. It records stock `cnss-daemon` liveness, maps load-bias, computed `wlfw_start` runtime PC, fd/socket surface, task state, and MHI/ks absence.",
        "- `cnss-uprobe-unavailable-fallback-needed` means the read-only `/proc` fallback is valid evidence of liveness/stall, but it does not prove whether `cnss-daemon+0xec00` was entered.",
        "- Do not add PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping from this label alone.",
        "",
    ])
    return ORIGINAL_RENDER_REPORT(result) + "\n" + extra


def main(argv: list[str] | None = None) -> int:
    configure_base()
    base.base.classify_gate = classify_gate
    base.base.render_report = render_report
    return base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
