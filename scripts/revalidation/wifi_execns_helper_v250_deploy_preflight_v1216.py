#!/usr/bin/env python3
"""V1216 execns helper v250 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1216-execns-helper-v250-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "db9531f09f2c69b7028fe2fcb10ffdbed1051f81542787a43c36fb8a553e7886"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v250"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-fake-esoc-name-sdxprairie"
deploy.DEPLOY_LABEL = "v250"
deploy.DEPLOY_NAME = "execns-helper-v250"
deploy.DEPLOY_PLAN_VERSION = "V1216"
deploy.DEPLOY_LOG_PREFIX = "v1216a"
deploy.SUMMARY_TITLE = "v1216a Execns Helper v250 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1216 deploy execns helper v250 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
