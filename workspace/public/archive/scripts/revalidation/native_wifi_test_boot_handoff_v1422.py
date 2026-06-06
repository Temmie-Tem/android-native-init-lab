#!/usr/bin/env python3
"""V1422 bounded live handoff for the V1420 RC1-window Wi-Fi test boot artifact."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1422",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1422-wifi-test-boot-rc1-window-sampler-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1422_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1421-wifi-test-boot-rc1-window-sampler-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1420-wifi-test-boot-rc1-window-sampler"
        / "boot_linux_v1420_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.76 (v1420-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1420.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1420.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1420-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1420-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1420|TEST: 11|Assert the reset|Release the reset|PCIE20_PARF_INT_ALL_MASK|"
        "PCIe RC1 PHY is ready|PCIe RC1 Current|PCIe RC1 link|LTSSM|GPIO142|mdm status|"
        "wlfw|WLFW|FW ready|BDF|wlan0|mhi|MHI|ks|subsystem_get|mdm_subsys_powerup"
    ),
    "--post-boot-hold-sec",
    "6",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
