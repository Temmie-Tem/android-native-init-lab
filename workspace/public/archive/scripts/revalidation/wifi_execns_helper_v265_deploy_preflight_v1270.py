#!/usr/bin/env python3
"""V1270 execns helper v265 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1270-execns-helper-v265-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v265")
deploy.DEFAULT_HELPER_SHA256 = (
    "97ffa91a1aa7b8f4ab2c3a74716ae5664c703e98fe19a322351b1277fbd282b2"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v265"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v265"
deploy.DEPLOY_NAME = "execns-helper-v265"
deploy.DEPLOY_PLAN_VERSION = "V1270"
deploy.DEPLOY_LOG_PREFIX = "v1270h"
deploy.SUMMARY_TITLE = "V1270 Execns Helper v265 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1270 deploy execns helper v265 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
