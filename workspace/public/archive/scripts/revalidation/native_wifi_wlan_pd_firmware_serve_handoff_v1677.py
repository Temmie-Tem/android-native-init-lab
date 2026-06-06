#!/usr/bin/env python3
"""V1677 corrected one-run WLAN-PD firmware-serve gate handoff."""

from __future__ import annotations

from pathlib import Path

import native_wifi_wlan_pd_firmware_serve_handoff_v1675 as base


base.CYCLE = "V1677"
base.DEFAULT_SOURCE_MANIFEST = (
    base.REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1676-wlan-pd-firmware-serve-gate-corrected-test-boot"
    / "manifest.json"
)
base.DEFAULT_OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1677-wlan-pd-firmware-serve-gate-corrected-handoff"
base.DEFAULT_REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1677_WLAN_PD_FIRMWARE_SERVE_GATE_CORRECTED_HANDOFF_2026-06-02.md"
)
base.DEFAULT_TEST_IMAGE = (
    base.REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1676-wlan-pd-firmware-serve-gate-corrected-test-boot"
    / "boot_linux_v1676_wlan_pd_firmware_serve_gate_corrected.img"
)
base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.121 (v1676-wlan-pd-firmware-serve-gate-corrected)"
base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1676.log"
base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1676.summary"
base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1676-helper.result"
base.DMESG_PATTERN = "A90v1676|wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|wlfw|icnss|FW ready|BDF|wlan0"


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
