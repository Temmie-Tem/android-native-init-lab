#!/usr/bin/env python3
"""V565 execns helper v90 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v89_deploy_preflight as v89


deploy = v89.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v565-execns-helper-v90-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v565-a90_android_execns_probe-v90/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "0b150699f737479a3a3d970016a51d9308fb7fa47b35ba3965dbc6ac91c32907"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v90"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
deploy.DEPLOY_LABEL = "v90"
deploy.DEPLOY_NAME = "execns-helper-v90"
deploy.DEPLOY_PLAN_VERSION = "V565"
deploy.DEPLOY_LOG_PREFIX = "v565"
deploy.SUMMARY_TITLE = "v565 Execns Helper v90 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v565 deploy execns helper v90 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v90",
    "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start",
    "iwifi_start.interface_token_wire=string16-strictmode",
    "iwifi_start.mmap.ok=1",
    "wifi_companion_hal_order.iwifi_start=%d",
    "wifi_companion_hal_order.service_query=%d",
    "wifi_companion_hal_order.iwifi_start_result=%d",
    "iwifi_start.descriptor=android.hardware.wifi@1.0::IWifi",
    "wifi_hal_micro_query.variant=targeted-lshal-wait",
    "android.hardware.wifi@1.0::IWifi/default",
    "--allow-hal-service-query",
    "--allow-iwifi-start-only",
    "wifi_companion_hal_order.scan_connect_linkup=0",
    "wifi_companion_hal_order.external_ping=0",
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
        next_step = "deploy helper v90, then run V565 hwbinder mmap proof" if deploy_needed else "run V565 hwbinder mmap proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v90 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V565 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v90 deployed or already current; V500 preflight was rerun", "run V565 hwbinder mmap proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
