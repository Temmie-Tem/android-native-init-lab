#!/usr/bin/env python3
"""V386 compact ptrace service-manager live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V386 runtime
profile: helper v17, private property root, private-empty /data, ptrace-lite
capture mode with compact service-manager snapshots, and residual process-group
cleanup evidence. It requires a V386-specific approval phrase before any
service-manager start-only attempt and it does not start Wi-Fi HAL or bring up
Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v386-servicemanager-compact-ptrace-live-runner")
runner.DEFAULT_HELPER_SHA256 = "45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v386 Service-Manager Compact Ptrace Capture Live Runner"
runner.HELPER_LABEL = "v17"
runner.HELPER_DEPLOY_HINT = "run V386 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v386 service-manager compact ptrace capture only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
