#!/usr/bin/env python3
"""V1221 execns helper v253 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1221-execns-helper-v253-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "d61cae5e8b6de997aff6c06ca08140e8d8b38951ca408b3e91b6e39577329f36"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v253"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-private-cnss-daemon-sdx50m"
deploy.DEPLOY_LABEL = "v253"
deploy.DEPLOY_NAME = "execns-helper-v253"
deploy.DEPLOY_PLAN_VERSION = "V1221"
deploy.DEPLOY_LOG_PREFIX = "v1221h"
deploy.SUMMARY_TITLE = "v1221h Execns Helper v253 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1221 deploy execns helper v253 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
