#!/usr/bin/env python3
"""V387 ptrace timeout cleanup service-manager live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V387 runtime
profile: helper v18, private property root, private-empty /data, ptrace-lite
capture mode with compact service-manager snapshots, residual process-group
cleanup evidence, and ptrace timeout cleanup evidence. It requires a
V387-specific approval phrase before any service-manager start-only attempt and
it does not start Wi-Fi HAL or bring up Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v387-servicemanager-ptrace-timeout-cleanup-live-runner")
runner.DEFAULT_HELPER_SHA256 = "1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v387 Service-Manager Ptrace Timeout Cleanup Live Runner"
runner.HELPER_LABEL = "v18"
runner.HELPER_DEPLOY_HINT = "run V387 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v387 service-manager ptrace timeout cleanup only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
