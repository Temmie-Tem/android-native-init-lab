#!/usr/bin/env python3
"""Build the V1425 Wi-Fi test boot artifact with bounded RC1 retry policy."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1425-wifi-test-boot-rc1-retry"

DEFAULT_ARGS = [
    "--cycle",
    "V1425",
    "--decision",
    "v1425-wifi-test-boot-rc1-retry-source-build-pass",
    "--cycle-label",
    "v1425",
    "--init-version",
    "0.9.77",
    "--init-build",
    "v1425-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1425_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1425_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1425_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1425",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1425.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1425.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1425.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1425.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1425-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1425-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1425-rc1-window.result",
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
    "--wifi-test-rc1-retry-count",
    "2",
    "--wifi-test-rc1-retry-delay-ms",
    "500",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
