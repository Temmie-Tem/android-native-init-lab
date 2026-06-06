#!/usr/bin/env python3
"""V969 deploy-only wrapper for a90_android_execns_probe v161."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v969-execns-helper-v161-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v967-execns-helper-v161-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "1d936d9117e68b97c1449d9ed357560ec7ae1901eeb179da474f1dacbc837643"
base.HELPER_MARKER = "a90_android_execns_probe v161"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.ALLOW_FLAG = "--allow-android-wifi-service-window"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v969 deploy execns helper v161 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v969-execns-helper-v161-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v161"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v969"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V969 Execns Helper v161 Deploy")
        .replace("helper v154", "helper v161")
        .replace("local-helper-v154", "local-helper-v161")
        .replace("remote-helper-v154", "remote-helper-v161")
        .replace("execns-helper-v154", "execns-helper-v161")
        .replace("V930", "V969")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run one V970 Android service-window proof below scan/connect")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v161"),
        pass_ok,
        reason.replace("v154", "v161").replace("V930", "V969"),
        next_step.replace("v154", "v161")
        .replace("V930", "V969")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run one V970 Android service-window proof below scan/connect"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
