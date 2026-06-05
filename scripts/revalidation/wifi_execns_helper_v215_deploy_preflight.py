#!/usr/bin/env python3
"""V1142 execns helper v215 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1142-execns-helper-v215-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1141-execns-helper-v215-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "7bf107db54e4e3b2f9bbee196d40564ab4c62b2de1bcaa392ba843a6a6f3419e"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v215"
deploy.SERVICE_MODE_TOKEN = "--allow-post-pm-mdm-helper-lower-trace"
deploy.DEPLOY_LABEL = "v215"
deploy.DEPLOY_NAME = "execns-helper-v215"
deploy.DEPLOY_PLAN_VERSION = "V1142"
deploy.DEPLOY_LOG_PREFIX = "v1142"
deploy.SUMMARY_TITLE = "v1142 Execns Helper v215 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1142 deploy execns helper v215 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
