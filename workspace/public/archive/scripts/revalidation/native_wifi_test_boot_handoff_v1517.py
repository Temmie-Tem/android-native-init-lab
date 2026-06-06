#!/usr/bin/env python3
"""V1517 handoff for the V1515 critical-source pre-L0 Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1517",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1517-wifi-critical-source-pre-l0-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1517_WIFI_CRITICAL_SOURCE_PRE_L0_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1516-wifi-critical-source-pre-l0-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1515-wifi-critical-source-pre-l0-test-boot"
        / "boot_linux_v1515_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.97 (v1515-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1515.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1515.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1515-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1515-critical-source-pre-l0.result",
    "--dmesg-grep-pattern",
    (
        "A90v1515|auto_readiness|rc1_window|rc1_micro|case_aligned|"
        "micro_critical|source_timing|pid1_rc1|wlfw|WLFW|icnss_qmi|BDF|"
        "bdwlan|regdb|FW ready|fw_ready|wlan0|subsystem_get|"
        "mdm_subsys_powerup|PCIe RC1|LTSSM|pcie|PCIe|mhi|MHI|ks|"
        "cnss|CNSS|gpio102|gpio103|gpio104|gpio135|gpio142|pcie_1_gdsc"
    ),
    "--post-boot-hold-sec",
    "12",
    "--native-direct-rollback-fallback",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
