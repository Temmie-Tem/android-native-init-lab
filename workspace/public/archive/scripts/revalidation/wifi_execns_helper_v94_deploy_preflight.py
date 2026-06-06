#!/usr/bin/env python3
"""V570 execns helper v94 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v93_deploy_preflight as v93


deploy = v93.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v570-execns-helper-v94-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v570-a90_android_execns_probe-v94/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "8030c00267a35581406f6faf487090e081133f5aca1967b6d2edeae737db3948"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v94"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
deploy.DEPLOY_LABEL = "v94"
deploy.DEPLOY_NAME = "execns-helper-v94"
deploy.DEPLOY_PLAN_VERSION = "V570"
deploy.DEPLOY_LOG_PREFIX = "v570"
deploy.SUMMARY_TITLE = "v570 Execns Helper v94 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v570 deploy execns helper v94 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v94",
    "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start",
    "rmt_storage-android-runtime",
    "tftp_server-android-runtime",
    "iwifi_start.interface_token_wire_order=string16-strictmode,cstring",
    "iwifi_start.mmap.ok=1",
    "iwifi_start.service_retained=%d",
    "iwifi_start.start.wifi_status_decoded=%d",
    "iwifi_start.start.wifi_status_code=%u",
    "iwifi_start.start.wifi_status_name=%s",
    "wifi_companion_hal_order.iwifi_start_result=%d",
    "wifi_companion_qrtr_readback.reason=missing-allow-qrtr-ns-readback",
    "android.hardware.wifi@1.0::IWifi/default",
    "--allow-hal-service-query",
    "--allow-iwifi-start-only",
    "--allow-qrtr-ns-readback",
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
        next_step = "deploy helper v94, then run V570 rmt/tftp identity retry" if deploy_needed else "run V570 rmt/tftp identity retry"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v94 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V570 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v94 deployed or already current; V500 preflight was rerun", "run V570 rmt/tftp identity retry"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
