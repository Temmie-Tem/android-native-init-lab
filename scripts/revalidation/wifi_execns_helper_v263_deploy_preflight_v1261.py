#!/usr/bin/env python3
"""V1261 execns helper v263 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1261-execns-helper-v263-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v263")
deploy.DEFAULT_HELPER_SHA256 = (
    "32ac877a165a266d96589387d9974dfea38c81d0adb368bf17ff15de77a9f9fb"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v263"
deploy.SERVICE_MODE_TOKEN = "--allow-pmic-gpiochip-line-info-preflight"
deploy.DEPLOY_LABEL = "v263"
deploy.DEPLOY_NAME = "execns-helper-v263"
deploy.DEPLOY_PLAN_VERSION = "V1261"
deploy.DEPLOY_LOG_PREFIX = "v1261h"
deploy.SUMMARY_TITLE = "V1261 Execns Helper v263 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1261 deploy execns helper v263 only; "
    "no GPIO line request, no PMIC write, no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
