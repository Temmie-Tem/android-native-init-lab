#!/usr/bin/env python3
"""V1278 execns helper v267 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1278-execns-helper-v267-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v267")
deploy.DEFAULT_HELPER_SHA256 = (
    "eccd9ca475927c2a37551304fedcc6740d19aeb048ebd137f966a18c269f0337"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v267"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v267"
deploy.DEPLOY_NAME = "execns-helper-v267"
deploy.DEPLOY_PLAN_VERSION = "V1278"
deploy.DEPLOY_LOG_PREFIX = "v1278h"
deploy.SUMMARY_TITLE = "V1278 Execns Helper v267 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1278 deploy execns helper v267 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
