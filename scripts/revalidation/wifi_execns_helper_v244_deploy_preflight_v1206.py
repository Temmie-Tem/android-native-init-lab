#!/usr/bin/env python3
"""V1206 execns helper v244 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1206-execns-helper-v244-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "693b6c306734abdf339492603db98277a1d585f37205012bb72a562ff4d2d7b9"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v244"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v244"
deploy.DEPLOY_NAME = "execns-helper-v244"
deploy.DEPLOY_PLAN_VERSION = "V1206"
deploy.DEPLOY_LOG_PREFIX = "v1206a"
deploy.SUMMARY_TITLE = "v1206a Execns Helper v244 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1206 deploy execns helper v244 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
