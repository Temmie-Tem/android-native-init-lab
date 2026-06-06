#!/usr/bin/env python3
"""V482 execns helper v41 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v40_deploy_preflight as v40


deploy = v40.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v482-execns-helper-v41-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v482-a90_android_execns_probe-v41/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "0a0c01c6978fb602e0716b4cd0960272a4257f608844d80b547c519cb6e93224"
deploy.HELPER_MARKER = "a90_android_execns_probe v41"
deploy.DEPLOY_LABEL = "v41"
deploy.DEPLOY_NAME = "execns-helper-v41"
deploy.DEPLOY_PLAN_VERSION = "V482"
deploy.DEPLOY_LOG_PREFIX = "v482"
deploy.SUMMARY_TITLE = "v482 Execns Helper v41 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v482 deploy execns helper v41 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
