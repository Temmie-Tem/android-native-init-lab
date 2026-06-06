#!/usr/bin/env python3
"""V386 execns helper v17 deploy/preflight wrapper.

This reuses the fail-closed V375/V382 deployment mechanics while overriding
only the version-specific helper marker, local artifact, expected hash, output
directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v386-execns-helper-v17-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v386-a90_android_execns_probe-v17/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5"
deploy.HELPER_MARKER = "a90_android_execns_probe v17"
deploy.DEPLOY_LABEL = "v17"
deploy.DEPLOY_NAME = "execns-helper-v17"
deploy.DEPLOY_PLAN_VERSION = "V386"
deploy.DEPLOY_LOG_PREFIX = "v386"
deploy.SUMMARY_TITLE = "v386 Execns Helper v17 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v386 deploy execns helper v17 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
