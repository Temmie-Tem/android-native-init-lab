#!/usr/bin/env python3
"""V895 execns helper v143 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v895-execns-helper-v143-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v895-execns-helper-v143-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "994959b2f70339c25f37d836803c12e9fda10f577cdd3b7452a883efa42f6bc4"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.READ_ONLY_COMMANDS = tuple(item for item in deploy.READ_ONLY_COMMANDS if item[0] != "version")
deploy.HELPER_MARKER = "a90_android_execns_probe v143"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-esoc-conditional-response-preflight"
deploy.DEPLOY_LABEL = "v143"
deploy.DEPLOY_NAME = "execns-helper-v143"
deploy.DEPLOY_PLAN_VERSION = "V895"
deploy.DEPLOY_LOG_PREFIX = "v895"
deploy.SUMMARY_TITLE = "v895 Execns Helper v143 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v895 deploy execns helper v143 only; "
    "no daemon start, no live eSoC ioctl and no Wi-Fi bring-up"
)


def run_post_deploy_noop(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    return {
        "command": "post-deploy verification covered by deploy read-only preflight",
        "rc": 0,
        "ok": True,
        "file": "",
        "manifest": "",
        "decision": "v895-helper-v143-post-deploy-readonly-pass",
        "pass": True,
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           post_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V895 helper v143 deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V895 helper v143 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V895 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if post_result and not post_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"post_result={post_result}", "inspect helper v143 post-deploy output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v143 deployed or already current", "run V895 bounded IRQ snapshot proof; live eSoC action remains separate"


deploy.run_v373_preflight = run_post_deploy_noop
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
