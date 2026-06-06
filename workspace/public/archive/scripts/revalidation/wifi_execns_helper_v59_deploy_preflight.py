#!/usr/bin/env python3
"""V513 execns helper v59 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V513 deploy approval phrase. It does not run the driver-state proof,
start daemons, scan, connect, request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v58_deploy_preflight as v58


deploy = v58.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v513-execns-helper-v59-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v513-a90_android_execns_probe-v59/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "9eb52d625974470427a1dda225e11fb5c1c1dffe18c1839f27626cdca6906100"
deploy.HELPER_MARKER = "a90_android_execns_probe v59"
deploy.SERVICE_MODE_TOKEN = "wifi-dual-hal-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v59"
deploy.DEPLOY_NAME = "execns-helper-v59"
deploy.DEPLOY_PLAN_VERSION = "V513"
deploy.DEPLOY_LOG_PREFIX = "v513"
deploy.SUMMARY_TITLE = "v513 Execns Helper v59 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v513 deploy execns helper v59 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v59",
    "wifi-dual-hal-lshal-wait-iwifi",
    "wifi_runtime_surface",
    "dev_wlan",
    "wlan_driver_state_on",
    "--allow-wlan-driver-state-on",
    "CAP_NET_ADMIN,CAP_NET_RAW",
)


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v500_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v59 deploy still requires exact approval", "deploy helper v59, then run V513 driver-state proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v59 already current", "run V513 driver-state proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V513 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v59 deployed or already current; V500 preflight was rerun", "run V513 dual-HAL driver-state proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
