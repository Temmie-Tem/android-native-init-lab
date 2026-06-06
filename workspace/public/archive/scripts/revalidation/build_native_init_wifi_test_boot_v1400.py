#!/usr/bin/env python3
"""Build the V1400 Wi-Fi test boot artifact with supervised helper wait."""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1400-wifi-test-boot"

DEFAULT_ARGS = [
    "--cycle",
    "V1400",
    "--decision",
    "v1400-wifi-test-boot-supervisor-source-build-pass",
    "--cycle-label",
    "v1400",
    "--init-version",
    "0.9.71",
    "--init-build",
    "v1400-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1400_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1400_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1400_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1400",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1400.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1400.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1400.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1400.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1400-supervisor.pid",
    "--wifi-test-watch-sec",
    "35",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "40",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
