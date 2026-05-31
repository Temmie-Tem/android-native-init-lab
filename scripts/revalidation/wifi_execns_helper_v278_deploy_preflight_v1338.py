#!/usr/bin/env python3
"""V1338 execns helper v278 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1338-execns-helper-v278-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v278")
deploy.DEFAULT_HELPER_SHA256 = (
    "dd4f9996f5798a09498d4f7ce2f4e0385c161cc793e0ce0c96db284863f9d1e7"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v278"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-android-order-pre-cnss-provider-observe-only"
deploy.DEPLOY_LABEL = "v278"
deploy.DEPLOY_NAME = "execns-helper-v278"
deploy.DEPLOY_PLAN_VERSION = "V1338"
deploy.DEPLOY_LOG_PREFIX = "v1338"
deploy.SUMMARY_TITLE = "V1338 Execns Helper v278 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1338 deploy execns helper v278 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
