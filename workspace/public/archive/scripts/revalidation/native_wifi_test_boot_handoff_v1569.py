#!/usr/bin/env python3
"""V1569 rollbackable live handoff for the V1568 service-window result-output test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1569",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1569-service-window-result-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1569_SERVICE_WINDOW_RESULT_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1568-service-window-subsys-trigger-result-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1568-service-window-subsys-trigger-result-test-boot"
        / "boot_linux_v1393_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.69 (v1568-service-window-subsys-trigger-result)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1393.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1393.summary",
    "--test-helper-result-path",
    "/cache/native-init-wifi-test-boot-v1393-helper.result",
    "--dmesg-grep-pattern",
    (
        "A90v1568|android_wifi_service_window|cnss_before_esoc|subsys_esoc0|"
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
