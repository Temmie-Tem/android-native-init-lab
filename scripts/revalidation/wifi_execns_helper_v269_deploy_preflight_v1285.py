#!/usr/bin/env python3
"""V1285 execns helper v269 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1285-execns-helper-v269-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v269")
deploy.DEFAULT_HELPER_SHA256 = (
    "dbb1f67652913ffe94b1f083a082d8f221820040b9f28e08b226eb1e0a50fc83"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v269"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v269"
deploy.DEPLOY_NAME = "execns-helper-v269"
deploy.DEPLOY_PLAN_VERSION = "V1285"
deploy.DEPLOY_LOG_PREFIX = "v1285h"
deploy.SUMMARY_TITLE = "V1285 Execns Helper v269 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1285 deploy execns helper v269 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
