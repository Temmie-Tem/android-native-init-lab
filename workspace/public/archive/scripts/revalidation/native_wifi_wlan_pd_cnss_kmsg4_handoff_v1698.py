#!/usr/bin/env python3
"""V1698 one-run WLAN-PD cnss-daemon kmsg4 output-visibility handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_output_visibility_handoff_v1695 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1698"
V1697_OUT = REPO_ROOT / "tmp" / "wifi" / "v1697-wlan-pd-cnss-kmsg4-output-visibility-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1697/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1698-wlan-pd-cnss-kmsg4-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1698_WLAN_PD_CNSS_KMSG4_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.126 (v1697-wlan-pd-cnss-kmsg4-output-visibility)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1697.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1697.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1697-helper.result"
DMESG_PATTERN = (
    "A90v1697|wlan_pd_cnss_output_visibility|property_lookup|"
    "wlan_pd_cnss_nonlog_control_flow|wlan_pd_firmware_serve_gate|"
    "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)


ORIGINAL_RENDER_REPORT = base.render_report
ORIGINAL_CONFIGURE_BASE = base.configure_base


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.V1693_OUT = V1697_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = DMESG_PATTERN
    ORIGINAL_CONFIGURE_BASE()
    base.base.base.DEFAULT_TEST_IMAGE = V1697_OUT / "boot_linux_v1697_wlan_pd_cnss_kmsg4_output_visibility.img"


def render_report(result: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_REPORT(result)
    text = text.replace("V1695", "V1698")
    text = text.replace("V1693", "V1697")
    text = text.replace("v1695", "v1698")
    text = text.replace("v1693", "v1697")
    text += "\n".join([
        "",
        "## V1698 kmsg4 Scope",
        "",
        "- Reuses the V1680 internal-modem firmware-serve route and V1695 rollback/status fallback logic.",
        "- Uses V1697 property runtime with `persist.vendor.cnss-daemon.kmsg_logging=4` and `debug_level=4`.",
        "- One run fixes one label: `wlfw-start-reached-downstream-block`, `cnss-init-step-failed-<name>`, or `cnss-output-still-invisible`.",
        "- Keeps PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping disabled.",
        "",
        "## V1698 Interpretation",
        "",
        "- If the label remains `cnss-output-still-invisible` while property lookup reports `kmsg_logging=4` and `debug_level=4`, the V1696 threshold gap is closed.",
        "- That result does not justify adding PM/service-window actors or `boot_wlan`; it justifies a bounded non-log proof for whether stock `cnss-daemon` reaches `wlfw_start`.",
        "",
    ])
    return text


def main(argv: list[str] | None = None) -> int:
    base.configure_base = configure_base
    base.render_report = render_report
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
