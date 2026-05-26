#!/usr/bin/env python3
"""V1108 execns helper v207 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1108-execns-helper-v207-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v1108-execns-helper-v207-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "57cccbae22dd325e09b40641f91fef6b3c1abbfe631186539cc68e30ea2e6a0c"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v207"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-pm-service-trigger-observer"
deploy.DEPLOY_LABEL = "v207"
deploy.DEPLOY_NAME = "execns-helper-v207"
deploy.DEPLOY_PLAN_VERSION = "V1108"
deploy.DEPLOY_LOG_PREFIX = "v1108"
deploy.SUMMARY_TITLE = "v1108 Execns Helper v207 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1108 deploy execns helper v207 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
