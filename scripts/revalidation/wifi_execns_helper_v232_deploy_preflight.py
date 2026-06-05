#!/usr/bin/env python3
"""V1197 execns helper v232 deploy/preflight wrapper (mdm_helper wchan observation)."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1197-execns-helper-v232-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "1c242cdd0cd659129d956c788e714c78130cb0633fea8f42b33e8d07f7818f37"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v232"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v232"
deploy.DEPLOY_NAME = "execns-helper-v232"
deploy.DEPLOY_PLAN_VERSION = "V1197"
deploy.DEPLOY_LOG_PREFIX = "v1197b"
deploy.SUMMARY_TITLE = "v1197b Execns Helper v232 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1197 deploy execns helper v232 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
