#!/usr/bin/env python3
"""V1243 execns helper v259 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1243-execns-helper-v259-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v259")
deploy.DEFAULT_HELPER_SHA256 = (
    "21085ecd7ddeb8132ae52d236f5d95d47d8cc899494eaa9646f0f196d8c035e5"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v259"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v259"
deploy.DEPLOY_NAME = "execns-helper-v259"
deploy.DEPLOY_PLAN_VERSION = "V1243"
deploy.DEPLOY_LOG_PREFIX = "v1243h"
deploy.SUMMARY_TITLE = "V1243 Execns Helper v259 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1243 deploy execns helper v259 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
