#!/usr/bin/env python3
"""V1283 bounded PCIe/GDSC/kmsg response observer.

This wraps the V1242 late per_proxy response sampler with helper v268.  Helper
v268 adds read-only /dev/kmsg marker counts for PCIe/GDSC/MHI/eSoC/MDM/SDX50M
and WLFW-related lines to the existing PM-service /dev/subsys_esoc0 window.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1283-pcie-kmsg-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1283-pcie-kmsg-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v268"
base.HELPER_SHA256 = "e86db44aad14e54572d88d77c1ea2019ea28b1f91c01f7a9af9e6eabc690a3ba"
base.CYCLE_LABEL = "v1283"
base.CYCLE_NAME = "V1283"
base.SUMMARY_HEADING = "V1283 PCIe/GDSC/kmsg Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1283"


if __name__ == "__main__":
    raise SystemExit(base.main())
