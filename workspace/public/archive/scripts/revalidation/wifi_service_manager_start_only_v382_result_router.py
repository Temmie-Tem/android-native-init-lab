#!/usr/bin/env python3
"""V382 service-manager start-only result router wrapper.

This reuses the V377 host-only router but points recommended live commands at
the V382 property-runtime live wrapper. It never opens the bridge or mutates the
device.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_result_router as router


router.DEFAULT_OUT_DIR = Path("tmp/wifi/v382-service-manager-start-only-result-router")
router.DEFAULT_V376_GLOB = "v382-*/manifest.json"
router.LIVE_LABEL = "V382"
router.LIVE_RUNNER_SCRIPT = "scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py"
router.LIVE_RUNNER_OUT_DIR = "tmp/wifi/v382-approved-live-$(date +%Y%m%d-%H%M%S)"
router.SUMMARY_TITLE = "V382 Service-Manager Property Runtime Result Router"


if __name__ == "__main__":
    raise SystemExit(router.main())
