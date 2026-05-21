#!/usr/bin/env python3
"""V506 execns helper v56 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V506 deploy approval phrase. It does not run the dual-HAL runtime-gap
proof, start daemons, scan, connect, request DHCP, ping externally, or bring up
Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v52_deploy_preflight as v52


deploy = v52.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v506-execns-helper-v56-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v506-a90_android_execns_probe-v56/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "b4c08bf0e7243996101a4d6ebf10292be1e03d0d9134c210c03dd5be26e5e67e"
deploy.HELPER_MARKER = "a90_android_execns_probe v56"
deploy.SERVICE_MODE_TOKEN = "wifi-dual-hal-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v56"
deploy.DEPLOY_NAME = "execns-helper-v56"
deploy.DEPLOY_PLAN_VERSION = "V506"
deploy.DEPLOY_LOG_PREFIX = "v506"
deploy.SUMMARY_TITLE = "v506 Execns Helper v56 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v506 deploy execns helper v56 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v33.V33_TOKENS = (
    "a90_android_execns_probe v56",
    "wifi-dual-hal-lshal-wait-iwifi",
    "wifi_runtime_surface",
    "proc_attr_current_captured",
    "CAP_NET_ADMIN,CAP_NET_RAW",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v56 deploy still requires exact approval", "deploy helper v56, then run V506 runtime-gap proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v56 already current", "run V506 runtime-gap proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V506 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v56 deployed or already current; V500 preflight was rerun", "run V506 dual-HAL runtime-gap proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
