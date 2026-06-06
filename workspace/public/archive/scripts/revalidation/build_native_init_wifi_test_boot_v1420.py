#!/usr/bin/env python3
"""Build the V1420 Wi-Fi test boot artifact with RC1-window read-only sampler."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1420-wifi-test-boot-rc1-window-sampler"

DEFAULT_ARGS = [
    "--cycle",
    "V1420",
    "--decision",
    "v1420-wifi-test-boot-rc1-window-sampler-source-build-pass",
    "--cycle-label",
    "v1420",
    "--init-version",
    "0.9.76",
    "--init-build",
    "v1420-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1420_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1420_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1420_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1420",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1420.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1420.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1420.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1420.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1420-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1420-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1420-rc1-window.result",
    "--wifi-test-watch-sec",
    "35",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "40",
    "--wifi-test-mount-debugfs",
    "--wifi-test-pid1-rc1-watcher",
    "--wifi-test-rc1-watcher-timeout-sec",
    "45",
    "--wifi-test-rc1-watcher-delay-ms",
    "250",
    "--wifi-test-rc1-window-sampler",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
