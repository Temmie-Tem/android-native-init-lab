#!/usr/bin/env python3
"""V560 execns helper v85 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v84_deploy_preflight as v84


deploy = v84.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v560-execns-helper-v85-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v560-a90_android_execns_probe-v85/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "e98dac60aa3317e86e7ca3053264b7d28257b8c9bd25723bff52438719c148b6"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v85"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-dual-hal-wificond-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v85"
deploy.DEPLOY_NAME = "execns-helper-v85"
deploy.DEPLOY_PLAN_VERSION = "V560"
deploy.DEPLOY_LOG_PREFIX = "v560"
deploy.SUMMARY_TITLE = "v560 Execns Helper v85 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v560 deploy execns helper v85 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v85",
    "wifi-companion-dual-hal-wificond-lshal-wait-iwifi",
    "wifi_companion_hal_order.dual_hal=%d",
    "wifi_hal_legacy",
    "wifi_hal_ext",
    "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal_legacy,wifi_hal_ext,cnss_diag,wificond,cnss_daemon",
    "android.hardware.wifi@1.0::IWifi/default",
    "wifi_hal_micro_query.variant=targeted-lshal-wait",
    "wifi_companion_hal_order.service_query_result=%d",
    "wifi_companion_hal_order.scan_connect_linkup=0",
    "wifi_companion_hal_order.external_ping=0",
    "wifi_companion_hal_order.qmi_payload=0",
    "--allow-hal-service-query",
    "/vendor/bin/hw/android.hardware.wifi@1.0-service",
    "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
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
        next_step = "deploy helper v85, then run V560 dual-HAL IWifi registration proof" if deploy_needed else "run V560 dual-HAL IWifi registration proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v85 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V560 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v85 deployed or already current; V500 preflight was rerun", "run V560 dual-HAL IWifi registration proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
