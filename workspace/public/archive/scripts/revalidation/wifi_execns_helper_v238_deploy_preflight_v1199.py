#!/usr/bin/env python3
"""V1199 execns helper v238 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1199-execns-helper-v238-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "867f96632b07481c4244bcd7635cec65fc782e9905cb2313630563f0f4e4516a"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v238"
deploy.SERVICE_MODE_TOKEN = "--allow-esoc-img-xfer-mhi-observe"
deploy.DEPLOY_LABEL = "v238"
deploy.DEPLOY_NAME = "execns-helper-v238"
deploy.DEPLOY_PLAN_VERSION = "V1199"
deploy.DEPLOY_LOG_PREFIX = "v1199a"
deploy.SUMMARY_TITLE = "v1199a Execns Helper v238 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1199 deploy execns helper v238 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
