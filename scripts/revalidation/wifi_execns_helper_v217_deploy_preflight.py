#!/usr/bin/env python3
"""V1165 execns helper v217 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1165-execns-helper-v217-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1165-execns-helper-v217-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "559adaf4b2acd4c0a84d6f4082eb9bdd085717b9a875eec8766d803b51257a6f"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v217"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd"
deploy.DEPLOY_LABEL = "v217"
deploy.DEPLOY_NAME = "execns-helper-v217"
deploy.DEPLOY_PLAN_VERSION = "V1165"
deploy.DEPLOY_LOG_PREFIX = "v1165"
deploy.SUMMARY_TITLE = "v1165 Execns Helper v217 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1165 deploy execns helper v217 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
