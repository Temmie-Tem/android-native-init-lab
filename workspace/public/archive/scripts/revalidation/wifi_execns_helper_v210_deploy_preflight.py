#!/usr/bin/env python3
"""V1116 execns helper v210 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1116-execns-helper-v210-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1115-execns-helper-v210-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "05cf75f9410ec14b07fca0f21de10cf4c08ab618b33770632190099f360497ed"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v210"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v210"
deploy.DEPLOY_NAME = "execns-helper-v210"
deploy.DEPLOY_PLAN_VERSION = "V1116"
deploy.DEPLOY_LOG_PREFIX = "v1116"
deploy.SUMMARY_TITLE = "v1116 Execns Helper v210 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1116 deploy execns helper v210 only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
