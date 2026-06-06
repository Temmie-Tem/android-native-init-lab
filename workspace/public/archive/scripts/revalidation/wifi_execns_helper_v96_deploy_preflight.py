#!/usr/bin/env python3
"""V579 execns helper v96 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v95_deploy_preflight as v95


deploy = v95.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v579-execns-helper-v96-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v579-a90_android_execns_probe-v96/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "97982aa10d61297691ac87688336fb51183d21a70958660697c7462e009b84f0"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1400
deploy.HELPER_MARKER = "a90_android_execns_probe v96"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
deploy.DEPLOY_LABEL = "v96"
deploy.DEPLOY_NAME = "execns-helper-v96"
deploy.DEPLOY_PLAN_VERSION = "V579"
deploy.DEPLOY_LOG_PREFIX = "v579"
deploy.SUMMARY_TITLE = "v579 Execns Helper v96 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v579 deploy execns helper v96 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v96",
    "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start",
    "--allow-wlan-driver-state-on",
    "wifi_companion_hal_order.qcwlanstate_write=%d",
    "wifi_companion_hal_order.allow_wlan_driver_state_on=%d",
    "rmt_storage-init-root",
    "tftp_server-init-root",
    "iwifi_start.interface_token_wire_order=string16-strictmode,cstring",
    "iwifi_start.mmap.ok=1",
    "iwifi_start.service_retained=%d",
    "iwifi_start.start.wifi_status_decoded=%d",
    "iwifi_start.start.wifi_status_code=%u",
    "iwifi_start.start.wifi_status_name=%s",
    "wifi_companion_hal_order.iwifi_start_result=%d",
    "wifi_companion_hal_order.scan_connect_linkup=0",
    "wifi_companion_hal_order.external_ping=0",
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
        next_step = "deploy helper v96, then run V579 combined proof" if deploy_needed else "run V579 combined proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v96 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V579 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v96 deployed or already current; V500 preflight was rerun", "run V579 combined proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
