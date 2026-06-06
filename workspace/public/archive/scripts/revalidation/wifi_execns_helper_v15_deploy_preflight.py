#!/usr/bin/env python3
"""V384 execns helper v15 deploy/preflight wrapper.

This reuses the fail-closed V375/V382 deployment mechanics while overriding
only the version-specific helper marker, local artifact, expected hash, output
directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v384-execns-helper-v15-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v384-a90_android_execns_probe-v15/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16"
deploy.HELPER_MARKER = "a90_android_execns_probe v15"
deploy.DEPLOY_LABEL = "v15"
deploy.DEPLOY_NAME = "execns-helper-v15"
deploy.DEPLOY_PLAN_VERSION = "V384"
deploy.DEPLOY_LOG_PREFIX = "v384"
deploy.SUMMARY_TITLE = "v384 Execns Helper v15 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v384 deploy execns helper v15 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
