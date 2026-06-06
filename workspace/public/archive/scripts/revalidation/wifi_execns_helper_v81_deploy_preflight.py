#!/usr/bin/env python3
"""V556 execns helper v81 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v80_deploy_preflight as v80


deploy = v80.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v556-execns-helper-v81-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v556-a90_android_execns_probe-v81/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "b5b72889bca65a69523946afa914979f0ca8b921809f44aebb6de30debcc41c9"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v81"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-hal-order-start-only"
deploy.DEPLOY_LABEL = "v81"
deploy.DEPLOY_NAME = "execns-helper-v81"
deploy.DEPLOY_PLAN_VERSION = "V556"
deploy.DEPLOY_LOG_PREFIX = "v556"
deploy.SUMMARY_TITLE = "v556 Execns Helper v81 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v556 deploy execns helper v81 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v81",
    "wifi-companion-hal-order-start-only",
    "wifi_companion_hal_order.begin=1",
    "wifi_companion_hal_order.order=servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal,cnss_diag,cnss_daemon",
    "wifi_companion_hal_order.scan_connect_linkup=0",
    "wifi_companion_hal_order.external_ping=0",
    "wifi_companion_hal_order.qmi_payload=0",
    "--allow-wifi-companion-start-only",
    "--allow-service-manager-start-only",
    "--allow-wifi-hal-start-only",
    "--allow-qrtr-ns-readback",
    "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
    "/vendor/bin/cnss-daemon",
    "/vendor/bin/tftp_server",
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
        next_step = "deploy helper v81, then run V556 companion+HAL order proof" if deploy_needed else "run V556 companion+HAL order proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v81 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V556 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v81 deployed or already current; V500 preflight was rerun", "run V556 companion+HAL order proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
