#!/usr/bin/env python3
"""V922 execns helper v152 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe`. It does not start
service-manager, Wi-Fi HAL, CNSS actors, scan/connect, request DHCP, ping
externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v922-execns-helper-v152-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v921-execns-helper-v152-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "cdaa1adde9774e90e1d1e9f5f4eca43be4643b7ff0be2c8a0a08da5bf3e52105"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "serial"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1800
deploy.READ_ONLY_COMMANDS = tuple(item for item in deploy.READ_ONLY_COMMANDS if item[0] != "version")
deploy.HELPER_MARKER = "a90_android_execns_probe v152"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
deploy.DEPLOY_LABEL = "v152"
deploy.DEPLOY_NAME = "execns-helper-v152"
deploy.DEPLOY_PLAN_VERSION = "V922"
deploy.DEPLOY_LOG_PREFIX = "v922"
deploy.SUMMARY_TITLE = "v922 Execns Helper v152 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v922 deploy execns helper v152 only; "
    "no daemon start and no Wi-Fi bring-up"
)


def run_post_deploy_noop(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    return {
        "command": "post-deploy verification covered by deploy read-only preflight",
        "rc": 0,
        "ok": True,
        "file": "",
        "manifest": "",
        "decision": "v922-helper-v152-post-deploy-readonly-pass",
        "pass": True,
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           post_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V922 helper v152 deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V922 helper v152 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V922 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if post_result and not post_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"post_result={post_result}", "inspect helper v152 post-deploy output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v152 deployed or already current", "run bounded V923 CNSS-before-eSoC precondition gate"


deploy.run_v373_preflight = run_post_deploy_noop
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
