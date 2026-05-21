#!/usr/bin/env python3
"""V505 execns helper v55 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V505 deploy approval phrase. It does not run the dual-HAL proof, start
daemons, scan, connect, request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v52_deploy_preflight as v52


deploy = v52.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v505-execns-helper-v55-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v505-a90_android_execns_probe-v55/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "d3e8fa14e31ee4dfc8152829b86e4549a03e8f693aa7099573eca47e9362cc7a"
deploy.HELPER_MARKER = "a90_android_execns_probe v55"
deploy.SERVICE_MODE_TOKEN = "wifi-dual-hal-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v55"
deploy.DEPLOY_NAME = "execns-helper-v55"
deploy.DEPLOY_PLAN_VERSION = "V505"
deploy.DEPLOY_LOG_PREFIX = "v505"
deploy.SUMMARY_TITLE = "v505 Execns Helper v55 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v505 deploy execns helper v55 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v33.V33_TOKENS = (
    "a90_android_execns_probe v55",
    "wifi-dual-hal-lshal-wait-iwifi",
    "wifi-dual-hal-iwifi-start-surface",
    "PROP_MSG_SETPROP|PROP_MSG_SETPROP2",
    "wifi_hal_legacy",
    "wifi_hal_ext",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v55 deploy still requires exact approval", "deploy helper v55, then run V505 dual-HAL lshal proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v55 already current", "run V505 dual-HAL lshal proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V505 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v55 deployed or already current; V500 preflight was rerun", "run V505 dual-HAL lshal IWifi proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
