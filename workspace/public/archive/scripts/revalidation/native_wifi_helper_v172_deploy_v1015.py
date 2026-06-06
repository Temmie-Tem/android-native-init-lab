#!/usr/bin/env python3
"""V1015 deploy-only wrapper for a90_android_execns_probe v172."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1015-execns-helper-v172-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1014-execns-helper-v172-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "0c9b6d34be91211255a1359198329405806092fb9b4eeb4f24d3089e878df54d"
base.HELPER_MARKER = "a90_android_execns_probe v172"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
base.ORDER_ENUM = (
    "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|"
    "after-mdm-helper-esoc-fd-with-pm-proxy|after-mdm-helper-esoc-fd-with-wifi-surface"
)
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1015 deploy execns helper v172 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1015-execns-helper-v172-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v172"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1015"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1015 Execns Helper v172 Deploy")
        .replace("helper v154", "helper v172")
        .replace("local-helper-v154", "local-helper-v172")
        .replace("remote-helper-v154", "remote-helper-v172")
        .replace("execns-helper-v154", "execns-helper-v172")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1014 helper v172 before deploy")
        .replace("V930", "V1015")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1016 bounded after-fd Wi-Fi surface matrix live gate")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v172"),
        pass_ok,
        reason.replace("v154", "v172").replace("V930", "V1015"),
        next_step.replace("v154", "v172")
        .replace("V930", "V1015")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1016 bounded after-fd Wi-Fi surface matrix live gate"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
