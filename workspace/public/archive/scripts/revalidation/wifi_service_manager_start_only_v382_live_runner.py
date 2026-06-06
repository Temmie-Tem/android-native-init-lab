#!/usr/bin/env python3
"""V382 service-manager start-only live runner wrapper.

This reuses the guarded V376 runner body but fixes the V382 runtime profile:
helper v14, private property root, and private-empty /data. It still requires
the exact V373 service-manager start-only approval phrase before any daemon
start, and it does not start Wi-Fi HAL or bring up Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v382-service-manager-property-runtime-live-runner")
runner.DEFAULT_HELPER_SHA256 = "f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.SUMMARY_TITLE = "v382 Service-Manager Property Runtime Start-Only Live Runner"
runner.HELPER_LABEL = "v14"
runner.HELPER_DEPLOY_HINT = "run V382 deploy first"


if __name__ == "__main__":
    raise SystemExit(runner.main())
