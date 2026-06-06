#!/usr/bin/env python3
"""V479 execns helper v38 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V479 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v479-execns-helper-v38-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v479-a90_android_execns_probe-v38/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "71f54f6db6742c4b9bd679b74483c37d85a6190f72d8d539f8ec686d89e77c91"
deploy.HELPER_MARKER = "a90_android_execns_probe v38"
deploy.SERVICE_MODE_TOKEN = "--android-selinux-context-mode"
deploy.DEPLOY_LABEL = "v38"
deploy.DEPLOY_NAME = "execns-helper-v38"
deploy.DEPLOY_PLAN_VERSION = "V479"
deploy.DEPLOY_LOG_PREFIX = "v479"
deploy.SUMMARY_TITLE = "v479 Execns Helper v38 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v479 deploy execns helper v38 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_samsung_wifi_registration_v479.py")


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v479_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=args.command == "run" and deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", f"operator may approve {deploy.DEPLOY_PLAN_VERSION} deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v479_result and not v479_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-blocked", False, f"V479 preflight decision={v479_result.get('decision')}", "resolve V479 post-deploy blockers"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, f"helper {deploy.DEPLOY_LABEL} deployed or already current; V479 preflight is ready", "next requires separate V479 Samsung registration approval"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
