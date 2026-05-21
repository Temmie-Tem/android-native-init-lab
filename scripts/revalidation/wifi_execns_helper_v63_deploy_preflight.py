#!/usr/bin/env python3
"""V530 execns helper v63 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V530 deploy approval phrase. It does not start daemons, scan, connect,
request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v62_deploy_preflight as v62


deploy = v62.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v530-execns-helper-v63-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v530-a90_android_execns_probe-v63/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "6ee31adef3eb26334376ac55043c2f3993ef8ea21b40022c906dbb3005b2de51"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v63"
deploy.SERVICE_MODE_TOKEN = "rmt-storage-start-only"
deploy.DEPLOY_LABEL = "v63"
deploy.DEPLOY_NAME = "execns-helper-v63"
deploy.DEPLOY_PLAN_VERSION = "V530"
deploy.DEPLOY_LOG_PREFIX = "v530"
deploy.SUMMARY_TITLE = "v530 Execns Helper v63 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v530 deploy execns helper v63 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v63",
    "rmt-storage-start-only",
    "rmt_storage_start",
    "--allow-wifi-companion-start-only",
    "rmt_storage-init-root",
    "android-init-root",
    "/dev/block/bootdevice/by-name",
    "/sys/class/uio/uio0/dev",
    "/sys/power/wake_lock",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v63 deploy still requires exact approval", "deploy helper v63, then run V530 rmt-only proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v63 already current", "run V530 rmt-only proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V530 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v63 deployed or already current; V500 preflight was rerun", "run V530 rmt-only proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
