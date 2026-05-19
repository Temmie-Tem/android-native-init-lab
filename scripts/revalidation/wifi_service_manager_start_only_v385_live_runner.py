#!/usr/bin/env python3
"""V385 service-manager residual-PGID cleanup live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V385 runtime
profile: helper v16, private property root, private-empty /data,
ptrace-lite capture mode, and residual process-group cleanup evidence. It requires a V385-specific approval phrase before
any service-manager start-only attempt and it does not start Wi-Fi HAL or bring
up Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v385-servicemanager-residual-pgid-cleanup-live-runner")
runner.DEFAULT_HELPER_SHA256 = "4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v385 Service-Manager Residual PGID Cleanup Live Runner"
runner.HELPER_LABEL = "v16"
runner.HELPER_DEPLOY_HINT = "run V385 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v385 service-manager residual pgid cleanup only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
