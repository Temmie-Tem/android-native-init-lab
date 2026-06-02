#!/usr/bin/env python3
"""V1740 one-run WLAN-PD cnss-daemon output-source visibility handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_property_lookup_handoff_v1691 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1740"
V1739_OUT = REPO_ROOT / "tmp" / "wifi" / "v1739-wlan-pd-cnss-output-source-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1739/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1740-wlan-pd-cnss-output-source-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1740_WLAN_PD_CNSS_OUTPUT_SOURCE_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.140 (v1739-wlan-pd-cnss-output-source)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1739.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1739.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1739-helper.result"
DMESG_PATTERN = (
    "A90v1739|wlan_pd_cnss_output_visibility|property_lookup|"
    "wlan_pd_cnss_nonlog_control_flow|wlan_pd_firmware_serve_gate|"
    "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)

ORIGINAL_CLASSIFY_GATE = base.classify_gate
ORIGINAL_RENDER_REPORT = base.render_report


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.base.CYCLE = CYCLE
    base.V1690_OUT = V1739_OUT
    base.base.V1687_OUT = V1739_OUT
    base.base.DEFAULT_SOURCE_MANIFEST = V1739_OUT / "manifest.json"
    base.base.DEFAULT_TEST_IMAGE = V1739_OUT / "boot_linux_v1739_wlan_pd_cnss_output_source.img"
    base.base.LOCAL_PROPERTY_ROOT = V1739_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.base.TEST_LOG_PATH = TEST_LOG_PATH
    base.base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.base.DMESG_PATTERN = DMESG_PATTERN
    base.V1690_OUT = V1739_OUT
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
    test_status = base.base.fwbase.read_text(evidence_dir, "test-status.stdout.txt")
    version_status_fallback_ok = args.expect_test_version in test_status
    label = str(details.get("label") or "")
    fixed_label = (
        label == "wlfw-start-reached-downstream-block"
        or label == "cnss-output-still-invisible"
        or label.startswith("cnss-init-step-failed-")
    )
    details.update({
        "version_status_fallback_ok": version_status_fallback_ok,
        "stdout_bytes": helper_fields.get("wlan_pd_cnss_output_visibility.stdout_bytes"),
        "stderr_bytes": helper_fields.get("wlan_pd_cnss_output_visibility.stderr_bytes"),
        "wlfw_start_source": helper_fields.get("wlan_pd_cnss_output_visibility.wlfw_start.source"),
        "wlfw_start_stdout_count": helper_fields.get("wlan_pd_cnss_output_visibility.wlfw_start.stdout_count"),
        "wlfw_start_stderr_count": helper_fields.get("wlan_pd_cnss_output_visibility.wlfw_start.stderr_count"),
        "wlfw_start_kmsg_count": helper_fields.get("wlan_pd_cnss_output_visibility.wlfw_start.kmsg_count"),
        "failure_nl_loop_stdout": helper_fields.get("wlan_pd_cnss_output_visibility.failure.nl_loop.stdout_count"),
        "failure_nl_loop_stderr": helper_fields.get("wlan_pd_cnss_output_visibility.failure.nl_loop.stderr_count"),
        "failure_nl_loop_kmsg": helper_fields.get("wlan_pd_cnss_output_visibility.failure.nl_loop.kmsg_count"),
        "failure_netlink_common_stdout": helper_fields.get("wlan_pd_cnss_output_visibility.failure.netlink_common.stdout_count"),
        "failure_netlink_common_stderr": helper_fields.get("wlan_pd_cnss_output_visibility.failure.netlink_common.stderr_count"),
        "failure_netlink_common_kmsg": helper_fields.get("wlan_pd_cnss_output_visibility.failure.netlink_common.kmsg_count"),
        "failure_wlan_service_stdout": helper_fields.get("wlan_pd_cnss_output_visibility.failure.wlan_service.stdout_count"),
        "failure_wlan_service_stderr": helper_fields.get("wlan_pd_cnss_output_visibility.failure.wlan_service.stderr_count"),
        "failure_wlan_service_kmsg": helper_fields.get("wlan_pd_cnss_output_visibility.failure.wlan_service.kmsg_count"),
        "failure_wlan_datapath_stdout": helper_fields.get("wlan_pd_cnss_output_visibility.failure.wlan_datapath_service.stdout_count"),
        "failure_wlan_datapath_stderr": helper_fields.get("wlan_pd_cnss_output_visibility.failure.wlan_datapath_service.stderr_count"),
        "failure_wlan_datapath_kmsg": helper_fields.get("wlan_pd_cnss_output_visibility.failure.wlan_datapath_service.kmsg_count"),
        "nonlog_contract_seen": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1",
        "nonlog_label": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label"),
        "nonlog_cnss_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "nonlog_fd_kmsg_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.kmsg_count"),
    })
    if (
        not pass_ok
        and decision == f"{args.cycle.lower()}-test-boot-version-missing"
        and version_status_fallback_ok
        and bool(test_flash.get("ok"))
        and bool(rollback_result.get("ok"))
        and details.get("helper_contract_seen")
        and details.get("label_ok")
    ):
        details["version_ok"] = True
        pass_ok = True
        decision = f"{args.cycle.lower()}-{label}-rollback-pass"
        reason = (
            "one cnss output-source gate run produced a fixed label, "
            "test-status contained the expected test boot version, and rollback verified"
        )
    if pass_ok and not fixed_label:
        return (
            f"{args.cycle.lower()}-cnss-output-source-label-missing",
            False,
            "helper result did not produce one of the fixed cnss output-source labels",
            details,
        )
    return decision, pass_ok, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    extra = "\n".join([
        "## Corrected Scope",
        "",
        "- This gate treats missing `wlfw_start` dmesg as a possible measurement artifact.",
        "- It does not add PM/service-window actors and does not start `boot_wlan`.",
        "- It reuses only the internal modem firmware-serve route: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "",
        "## Output-source Decision",
        "",
        f"- output label: `{gate.get('label')}`",
        f"- stdout/stderr bytes: `{gate.get('stdout_bytes')}` / `{gate.get('stderr_bytes')}`",
        f"- `wlfw_start` source: `{gate.get('wlfw_start_source')}`",
        f"- `wlfw_start` stdout/stderr/kmsg counts: `{gate.get('wlfw_start_stdout_count')}` / `{gate.get('wlfw_start_stderr_count')}` / `{gate.get('wlfw_start_kmsg_count')}`",
        f"- first init failure slug: `{gate.get('first_failure_slug')}`",
        f"- syslog available/errno/filtered: `{gate.get('syslog_available')}` / `{gate.get('syslog_errno')}` / `{gate.get('syslog_filtered_count')}`",
        f"- property lookup all_match: `{gate.get('property_lookup_all_match')}`",
        f"- kmsg_logging value/match: `{gate.get('property_lookup_kmsg_value')}` / `{gate.get('property_lookup_kmsg_match')}`",
        f"- debug_level value/match: `{gate.get('property_lookup_debug_value')}` / `{gate.get('property_lookup_debug_match')}`",
        "",
        "## Failure Source Counts",
        "",
        f"- `Failed to init nl_loop` stdout/stderr/kmsg: `{gate.get('failure_nl_loop_stdout')}` / `{gate.get('failure_nl_loop_stderr')}` / `{gate.get('failure_nl_loop_kmsg')}`",
        f"- `Failed to init netlink common` stdout/stderr/kmsg: `{gate.get('failure_netlink_common_stdout')}` / `{gate.get('failure_netlink_common_stderr')}` / `{gate.get('failure_netlink_common_kmsg')}`",
        f"- `Failed to start wlan service` stdout/stderr/kmsg: `{gate.get('failure_wlan_service_stdout')}` / `{gate.get('failure_wlan_service_stderr')}` / `{gate.get('failure_wlan_service_kmsg')}`",
        f"- `Failed to start wlan datapath service` stdout/stderr/kmsg: `{gate.get('failure_wlan_datapath_stdout')}` / `{gate.get('failure_wlan_datapath_stderr')}` / `{gate.get('failure_wlan_datapath_kmsg')}`",
        "",
        "## Non-log Supplemental Fields",
        "",
        f"- non-log contract seen: `{gate.get('nonlog_contract_seen')}`",
        f"- non-log label: `{gate.get('nonlog_label')}`",
        f"- cnss running: `{gate.get('nonlog_cnss_running')}`",
        f"- cnss kmsg fd count: `{gate.get('nonlog_fd_kmsg_count')}`",
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
