#!/usr/bin/env python3
"""V1200 execns helper v239 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1200-execns-helper-v240-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "c4633478c91610aa18de7da6fc4983c6bc4f8c0d02fb12511842936f850ce1f6"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v240"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v240"
deploy.DEPLOY_NAME = "execns-helper-v240"
deploy.DEPLOY_PLAN_VERSION = "V1200"
deploy.DEPLOY_LOG_PREFIX = "v1200a"
deploy.SUMMARY_TITLE = "v1200a Execns Helper v239 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1200 deploy execns helper v239 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
