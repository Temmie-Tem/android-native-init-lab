#!/usr/bin/env python3
"""V1427 bounded live handoff for the V1425 RC1-retry Wi-Fi test boot artifact."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1427",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1427-wifi-test-boot-rc1-retry-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1427_WIFI_TEST_BOOT_RC1_RETRY_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1426-wifi-test-boot-rc1-retry-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1425-wifi-test-boot-rc1-retry"
        / "boot_linux_v1425_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.77 (v1425-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1425.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1425.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1425-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1425-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1425|TEST: 11|Assert the reset|Release the reset|PCIE20_PARF_INT_ALL_MASK|"
        "PCIe RC1 PHY is ready|PCIe RC1 Current|PCIe RC1 link|LTSSM|GPIO142|mdm status|"
        "wlfw|WLFW|FW ready|BDF|wlan0|mhi|MHI|ks|subsystem_get|mdm_subsys_powerup"
    ),
    "--post-boot-hold-sec",
    "8",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
