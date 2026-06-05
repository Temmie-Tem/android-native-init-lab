#!/usr/bin/env python3
"""V1378 execns helper v283 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1378-execns-helper-v283-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v283")
deploy.DEFAULT_HELPER_SHA256 = (
    "985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v283"
deploy.SERVICE_MODE_TOKEN = "gate_pm_service_powerup_thread_count"
deploy.DEPLOY_LABEL = "v283"
deploy.DEPLOY_NAME = "execns-helper-v283"
deploy.DEPLOY_PLAN_VERSION = "V1378"
deploy.DEPLOY_LOG_PREFIX = "v1378"
deploy.SUMMARY_TITLE = "V1378 Execns Helper v283 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1378 deploy execns helper v283 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
