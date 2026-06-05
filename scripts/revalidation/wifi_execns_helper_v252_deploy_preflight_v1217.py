#!/usr/bin/env python3
"""V1217 execns helper v252 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1217-execns-helper-v252-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "4511f11399d4f86f5265d79eb57b2db04ae5ad869ab543565f2c657b97af8587"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v252"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-fake-esoc-name-readback-only"
deploy.DEPLOY_LABEL = "v252"
deploy.DEPLOY_NAME = "execns-helper-v252"
deploy.DEPLOY_PLAN_VERSION = "V1217"
deploy.DEPLOY_LOG_PREFIX = "v1217a"
deploy.SUMMARY_TITLE = "v1217a Execns Helper v252 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1217 deploy execns helper v252 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
