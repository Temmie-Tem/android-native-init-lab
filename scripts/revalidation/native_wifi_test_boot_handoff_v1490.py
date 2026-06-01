#!/usr/bin/env python3
"""V1490 bounded live handoff for the V1488 timeout-safe Wi-Fi test boot."""

from __future__ import annotations

import sys

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_ARGS = [
    "--cycle",
    "V1490",
    "--out-dir",
    str(base.REPO_ROOT / "tmp" / "wifi" / "v1490-wifi-auto-readiness-timeout-safe-handoff"),
    "--report-path",
    str(
        base.REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1490_WIFI_AUTO_READINESS_TIMEOUT_SAFE_HANDOFF_2026-06-01.md"
    ),
    "--v1394-manifest",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1489-wifi-auto-readiness-timeout-safe-artifact-sanity"
        / "manifest.json"
    ),
    "--test-image",
    str(
        base.REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1488-wifi-auto-readiness-timeout-safe-test-boot"
        / "boot_linux_v1488_wifi_test.img"
    ),
    "--expect-test-version",
    "A90 Linux init 0.9.91 (v1488-wifitest)",
    "--test-log-path",
    "/cache/native-init-wifi-test-boot-v1488.log",
    "--test-summary-path",
    "/cache/native-init-wifi-test-boot-v1488.summary",
    "--dmesg-grep-pattern",
    (
        "A90v1488|auto_readiness|wlfw|WLFW|icnss_qmi|BDF|bdwlan|regdb|"
        "FW ready|fw_ready|wlan0|subsystem_get|mdm_subsys_powerup|"
        "PCIe RC1|LTSSM|mhi|MHI|ks|cnss|CNSS"
    ),
    "--post-boot-hold-sec",
    "90",
    "--strict-wifi-progress",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
