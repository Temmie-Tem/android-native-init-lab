#!/usr/bin/env python3
"""V468 execns helper v34 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V468 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33


deploy = v33.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v468-execns-helper-v34-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v468-a90_android_execns_probe-v34/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "f43308d768d5921a645d3de7e31562609a772f5c800cbd619170c592d18dba66"
deploy.HELPER_MARKER = "a90_android_execns_probe v34"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v34"
deploy.DEPLOY_NAME = "execns-helper-v34"
deploy.DEPLOY_PLAN_VERSION = "V468"
deploy.DEPLOY_LOG_PREFIX = "v468"
deploy.SUMMARY_TITLE = "v468 Execns Helper v34 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v468 deploy execns helper v34 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_iwifi_registration_longwait_v468.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v34",
    "wifi-surface-composite-lshal-wait-iwifi",
    "--allow-hal-service-query",
    "lshal wait <fqinstance>",
    "android.hardware.wifi@1.0::IWifi/default",
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
