#!/usr/bin/env python3
"""V1074 execns helper v196 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1074-execns-helper-v196-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1074-execns-helper-v196-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "61b8ac54460f05e1d3a6fc6b68d8873c04537c171054921b4266be1ef6a0fb59"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v196"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v196"
deploy.DEPLOY_NAME = "execns-helper-v196"
deploy.DEPLOY_PLAN_VERSION = "V1074"
deploy.DEPLOY_LOG_PREFIX = "v1074"
deploy.SUMMARY_TITLE = "v1074 Execns Helper v196 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1074 deploy execns helper v196 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
