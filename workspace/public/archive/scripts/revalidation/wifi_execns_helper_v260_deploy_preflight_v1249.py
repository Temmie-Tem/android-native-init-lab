#!/usr/bin/env python3
"""V1249 execns helper v260 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1249-execns-helper-v260-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v260")
deploy.DEFAULT_HELPER_SHA256 = (
    "0313d613d95c56af5681871062b7fceb47ede3c3ef8fcff534d0eea3338eaa2f"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v260"
deploy.SERVICE_MODE_TOKEN = "--allow-pmic-soft-reset-preflight"
deploy.DEPLOY_LABEL = "v260"
deploy.DEPLOY_NAME = "execns-helper-v260"
deploy.DEPLOY_PLAN_VERSION = "V1249"
deploy.DEPLOY_LOG_PREFIX = "v1249h"
deploy.SUMMARY_TITLE = "V1249 Execns Helper v260 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1249 deploy execns helper v260 only; "
    "no PMIC write, no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
