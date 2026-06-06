#!/usr/bin/env python3
"""V566 execns helper v91 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v90_deploy_preflight as v90


deploy = v90.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v566-execns-helper-v91-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v566-a90_android_execns_probe-v91/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "3246fade6f0a484b6cbc416a64c3884d686dc4f9b2dd35ae8a3f656516893f85"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v91"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
deploy.DEPLOY_LABEL = "v91"
deploy.DEPLOY_NAME = "execns-helper-v91"
deploy.DEPLOY_PLAN_VERSION = "V566"
deploy.DEPLOY_LOG_PREFIX = "v566"
deploy.SUMMARY_TITLE = "v566 Execns Helper v91 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v566 deploy execns helper v91 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v91",
    "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start",
    "iwifi_start.interface_token_wire_order=string16-strictmode,cstring",
    "iwifi_start.mmap.ok=1",
    "iwifi_start.get.%d.%zu.%zu.token_wire=%s",
    "iwifi_start.service_token_wire=%s",
    "iwifi_start.start.token_wire=%s",
    "reply.status_name=%s",
    "BAD_TYPE",
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
        next_step = "deploy helper v91, then run V566 hwbinder token-compat proof" if deploy_needed else "run V566 hwbinder token-compat proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v91 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V566 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v91 deployed or already current; V500 preflight was rerun", "run V566 hwbinder token-compat proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
