#!/usr/bin/env python3
"""V1214 execns helper v249 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1214-execns-helper-v249-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "53698377bcc86468da971b917106fc9c8cc5b8eb2b64cfce0c4acb6bb572c239"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v249"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-mknod-esoc-dev-node-before-cnss"
deploy.DEPLOY_LABEL = "v249"
deploy.DEPLOY_NAME = "execns-helper-v249"
deploy.DEPLOY_PLAN_VERSION = "V1214"
deploy.DEPLOY_LOG_PREFIX = "v1214a"
deploy.SUMMARY_TITLE = "v1214a Execns Helper v249 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1214 deploy execns helper v249 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
