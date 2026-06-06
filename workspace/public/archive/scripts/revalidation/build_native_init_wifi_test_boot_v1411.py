#!/usr/bin/env python3
"""Build the V1411 Wi-Fi test boot artifact with /proc/kmsg RC1 watcher fallback."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1411-wifi-test-boot-kmsg-fallback"

DEFAULT_ARGS = [
    "--cycle",
    "V1411",
    "--decision",
    "v1411-wifi-test-boot-kmsg-fallback-source-build-pass",
    "--cycle-label",
    "v1411",
    "--init-version",
    "0.9.74",
    "--init-build",
    "v1411-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1411_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1411_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1411_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1411",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1411.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1411.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1411.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1411.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1411-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1411-rc1-watcher.result",
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
