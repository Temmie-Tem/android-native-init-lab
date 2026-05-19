#!/usr/bin/env python3
"""V382 execns helper v14 deploy/preflight wrapper.

This intentionally reuses the fail-closed V375 deployment mechanics while
overriding only the version-specific helper marker, local artifact, expected
hash, output directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v382-execns-helper-v14-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7"
deploy.HELPER_MARKER = "a90_android_execns_probe v14"
deploy.DEPLOY_LABEL = "v14"
deploy.DEPLOY_NAME = "execns-helper-v14"
deploy.DEPLOY_PLAN_VERSION = "V382"
deploy.DEPLOY_LOG_PREFIX = "v382"
deploy.SUMMARY_TITLE = "v382 Execns Helper v14 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v382 deploy execns helper v14 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
