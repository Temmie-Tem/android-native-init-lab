#!/usr/bin/env python3
"""V1495 bounded live handoff for the V1493 RC1-window Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1495",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1495-wifi-auto-readiness-rc1-window-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1495_WIFI_AUTO_READINESS_RC1_WINDOW_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1494-wifi-auto-readiness-rc1-window-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1493-wifi-auto-readiness-rc1-window-test-boot"
        / "boot_linux_v1493_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.92 (v1493-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1493.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1493.summary",
    "--test-rc1-watcher-result-path",
    "/cache/native-init-wifi-test-boot-v1493-rc1-watcher.result",
    "--test-rc1-window-result-path",
    "/cache/native-init-wifi-test-boot-v1493-rc1-window.result",
    "--dmesg-grep-pattern",
    (
        "A90v1493|auto_readiness|rc1_window|pid1_rc1|wlfw|WLFW|icnss_qmi|"
        "BDF|bdwlan|regdb|FW ready|fw_ready|wlan0|subsystem_get|"
        "mdm_subsys_powerup|PCIe RC1|LTSSM|pcie|PCIe|mhi|MHI|ks|cnss|CNSS"
    ),
    "--post-boot-hold-sec",
    "100",
    "--native-direct-rollback-fallback",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
