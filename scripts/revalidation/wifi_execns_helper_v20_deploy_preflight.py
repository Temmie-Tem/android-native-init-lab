#!/usr/bin/env python3
"""V390 execns helper v20 deploy/preflight wrapper.

This reuses the fail-closed V375/V382 deployment mechanics while overriding
only the version-specific helper marker, local artifact, expected hash, output
directory, and approval phrase.

The script deploys only /cache/bin/a90_android_execns_probe when explicitly
approved. It does not start Android service-manager processes and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v390-execns-helper-v20-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v390-a90_android_execns_probe-v20/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171"
deploy.HELPER_MARKER = "a90_android_execns_probe v20"
deploy.DEPLOY_LABEL = "v20"
deploy.DEPLOY_NAME = "execns-helper-v20"
deploy.DEPLOY_PLAN_VERSION = "V390"
deploy.DEPLOY_LOG_PREFIX = "v390"
deploy.SUMMARY_TITLE = "v390 Execns Helper v20 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v390 deploy execns helper v20 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
