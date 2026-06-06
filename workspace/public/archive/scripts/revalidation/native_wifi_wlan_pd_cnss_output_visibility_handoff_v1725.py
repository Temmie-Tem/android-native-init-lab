#!/usr/bin/env python3
"""V1725 one-run corrected WLAN-PD cnss-daemon output-visibility handoff."""

from __future__ import annotations

import re
from pathlib import Path

import native_wifi_wlan_pd_cnss_output_visibility_handoff_v1688 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1725"
V1724_OUT = REPO_ROOT / "tmp" / "wifi" / "v1724-cnss-output-visible-route-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1724/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1725-cnss-output-visible-route-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1725_CNSS_OUTPUT_VISIBLE_ROUTE_HANDOFF_2026-06-03.md"
)

SENSITIVE_VERSION_CREATOR_RE = re.compile(r"(made by )[^\s\r\n]+")
ORIGINAL_CLASSIFY_GATE = prev.classify_gate
ORIGINAL_RENDER_REPORT = prev.render_report


def configure_base() -> None:
    prev.CYCLE = CYCLE
    prev.V1687_OUT = V1724_OUT
    prev.DEFAULT_SOURCE_MANIFEST = V1724_OUT / "manifest.json"
    prev.DEFAULT_TEST_IMAGE = V1724_OUT / "boot_linux_v1724_cnss_output_visible_route.img"
    prev.LOCAL_PROPERTY_ROOT = V1724_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev.TEST_EXPECT_VERSION = "A90 Linux init 0.9.135 (v1724-cnss-output-visible-route)"
    prev.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1724.log"
    prev.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1724.summary"
    prev.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1724-helper.result"
    prev.DMESG_PATTERN = (
        "A90v1724|wlan_pd_cnss_output_visibility|wlan_pd_firmware_serve_gate|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
        "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
        "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
    )


def sanitize_evidence_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sanitized = SENSITIVE_VERSION_CREATOR_RE.sub(r"\1[redacted]", text)
        if sanitized != text:
            item.write_text(sanitized, encoding="utf-8")


def classify_gate(*args: object, **kwargs: object) -> tuple[str, bool, str, dict[str, object]]:
    decision, pass_ok, reason, gate = ORIGINAL_CLASSIFY_GATE(*args, **kwargs)
    evidence_dir = args[3] if len(args) >= 4 else kwargs.get("evidence_dir")
    if isinstance(evidence_dir, Path):
        helper_fields = prev.fwbase.parse_helper_fields(evidence_dir)
        gate.update({
            "property_lookup_all_match": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.all_match"),
            "kmsg_logging_expected": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.kmsg_logging.expected"),
            "kmsg_logging_value": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.kmsg_logging.value"),
            "kmsg_logging_match": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.kmsg_logging.match"),
            "debug_level_expected": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.debug_level.expected"),
            "debug_level_value": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.debug_level.value"),
            "debug_level_match": helper_fields.get("wlan_pd_cnss_output_visibility.property_lookup.debug_level.match"),
            "nonlog_contract_seen": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.begin"),
            "nonlog_label": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label"),
            "nonlog_maps_text_seen": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.maps.text_seen"),
            "nonlog_tracefs_available": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available"),
            "nonlog_tracefs_errno": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.errno"),
            "nonlog_fd_vndbinder_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.vndbinder_count"),
            "nonlog_fd_kmsg_count": helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fd.kmsg_count"),
        })
    return decision, pass_ok, reason, gate


def render_report(result: dict[str, object]) -> str:
    text = ORIGINAL_RENDER_REPORT(result)
    gate = result.get("gate", {})
    if not isinstance(gate, dict):
        return text
    extra = "\n".join([
        "## Property Lookup",
        "",
        f"- `persist.vendor.cnss-daemon.kmsg_logging`: expected `{gate.get('kmsg_logging_expected')}`, value `{gate.get('kmsg_logging_value')}`, match `{gate.get('kmsg_logging_match')}`",
        f"- `persist.vendor.cnss-daemon.debug_level`: expected `{gate.get('debug_level_expected')}`, value `{gate.get('debug_level_value')}`, match `{gate.get('debug_level_match')}`",
        f"- all property lookups matched: `{gate.get('property_lookup_all_match')}`",
        "",
        "## Supplemental Fields",
        "",
        f"- non-log helper contract: `{gate.get('nonlog_contract_seen')}`",
        f"- cnss-daemon maps text seen: `{gate.get('nonlog_maps_text_seen')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tracefs available: `{gate.get('nonlog_tracefs_available')}` (`errno={gate.get('nonlog_tracefs_errno')}`)",
        f"- cnss-daemon fd counts: `vndbinder={gate.get('nonlog_fd_vndbinder_count')}`, `kmsg={gate.get('nonlog_fd_kmsg_count')}`",
        f"- non-log fallback label: `{gate.get('nonlog_label')}`",
        "",
        "## Interpretation",
        "",
        "- The corrected kmsg property contract is consumed in the same namespace, but no `wlfw_start: Starting` line or pre-WLFW `Failed to ...` string reaches kmsg/stdout/stderr.",
        "- This run fixes the old helper expectation mismatch (`kmsg_logging=4` vs actual `1`) and still returns `cnss-output-still-invisible`.",
        "- This is an output visibility result only. It does not justify adding PM/service-window actors, `boot_wlan`, eSoC/RC1, or Wi-Fi HAL work inside this gate.",
        "",
    ])
    return text.replace("## Safety Scope", extra + "\n## Safety Scope")


def main(argv: list[str] | None = None) -> int:
    configure_base()
    prev.classify_gate = classify_gate
    prev.render_report = render_report
    rc = prev.main(argv)
    sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
