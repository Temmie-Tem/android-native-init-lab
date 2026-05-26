#!/usr/bin/env python3
"""V962 deploy-only wrapper for a90_android_execns_probe v160."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v962-execns-helper-v160-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v961-execns-helper-v160-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "2b4d621b111fa8e0e24a3591dd233478ac1d94ca87fa8c0eb1541db4d6d11998"
base.HELPER_MARKER = "a90_android_execns_probe v160"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
base.ORDER_ENUM = "--subsys-trigger-gate wlfw-precondition|post-provider-no-wlfw"
base.APPROVAL_PHRASE = (
    "approve v962 deploy execns helper v160 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v962-execns-helper-v160-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v160"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v962"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V962 Execns Helper v160 Deploy")
        .replace("helper v154", "helper v160")
        .replace("local-helper-v154", "local-helper-v160")
        .replace("remote-helper-v154", "remote-helper-v160")
        .replace("execns-helper-v154", "execns-helper-v160")
        .replace("V930", "V962")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v160"),
        pass_ok,
        reason.replace("v154", "v160").replace("V930", "V962"),
        next_step.replace("v154", "v160").replace("V930", "V962"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
