#!/usr/bin/env python3
"""V469 execns helper v35 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V469 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33


deploy = v33.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v469-execns-helper-v35-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v469-a90_android_execns_probe-v35/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "867a38a1cf55baeb30d7d15150d02e2fbcff3e491b64c3fb11bc8ba26b9430a1"
deploy.HELPER_MARKER = "a90_android_execns_probe v35"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-lshal-wait-samsung"
deploy.DEPLOY_LABEL = "v35"
deploy.DEPLOY_NAME = "execns-helper-v35"
deploy.DEPLOY_PLAN_VERSION = "V469"
deploy.DEPLOY_LOG_PREFIX = "v469"
deploy.SUMMARY_TITLE = "v469 Execns Helper v35 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v469 deploy execns helper v35 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_samsung_wifi_registration_v469.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v35",
    "wifi-surface-composite-lshal-wait-samsung",
    "--allow-hal-service-query",
    "lshal wait <fqinstance>",
    "vendor.samsung.hardware.wifi@2.0::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.1::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.2::ISehWifi/default",
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
