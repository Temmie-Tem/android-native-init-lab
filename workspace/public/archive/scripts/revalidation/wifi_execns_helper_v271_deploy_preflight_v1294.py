#!/usr/bin/env python3
"""V1294 execns helper v271 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1294-execns-helper-v271-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("stage3/linux_init/helpers/a90_android_execns_probe_v271")
deploy.DEFAULT_HELPER_SHA256 = (
    "335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v271"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-late-per-proxy-dense-response-sampler"
deploy.DEPLOY_LABEL = "v271"
deploy.DEPLOY_NAME = "execns-helper-v271"
deploy.DEPLOY_PLAN_VERSION = "V1294"
deploy.DEPLOY_LOG_PREFIX = "v1294h"
deploy.SUMMARY_TITLE = "V1294 Execns Helper v271 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1294 deploy execns helper v271 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
