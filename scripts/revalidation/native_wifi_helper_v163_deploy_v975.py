#!/usr/bin/env python3
"""V975 deploy-only wrapper for a90_android_execns_probe v163."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v975-execns-helper-v163-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v974-execns-helper-v163-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "63ea88bbb3fbe074bf38e69873957ffa1082b061cf61b03e80061d83bc94b7f1"
base.HELPER_MARKER = "a90_android_execns_probe v163"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.ALLOW_FLAG = "--allow-android-wifi-service-window"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v975 deploy execns helper v163 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v975-execns-helper-v163-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v163"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v975"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V975 Execns Helper v163 Deploy")
        .replace("helper v154", "helper v163")
        .replace("local-helper-v154", "local-helper-v163")
        .replace("remote-helper-v154", "remote-helper-v163")
        .replace("execns-helper-v154", "execns-helper-v163")
        .replace("V930", "V975")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun bounded Android service-window proof with helper v163")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v163"),
        pass_ok,
        reason.replace("v154", "v163").replace("V930", "V975"),
        next_step.replace("v154", "v163")
        .replace("V930", "V975")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun bounded Android service-window proof with helper v163"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
