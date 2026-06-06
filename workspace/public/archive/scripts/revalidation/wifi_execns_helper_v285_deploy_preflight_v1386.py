#!/usr/bin/env python3
"""V1386 execns helper v285 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1386-execns-helper-v285-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v285")
deploy.DEFAULT_HELPER_SHA256 = (
    "09827b6f0301f077cd0beb4ed2ae9d48a63662d0ca34eff38245704f2f724cf4"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v285"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-prepoll-corrected-rc1-enumerate"
deploy.DEPLOY_LABEL = "v285"
deploy.DEPLOY_NAME = "execns-helper-v285"
deploy.DEPLOY_PLAN_VERSION = "V1386"
deploy.DEPLOY_LOG_PREFIX = "v1386"
deploy.SUMMARY_TITLE = "V1386 Execns Helper v285 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1386 deploy execns helper v285 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
