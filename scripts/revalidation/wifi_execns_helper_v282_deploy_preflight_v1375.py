#!/usr/bin/env python3
"""V1375 execns helper v282 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1375-execns-helper-v282-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v282")
deploy.DEFAULT_HELPER_SHA256 = (
    "c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v282"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-corrected-rc1-enumerate"
deploy.DEPLOY_LABEL = "v282"
deploy.DEPLOY_NAME = "execns-helper-v282"
deploy.DEPLOY_PLAN_VERSION = "V1375"
deploy.DEPLOY_LOG_PREFIX = "v1375"
deploy.SUMMARY_TITLE = "V1375 Execns Helper v282 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1375 deploy execns helper v282 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
