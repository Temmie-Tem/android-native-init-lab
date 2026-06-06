#!/usr/bin/env python3
"""V1271 bounded AP2MDM value/power response observer.

This wraps the V1242 late per_proxy response sampler with helper v265.  Helper
v265 adds read-only debugfs gpio and pinconf snapshots for PMIC GPIO9 / TLMM
GPIO135 / TLMM GPIO142 to the existing PM-service /dev/subsys_esoc0 response
window.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1271-ap2mdm-value-power-observer-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1271-ap2mdm-value-power-observer-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v265"
base.HELPER_SHA256 = "97ffa91a1aa7b8f4ab2c3a74716ae5664c703e98fe19a322351b1277fbd282b2"
base.CYCLE_LABEL = "v1271"
base.CYCLE_NAME = "V1271"
base.SUMMARY_HEADING = "V1271 AP2MDM Value/Power Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1271"


if __name__ == "__main__":
    raise SystemExit(base.main())
