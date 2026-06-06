#!/usr/bin/env python3
"""V1505 short-hold handoff for the V1503 dense pre-L0 parity Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1505",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1505-wifi-dense-pre-l0-parity-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1505_WIFI_DENSE_PRE_L0_PARITY_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1504-wifi-dense-pre-l0-parity-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1503-wifi-dense-pre-l0-parity-test-boot"
        / "boot_linux_v1503_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.94 (v1503-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1503.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1503.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1503-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1503-dense-pre-l0-parity.result",
    "--dmesg-grep-pattern",
    (
        "A90v1503|auto_readiness|rc1_window|rc1_micro|case_aligned|"
        "micro_focused|pid1_rc1|wlfw|WLFW|icnss_qmi|BDF|bdwlan|regdb|"
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
