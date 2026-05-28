#!/usr/bin/env python3
"""V1193 execns helper v226 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1193-execns-helper-v226-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "79f1ec51434c18a0bbcc3168a0a027d2e87ca2e7deac5ee63e5e8b7695b2d47b"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v226"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v226"
deploy.DEPLOY_NAME = "execns-helper-v226"
deploy.DEPLOY_PLAN_VERSION = "V1193"
deploy.DEPLOY_LOG_PREFIX = "v1193"
deploy.SUMMARY_TITLE = "v1193 Execns Helper v226 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1193 deploy execns helper v226 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
