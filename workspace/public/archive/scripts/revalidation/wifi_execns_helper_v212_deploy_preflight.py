#!/usr/bin/env python3
"""V1124 execns helper v212 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1124-execns-helper-v212-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1123-execns-helper-v212-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "65fe14f0d7095786d8228750e309e0a1b5d40c33825d1debb87870d9caba0ef3"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v212"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v212"
deploy.DEPLOY_NAME = "execns-helper-v212"
deploy.DEPLOY_PLAN_VERSION = "V1124"
deploy.DEPLOY_LOG_PREFIX = "v1124"
deploy.SUMMARY_TITLE = "v1124 Execns Helper v212 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1124 deploy execns helper v212 only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
