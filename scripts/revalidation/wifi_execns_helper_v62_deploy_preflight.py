#!/usr/bin/env python3
"""V528 execns helper v62 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V528 deploy approval phrase. It does not start daemons, scan, connect,
request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v61_deploy_preflight as v61


deploy = v61.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v528-execns-helper-v62-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v528-a90_android_execns_probe-v62/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "65d9ae002ff3f1e3eef1cc9526139dec6bec57e1b989b2090c46056bd2169ed3"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v62"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-start-only"
deploy.DEPLOY_LABEL = "v62"
deploy.DEPLOY_NAME = "execns-helper-v62"
deploy.DEPLOY_PLAN_VERSION = "V528"
deploy.DEPLOY_LOG_PREFIX = "v528"
deploy.SUMMARY_TITLE = "v528 Execns Helper v62 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v528 deploy execns helper v62 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v62",
    "wifi-companion-start-only",
    "wifi_companion_start",
    "--allow-wifi-companion-start-only",
    "rmt_storage-init-root",
    "tftp_server-init-root",
    "android-init-root",
    "/vendor/bin/qrtr-ns -f",
    "/vendor/bin/rmt_storage",
    "/vendor/bin/tftp_server",
    "/vendor/bin/pd-mapper",
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v62 deploy still requires exact approval", "deploy helper v62, then run V528 companion proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v62 already current", "run V528 companion proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V528 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v62 deployed or already current; V500 preflight was rerun", "run V528 companion proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
