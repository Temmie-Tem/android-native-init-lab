#!/usr/bin/env python3
"""V1212 execns helper v247 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1212-execns-helper-v247-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "ab95cb2379083833b59da84cad111379252c29f61092767a5c4fcc95e5328c81"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v247"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-mknod-esoc-dev-node-before-cnss"
deploy.DEPLOY_LABEL = "v247"
deploy.DEPLOY_NAME = "execns-helper-v247"
deploy.DEPLOY_PLAN_VERSION = "V1212"
deploy.DEPLOY_LOG_PREFIX = "v1212a"
deploy.SUMMARY_TITLE = "v1212a Execns Helper v247 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1212 deploy execns helper v247 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
