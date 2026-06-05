#!/usr/bin/env python3
"""V1195 execns helper v229 deploy/preflight wrapper (mdm3 restart_level=RELATED)."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1195-execns-helper-v229-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "aac9094a0c583e51f5fadca6a8451599ce6148a5f7c1a9f92e3a66b2310806ea"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v229"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v229"
deploy.DEPLOY_NAME = "execns-helper-v229"
deploy.DEPLOY_PLAN_VERSION = "V1195"
deploy.DEPLOY_LOG_PREFIX = "v1195"
deploy.SUMMARY_TITLE = "v1195 Execns Helper v229 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1195 deploy execns helper v229 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
