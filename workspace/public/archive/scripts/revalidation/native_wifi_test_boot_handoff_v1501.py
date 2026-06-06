#!/usr/bin/env python3
"""V1501 short-hold handoff for the V1499 pre-L0 parity Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1501",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1501-wifi-pre-l0-parity-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1501_WIFI_PRE_L0_PARITY_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1500-wifi-auto-readiness-pre-l0-parity-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1499-wifi-auto-readiness-pre-l0-parity-test-boot"
        / "boot_linux_v1499_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.93 (v1499-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1499.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1499.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1499-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1499-pre-l0-parity.result",
    "--dmesg-grep-pattern",
    (
        "A90v1499|auto_readiness|rc1_window|rc1_micro|case_aligned|"
        "pid1_rc1|wlfw|WLFW|icnss_qmi|BDF|bdwlan|regdb|FW ready|fw_ready|"
        "wlan0|subsystem_get|mdm_subsys_powerup|PCIe RC1|LTSSM|pcie|PCIe|"
        "mhi|MHI|ks|cnss|CNSS|gpio102|gpio103|gpio104|gpio135|gpio142"
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
