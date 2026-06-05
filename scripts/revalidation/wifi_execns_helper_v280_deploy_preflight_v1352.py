#!/usr/bin/env python3
"""V1352 execns helper v280 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1352-execns-helper-v280-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v280")
deploy.DEFAULT_HELPER_SHA256 = (
    "509f7bb1eb599883d337afb167b29e271c3fe238e1bb1205fb9a93229263c278"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v280"
deploy.SERVICE_MODE_TOKEN = "current-route-cnss-wlfw-precondition"
deploy.DEPLOY_LABEL = "v280"
deploy.DEPLOY_NAME = "execns-helper-v280"
deploy.DEPLOY_PLAN_VERSION = "V1352"
deploy.DEPLOY_LOG_PREFIX = "v1352"
deploy.SUMMARY_TITLE = "V1352 Execns Helper v280 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1352 deploy execns helper v280 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
