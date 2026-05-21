#!/usr/bin/env python3
"""V504 execns helper v54 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V504 deploy approval phrase. It does not run the dual-HAL proof, start
daemons, connect, request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v52_deploy_preflight as v52


deploy = v52.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v504-execns-helper-v54-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v504-a90_android_execns_probe-v54/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "4253d2babfb40f42cc0c2aaac3e1bfa322447c375a9e89e980cd81a840082740"
deploy.HELPER_MARKER = "a90_android_execns_probe v54"
deploy.SERVICE_MODE_TOKEN = "wifi-dual-hal-iwifi-start-surface"
deploy.DEPLOY_LABEL = "v54"
deploy.DEPLOY_NAME = "execns-helper-v54"
deploy.DEPLOY_PLAN_VERSION = "V504"
deploy.DEPLOY_LOG_PREFIX = "v504"
deploy.SUMMARY_TITLE = "v504 Execns Helper v54 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v504 deploy execns helper v54 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v33.V33_TOKENS = (
    "a90_android_execns_probe v54",
    "wifi-dual-hal-iwifi-start-surface",
    "wifi_hal_composite_start.dual_hal",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v54 deploy still requires exact approval", "deploy helper v54, then run V504 legacy-property proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v54 already current", "run V504 legacy-property proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V504 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v54 deployed or already current; V500 preflight was rerun", "run V504 dual-HAL legacy-property proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
