#!/usr/bin/env python3
"""V1290 bounded no-write TLMM/PCIe response observer.

This wraps the V1242 late per_proxy response sampler with helper v270. Helper
v270 adds exact no-write /sys/kernel/debug/gpio target scans for gpio135/gpio142
to the existing klogctl, PMIC9, GDSC, PCIe, MHI, and wlan0 response window.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1290-tlmm-pcie-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1290-tlmm-pcie-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v270"
base.HELPER_SHA256 = "f1748fdc9c64a748c3270cd02a2b9bb796065b79632849e7384c2f37910f6e88"
base.CYCLE_LABEL = "v1290"
base.CYCLE_NAME = "V1290"
base.SUMMARY_HEADING = "V1290 TLMM/PCIe Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1290"


if __name__ == "__main__":
    raise SystemExit(base.main())
