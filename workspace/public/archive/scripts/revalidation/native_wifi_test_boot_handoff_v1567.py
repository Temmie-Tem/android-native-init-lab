#!/usr/bin/env python3
"""V1567 rollbackable live handoff for the V1566 service-window subsys-trigger test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1567",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1567-service-window-subsys-trigger-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1567_SERVICE_WINDOW_SUBSYS_TRIGGER_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1566-service-window-subsys-trigger-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1566-android-wifi-service-window-subsys-trigger-test-boot"
        / "boot_linux_v1393_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1393.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1393.summary",
    "--dmesg-grep-pattern",
    (
        "A90v1566|android_wifi_service_window|cnss_before_esoc|subsys_esoc0|"
        "wifi_hal|wificond|wlfw|WLFW|wlfw_start|wlfw_service_request|"
        "icnss_qmi|BDF|bdwlan|regdb|FW ready|fw_ready|wlan0|"
        "subsystem_get|mdm_subsys_powerup|sdx50m_toggle_soft_reset|"
        "PCIe RC1|LTSSM|mhi|MHI|ks|cnss|CNSS"
    ),
    "--post-boot-hold-sec",
    "105",
    "--native-direct-rollback-fallback",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
