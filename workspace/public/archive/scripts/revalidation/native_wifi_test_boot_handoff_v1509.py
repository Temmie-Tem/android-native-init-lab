#!/usr/bin/env python3
"""V1509 short-hold handoff for the V1507 batched pre-L0 parity Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1509",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1509-wifi-batched-pre-l0-parity-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1509_WIFI_BATCHED_PRE_L0_PARITY_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1508-wifi-batched-pre-l0-parity-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1507-wifi-batched-pre-l0-parity-test-boot"
        / "boot_linux_v1507_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.95 (v1507-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1507.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1507.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1507-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1507-batched-pre-l0-parity.result",
    "--dmesg-grep-pattern",
    (
        "A90v1507|auto_readiness|rc1_window|rc1_micro|case_aligned|"
        "micro_batched|pid1_rc1|wlfw|WLFW|icnss_qmi|BDF|bdwlan|regdb|"
        "FW ready|fw_ready|wlan0|subsystem_get|mdm_subsys_powerup|PCIe RC1|"
        "LTSSM|pcie|PCIe|mhi|MHI|ks|cnss|CNSS|gpio102|gpio103|gpio104|"
        "gpio135|gpio142|pcie_1_gdsc|gcc_pcie_1"
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
