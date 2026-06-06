#!/usr/bin/env python3
"""V1312 execns helper v275 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1312-execns-helper-v275-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v275")
deploy.DEFAULT_HELPER_SHA256 = (
    "66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v275"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-lower-sequence-summary-sampler"
deploy.DEPLOY_LABEL = "v275"
deploy.DEPLOY_NAME = "execns-helper-v275"
deploy.DEPLOY_PLAN_VERSION = "V1312"
deploy.DEPLOY_LOG_PREFIX = "v1312h"
deploy.SUMMARY_TITLE = "V1312 Execns Helper v275 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1312 deploy execns helper v275 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
