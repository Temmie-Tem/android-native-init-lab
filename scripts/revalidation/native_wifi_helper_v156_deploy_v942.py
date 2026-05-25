#!/usr/bin/env python3
"""V942 deploy-only wrapper for a90_android_execns_probe v156."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v942-execns-helper-v156-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v941-execns-helper-v156-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "ff5a87694bbb9c557aaaaacf61e1ceb0af9dffb3984d9f6887a2f93c8bceceb8"
base.HELPER_MARKER = "a90_android_execns_probe v156"
base.NEW_MODE = "wifi-companion-mdm-helper-runtime-contract-capture"
base.ALLOW_FLAG = "--allow-mdm-helper-runtime-contract-capture"
base.APPROVAL_PHRASE = (
    "approve v942 deploy execns helper v156 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v942-execns-helper-v156-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v156"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v942"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V942 Execns Helper v156 Deploy")
        .replace("helper v154", "helper v156")
        .replace("V930", "V942")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v156"),
        pass_ok,
        reason.replace("v154", "v156").replace("V930", "V942"),
        next_step.replace("v154", "v156").replace("V930", "V942"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
