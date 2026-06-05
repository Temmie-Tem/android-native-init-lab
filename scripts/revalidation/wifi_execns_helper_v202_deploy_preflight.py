#!/usr/bin/env python3
"""V1092 execns helper v202 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1092-execns-helper-v202-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1092-execns-helper-v202-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "54a2488dda1d659ffef52a89be643abc5bfaf5254477c2771d41901897211435"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v202"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v202"
deploy.DEPLOY_NAME = "execns-helper-v202"
deploy.DEPLOY_PLAN_VERSION = "V1092"
deploy.DEPLOY_LOG_PREFIX = "v1092"
deploy.SUMMARY_TITLE = "v1092 Execns Helper v202 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1092 deploy execns helper v202 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
