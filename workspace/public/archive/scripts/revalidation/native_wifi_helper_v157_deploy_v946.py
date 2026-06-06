#!/usr/bin/env python3
"""V946 deploy-only wrapper for a90_android_execns_probe v157."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v946-execns-helper-v157-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v945-execns-helper-v157-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "308b0f37bfe1265874afdc141f07c8d0b638e6d80c5093af03641f54e96371c2"
base.HELPER_MARKER = "a90_android_execns_probe v157"
base.NEW_MODE = "wifi-companion-mdm-helper-runtime-contract-capture"
base.ALLOW_FLAG = "--allow-mdm-helper-runtime-contract-capture"
base.APPROVAL_PHRASE = (
    "approve v946 deploy execns helper v157 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v946-execns-helper-v157-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v157"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v946"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V946 Execns Helper v157 Deploy")
        .replace("helper v154", "helper v157")
        .replace("V930", "V946")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v157"),
        pass_ok,
        reason.replace("v154", "v157").replace("V930", "V946"),
        next_step.replace("v154", "v157").replace("V930", "V946"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
