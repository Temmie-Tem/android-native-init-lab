#!/usr/bin/env python3
"""V1194 execns helper v227 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1194-execns-helper-v227-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "5916fd8e28a419f2f0391d86df274646b80abb1eb54e68bb12efaafe0295299a"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v227"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v227"
deploy.DEPLOY_NAME = "execns-helper-v227"
deploy.DEPLOY_PLAN_VERSION = "V1194"
deploy.DEPLOY_LOG_PREFIX = "v1194"
deploy.SUMMARY_TITLE = "v1194 Execns Helper v227 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1194 deploy execns helper v227 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
