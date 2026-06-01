#!/usr/bin/env python3
"""Build the V1404 Wi-Fi test boot artifact with PID1 debugfs preparation."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1404-wifi-test-boot-debugfs"

DEFAULT_ARGS = [
    "--cycle",
    "V1404",
    "--decision",
    "v1404-wifi-test-boot-debugfs-source-build-pass",
    "--cycle-label",
    "v1404",
    "--init-version",
    "0.9.72",
    "--init-build",
    "v1404-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1404_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1404_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1404_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1404",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1404.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1404.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1404.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1404.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1404-supervisor.pid",
    "--wifi-test-watch-sec",
    "35",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "40",
    "--wifi-test-mount-debugfs",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
