#!/usr/bin/env python3
"""V387 execns helper v18 deploy/preflight wrapper.

This reuses the fail-closed V375/V382 deployment mechanics while overriding
only the version-specific helper marker, local artifact, expected hash, output
directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v387-execns-helper-v18-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v387-a90_android_execns_probe-v18/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e"
deploy.HELPER_MARKER = "a90_android_execns_probe v18"
deploy.DEPLOY_LABEL = "v18"
deploy.DEPLOY_NAME = "execns-helper-v18"
deploy.DEPLOY_PLAN_VERSION = "V387"
deploy.DEPLOY_LOG_PREFIX = "v387"
deploy.SUMMARY_TITLE = "v387 Execns Helper v18 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v387 deploy execns helper v18 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
