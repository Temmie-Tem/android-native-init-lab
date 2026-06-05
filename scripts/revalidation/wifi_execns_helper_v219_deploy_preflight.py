#!/usr/bin/env python3
"""V1180 execns helper v219 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1180-execns-helper-v219-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1180-execns-helper-v219-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "b9c93cf4e87b11a33203b5cec36b01c323e99bc61d3bbc20c24d2d811ee768fc"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v219"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-zero-delay-per-mgr-probe"
deploy.DEPLOY_LABEL = "v219"
deploy.DEPLOY_NAME = "execns-helper-v219"
deploy.DEPLOY_PLAN_VERSION = "V1180"
deploy.DEPLOY_LOG_PREFIX = "v1180"
deploy.SUMMARY_TITLE = "v1180 Execns Helper v219 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1180 deploy execns helper v219 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
