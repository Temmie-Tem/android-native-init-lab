#!/usr/bin/env python3
"""V992 deploy-only wrapper for a90_android_execns_probe v168."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v992-execns-helper-v168-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v991-execns-helper-v168-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "4407766d01d816e03bc81bde6ea994112cb59fb66bf9444900929db862889fa0"
base.HELPER_MARKER = "a90_android_execns_probe v168"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.ALLOW_FLAG = "--allow-android-wifi-service-window"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v992 deploy execns helper v168 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v992-execns-helper-v168-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v168"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v992"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V992 Execns Helper v168 Deploy")
        .replace("helper v154", "helper v168")
        .replace("local-helper-v154", "local-helper-v168")
        .replace("remote-helper-v154", "remote-helper-v168")
        .replace("execns-helper-v154", "execns-helper-v168")
        .replace("rebuild V929 helper v167 before deploy", "rebuild helper v168 before deploy")
        .replace("V930", "V992")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun bounded Android service-window proof with helper v168")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v168"),
        pass_ok,
        reason.replace("v154", "v168").replace("V930", "V992"),
        next_step.replace("v154", "v168").replace("V930", "V992"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
