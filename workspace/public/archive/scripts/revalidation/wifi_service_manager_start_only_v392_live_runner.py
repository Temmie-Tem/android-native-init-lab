#!/usr/bin/env python3
"""V392 service-manager backchain capture live runner wrapper.

This reuses the guarded service-manager runner body but fixes the V392 runtime
profile: helper v21, private property root, private-empty /data, ptrace-lite
capture mode with compact service-manager snapshots, PC/LR map rows, and
bounded frame-chain/backchain evidence. It requires a V392-specific approval
phrase before any service-manager start-only attempt and it does not start
Wi-Fi HAL or bring up Wi-Fi.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.__doc__ = __doc__
runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v392-servicemanager-backchain-capture-live-runner")
runner.DEFAULT_HELPER_SHA256 = "c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v392 Service-Manager Backchain Capture Live Runner"
runner.HELPER_LABEL = "v21"
runner.HELPER_DEPLOY_HINT = "run V392 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v392 service-manager backchain capture only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
