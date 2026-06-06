#!/usr/bin/env python3
"""V1548 handoff for the V1546 low-overhead endpoint observer test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1548",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1548-low-overhead-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1548_LOW_OVERHEAD_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1547-low-overhead-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1546-low-overhead-endpoint-observer-test-boot"
        / "boot_linux_v1546_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.100 (v1546-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1546.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1546.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1546-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1546-low-overhead-endpoint.result",
    "--dmesg-grep-pattern",
    (
        "A90v1546|sysfs_client|low_overhead|auto_readiness|rc1_window|"
        "rc1_micro|case_aligned|micro_critical|source_timing|"
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
