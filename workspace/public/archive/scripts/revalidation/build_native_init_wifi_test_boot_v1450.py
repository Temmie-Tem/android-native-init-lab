#!/usr/bin/env python3
"""Build the V1450 Wi-Fi test boot artifact with provider-trigger micro endpoint sampling."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1450-wifi-test-boot-provider-trigger-micro-endpoint-sampler"

DEFAULT_ARGS = [
    "--cycle",
    "V1450",
    "--decision",
    "v1450-wifi-test-boot-provider-trigger-micro-endpoint-source-build-pass",
    "--cycle-label",
    "v1450",
    "--init-version",
    "0.9.83",
    "--init-build",
    "v1450-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1450_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1450_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1450_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1450",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1450.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1450.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1450.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1450.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1450-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1450-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1450-rc1-window.result",
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
    "0",
    "--wifi-test-rc1-window-sampler",
    "--wifi-test-rc1-endpoint-sampler",
    "--wifi-test-rc1-micro-endpoint-sampler",
    "--wifi-test-provider-trigger-micro-endpoint-sampler",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
