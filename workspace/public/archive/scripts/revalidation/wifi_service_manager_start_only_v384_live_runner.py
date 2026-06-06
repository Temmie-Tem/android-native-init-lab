#!/usr/bin/env python3
"""V384 service-manager ptrace-lite crash-capture live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V384 runtime
profile: helper v15, private property root, private-empty /data, and
ptrace-lite capture mode. It requires a V384-specific approval phrase before
any service-manager start-only attempt and it does not start Wi-Fi HAL or bring
up Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v384-servicemanager-ptrace-crash-capture-live-runner")
runner.DEFAULT_HELPER_SHA256 = "dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v384 Service-Manager Ptrace-Lite Crash Capture Live Runner"
runner.HELPER_LABEL = "v15"
runner.HELPER_DEPLOY_HINT = "run V384 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v384 service-manager ptrace-lite crash capture only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
