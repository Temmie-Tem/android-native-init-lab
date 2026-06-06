#!/usr/bin/env python3
"""V1289 execns helper v270 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1289-execns-helper-v270-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v270")
deploy.DEFAULT_HELPER_SHA256 = (
    "f1748fdc9c64a748c3270cd02a2b9bb796065b79632849e7384c2f37910f6e88"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v270"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v270"
deploy.DEPLOY_NAME = "execns-helper-v270"
deploy.DEPLOY_PLAN_VERSION = "V1289"
deploy.DEPLOY_LOG_PREFIX = "v1289h"
deploy.SUMMARY_TITLE = "V1289 Execns Helper v270 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1289 deploy execns helper v270 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
