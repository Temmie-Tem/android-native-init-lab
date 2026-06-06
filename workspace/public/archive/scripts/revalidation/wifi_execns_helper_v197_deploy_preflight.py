#!/usr/bin/env python3
"""V1085 execns helper v197 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1085-execns-helper-v197-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1085-execns-helper-v197-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "8dbf5aed1a3d087fc59c308bd674132e19c9cf2da0c42843b64c9c4efaf1672f"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v197"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v197"
deploy.DEPLOY_NAME = "execns-helper-v197"
deploy.DEPLOY_PLAN_VERSION = "V1085"
deploy.DEPLOY_LOG_PREFIX = "v1085"
deploy.SUMMARY_TITLE = "v1085 Execns Helper v197 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1085 deploy execns helper v197 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
