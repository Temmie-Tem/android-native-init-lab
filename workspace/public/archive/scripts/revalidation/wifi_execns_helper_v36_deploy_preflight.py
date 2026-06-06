#!/usr/bin/env python3
"""V470 execns helper v36 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V470 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33


deploy = v33.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v470-execns-helper-v36-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v470-a90_android_execns_probe-v36/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "9d219f2c28102a8c56d3b283b37c14af12603d9c89700240f3a3d980b5f7de7f"
deploy.HELPER_MARKER = "a90_android_execns_probe v36"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-lshal-wait-samsung"
deploy.DEPLOY_LABEL = "v36"
deploy.DEPLOY_NAME = "execns-helper-v36"
deploy.DEPLOY_PLAN_VERSION = "V470"
deploy.DEPLOY_LOG_PREFIX = "v470"
deploy.SUMMARY_TITLE = "v470 Execns Helper v36 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v470 deploy execns helper v36 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_samsung_wifi_registration_v469.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v36",
    "wifi-surface-composite-lshal-wait-samsung",
    "ro.property_service.version",
    "init.svc.vendor.wifi_hal_ext",
    "wlan.driver.status",
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
