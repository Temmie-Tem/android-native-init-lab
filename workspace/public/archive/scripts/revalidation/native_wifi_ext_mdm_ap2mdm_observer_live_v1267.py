#!/usr/bin/env python3
"""V1267 bounded ext-mdm/AP2MDM response observer.

This wraps the V1242/V1243 late per_proxy response sampler with helper v264.
Helper v264 adds read-only PMIC GPIO9 GPIO_GET_LINEINFO_IOCTL snapshots to each
response sample.  The live action surface remains the existing bounded
PM-service /dev/subsys_esoc0 response window; this wrapper does not add GPIO
line requests, PMIC writes, direct eSoC ioctls, Wi-Fi scan/connect, credentials,
DHCP/routes, external ping, flash, boot image writes, or partition writes.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1267-ext-mdm-ap2mdm-observer-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1267-ext-mdm-ap2mdm-observer-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v264"
base.HELPER_SHA256 = "a06ff29245023c265c69e58e2ae3f32a4facbc291bcb63a4450f39efd9515dc5"
base.CYCLE_LABEL = "v1267"
base.CYCLE_NAME = "V1267"
base.SUMMARY_HEADING = "V1267 ext-mdm/AP2MDM Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1267"


if __name__ == "__main__":
    raise SystemExit(base.main())
