#!/usr/bin/env python3
"""V542 execns helper v72 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V542 deploy approval phrase. It does not start daemons, scan, connect,
request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v66_deploy_preflight as v66


deploy = v66.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v542-execns-helper-v72-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v542-a90_android_execns_probe-v72/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "30c15d7dc33f537753ab0aecd45280a598e6d480340c6fb6f53f26573a96d2cd"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v72"
deploy.SERVICE_MODE_TOKEN = "rmt-storage-start-only"
deploy.DEPLOY_LABEL = "v72"
deploy.DEPLOY_NAME = "execns-helper-v72"
deploy.DEPLOY_PLAN_VERSION = "V542"
deploy.DEPLOY_LOG_PREFIX = "v542"
deploy.SUMMARY_TITLE = "v542 Execns Helper v72 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v542 deploy execns helper v72 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v72",
    "rmt-storage-start-only",
    "wifi-companion-start-only",
    "ptrace-lite",
    "--capture-mode",
    "--allow-wifi-companion-start-only",
    "rmt_storage-init-root",
    "debug.ld.app.cnss-daemon",
    "persist.vendor.cnss-daemon.hw_trc_disable_override",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v72 deploy still requires exact approval", "deploy helper v72, then run V543 ptrace capture"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v72 already current", "run V543 ptrace capture"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V542 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v72 deployed or already current; V500 preflight was rerun", "run V543 ptrace capture"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
