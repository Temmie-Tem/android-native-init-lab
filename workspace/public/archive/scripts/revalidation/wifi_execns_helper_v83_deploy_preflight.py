#!/usr/bin/env python3
"""V558 execns helper v83 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v82_deploy_preflight as v82


deploy = v82.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v558-execns-helper-v83-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v558-a90_android_execns_probe-v83/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "79af5542abe0c2f73641302f82b8e481654844ed983e0e4eb7ae367afb9d0111"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v83"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-hal-wificond-lshal-wait-samsung"
deploy.DEPLOY_LABEL = "v83"
deploy.DEPLOY_NAME = "execns-helper-v83"
deploy.DEPLOY_PLAN_VERSION = "V558"
deploy.DEPLOY_LOG_PREFIX = "v558"
deploy.SUMMARY_TITLE = "v558 Execns Helper v83 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v558 deploy execns helper v83 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v83",
    "wifi-companion-hal-wificond-lshal-wait-samsung",
    "wifi_companion_hal_order.service_query=%d",
    "wifi_companion_hal_order.service_query_result=%d",
    "wifi_hal_micro_query.variant=targeted-lshal-wait",
    "wifi_hal_micro_query.matched_fqinstance=%s",
    "wifi_companion_hal_order.wificond=%d",
    "/system/bin/wificond",
    "u:r:wificond:s0",
    "wifi_companion_hal_order.scan_connect_linkup=0",
    "wifi_companion_hal_order.external_ping=0",
    "wifi_companion_hal_order.qmi_payload=0",
    "--allow-hal-service-query",
    "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
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
        next_step = "deploy helper v83, then run V558 registration wait proof" if deploy_needed else "run V558 registration wait proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v83 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V558 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v83 deployed or already current; V500 preflight was rerun", "run V558 registration wait proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
