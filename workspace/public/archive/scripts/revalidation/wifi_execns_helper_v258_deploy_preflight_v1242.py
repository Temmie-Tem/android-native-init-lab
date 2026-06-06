#!/usr/bin/env python3
"""V1242 execns helper v258 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1242-execns-helper-v258-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v258")
deploy.DEFAULT_HELPER_SHA256 = (
    "dd9bee9e2c0750c51be2151dd4b192d0612dd9269419c1641b9395d7336b6119"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v258"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v258"
deploy.DEPLOY_NAME = "execns-helper-v258"
deploy.DEPLOY_PLAN_VERSION = "V1242"
deploy.DEPLOY_LOG_PREFIX = "v1242h"
deploy.SUMMARY_TITLE = "V1242 Execns Helper v258 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1242 deploy execns helper v258 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
