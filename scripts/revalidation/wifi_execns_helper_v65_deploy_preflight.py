#!/usr/bin/env python3
"""V532 execns helper v65 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V532 deploy approval phrase. It does not start daemons, scan, connect,
request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v62_deploy_preflight as v62


deploy = v62.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v532-execns-helper-v65-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v532-a90_android_execns_probe-v65/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "5c6769cf65757d38622f4387ebdb53eaca41a1c3234754c8a4d6c2f2f59dee2e"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v65"
deploy.SERVICE_MODE_TOKEN = "rmt-storage-start-only"
deploy.DEPLOY_LABEL = "v65"
deploy.DEPLOY_NAME = "execns-helper-v65"
deploy.DEPLOY_PLAN_VERSION = "V532"
deploy.DEPLOY_LOG_PREFIX = "v532"
deploy.SUMMARY_TITLE = "v532 Execns Helper v65 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v532 deploy execns helper v65 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v65",
    "rmt-storage-start-only",
    "rmt_storage_start",
    "--allow-wifi-companion-start-only",
    "rmt_storage-init-root",
    "android-init-root",
    "/dev/block/bootdevice/by-name",
    "/sys/class/uio/uio0/dev",
    "/sys/class/uio/uio0/maps/map0/size",
    "/dev/kmsg",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v65 deploy still requires exact approval", "deploy helper v65, then run V532 rmt-only proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v65 already current", "run V532 rmt-only proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V532 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v65 deployed or already current; V500 preflight was rerun", "run V532 rmt-only proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
