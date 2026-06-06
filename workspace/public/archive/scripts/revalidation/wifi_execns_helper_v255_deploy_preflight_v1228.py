#!/usr/bin/env python3
"""V1228 execns helper v255 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1228-execns-helper-v255-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "tmp/wifi/v1228-execns-helper-v255-build/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "8701add8d4e106616d61abbf6cd9b87eb26def99c619b49e79251ed8026439d1"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v255"
deploy.SERVICE_MODE_TOKEN = "post_pm_mdm_helper_early_trace.begin=1"
deploy.DEPLOY_LABEL = "v255"
deploy.DEPLOY_NAME = "execns-helper-v255"
deploy.DEPLOY_PLAN_VERSION = "V1228"
deploy.DEPLOY_LOG_PREFIX = "v1228h"
deploy.SUMMARY_TITLE = "v1228h Execns Helper v255 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1228 deploy execns helper v255 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
