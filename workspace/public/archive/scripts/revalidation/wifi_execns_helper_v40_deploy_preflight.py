#!/usr/bin/env python3
"""V481 execns helper v40 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V481 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v39_deploy_preflight as v39


deploy = v39.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v481-execns-helper-v40-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v481-a90_android_execns_probe-v40/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "0512be02c3f262d2d513f59f4246b781fa35393af7083e027ceaf1ebb22d73c0"
deploy.HELPER_MARKER = "a90_android_execns_probe v40"
deploy.DEPLOY_LABEL = "v40"
deploy.DEPLOY_NAME = "execns-helper-v40"
deploy.DEPLOY_PLAN_VERSION = "V481"
deploy.DEPLOY_LOG_PREFIX = "v481"
deploy.SUMMARY_TITLE = "v481 Execns Helper v40 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v481 deploy execns helper v40 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
