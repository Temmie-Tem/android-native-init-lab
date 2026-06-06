#!/usr/bin/env python3
"""V1435 bounded live handoff for the V1433 focused endpoint-sampler Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1435",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1435-wifi-test-boot-focused-endpoint-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1435_WIFI_TEST_BOOT_FOCUSED_ENDPOINT_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1434-wifi-test-boot-focused-endpoint-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1433-wifi-test-boot-focused-endpoint-sampler"
        / "boot_linux_v1433_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.79 (v1433-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1433.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1433.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1433-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1433-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1433|TEST: 11|Assert the reset|Release the reset|PCIE20_PARF_INT_ALL_MASK|"
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
