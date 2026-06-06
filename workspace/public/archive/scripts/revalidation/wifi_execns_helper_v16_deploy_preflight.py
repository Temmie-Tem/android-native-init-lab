#!/usr/bin/env python3
"""V385 execns helper v16 deploy/preflight wrapper.

This reuses the fail-closed V375/V382 deployment mechanics while overriding
only the version-specific helper marker, local artifact, expected hash, output
directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v385-execns-helper-v16-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v385-a90_android_execns_probe-v16/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8"
deploy.HELPER_MARKER = "a90_android_execns_probe v16"
deploy.DEPLOY_LABEL = "v16"
deploy.DEPLOY_NAME = "execns-helper-v16"
deploy.DEPLOY_PLAN_VERSION = "V385"
deploy.DEPLOY_LOG_PREFIX = "v385"
deploy.SUMMARY_TITLE = "v385 Execns Helper v16 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v385 deploy execns helper v16 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
