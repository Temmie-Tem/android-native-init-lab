#!/usr/bin/env python3
"""V389 enhanced crash capture service-manager live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V389 runtime
profile: helper v19, private property root, private-empty /data, ptrace-lite
capture mode with compact service-manager snapshots, residual process-group
cleanup evidence, ptrace timeout cleanup evidence, and enhanced crash capture
evidence. It requires a V389-specific approval phrase before any
service-manager start-only attempt and it does not start Wi-Fi HAL or bring up
Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v389-servicemanager-enhanced-crash-capture-live-runner")
runner.DEFAULT_HELPER_SHA256 = "e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v389 Service-Manager Enhanced Crash Capture Live Runner"
runner.HELPER_LABEL = "v19"
runner.HELPER_DEPLOY_HINT = "run V389 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v389 service-manager enhanced crash capture only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
