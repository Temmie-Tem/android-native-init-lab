#!/usr/bin/env python3
"""Build the V1397 Wi-Fi test boot artifact with per-boot helper logging.

This wraps the V1393 test-boot builder with a new cycle label, native build
identity, fresh `/cache` log paths, and the summary watcher enabled by the
shared PID1 hook.
"""

from __future__ import annotations

import sys

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1397-wifi-test-boot"

DEFAULT_ARGS = [
    "--cycle",
    "V1397",
    "--decision",
    "v1397-wifi-test-boot-logging-source-build-pass",
    "--cycle-label",
    "v1397",
    "--init-version",
    "0.9.70",
    "--init-build",
    "v1397-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1397_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1397_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1397_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1397",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1397.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1397.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1397.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1397.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1397-watcher.pid",
    "--wifi-test-watch-sec",
    "35",
]


def main() -> int:
    return base.main([*DEFAULT_ARGS, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
