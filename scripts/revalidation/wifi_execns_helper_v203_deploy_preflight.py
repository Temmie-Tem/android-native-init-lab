#!/usr/bin/env python3
"""V1093 execns helper v203 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1093-execns-helper-v203-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1093-execns-helper-v203-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "3b8d0bd04cf0c4519d907833acdd8aac88c2db61f388872342ee35a91de5b594"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v203"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v203"
deploy.DEPLOY_NAME = "execns-helper-v203"
deploy.DEPLOY_PLAN_VERSION = "V1093"
deploy.DEPLOY_LOG_PREFIX = "v1093"
deploy.SUMMARY_TITLE = "v1093 Execns Helper v203 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1093 deploy execns helper v203 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
