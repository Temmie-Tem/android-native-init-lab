#!/usr/bin/env python3
"""V1131 execns helper v213 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1131-execns-helper-v213-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1130-execns-helper-v213-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v213"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v213"
deploy.DEPLOY_NAME = "execns-helper-v213"
deploy.DEPLOY_PLAN_VERSION = "V1131"
deploy.DEPLOY_LOG_PREFIX = "v1131"
deploy.SUMMARY_TITLE = "v1131 Execns Helper v213 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1131 deploy execns helper v213 only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
