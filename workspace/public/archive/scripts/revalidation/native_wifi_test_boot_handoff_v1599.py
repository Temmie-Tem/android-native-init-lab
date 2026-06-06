#!/usr/bin/env python3
"""V1599 rollbackable live handoff for the V1597 PM-first late-per-proxy lower-marker test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1599",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1599-pm-first-late-per-proxy-lower-marker-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1599_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1598-pm-first-late-per-proxy-lower-marker-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1597-pm-first-late-per-proxy-lower-marker-test-boot"
        / "boot_linux_v1597_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.104 (v1597-pm-first-late-per-proxy-lower-marker)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1597.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1597.summary",
    "--test-helper-result-path",
    "/cache/native-init-wifi-test-boot-v1597-helper.result",
    "--dmesg-grep-pattern",
    (
        "A90v1597|firmware mounts|firmware_mnt|firmware-modem|"
        "android_wifi_service_window|lower_marker|pm_first_late_per_proxy_route|pm_first_late|pm_first_route|pm_first|"
        "late_per_proxy|pm_proxy|pm-service|pm_proxy_helper|per_mgr|"
        "mdm_helper_launch_contract|mdm_helper|cnss_daemon|subsys_esoc0|"
        "/dev/esoc-0|wifi_hal|wificond|wlfw|WLFW|wlfw_start|"
        "wlfw_service_request|icnss_qmi|BDF|bdwlan|regdb|FW ready|"
        "fw_ready|wlan0|subsystem_get|mdm_subsys_powerup|"
        "sdx50m_toggle_soft_reset|PCIe RC1|LTSSM|mhi|MHI|ks|cnss|CNSS"
    ),
    "--post-boot-hold-sec",
    "150",
    "--native-direct-rollback-fallback",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
