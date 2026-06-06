#!/usr/bin/env python3
"""V972 deploy-only wrapper for a90_android_execns_probe v162."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v972-execns-helper-v162-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v971-execns-helper-v162-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "c51912bd4b723beddcd54ab2f958462dff4b291ace209bd0590bc45d108d0db7"
base.HELPER_MARKER = "a90_android_execns_probe v162"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.ALLOW_FLAG = "--allow-android-wifi-service-window"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v972 deploy execns helper v162 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v972-execns-helper-v162-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v162"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v972"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V972 Execns Helper v162 Deploy")
        .replace("helper v154", "helper v162")
        .replace("local-helper-v154", "local-helper-v162")
        .replace("remote-helper-v154", "remote-helper-v162")
        .replace("execns-helper-v154", "execns-helper-v162")
        .replace("V930", "V972")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun V970 Android service-window proof with helper v162")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v162"),
        pass_ok,
        reason.replace("v154", "v162").replace("V930", "V972"),
        next_step.replace("v154", "v162")
        .replace("V930", "V972")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun V970 Android service-window proof with helper v162"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
