#!/usr/bin/env python3
"""V1185 execns helper v221 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1185-execns-helper-v221-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "120fad47dad2965ab8a541759bf1cd04396b9f81eb0c06986096e6f05dfdf05d"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v221"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v221"
deploy.DEPLOY_NAME = "execns-helper-v221"
deploy.DEPLOY_PLAN_VERSION = "V1185"
deploy.DEPLOY_LOG_PREFIX = "v1185"
deploy.SUMMARY_TITLE = "v1185 Execns Helper v221 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1185 deploy execns helper v221 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
