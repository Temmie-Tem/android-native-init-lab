#!/usr/bin/env python3
"""V987 deploy-only wrapper for a90_android_execns_probe v167."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v987-execns-helper-v167-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v986-execns-helper-v167-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "fa96337b9103a411d6e229fe9ada744a6ed7df296f3d986e5a9d00a861736626"
base.HELPER_MARKER = "a90_android_execns_probe v167"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.ALLOW_FLAG = "--allow-android-wifi-service-window"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v987 deploy execns helper v167 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v987-execns-helper-v167-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v167"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v987"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V987 Execns Helper v167 Deploy")
        .replace("helper v154", "helper v167")
        .replace("local-helper-v154", "local-helper-v167")
        .replace("remote-helper-v154", "remote-helper-v167")
        .replace("execns-helper-v154", "execns-helper-v167")
        .replace("rebuild V929 helper v167 before deploy", "rebuild helper v167 before deploy")
        .replace("V930", "V987")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun bounded Android service-window proof with helper v167")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v167"),
        pass_ok,
        reason.replace("v154", "v167").replace("V930", "V987"),
        next_step.replace("v154", "v167")
        .replace("V930", "V987")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun bounded Android service-window proof with helper v167"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
