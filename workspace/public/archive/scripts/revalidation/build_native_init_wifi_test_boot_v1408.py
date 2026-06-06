#!/usr/bin/env python3
"""Build the V1408 Wi-Fi test boot artifact with a PID1 RC1 watcher."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1408-wifi-test-boot-pid1-rc1-watcher"

DEFAULT_ARGS = [
    "--cycle",
    "V1408",
    "--decision",
    "v1408-wifi-test-boot-pid1-rc1-watcher-source-build-pass",
    "--cycle-label",
    "v1408",
    "--init-version",
    "0.9.73",
    "--init-build",
    "v1408-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1408_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1408_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1408_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1408",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1408.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1408.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1408.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1408.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1408-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1408-rc1-watcher.result",
    "--wifi-test-watch-sec",
    "35",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "40",
    "--wifi-test-mount-debugfs",
    "--wifi-test-pid1-rc1-watcher",
    "--wifi-test-rc1-watcher-timeout-sec",
    "45",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
