#!/usr/bin/env python3
"""V1543 handoff for the V1541 endpoint-electrical observer Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1543",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1543-endpoint-electrical-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1543_ENDPOINT_ELECTRICAL_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1542-endpoint-electrical-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1541-endpoint-electrical-observer-test-boot"
        / "boot_linux_v1541_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.99 (v1541-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1541.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1541.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1541-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1541-endpoint-electrical.result",
    "--dmesg-grep-pattern",
    (
        "A90v1541|sysfs_client|endpoint_electrical|auto_readiness|rc1_window|"
        "rc1_micro|case_aligned|micro_critical|micro_focused|source_timing|"
        "pid1_rc1|wlfw|WLFW|icnss_qmi|BDF|bdwlan|regdb|FW ready|fw_ready|"
        "wlan0|subsystem_get|mdm_subsys_powerup|PCIe RC1|LTSSM|pcie|PCIe|"
        "mhi|MHI|ks|cnss|CNSS|gpio102|gpio103|gpio104|gpio135|gpio142|"
        "pcie_1_gdsc|gcc_pcie_1|clkref|refgen"
    ),
    "--post-boot-hold-sec",
    "18",
    "--native-direct-rollback-fallback",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
