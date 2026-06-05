#!/usr/bin/env python3
"""V1258 execns helper v262 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1258-execns-helper-v262-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v262")
deploy.DEFAULT_HELPER_SHA256 = (
    "17773e5bcdec090c061a962833d27a783439e1b718c96b47a504f625d79cc36d"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v262"
deploy.SERVICE_MODE_TOKEN = "--allow-pmic-gpiochip-devnode-open-preflight"
deploy.DEPLOY_LABEL = "v262"
deploy.DEPLOY_NAME = "execns-helper-v262"
deploy.DEPLOY_PLAN_VERSION = "V1258"
deploy.DEPLOY_LOG_PREFIX = "v1258h"
deploy.SUMMARY_TITLE = "V1258 Execns Helper v262 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1258 deploy execns helper v262 only; "
    "no GPIO line request, no PMIC write, no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
