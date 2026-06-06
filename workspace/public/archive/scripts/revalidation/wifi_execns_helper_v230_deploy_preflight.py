#!/usr/bin/env python3
"""V1196 execns helper v230 deploy/preflight wrapper (periodic mdm3 status)."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1196-execns-helper-v230-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "8b903c2f0b4af7d1bb6304997c0cdee44401c4e1183e1767347081326623b994"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v230"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v230"
deploy.DEPLOY_NAME = "execns-helper-v230"
deploy.DEPLOY_PLAN_VERSION = "V1196"
deploy.DEPLOY_LOG_PREFIX = "v1196"
deploy.SUMMARY_TITLE = "v1196 Execns Helper v230 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1196 deploy execns helper v230 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
