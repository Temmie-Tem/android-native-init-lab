#!/usr/bin/env python3
"""V1003 deploy-only wrapper for a90_android_execns_probe v170."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1003-execns-helper-v170-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "edbccfef2fd117c5264c140ff5b2f4cec5424c917151607cecc309268cd9c254"
base.HELPER_MARKER = "a90_android_execns_probe v170"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-subsys-trigger-capture"
base.ALLOW_FLAG = "--allow-android-wifi-service-window-subsys-trigger-capture"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v1003 deploy execns helper v170 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1003-execns-helper-v170-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v170"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1003"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1003 Execns Helper v170 Deploy")
        .replace("helper v154", "helper v170")
        .replace("local-helper-v154", "local-helper-v170")
        .replace("remote-helper-v154", "remote-helper-v170")
        .replace("execns-helper-v154", "execns-helper-v170")
        .replace("rebuild V929 helper v154 before deploy", "rebuild helper v170 before deploy")
        .replace("V930", "V1003")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run current-boot SELinux refresh plus service-window subsystem trigger capture")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v170"),
        pass_ok,
        reason.replace("v154", "v170").replace("V930", "V1003"),
        next_step.replace("v154", "v170")
        .replace("V930", "V1003")
        .replace("run one V931 matrix order below Wi-Fi HAL",
                 "run current-boot SELinux refresh plus service-window subsystem trigger capture"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
