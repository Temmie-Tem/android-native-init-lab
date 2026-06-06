#!/usr/bin/env python3
"""V1308 execns helper v274 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1308-execns-helper-v274-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v274")
deploy.DEFAULT_HELPER_SHA256 = (
    "eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v274"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-pmic-gdsc-transition-sampler"
deploy.DEPLOY_LABEL = "v274"
deploy.DEPLOY_NAME = "execns-helper-v274"
deploy.DEPLOY_PLAN_VERSION = "V1308"
deploy.DEPLOY_LOG_PREFIX = "v1308h"
deploy.SUMMARY_TITLE = "V1308 Execns Helper v274 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1308 deploy execns helper v274 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
