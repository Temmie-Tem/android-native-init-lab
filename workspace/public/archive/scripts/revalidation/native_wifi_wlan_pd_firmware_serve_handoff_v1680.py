#!/usr/bin/env python3
"""V1680 corrected WLAN-PD firmware-serve modem-holder gate handoff."""

from __future__ import annotations

import native_wifi_wlan_pd_firmware_serve_handoff_v1675 as base


base.CYCLE = "V1680"
base.DEFAULT_SOURCE_MANIFEST = (
    base.REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1679-wlan-pd-firmware-serve-modem-holder-test-boot"
    / "manifest.json"
)
base.DEFAULT_OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1680-wlan-pd-firmware-serve-modem-holder-handoff"
base.DEFAULT_REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1680_WLAN_PD_FIRMWARE_SERVE_MODEM_HOLDER_HANDOFF_2026-06-02.md"
)
base.DEFAULT_TEST_IMAGE = (
    base.REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1679-wlan-pd-firmware-serve-modem-holder-test-boot"
    / "boot_linux_v1679_wlan_pd_firmware_serve_modem_holder.img"
)
base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.122 (v1679-wlan-pd-firmware-serve-modem-holder)"
base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1679.log"
base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1679.summary"
base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1679-helper.result"
base.DMESG_PATTERN = "A90v1679|wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|wlfw|icnss|FW ready|BDF|wlan0|4080000.qcom,mss|Brought out of reset|modem: loading"


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
