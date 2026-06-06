#!/usr/bin/env python3
"""V1354 pcie1 RC power observer live wrapper.

Runs the existing current-route MDM2AP timing sampler with helper v281, adding
the read-only pcie1 RC GDSC/refclk/PERST/CLKREQ/WAKE fields introduced by the
2026-06-01 eSoC-provider pivot.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_current_route_mdm2ap_timing_sampler_live_v1345 as route


route.DEFAULT_OUT_DIR = Path("tmp/wifi/v1354-pcie1-rc-power-observer-live")
route.LATEST_POINTER = Path("tmp/wifi/latest-v1354-pcie1-rc-power-observer-live.txt")
route.PLAN_OUT_DIR = Path("tmp/wifi/v1354-pcie1-rc-power-observer-plan")
route.PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1354-pcie1-rc-power-observer-plan.txt")
route.REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md")

route.CYCLE_LABEL = "v1354"
route.CYCLE_NAME = "V1354"
route.SUMMARY_HEADING = "V1354 pcie1 RC Power Observer"
route.REPORT_TITLE = "Native Init V1354 pcie1 RC Power Observer Live"
route.SCRIPT_PATH = "scripts/revalidation/native_wifi_pcie1_rc_power_observer_live_v1354.py"
route.HELPER_MARKER = "a90_android_execns_probe v281"
route.HELPER_SHA256 = "a68b2fb226d02d949890781ff72af8853958fcfb073a8d055068a48ba50d8c6f"


if __name__ == "__main__":
    raise SystemExit(route.main())
