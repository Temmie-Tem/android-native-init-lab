#!/usr/bin/env python3
"""V510 execns helper v58 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V510 deploy approval phrase. It does not run the private-devnode proof,
start daemons, scan, connect, request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v57_deploy_preflight as v57


deploy = v57.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v510-execns-helper-v58-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v510-a90_android_execns_probe-v58/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "85b241e504426d041f64388408f78bbfc5d955a57ca1c08690c54a9e24116a19"
deploy.HELPER_MARKER = "a90_android_execns_probe v58"
deploy.SERVICE_MODE_TOKEN = "wifi-dual-hal-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v58"
deploy.DEPLOY_NAME = "execns-helper-v58"
deploy.DEPLOY_PLAN_VERSION = "V510"
deploy.DEPLOY_LOG_PREFIX = "v510"
deploy.SUMMARY_TITLE = "v510 Execns Helper v58 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v510 deploy execns helper v58 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v58",
    "wifi-dual-hal-lshal-wait-iwifi",
    "wifi_runtime_surface",
    "dev_wlan",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v58 deploy still requires exact approval", "deploy helper v58, then run V510 private-devnode proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v58 already current", "run V510 private-devnode proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V510 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v58 deployed or already current; V500 preflight was rerun", "run V510 private-devnode proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
