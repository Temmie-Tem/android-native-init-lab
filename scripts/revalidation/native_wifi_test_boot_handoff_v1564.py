#!/usr/bin/env python3
"""V1564 rollbackable live handoff for the V1562 Android Wi-Fi service-window test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1564",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1564-android-wifi-service-window-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1564_ANDROID_WIFI_SERVICE_WINDOW_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1563-android-wifi-service-window-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1562-android-wifi-service-window-test-boot"
        / "boot_linux_v1393_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.69 (v1562-service-window)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1393.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1393.summary",
    "--dmesg-grep-pattern",
    (
        "A90v1562|android_wifi_service_window|wifi_hal|wificond|wlfw|WLFW|"
        "wlfw_start|wlfw_service_request|icnss_qmi|BDF|bdwlan|regdb|"
        "FW ready|fw_ready|wlan0|subsystem_get|mdm_subsys_powerup|"
        "PCIe RC1|LTSSM|mhi|MHI|ks|cnss|CNSS"
    ),
    "--post-boot-hold-sec",
    "65",
    "--native-direct-rollback-fallback",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
