#!/usr/bin/env python3
"""V1111 execns helper v209 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1111-execns-helper-v209-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1111-execns-helper-v209-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "467ea2ef54a7b1ad95d95876ce8a8b5fe90bb4d8c9bfce6360211d6848c874a5"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v209"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v209"
deploy.DEPLOY_NAME = "execns-helper-v209"
deploy.DEPLOY_PLAN_VERSION = "V1111"
deploy.DEPLOY_LOG_PREFIX = "v1111"
deploy.SUMMARY_TITLE = "v1111 Execns Helper v209 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1111 deploy execns helper v209 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
