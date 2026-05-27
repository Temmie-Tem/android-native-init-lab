#!/usr/bin/env python3
"""V1162 execns helper v216 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1162-execns-helper-v216-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1161-execns-helper-v216-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "b9518555ef53f8e721f8a057c8145085b3ba91899c34609c59cb1885e8b71241"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v216"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd"
deploy.DEPLOY_LABEL = "v216"
deploy.DEPLOY_NAME = "execns-helper-v216"
deploy.DEPLOY_PLAN_VERSION = "V1162"
deploy.DEPLOY_LOG_PREFIX = "v1162"
deploy.SUMMARY_TITLE = "v1162 Execns Helper v216 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1162 deploy execns helper v216 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
