#!/usr/bin/env python3
"""V1382 execns helper v284 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1382-execns-helper-v284-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v284")
deploy.DEFAULT_HELPER_SHA256 = (
    "da1f8b65cbc3872f7ec31a368bd382720a399d3a785e50ae383c800632047b9f"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v284"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-immediate-corrected-rc1-enumerate"
deploy.DEPLOY_LABEL = "v284"
deploy.DEPLOY_NAME = "execns-helper-v284"
deploy.DEPLOY_PLAN_VERSION = "V1382"
deploy.DEPLOY_LOG_PREFIX = "v1382"
deploy.SUMMARY_TITLE = "V1382 Execns Helper v284 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1382 deploy execns helper v284 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
