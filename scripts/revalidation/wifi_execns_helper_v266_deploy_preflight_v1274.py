#!/usr/bin/env python3
"""V1274 execns helper v266 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1274-execns-helper-v266-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v266")
deploy.DEFAULT_HELPER_SHA256 = (
    "3bf4105d685f023ccdeb75ae28d7d104ca005fc9f70870dc6f402a9ea4038ed4"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v266"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v266"
deploy.DEPLOY_NAME = "execns-helper-v266"
deploy.DEPLOY_PLAN_VERSION = "V1274"
deploy.DEPLOY_LOG_PREFIX = "v1274h"
deploy.SUMMARY_TITLE = "V1274 Execns Helper v266 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1274 deploy execns helper v266 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
