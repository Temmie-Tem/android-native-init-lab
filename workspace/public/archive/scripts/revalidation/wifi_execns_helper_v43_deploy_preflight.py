#!/usr/bin/env python3
"""V484 execns helper v43 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V484 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v42_deploy_preflight as v42


deploy = v42.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v484-execns-helper-v43-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v484-a90_android_execns_probe-v43/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "1b061faf5031225066d5d58fdef32512b488b72520a2d828a148c5466972ba49"
deploy.HELPER_MARKER = "a90_android_execns_probe v43"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-lshal-wait-samsung-ptrace"
deploy.DEPLOY_LABEL = "v43"
deploy.DEPLOY_NAME = "execns-helper-v43"
deploy.DEPLOY_PLAN_VERSION = "V484"
deploy.DEPLOY_LOG_PREFIX = "v484"
deploy.SUMMARY_TITLE = "v484 Execns Helper v43 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v484 deploy execns helper v43 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_samsung_wifi_hal_abort_capture_v484.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v43",
    "wifi-surface-composite-lshal-wait-samsung-ptrace",
    "property_service_shim",
    "capture.%s.siginfo.signo",
    "trace.crash_stop=1",
    "PROP_MSG_SETPROP2",
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
