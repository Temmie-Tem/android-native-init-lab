#!/usr/bin/env python3
"""V1227 execns helper v254 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1227-execns-helper-v254-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "tmp/wifi/v1227-execns-helper-v254-build/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "6dd38887f6431db6748ff60d90600deb1650a37c735f05f21824d3e1b58bda8c"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v254"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-mdm-helper-only-syscall-trace"
deploy.DEPLOY_LABEL = "v254"
deploy.DEPLOY_NAME = "execns-helper-v254"
deploy.DEPLOY_PLAN_VERSION = "V1227"
deploy.DEPLOY_LOG_PREFIX = "v1227h"
deploy.SUMMARY_TITLE = "v1227h Execns Helper v254 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1227 deploy execns helper v254 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
