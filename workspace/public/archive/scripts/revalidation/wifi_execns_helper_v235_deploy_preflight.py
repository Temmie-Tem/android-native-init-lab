#!/usr/bin/env python3
"""V1197 execns helper v235 deploy/preflight wrapper (PCIe enumerate trigger)."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v1197-execns-helper-v235-deploy")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
deploy.DEFAULT_HELPER_SHA256 = (
    "f208dbbd1c253241e63c6ac61b53e263ab0b5cea5563d029363c39149437dbb3"
)
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v235"
deploy.SERVICE_MODE_TOKEN = "--pm-observer-per-proxy-after-vndservice-provider"
deploy.DEPLOY_LABEL = "v235"
deploy.DEPLOY_NAME = "execns-helper-v235"
deploy.DEPLOY_PLAN_VERSION = "V1197"
deploy.DEPLOY_LOG_PREFIX = "v1197e"
deploy.SUMMARY_TITLE = "v1197e Execns Helper v235 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v1197 deploy execns helper v235 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
