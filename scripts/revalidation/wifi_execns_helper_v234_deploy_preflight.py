#!/usr/bin/env python3
"""V1197 execns helper v234 deploy/preflight wrapper (real /dev/mhi* check)."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1197-execns-helper-v234-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "75d4b5d0c203312ee1cb8fd4d7d89ed717653427442f075fbf00eb75b555897f"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v234"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v234"
deploy.DEPLOY_NAME = "execns-helper-v234"
deploy.DEPLOY_PLAN_VERSION = "V1197"
deploy.DEPLOY_LOG_PREFIX = "v1197d"
deploy.SUMMARY_TITLE = "v1197d Execns Helper v234 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1197 deploy execns helper v234 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
