#!/usr/bin/env python3
"""V1208 execns helper v245 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1208-execns-helper-v245-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "1a80cc3a113f0dd2b2aaf02d9cbe653f9bbfccfc7d3dbb24e3069d7301b2e50e"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v245"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v245"
deploy.DEPLOY_NAME = "execns-helper-v245"
deploy.DEPLOY_PLAN_VERSION = "V1208"
deploy.DEPLOY_LOG_PREFIX = "v1208a"
deploy.SUMMARY_TITLE = "v1208a Execns Helper v245 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1208 deploy execns helper v245 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
