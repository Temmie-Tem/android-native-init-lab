#!/usr/bin/env python3
"""V1213 execns helper v248 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1213-execns-helper-v248-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "e8c367e877bc96ad37beb3397e3bf519887f43651425f6f1fae1386403403f0c"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v248"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-mknod-esoc-dev-node-before-cnss"
deploy.DEPLOY_LABEL = "v248"
deploy.DEPLOY_NAME = "execns-helper-v248"
deploy.DEPLOY_PLAN_VERSION = "V1213"
deploy.DEPLOY_LOG_PREFIX = "v1213a"
deploy.SUMMARY_TITLE = "v1213a Execns Helper v248 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1213 deploy execns helper v248 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
