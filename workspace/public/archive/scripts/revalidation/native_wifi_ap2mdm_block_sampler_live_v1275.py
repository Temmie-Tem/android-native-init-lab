#!/usr/bin/env python3
"""V1275 bounded AP2MDM debugfs block response observer.

This wraps the V1242 late per_proxy response sampler with helper v266.  Helper
v266 adds compact read-only debugfs GPIO/pinconf block snapshots to the existing
PM-service /dev/subsys_esoc0 response window.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1275-ap2mdm-block-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1275-ap2mdm-block-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v266"
base.HELPER_SHA256 = "3bf4105d685f023ccdeb75ae28d7d104ca005fc9f70870dc6f402a9ea4038ed4"
base.CYCLE_LABEL = "v1275"
base.CYCLE_NAME = "V1275"
base.SUMMARY_HEADING = "V1275 AP2MDM Debugfs Block Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1275"


if __name__ == "__main__":
    raise SystemExit(base.main())
