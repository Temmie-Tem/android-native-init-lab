#!/usr/bin/env python3
"""V1189 execns helper v224 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1189-execns-helper-v224-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "5c2af22eb0a331e9b12470a5ae77e3be2c8d6a1809e48092b412ff9f82005a5d"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v224"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v224"
deploy.DEPLOY_NAME = "execns-helper-v224"
deploy.DEPLOY_PLAN_VERSION = "V1189"
deploy.DEPLOY_LOG_PREFIX = "v1189"
deploy.SUMMARY_TITLE = "v1189 Execns Helper v224 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1189 deploy execns helper v224 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
