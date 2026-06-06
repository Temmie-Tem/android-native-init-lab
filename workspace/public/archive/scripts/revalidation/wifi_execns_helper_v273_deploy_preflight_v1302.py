#!/usr/bin/env python3
"""V1302 execns helper v273 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1302-execns-helper-v273-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v273")
deploy.DEFAULT_HELPER_SHA256 = (
    "dd1d15a5ef01189526720814c50b007f6dc9a0f25e9239caf0e9da34c65b6b46"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v273"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-compact-response-sampler"
deploy.DEPLOY_LABEL = "v273"
deploy.DEPLOY_NAME = "execns-helper-v273"
deploy.DEPLOY_PLAN_VERSION = "V1302"
deploy.DEPLOY_LOG_PREFIX = "v1302h"
deploy.SUMMARY_TITLE = "V1302 Execns Helper v273 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1302 deploy execns helper v273 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
