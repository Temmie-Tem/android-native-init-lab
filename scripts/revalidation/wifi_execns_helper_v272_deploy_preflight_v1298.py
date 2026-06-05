#!/usr/bin/env python3
"""V1298 execns helper v272 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1298-execns-helper-v272-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v272")
deploy.DEFAULT_HELPER_SHA256 = (
    "1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v272"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-compact-response-sampler"
deploy.DEPLOY_LABEL = "v272"
deploy.DEPLOY_NAME = "execns-helper-v272"
deploy.DEPLOY_PLAN_VERSION = "V1298"
deploy.DEPLOY_LOG_PREFIX = "v1298h"
deploy.SUMMARY_TITLE = "V1298 Execns Helper v272 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1298 deploy execns helper v272 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
