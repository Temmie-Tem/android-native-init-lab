#!/usr/bin/env python3
"""V1390 execns helper v286 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1390-execns-helper-v286-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v286")
deploy.DEFAULT_HELPER_SHA256 = (
    "e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v286"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-early-powerup-corrected-rc1-enumerate"
deploy.DEPLOY_LABEL = "v286"
deploy.DEPLOY_NAME = "execns-helper-v286"
deploy.DEPLOY_PLAN_VERSION = "V1390"
deploy.DEPLOY_LOG_PREFIX = "v1390"
deploy.SUMMARY_TITLE = "V1390 Execns Helper v286 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1390 deploy execns helper v286 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
