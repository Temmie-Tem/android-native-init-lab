#!/usr/bin/env python3
"""V1234 execns helper v257 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1234-execns-helper-v257-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v257")
deploy.DEFAULT_HELPER_SHA256 = (
    "66c3bc5a9cc0daa9a9a04fe7b98ebe2d7aa974798ed131adf82e5b314b2753e5"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v257"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-mdm-helper-post-wait-req-branch-snapshot"
deploy.DEPLOY_LABEL = "v257"
deploy.DEPLOY_NAME = "execns-helper-v257"
deploy.DEPLOY_PLAN_VERSION = "V1234"
deploy.DEPLOY_LOG_PREFIX = "v1234h"
deploy.SUMMARY_TITLE = "V1234 Execns Helper v257 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1234 deploy execns helper v257 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
