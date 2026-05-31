#!/usr/bin/env python3
"""V1279 bounded TLMM debugfs range response observer.

This wraps the V1242 late per_proxy response sampler with helper v267.  Helper
v267 adds compact read-only TLMM GPIO range snapshots for GPIO135/GPIO142 to the
existing PM-service /dev/subsys_esoc0 response window.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1279-tlmm-range-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1279-tlmm-range-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v267"
base.HELPER_SHA256 = "eccd9ca475927c2a37551304fedcc6740d19aeb048ebd137f966a18c269f0337"
base.CYCLE_LABEL = "v1279"
base.CYCLE_NAME = "V1279"
base.SUMMARY_HEADING = "V1279 TLMM Debugfs Range Response Observer"
base.EVIDENCE_FILE_PREFIX = "v1279"


if __name__ == "__main__":
    raise SystemExit(base.main())
