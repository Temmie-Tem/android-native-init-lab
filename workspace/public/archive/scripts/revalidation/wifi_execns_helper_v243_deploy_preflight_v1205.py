#!/usr/bin/env python3
"""V1205 execns helper v243 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1205-execns-helper-v243-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "ae628a539268be5f70c59208839da0fff485c6befc07bd467d874480fb6866bd"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v243"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v243"
deploy.DEPLOY_NAME = "execns-helper-v243"
deploy.DEPLOY_PLAN_VERSION = "V1205"
deploy.DEPLOY_LOG_PREFIX = "v1205a"
deploy.SUMMARY_TITLE = "v1205a Execns Helper v243 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1205 deploy execns helper v243 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
