#!/usr/bin/env python3
"""V1243 SDX50M power prerequisite response sampler.

This wraps the V1242 late per_proxy response sampler with helper v259.  The
new helper keeps the same bounded action surface but records source paths for
GPIO135/GPIO142 pinctrl lines and separates the PM8150L soft-reset GPIO and
PCIe GDSC regulator lines from generic TLMM GPIO9 matches.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1243-sdx50m-power-prereq-response-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1243-sdx50m-power-prereq-response-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v259"
base.HELPER_SHA256 = "21085ecd7ddeb8132ae52d236f5d95d47d8cc899494eaa9646f0f196d8c035e5"
base.CYCLE_LABEL = "v1243"
base.CYCLE_NAME = "V1243"
base.SUMMARY_HEADING = "V1243 SDX50M Power Prerequisite Response Sampler"
base.EVIDENCE_FILE_PREFIX = "v1243"


if __name__ == "__main__":
    raise SystemExit(base.main())
