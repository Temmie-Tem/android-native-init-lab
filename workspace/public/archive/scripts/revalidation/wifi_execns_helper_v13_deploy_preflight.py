#!/usr/bin/env python3
"""V380 execns helper v13 deploy/preflight wrapper.

This intentionally reuses the fail-closed V375 deployment mechanics while
overriding only the version-specific helper marker, local artifact, expected
hash, output directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v380-execns-helper-v13-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v379-a90_android_execns_probe-v13/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "9866c8f1e7c346906f4a400ee431ea35ed3880c157e5ee4e8b1757377dcfffa8"
deploy.HELPER_MARKER = "a90_android_execns_probe v13"
deploy.DEPLOY_LABEL = "v13"
deploy.DEPLOY_NAME = "execns-helper-v13"
deploy.DEPLOY_PLAN_VERSION = "V380"
deploy.DEPLOY_LOG_PREFIX = "v380"
deploy.SUMMARY_TITLE = "v380 Execns Helper v13 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v380 deploy execns helper v13 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
