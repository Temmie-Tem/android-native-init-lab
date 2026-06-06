#!/usr/bin/env python3
"""V1110 execns helper v208 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1110-execns-helper-v208-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1110-execns-helper-v208-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "a373aaa7954a87c9c5bb4c7a4c3f2f6b2ec046022a01c571e460b134b4596a98"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v208"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v208"
deploy.DEPLOY_NAME = "execns-helper-v208"
deploy.DEPLOY_PLAN_VERSION = "V1110"
deploy.DEPLOY_LOG_PREFIX = "v1110"
deploy.SUMMARY_TITLE = "v1110 Execns Helper v208 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1110 deploy execns helper v208 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
