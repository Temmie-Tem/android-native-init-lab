#!/usr/bin/env python3
"""V1200 execns helper v239 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1200-execns-helper-v239-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "9e2442941c80d55673d7bba4f8af588da7bb6d4cb502c187dacca88b92e3df28"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v239"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v239"
deploy.DEPLOY_NAME = "execns-helper-v239"
deploy.DEPLOY_PLAN_VERSION = "V1200"
deploy.DEPLOY_LOG_PREFIX = "v1200a"
deploy.SUMMARY_TITLE = "v1200a Execns Helper v239 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1200 deploy execns helper v239 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
