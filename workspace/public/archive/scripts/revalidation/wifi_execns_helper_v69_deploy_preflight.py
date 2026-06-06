#!/usr/bin/env python3
"""V539 execns helper v69 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V539 deploy approval phrase. It does not start daemons, scan, connect,
request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v66_deploy_preflight as v66


deploy = v66.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v539-execns-helper-v69-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v539-a90_android_execns_probe-v69/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "8e92cd228ad41b3fe2fedbaea3cee4d30a374213701377b3f5a5e96309facc44"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v69"
deploy.SERVICE_MODE_TOKEN = "rmt-storage-start-only"
deploy.DEPLOY_LABEL = "v69"
deploy.DEPLOY_NAME = "execns-helper-v69"
deploy.DEPLOY_PLAN_VERSION = "V539"
deploy.DEPLOY_LOG_PREFIX = "v539"
deploy.SUMMARY_TITLE = "v539 Execns Helper v69 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v539 deploy execns helper v69 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v69",
    "rmt-storage-start-only",
    "rmt_storage_start",
    "--allow-wifi-companion-start-only",
    "rmt_storage-init-root",
    "persist.log.semlevel",
    "ctl.stop:vendor.rmt_storage",
    "/vendor/bin/rmt_storage",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v69 deploy still requires exact approval", "deploy helper v69, then run V539 rmt-only proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v69 already current", "run V539 rmt-only proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V539 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v69 deployed or already current; V500 preflight was rerun", "run V539 rmt-only proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
