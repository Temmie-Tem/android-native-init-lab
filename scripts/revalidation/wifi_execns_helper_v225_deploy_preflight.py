#!/usr/bin/env python3
"""V1191 execns helper v225 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1191-execns-helper-v225-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "cfe70c8879ab956670d8502ffd0d51c7544c26dd2a641db12c29129613d40664"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v225"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v225"
deploy.DEPLOY_NAME = "execns-helper-v225"
deploy.DEPLOY_PLAN_VERSION = "V1191"
deploy.DEPLOY_LOG_PREFIX = "v1191"
deploy.SUMMARY_TITLE = "v1191 Execns Helper v225 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1191 deploy execns helper v225 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
