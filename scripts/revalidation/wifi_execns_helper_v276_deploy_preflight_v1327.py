#!/usr/bin/env python3
"""V1327 execns helper v276 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1327-execns-helper-v276-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v276")
deploy.DEFAULT_HELPER_SHA256 = (
    "dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v276"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler"
deploy.DEPLOY_LABEL = "v276"
deploy.DEPLOY_NAME = "execns-helper-v276"
deploy.DEPLOY_PLAN_VERSION = "V1327"
deploy.DEPLOY_LOG_PREFIX = "v1327h"
deploy.SUMMARY_TITLE = "V1327 Execns Helper v276 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1327 deploy execns helper v276 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
