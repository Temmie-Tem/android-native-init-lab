#!/usr/bin/env python3
"""V587 execns helper v98 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v97_deploy_preflight as v97


deploy = v97.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v587-execns-helper-v98-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v587-a90_android_execns_probe-v98/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "be9b59f20af3013e996266e35c225487d266d789455a4f656dfaa2efeacd7f23"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v98"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-start-only"
deploy.DEPLOY_LABEL = "v98"
deploy.DEPLOY_NAME = "execns-helper-v98"
deploy.DEPLOY_PLAN_VERSION = "V587"
deploy.DEPLOY_LOG_PREFIX = "v587"
deploy.SUMMARY_TITLE = "v587 Execns Helper v98 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v587 deploy execns helper v98 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v98",
    "wifi-companion-start-only",
    "wifi_companion_start.surface_%s.begin=1",
    "wifi_window_msm_subsys_devices",
    "wifi_window_rpmsg_devices",
    "wifi_window_service_notifier",
    "wifi_window_dev_filtered",
    "firmware_mnt_mount_source=%s",
    "firmware_modem_mount_source=%s",
    "rmt_storage-init-root",
    "tftp_server-init-root",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
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
        next_step = "deploy helper v98, then run V587 QRTR/modem window surface proof" if deploy_needed else "run V587 QRTR/modem window surface proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v98 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V587 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v98 deployed or already current; V500 preflight was rerun", "run V587 QRTR/modem window surface proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
