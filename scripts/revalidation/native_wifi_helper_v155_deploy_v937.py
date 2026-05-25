#!/usr/bin/env python3
"""V937 deploy-only wrapper for a90_android_execns_probe v155."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v937-execns-helper-v155-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v936-execns-helper-v155-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "44d7820e7bc33ab9886ea4f5f39248b1902c404c694c48fcd00a3ecc0fb76063"
base.HELPER_MARKER = "a90_android_execns_probe v155"
base.NEW_MODE = "wifi-companion-mdm-helper-runtime-contract-capture"
base.ALLOW_FLAG = "--allow-mdm-helper-runtime-contract-capture"
base.APPROVAL_PHRASE = (
    "approve v937 deploy execns helper v155 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v937-execns-helper-v155-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v155"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v937"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V937 Execns Helper v155 Deploy")
        .replace("helper v154", "helper v155")
        .replace("V930", "V937")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v155"),
        pass_ok,
        reason.replace("v154", "v155").replace("V930", "V937"),
        next_step.replace("v154", "v155").replace("V930", "V937"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
