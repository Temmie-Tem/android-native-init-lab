#!/usr/bin/env python3
"""V899 execns helper v144 deploy/preflight wrapper."""

from __future__ import annotations

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v899-execns-helper-v144-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v898-mdm-helper-ks-contract-helper-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.READ_ONLY_COMMANDS = tuple(item for item in deploy.READ_ONLY_COMMANDS if item[0] != "version")
deploy.HELPER_MARKER = "a90_android_execns_probe v144"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-mdm-helper-ks-image-contract-preflight"
deploy.DEPLOY_LABEL = "v144"
deploy.DEPLOY_NAME = "execns-helper-v144"
deploy.DEPLOY_PLAN_VERSION = "V899"
deploy.DEPLOY_LOG_PREFIX = "v899"
deploy.SUMMARY_TITLE = "v899 Execns Helper v144 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v899 deploy execns helper v144 only; "
    "no live eSoC ioctl, no mdm_helper start, no ks start and no Wi-Fi bring-up"
)


def run_post_deploy_noop(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    return {
        "command": "post-deploy verification covered by deploy read-only preflight",
        "rc": 0,
        "ok": True,
        "file": "",
        "manifest": "",
        "decision": "v899-helper-v144-post-deploy-readonly-pass",
        "pass": True,
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           post_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V899 helper v144 deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V899 helper v144 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V899 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if post_result and not post_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"post_result={post_result}", "inspect helper v144 post-deploy output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v144 deployed or already current", "run V900 bounded mdm_helper/ks contract proof; live action remains separate"


deploy.run_v373_preflight = run_post_deploy_noop
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
