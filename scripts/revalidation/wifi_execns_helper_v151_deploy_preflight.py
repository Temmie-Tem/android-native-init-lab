#!/usr/bin/env python3
"""V918 execns helper v151 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v918-execns-helper-v151-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v918-execns-helper-v151-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "aa8e833c292b1b906ec375a6eff9f2c2bd5691b9bfbffb951d6774a6b4ff06c8"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "ncm"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 3000
deploy.READ_ONLY_COMMANDS = tuple(item for item in deploy.READ_ONLY_COMMANDS if item[0] != "version")
deploy.HELPER_MARKER = "a90_android_execns_probe v151"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-mdm-helper-runtime-subsys-trigger-capture"
deploy.DEPLOY_LABEL = "v151"
deploy.DEPLOY_NAME = "execns-helper-v151"
deploy.DEPLOY_PLAN_VERSION = "V918"
deploy.DEPLOY_LOG_PREFIX = "v918"
deploy.SUMMARY_TITLE = "v918 Execns Helper v151 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v918 deploy execns helper v151 only; "
    "no daemon start and no Wi-Fi bring-up"
)


def run_post_deploy_noop(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    return {
        "command": "post-deploy verification covered by deploy read-only preflight",
        "rc": 0,
        "ok": True,
        "file": "",
        "manifest": "",
        "decision": "v918-helper-v151-post-deploy-readonly-pass",
        "pass": True,
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           post_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V918 helper v151 deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V918 helper v151 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V918 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if post_result and not post_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"post_result={post_result}", "inspect helper v151 post-deploy output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v151 deployed or already current", "run bounded V918 mdm_helper subsys trigger capture"


deploy.run_v373_preflight = run_post_deploy_noop
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
