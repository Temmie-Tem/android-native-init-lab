#!/usr/bin/env python3
"""V557 execns helper v82 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v81_deploy_preflight as v81


deploy = v81.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v557-execns-helper-v82-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v557-a90_android_execns_probe-v82/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "643a40aa3e0bd2108f5417e30c704d490ec1c237cadfd005650732621f82a881"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.HELPER_MARKER = "a90_android_execns_probe v82"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-hal-wificond-order-start-only"
deploy.DEPLOY_LABEL = "v82"
deploy.DEPLOY_NAME = "execns-helper-v82"
deploy.DEPLOY_PLAN_VERSION = "V557"
deploy.DEPLOY_LOG_PREFIX = "v557"
deploy.SUMMARY_TITLE = "v557 Execns Helper v82 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v557 deploy execns helper v82 only; "
    "no daemon start and no Wi-Fi bring-up"
)

v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v82",
    "wifi-companion-hal-wificond-order-start-only",
    "wifi_companion_hal_order.wificond=%d",
    "/system/bin/wificond",
    "u:r:wificond:s0",
    "wifi_companion_hal_order.scan_connect_linkup=0",
    "wifi_companion_hal_order.external_ping=0",
    "wifi_companion_hal_order.qmi_payload=0",
    "--allow-wifi-companion-start-only",
    "--allow-service-manager-start-only",
    "--allow-wifi-hal-start-only",
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
        next_step = "deploy helper v82, then run V557 wificond order proof" if deploy_needed else "run V557 wificond order proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v82 deploy still requires exact approval", next_step
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V557 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v82 deployed or already current; V500 preflight was rerun", "run V557 wificond order proof"


deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
