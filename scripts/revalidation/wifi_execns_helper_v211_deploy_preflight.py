#!/usr/bin/env python3
"""V1118 execns helper v211 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1118-execns-helper-v211-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1117-execns-helper-v211-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "6bcf4ad606453f56c4cc25744f6ab90ff6b4cb89942b13c4cc86a7b2f024e44d"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v211"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v211"
deploy.DEPLOY_NAME = "execns-helper-v211"
deploy.DEPLOY_PLAN_VERSION = "V1118"
deploy.DEPLOY_LOG_PREFIX = "v1118"
deploy.SUMMARY_TITLE = "v1118 Execns Helper v211 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1118 deploy execns helper v211 only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
