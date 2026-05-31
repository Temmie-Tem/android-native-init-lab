#!/usr/bin/env python3
"""V1341 execns helper v279 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1341-execns-helper-v279-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v279")
deploy.DEFAULT_HELPER_SHA256 = (
    "2ec7c9584e0adb09755e1066ee01a986e3b7fd719c11b8a96aaf5c500d9dd15a"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v279"
deploy.SERVICE_MODE_TOKEN = "android_pre_cnss_provider_after_per_mgr"
deploy.DEPLOY_LABEL = "v279"
deploy.DEPLOY_NAME = "execns-helper-v279"
deploy.DEPLOY_PLAN_VERSION = "V1341"
deploy.DEPLOY_LOG_PREFIX = "v1341"
deploy.SUMMARY_TITLE = "V1341 Execns Helper v279 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1341 deploy execns helper v279 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
