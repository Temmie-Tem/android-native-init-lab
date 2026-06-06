#!/usr/bin/env python3
"""V1619 rollbackable live handoff for the V1617 pm-service system-info surface boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1619",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1619-pm-service-system-info-surface-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1619_PM_SERVICE_SYSTEM_INFO_SURFACE_HANDOFF_2026-06-02.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1618-pm-service-system-info-surface-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1617-pm-service-system-info-surface-test-boot"
        / "boot_linux_v1617_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.109 (v1617-pm-service-system-info-surface)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1617.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1617.summary",
    "--test-helper-result-path",
    "/cache/native-init-wifi-test-boot-v1617-helper.result",
    "--dmesg-grep-pattern",
    (
        "A90v1617|firmware mounts|firmware_mnt|firmware-modem|"
        "android_wifi_service_window|per_mgr_startup_trace|per_mgr_nonstop_context_trace|pm_service_system_info_surface|per_mgr_system_info_surface|system_info_surface|"
        "wifi_registry_snapshot|runtime_per_mgr|pm_service_system_info|system_info_surface|lower_marker|"
        "pph_modem_fd_gate|pph_modem|pm_first_late_per_proxy_route|"
        "pm_first_late|pm_first_route|pm_first|late_per_proxy|"
        "pm_proxy|pm-service|pm_proxy_helper|per_mgr|"
        "mdm_helper_launch_contract|mdm_helper|cnss_daemon|subsys_esoc0|"
        "/dev/esoc-0|/dev/subsys_modem|/dev/vndbinder|/dev/hwbinder|"
        "wifi_hal|wificond|wlfw|WLFW|wlfw_start|wlfw_service_request|"
        "icnss_qmi|BDF|bdwlan|regdb|FW ready|fw_ready|wlan0|"
        "subsystem_get|mdm_subsys_powerup|sdx50m_toggle_soft_reset|"
        "PCIe RC1|LTSSM|mhi|MHI|ks|cnss|CNSS"
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
