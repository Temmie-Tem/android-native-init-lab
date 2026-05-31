#!/usr/bin/env python3
"""V1286 bounded PCIe/GDSC/klogctl response observer.

This wraps the V1242 late per_proxy response sampler with helper v269. Helper
v269 keeps the previous read-only PCIe/GDSC/MHI/eSoC/MDM/SDX50M/WLFW marker
counts and adds a syslog/klogctl fallback when /dev/kmsg is absent.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1286-pcie-klogctl-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1286-pcie-klogctl-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v269"
base.HELPER_SHA256 = "dbb1f67652913ffe94b1f083a082d8f221820040b9f28e08b226eb1e0a50fc83"
base.CYCLE_LABEL = "v1286"
base.CYCLE_NAME = "V1286"
base.SUMMARY_HEADING = "V1286 PCIe/GDSC/klogctl Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1286"


if __name__ == "__main__":
    raise SystemExit(base.main())
