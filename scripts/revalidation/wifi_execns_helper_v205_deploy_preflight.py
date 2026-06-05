#!/usr/bin/env python3
"""V1094 execns helper v205 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1094-execns-helper-v205-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1094-execns-helper-v205-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "0b93ada5ceaf868cd907d3ad2fcd5986485024fa05bdfe3780daee945984af0f"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v205"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v205"
deploy.DEPLOY_NAME = "execns-helper-v205"
deploy.DEPLOY_PLAN_VERSION = "V1094"
deploy.DEPLOY_LOG_PREFIX = "v1094"
deploy.SUMMARY_TITLE = "v1094 Execns Helper v205 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1094 deploy execns helper v205 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
