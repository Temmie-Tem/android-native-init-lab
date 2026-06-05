#!/usr/bin/env python3
"""V1209 execns helper v246 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1209-execns-helper-v246-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "3c46f8cf3394762485b328215000da14599f16a9a7a63e5d69312f84d6b1d435"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v246"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v246"
deploy.DEPLOY_NAME = "execns-helper-v246"
deploy.DEPLOY_PLAN_VERSION = "V1209"
deploy.DEPLOY_LOG_PREFIX = "v1209a"
deploy.SUMMARY_TITLE = "v1209a Execns Helper v246 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1209 deploy execns helper v246 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
