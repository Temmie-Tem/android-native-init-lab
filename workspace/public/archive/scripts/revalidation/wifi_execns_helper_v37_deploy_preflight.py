#!/usr/bin/env python3
"""V478 execns helper v37 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V478 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v478-execns-helper-v37-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v478-a90_android_execns_probe-v37/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "5a8f94ccfe4cffc6762d28a74ac1711dbdcaa7b143fafe0dcd0d2085a1df9399"
deploy.HELPER_MARKER = "a90_android_execns_probe v37"
deploy.SERVICE_MODE_TOKEN = "selinux-domain-proof"
deploy.DEPLOY_LABEL = "v37"
deploy.DEPLOY_NAME = "execns-helper-v37"
deploy.DEPLOY_PLAN_VERSION = "V478"
deploy.DEPLOY_LOG_PREFIX = "v478"
deploy.SUMMARY_TITLE = "v478 Execns Helper v37 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v478 deploy execns helper v37 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_selinux_domain_proof_v478.py")


if __name__ == "__main__":
    raise SystemExit(deploy.main())
