#!/usr/bin/env python3
"""V1179 execns helper v218 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1179-execns-helper-v218-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1179-execns-helper-v218-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "12c98f2563a5fbea3e5cfdd5a1874b16e41e24b5ae47b975ccd02ffcef2a4d31"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v218"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-pph-delta-ms"
deploy.DEPLOY_LABEL = "v218"
deploy.DEPLOY_NAME = "execns-helper-v218"
deploy.DEPLOY_PLAN_VERSION = "V1179"
deploy.DEPLOY_LOG_PREFIX = "v1179"
deploy.SUMMARY_TITLE = "v1179 Execns Helper v218 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1179 deploy execns helper v218 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
