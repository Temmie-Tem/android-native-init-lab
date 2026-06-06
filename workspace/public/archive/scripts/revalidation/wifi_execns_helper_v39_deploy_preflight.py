#!/usr/bin/env python3
"""V480 execns helper v39 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V480 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v38_deploy_preflight as v38


deploy = v38.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v480-execns-helper-v39-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v480-a90_android_execns_probe-v39/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "950f2910b224985811a0237f47ea6ec74716077bfc523b22ea4bc0b04647ddad"
deploy.HELPER_MARKER = "a90_android_execns_probe v39"
deploy.DEPLOY_LABEL = "v39"
deploy.DEPLOY_NAME = "execns-helper-v39"
deploy.DEPLOY_PLAN_VERSION = "V480"
deploy.DEPLOY_LOG_PREFIX = "v480"
deploy.SUMMARY_TITLE = "v480 Execns Helper v39 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v480 deploy execns helper v39 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
