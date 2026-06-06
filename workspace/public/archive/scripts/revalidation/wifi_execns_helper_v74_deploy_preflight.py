#!/usr/bin/env python3
"""V546 execns helper v74 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v66_deploy_preflight as v66


deploy = v66.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v546-execns-helper-v74-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v546-a90_android_execns_probe-v74/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "e46b87897551ea4a4cee1991758e58c90e7d668e8b98057c41ddec3a99a9d424"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v74"
deploy.SERVICE_MODE_TOKEN = "rmt-storage-start-only"
deploy.DEPLOY_LABEL = "v74"
deploy.DEPLOY_NAME = "execns-helper-v74"
deploy.DEPLOY_PLAN_VERSION = "V546"
deploy.DEPLOY_LOG_PREFIX = "v546"
deploy.SUMMARY_TITLE = "v546 Execns Helper v74 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v546 deploy execns helper v74 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v74",
    "rmt-storage-start-only",
    "wifi-companion-start-only",
    "ptrace-lite",
    "--capture-mode",
    "--allow-wifi-companion-start-only",
    "/dev/binder",
    "/vendor/bin/rmt_storage",
)


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v500_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=args.command == "run" and deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v74, then run V547 replay" if deploy_needed else "run V547 replay"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v74 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V546 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v74 deployed or already current; V500 preflight was rerun", "run V547 replay"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
