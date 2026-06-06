#!/usr/bin/env python3
"""V1443 bounded live handoff for the V1441 micro endpoint-sampler Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1443",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1443-wifi-test-boot-micro-endpoint-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1443_WIFI_TEST_BOOT_MICRO_ENDPOINT_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1442-wifi-test-boot-micro-endpoint-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1441-wifi-test-boot-micro-endpoint-sampler"
        / "boot_linux_v1441_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.81 (v1441-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1441.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1441.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1441-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1441-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1441|TEST: 11|Assert the reset|Release the reset|PCIE20_PARF_INT_ALL_MASK|"
        "PCIe RC1 PHY is ready|PCIe RC1 Current|PCIe RC1 link|LTSSM|GPIO142|mdm status|"
        "wlfw|WLFW|FW ready|BDF|wlan0|mhi|MHI|ks|subsystem_get|mdm_subsys_powerup"
    ),
    "--post-boot-hold-sec",
    "12",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
