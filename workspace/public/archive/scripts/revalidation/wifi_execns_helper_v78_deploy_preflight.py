#!/usr/bin/env python3
"""V552 execns helper v78 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v77_deploy_preflight as v77


deploy = v77.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v552-execns-helper-v78-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v552-a90_android_execns_probe-v78/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "6d381a2bdc548fc45c4d89262d02bd2d61bdb2696ba2267be1251feb7522ef88"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.HELPER_MARKER = "a90_android_execns_probe v78"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-vnd-service-manager-start-only"
deploy.DEPLOY_LABEL = "v78"
deploy.DEPLOY_NAME = "execns-helper-v78"
deploy.DEPLOY_PLAN_VERSION = "V552"
deploy.DEPLOY_LOG_PREFIX = "v552"
deploy.SUMMARY_TITLE = "v552 Execns Helper v78 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v552 deploy execns helper v78 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v78",
    "wifi_companion_start.net_window",
    "wifi_companion_net_unix",
    "wifi_companion_net_netlink",
    "wifi_companion_net_sockstat",
    "fd_links.socket_count",
    "wifi-companion-vnd-service-manager-start-only",
    "--allow-wifi-companion-start-only",
    "--allow-service-manager-start-only",
    "/vendor/bin/qrtr-ns",
    "/vendor/bin/tftp_server",
    "/vendor/bin/pd-mapper",
    "/vendor/bin/cnss-daemon",
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
        next_step = "deploy helper v78, then run V552 socket family mapper" if deploy_needed else "run V552 socket family mapper"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v78 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V552 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v78 deployed or already current; V500 preflight was rerun", "run V552 socket family mapper"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
