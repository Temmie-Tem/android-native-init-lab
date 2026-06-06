#!/usr/bin/env python3
"""V403 service-manager start-only retry live runner wrapper.

This reuses the guarded service-manager runner body with the V402-proven
runtime surface: helper v22, private property root, private-empty /data,
SELinuxfs private bind support, and ptrace-lite capture. It requires a
V403-specific exact approval phrase before any service-manager start-only
attempt and it never starts Wi-Fi HAL or performs Wi-Fi bring-up.
"""

from __future__ import annotations

from pathlib import Path

import wifi_service_manager_start_only_live_runner as runner


runner.__doc__ = __doc__
runner.DEFAULT_OUT_DIR = Path("tmp/wifi/v403-servicemanager-start-only-retry-live-runner")
runner.DEFAULT_HELPER_SHA256 = "55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6"
runner.DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
runner.DEFAULT_DATA_WIFI_MODE = "private-empty"
runner.DEFAULT_CAPTURE_MODE = "ptrace-lite"
runner.SUMMARY_TITLE = "v403 Service-Manager Start-Only Retry Live Runner"
runner.HELPER_LABEL = "v22"
runner.HELPER_DEPLOY_HINT = "run V402 deploy first"
runner.APPROVAL_PHRASE = (
    "approve v403 service-manager start-only retry only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
