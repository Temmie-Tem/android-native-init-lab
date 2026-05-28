#!/usr/bin/env python3
"""V1187 execns helper v222 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1187-execns-helper-v222-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "3105288f689edff928858a78bb61f7a2c8e83aa8392c63d89754f4ecf25858c2"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v222"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v222"
deploy.DEPLOY_NAME = "execns-helper-v222"
deploy.DEPLOY_PLAN_VERSION = "V1187"
deploy.DEPLOY_LOG_PREFIX = "v1187"
deploy.SUMMARY_TITLE = "v1187 Execns Helper v222 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1187 deploy execns helper v222 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
