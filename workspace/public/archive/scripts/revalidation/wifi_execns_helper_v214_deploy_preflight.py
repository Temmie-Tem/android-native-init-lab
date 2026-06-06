#!/usr/bin/env python3
"""V1138 execns helper v214 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1138-execns-helper-v214-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1137-execns-helper-v214-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "4dd6dea42fddfc1b70732e5695323421a0abf505530ab2d437c6e5418a75638f"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v214"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-post-pm-mdm-helper-esoc-observer"
deploy.DEPLOY_LABEL = "v214"
deploy.DEPLOY_NAME = "execns-helper-v214"
deploy.DEPLOY_PLAN_VERSION = "V1138"
deploy.DEPLOY_LOG_PREFIX = "v1138"
deploy.SUMMARY_TITLE = "v1138 Execns Helper v214 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1138 deploy execns helper v214 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
