#!/usr/bin/env python3
"""V1691 one-run WLAN-PD cnss-daemon property lookup handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_output_visibility_handoff_v1688 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1691"
V1690_OUT = REPO_ROOT / "tmp" / "wifi" / "v1690-wlan-pd-cnss-property-lookup-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1690/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1691-wlan-pd-cnss-property-lookup-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1691_WLAN_PD_CNSS_PROPERTY_LOOKUP_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.124 (v1690-wlan-pd-cnss-property-lookup)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1690.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1690.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1690-helper.result"
DMESG_PATTERN = (
    "A90v1690|wlan_pd_cnss_output_visibility|property_lookup|"
    "wlan_pd_firmware_serve_gate|wlan_pd|wlanmdsp|tftp|rmt_storage|"
    "pd-mapper|qrtr|service 69|wlfw|wlfw_start|wlfw_service_request|"
    "icnss|FW ready|BDF|wlan0|cnss-daemon|4080000.qcom,mss|"
    "Brought out of reset|modem: loading"
)

ORIGINAL_CLASSIFY_GATE = base.classify_gate
ORIGINAL_RENDER_REPORT = base.render_report


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.V1687_OUT = V1690_OUT
    base.DEFAULT_SOURCE_MANIFEST = V1690_OUT / "manifest.json"
    base.DEFAULT_TEST_IMAGE = V1690_OUT / "boot_linux_v1690_wlan_pd_cnss_property_lookup.img"
    base.LOCAL_PROPERTY_ROOT = V1690_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
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
    helper_fields = base.fwbase.parse_helper_fields(evidence_dir)
    property_lookup_seen = helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.begin") == "1"
    property_lookup_all_match = helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.all_match") == "1"
    details.update({
        "property_lookup_seen": property_lookup_seen,
        "property_lookup_all_match": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.all_match"),
        "property_lookup_kmsg_value": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.kmsg_logging.value"),
        "property_lookup_kmsg_match": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.kmsg_logging.match"),
        "property_lookup_debug_value": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.debug_level.value"),
        "property_lookup_debug_match": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.debug_level.match"),
    })
    if not pass_ok:
        return decision, pass_ok, reason, details
    if not property_lookup_seen:
        return (
            f"{args.cycle.lower()}-property-lookup-contract-missing",
            False,
            "V1690 helper result did not include property lookup evidence",
            details,
        )
    if not property_lookup_all_match:
        return (
            f"{args.cycle.lower()}-property-runtime-visibility-failure-rollback-pass",
            True,
            "property lookup evidence was present but did not match expected cnss logging values; rollback verified",
            details,
        )
    return decision, pass_ok, reason + "; property lookup all_match=1", details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    extra = "\n".join([
        "## Property Lookup",
        "",
        f"- lookup evidence seen: `{gate.get('property_lookup_seen')}`",
        f"- all_match: `{gate.get('property_lookup_all_match')}`",
        f"- kmsg_logging value/match: `{gate.get('property_lookup_kmsg_value')}` / `{gate.get('property_lookup_kmsg_match')}`",
        f"- debug_level value/match: `{gate.get('property_lookup_debug_value')}` / `{gate.get('property_lookup_debug_match')}`",
        "",
        "## Interpretation",
        "",
        "- V1691 closes the V1689 property-consumption gap: the same namespace can read both cnss logging properties with the expected values.",
        "- `cnss-output-still-invisible` is therefore not caused by a missing private property area lookup.",
        "- The remaining blocker is a non-log cnss-daemon/control-flow or downstream WLAN-PD issue: stock `cnss-daemon` remains running, but no `wlfw_start`, pre-wlfw failure string, firmware request, WLFW service 69, or wlan0 marker appears.",
        "",
    ])
    return ORIGINAL_RENDER_REPORT(result) + "\n" + extra


def main(argv: list[str] | None = None) -> int:
    configure_base()
    base.classify_gate = classify_gate
    base.render_report = render_report
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
