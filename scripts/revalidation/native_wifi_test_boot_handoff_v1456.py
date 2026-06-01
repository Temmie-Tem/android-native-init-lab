#!/usr/bin/env python3
"""V1456 bounded live handoff for the V1454 exact-line provider long-window Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1456",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1456-wifi-test-boot-exact-provider-long-endpoint-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1456_WIFI_TEST_BOOT_EXACT_PROVIDER_LONG_ENDPOINT_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1455-wifi-test-boot-exact-provider-long-endpoint-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1454-wifi-test-boot-exact-provider-long-endpoint-sampler"
        / "boot_linux_v1454_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.84 (v1454-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1454.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1454.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1454-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1454-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1454|subsystem_get|mdm_subsys_powerup|Assert the reset|Release the reset|"
        "PCIE20_PARF_INT_ALL_MASK|PCIe RC1 PHY is ready|PCIe RC1 Current|PCIe RC1 link|"
        "LTSSM|GPIO142|mdm status|wlfw|WLFW|FW ready|BDF|wlan0|mhi_arch|mhi_pci|mhi_0305|MHI|ks"
    ),
    "--post-boot-hold-sec",
    "15",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
