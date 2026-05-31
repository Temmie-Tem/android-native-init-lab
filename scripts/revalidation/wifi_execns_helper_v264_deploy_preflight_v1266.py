#!/usr/bin/env python3
"""V1266 execns helper v264 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1266-execns-helper-v264-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v264")
deploy.DEFAULT_HELPER_SHA256 = (
    "a06ff29245023c265c69e58e2ae3f32a4facbc291bcb63a4450f39efd9515dc5"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v264"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v264"
deploy.DEPLOY_NAME = "execns-helper-v264"
deploy.DEPLOY_PLAN_VERSION = "V1266"
deploy.DEPLOY_LOG_PREFIX = "v1266h"
deploy.SUMMARY_TITLE = "V1266 Execns Helper v264 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1266 deploy execns helper v264 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
