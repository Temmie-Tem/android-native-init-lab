#!/usr/bin/env python3
"""V389 execns helper v19 deploy/preflight wrapper.

This reuses the fail-closed V375/V382 deployment mechanics while overriding
only the version-specific helper marker, local artifact, expected hash, output
directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v389-execns-helper-v19-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v389-a90_android_execns_probe-v19/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d"
deploy.HELPER_MARKER = "a90_android_execns_probe v19"
deploy.DEPLOY_LABEL = "v19"
deploy.DEPLOY_NAME = "execns-helper-v19"
deploy.DEPLOY_PLAN_VERSION = "V389"
deploy.DEPLOY_LOG_PREFIX = "v389"
deploy.SUMMARY_TITLE = "v389 Execns Helper v19 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v389 deploy execns helper v19 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
