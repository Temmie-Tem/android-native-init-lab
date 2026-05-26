#!/usr/bin/env python3
"""V1007 deploy-only wrapper for a90_android_execns_probe v171."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1007-execns-helper-v171-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1006-execns-helper-v171-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "347f38ab24d67bf300bd6dccd033a081328ec5afdd711b49f3d0d2f9328cf3a1"
base.HELPER_MARKER = "a90_android_execns_probe v171"
base.NEW_MODE = "wifi-companion-android-wifi-service-window-subsys-trigger-capture"
base.ALLOW_FLAG = "--allow-android-wifi-service-window-subsys-trigger-capture"
base.ORDER_ENUM = "--allow-android-wifi-service-window"
base.COMPACT_MODE = "wifi-companion-android-wifi-service-window-start-only"
base.APPROVAL_PHRASE = (
    "approve v1007 deploy execns helper v171 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1007-execns-helper-v171-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v171"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1007"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1007 Execns Helper v171 Deploy")
        .replace("helper v154", "helper v171")
        .replace("local-helper-v154", "local-helper-v171")
        .replace("remote-helper-v154", "remote-helper-v171")
        .replace("execns-helper-v154", "execns-helper-v171")
        .replace("rebuild V929 helper v154 before deploy", "rebuild helper v171 before deploy")
        .replace("rebuild V929 helper v171 before deploy", "rebuild V1006 helper v171 before deploy")
        .replace("V930", "V1007")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1008 current-boot fd-poll service-window live gate")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v171"),
        pass_ok,
        reason.replace("v154", "v171").replace("V930", "V1007"),
        next_step.replace("v154", "v171")
        .replace("V930", "V1007")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1008 current-boot fd-poll service-window live gate"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
