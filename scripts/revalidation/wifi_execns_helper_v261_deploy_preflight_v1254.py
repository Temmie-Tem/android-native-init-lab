#!/usr/bin/env python3
"""V1254 execns helper v261 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1254-execns-helper-v261-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v261")
deploy.DEFAULT_HELPER_SHA256 = (
    "37947e378f4743a6661a03ee36dfc95ddf5ce9cd79acec0862a28a4564573a7c"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v261"
deploy.SERVICE_MODE_TOKEN = "--allow-pmic-power-write-gate-preflight"
deploy.DEPLOY_LABEL = "v261"
deploy.DEPLOY_NAME = "execns-helper-v261"
deploy.DEPLOY_PLAN_VERSION = "V1254"
deploy.DEPLOY_LOG_PREFIX = "v1254h"
deploy.SUMMARY_TITLE = "V1254 Execns Helper v261 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1254 deploy execns helper v261 only; "
    "no PMIC write, no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
