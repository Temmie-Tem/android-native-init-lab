#!/usr/bin/env python3
"""V1202 execns helper v242 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1202-execns-helper-v242-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "affc335d580bbb016c651b19d44998ec755e9471fd2fff1ae7784c63861fe3fc"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v242"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-set-mdm-helper-selinux-context"
deploy.DEPLOY_LABEL = "v242"
deploy.DEPLOY_NAME = "execns-helper-v242"
deploy.DEPLOY_PLAN_VERSION = "V1202"
deploy.DEPLOY_LOG_PREFIX = "v1202a"
deploy.SUMMARY_TITLE = "v1202a Execns Helper v242 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1202 deploy execns helper v242 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
