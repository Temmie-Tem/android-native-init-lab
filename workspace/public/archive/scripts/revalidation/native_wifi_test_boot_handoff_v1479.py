#!/usr/bin/env python3
"""V1479 bounded live handoff for the V1477 AP2MDM hold Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1479",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1479-wifi-test-boot-ap2mdm-hold-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1479_WIFI_TEST_BOOT_AP2MDM_HOLD_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1478-wifi-test-boot-ap2mdm-hold-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1477-wifi-test-boot-ap2mdm-hold"
        / "boot_linux_v1477_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.89 (v1477-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1477.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1477.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1477-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1477-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1477|ap2mdm|AP2MDM|gpio135|GPIO135|GPIO142|subsystem_get|"
        "mdm_subsys_powerup|pil_notif|fw=esoc0|Assert the reset|"
        "Release the reset|PCIe RC1 PHY is ready|PCIe RC1 Current|"
        "PCIe RC1 link|LTSSM|mdm status|wlfw|WLFW|FW ready|BDF|wlan0|"
        "mhi_arch|mhi_pci|mhi_0305|MHI|ks"
    ),
    "--post-boot-hold-sec",
    "75",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
