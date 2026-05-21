#!/usr/bin/env python3
"""V516 execns helper v60 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V516 deploy approval phrase. It does not start daemons, scan, connect,
request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v59_deploy_preflight as v59


deploy = v59.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v516-execns-helper-v60-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v516-a90_android_execns_probe-v60/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "1a447e5e4ff1f6ae8fa3fc4666c4dacee3b760824d09c51d11a8289760a2e76b"
deploy.HELPER_MARKER = "a90_android_execns_probe v60"
deploy.SERVICE_MODE_TOKEN = "cnss-userspace-readiness"
deploy.DEPLOY_LABEL = "v60"
deploy.DEPLOY_NAME = "execns-helper-v60"
deploy.DEPLOY_PLAN_VERSION = "V516"
deploy.DEPLOY_LOG_PREFIX = "v516"
deploy.SUMMARY_TITLE = "v516 Execns Helper v60 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v516 deploy execns helper v60 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v60",
    "cnss-userspace-readiness",
    "cnss_userspace_readiness",
    "--allow-cnss-userspace-readiness",
    "/vendor/bin/cnss_diag -q -f -t HELIUM",
    "/vendor/bin/cnss-daemon -n -l",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v60 deploy still requires exact approval", "deploy helper v60, then run V516 CNSS userspace readiness proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v60 already current", "run V516 CNSS userspace readiness proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V516 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v60 deployed or already current; V500 preflight was rerun", "run V516 CNSS userspace readiness proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
