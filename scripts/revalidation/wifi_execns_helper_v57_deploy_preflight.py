#!/usr/bin/env python3
"""V507 execns helper v57 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V507 deploy approval phrase. It does not run the dual-HAL runtime-gap
proof, start daemons, scan, connect, request DHCP, ping externally, or bring up
Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v56_deploy_preflight as v56


deploy = v56.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v507-execns-helper-v57-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v507-a90_android_execns_probe-v57/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "9ae5562727682a9811df7216fb522e4e1dd7271b4f5c4ca4ecf6545bb8be9afa"
deploy.HELPER_MARKER = "a90_android_execns_probe v57"
deploy.SERVICE_MODE_TOKEN = "wifi-dual-hal-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v57"
deploy.DEPLOY_NAME = "execns-helper-v57"
deploy.DEPLOY_PLAN_VERSION = "V507"
deploy.DEPLOY_LOG_PREFIX = "v507"
deploy.SUMMARY_TITLE = "v507 Execns Helper v57 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v507 deploy execns helper v57 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v57",
    "wifi-dual-hal-lshal-wait-iwifi",
    "wifi_runtime_surface",
    "proc_attr_current_captured",
    "u:r:vendor_wcnss_service:s0",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v57 deploy still requires exact approval", "deploy helper v57, then run V507 CNSS-context proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v57 already current", "run V507 CNSS-context proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V507 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v57 deployed or already current; V500 preflight was rerun", "run V507 dual-HAL CNSS-context proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
