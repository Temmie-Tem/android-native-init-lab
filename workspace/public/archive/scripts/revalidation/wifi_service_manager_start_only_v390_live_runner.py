#!/usr/bin/env python3
"""V390 crash map-row service-manager live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V390 runtime
profile: helper v20, private property root, private-empty /data, ptrace-lite
capture mode with compact service-manager snapshots, enhanced crash capture,
and PC/LR map-row evidence. It requires a V390-specific approval phrase before
any service-manager start-only attempt and it does not start Wi-Fi HAL or bring
up Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.__doc__ = __doc__
runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v390-servicemanager-crash-map-capture-live-runner")
runner.DEFAULT_HELPER_SHA256 = "44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v390 Service-Manager Crash Map Capture Live Runner"
runner.HELPER_LABEL = "v20"
runner.HELPER_DEPLOY_HINT = "run V390 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v390 service-manager crash map capture only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
