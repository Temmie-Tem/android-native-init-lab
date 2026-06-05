#!/usr/bin/env python3
"""V1354 execns helper v281 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1354-execns-helper-v281-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v281")
deploy.DEFAULT_HELPER_SHA256 = (
    "a68b2fb226d02d949890781ff72af8853958fcfb073a8d055068a48ba50d8c6f"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v281"
deploy.SERVICE_MODE_TOKEN = "mdm2ap_timing.pcie1_clkref_seen"
deploy.DEPLOY_LABEL = "v281"
deploy.DEPLOY_NAME = "execns-helper-v281"
deploy.DEPLOY_PLAN_VERSION = "V1354"
deploy.DEPLOY_LOG_PREFIX = "v1354"
deploy.SUMMARY_TITLE = "V1354 Execns Helper v281 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1354 deploy execns helper v281 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
