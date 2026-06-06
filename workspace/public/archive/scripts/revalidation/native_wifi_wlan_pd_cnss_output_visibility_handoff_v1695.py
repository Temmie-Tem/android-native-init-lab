#!/usr/bin/env python3
"""V1695 one-run WLAN-PD cnss-daemon output-visibility handoff.

This wrapper reuses the V1693 test boot artifact because it already preserves
the V1680 internal-modem firmware-serve route, sets the cnss-daemon logging
properties in the private property runtime, and emits both output-visibility
and read-only non-log fallback fields.  V1695 intentionally classifies the run
by the output-visibility label, not by the non-log fallback label.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_property_lookup_handoff_v1691 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1695"
V1693_OUT = REPO_ROOT / "tmp" / "wifi" / "v1693-wlan-pd-cnss-nonlog-control-flow-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1693/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1695-wlan-pd-cnss-output-visibility-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1695_WLAN_PD_CNSS_OUTPUT_VISIBILITY_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.125 (v1693-wlan-pd-cnss-nonlog-control-flow)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1693.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1693.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1693-helper.result"
DMESG_PATTERN = (
    "A90v1693|wlan_pd_cnss_output_visibility|property_lookup|"
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
    decision, pass_ok, reason, details = ORIGINAL_CLASSIFY_GATE(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = base.base.fwbase.parse_helper_fields(evidence_dir)
    test_status = base.base.fwbase.read_text(evidence_dir, "test-status.stdout.txt")
    version_status_fallback_ok = args.expect_test_version in test_status
    details.update({
        "version_status_fallback_ok": version_status_fallback_ok,
        "nonlog_contract_seen": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin") == "1",
        "nonlog_label": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label"),
        "nonlog_cnss_running": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.cnss_daemon_running"),
        "nonlog_wlfw_start_pc": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.runtime.wlfw_start_pc"),
        "nonlog_socket_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.socket_count"),
        "nonlog_kmsg_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.kmsg_count"),
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
        label = details.get("label", "")
        details["version_ok"] = True
        return (
            f"{args.cycle.lower()}-{label}-rollback-pass",
            True,
            "one cnss output visibility gate run produced a fixed label, "
            "test-status contained the expected test boot version, and rollback verified",
            details,
        )
    return decision, pass_ok, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    extra = "\n".join([
        "## Latest Correction Scope",
        "",
        "- V1695 treats missing `wlfw_start` logs as an output-measurement question, not proof that `cnss-daemon` skipped `wlfw_start`.",
        "- The only live route is the internal modem firmware-serve route: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain disabled.",
        "",
        "## Output Visibility Decision",
        "",
        f"- output label: `{gate.get('label')}`",
        f"- version status fallback ok: `{gate.get('version_status_fallback_ok')}`",
        f"- `wlfw_start` seen: `{gate.get('wlfw_start_seen')}`",
        f"- first init failure slug: `{gate.get('first_failure_slug')}`",
        f"- syslog available/errno/filtered: `{gate.get('syslog_available')}` / `{gate.get('syslog_errno')}` / `{gate.get('syslog_filtered_count')}`",
        f"- property lookup all_match: `{gate.get('property_lookup_all_match')}`",
        f"- kmsg_logging value/match: `{gate.get('property_lookup_kmsg_value')}` / `{gate.get('property_lookup_kmsg_match')}`",
        f"- debug_level value/match: `{gate.get('property_lookup_debug_value')}` / `{gate.get('property_lookup_debug_match')}`",
        "",
        "## Non-log Supplemental Fields",
        "",
        f"- non-log contract seen: `{gate.get('nonlog_contract_seen')}`",
        f"- non-log label: `{gate.get('nonlog_label')}`",
        f"- cnss running: `{gate.get('nonlog_cnss_running')}`",
        f"- computed `wlfw_start` PC: `{gate.get('nonlog_wlfw_start_pc')}`",
        f"- socket/kmsg fd counts: `{gate.get('nonlog_socket_count')}` / `{gate.get('nonlog_kmsg_count')}`",
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
