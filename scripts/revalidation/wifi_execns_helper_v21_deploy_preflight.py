#!/usr/bin/env python3
"""V392 execns helper v21 deploy/preflight wrapper.

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
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v392-execns-helper-v21-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v392-a90_android_execns_probe-v21/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8"
deploy.HELPER_MARKER = "a90_android_execns_probe v21"
deploy.DEPLOY_LABEL = "v21"
deploy.DEPLOY_NAME = "execns-helper-v21"
deploy.DEPLOY_PLAN_VERSION = "V392"
deploy.DEPLOY_LOG_PREFIX = "v392"
deploy.SUMMARY_TITLE = "v392 Execns Helper v21 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v392 deploy execns helper v21 only; "
    "no daemon start and no Wi-Fi bring-up"
)


if __name__ == "__main__":
    raise SystemExit(deploy.main())
