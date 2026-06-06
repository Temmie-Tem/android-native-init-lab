#!/usr/bin/env python3
"""V483 execns helper v42 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V483 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v41_deploy_preflight as v41


deploy = v41.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v483-execns-helper-v42-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v483-a90_android_execns_probe-v42/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "1204c44843c90e4b7799c6126abfd6036a6e7fbb2560ba21a9c75b3ff7878ff1"
deploy.HELPER_MARKER = "a90_android_execns_probe v42"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-lshal-wait-samsung"
deploy.DEPLOY_LABEL = "v42"
deploy.DEPLOY_NAME = "execns-helper-v42"
deploy.DEPLOY_PLAN_VERSION = "V483"
deploy.DEPLOY_LOG_PREFIX = "v483"
deploy.SUMMARY_TITLE = "v483 Execns Helper v42 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v483 deploy execns helper v42 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_samsung_wifi_registration_v483.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v42",
    "wifi-surface-composite-lshal-wait-samsung",
    "--allow-hal-service-query",
    "property_service_shim",
    "hwservicemanager.ready:true",
    "PROP_MSG_SETPROP2",
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
