#!/usr/bin/env python3
"""V1095 execns helper v206 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1095-execns-helper-v206-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1095-execns-helper-v206-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "7920eeb353e1d6f09ded42efc84e7a8549fdb407cdd8236307422ebf2a9108e4"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v206"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v206"
deploy.DEPLOY_NAME = "execns-helper-v206"
deploy.DEPLOY_PLAN_VERSION = "V1095"
deploy.DEPLOY_LOG_PREFIX = "v1095"
deploy.SUMMARY_TITLE = "v1095 Execns Helper v206 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1095 deploy execns helper v206 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
