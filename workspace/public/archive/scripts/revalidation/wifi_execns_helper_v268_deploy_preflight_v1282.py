#!/usr/bin/env python3
"""V1282 execns helper v268 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1282-execns-helper-v268-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v268")
deploy.DEFAULT_HELPER_SHA256 = (
    "e86db44aad14e54572d88d77c1ea2019ea28b1f91c01f7a9af9e6eabc690a3ba"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v268"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-response-sampler"
deploy.DEPLOY_LABEL = "v268"
deploy.DEPLOY_NAME = "execns-helper-v268"
deploy.DEPLOY_PLAN_VERSION = "V1282"
deploy.DEPLOY_LOG_PREFIX = "v1282h"
deploy.SUMMARY_TITLE = "V1282 Execns Helper v268 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1282 deploy execns helper v268 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
