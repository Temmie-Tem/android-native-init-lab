#!/usr/bin/env python3
"""V1019 deploy-only wrapper for a90_android_execns_probe v173."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1019-execns-helper-v173-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1018-execns-helper-v173-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "63a2110d4b082ee6f1cd07d28c6d55e59335d0378089dac71824aff8f3903884"
base.HELPER_MARKER = "a90_android_execns_probe v173"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
base.ORDER_ENUM = (
    "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|"
    "after-mdm-helper-esoc-fd-with-pm-proxy|after-mdm-helper-esoc-fd-with-wifi-surface|"
    "after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window"
)
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1019 deploy execns helper v173 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1019-execns-helper-v173-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v173"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1019"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1019 Execns Helper v173 Deploy")
        .replace("helper v154", "helper v173")
        .replace("local-helper-v154", "local-helper-v173")
        .replace("remote-helper-v154", "remote-helper-v173")
        .replace("execns-helper-v154", "execns-helper-v173")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1018 helper v173 before deploy")
        .replace("rebuild V929 helper v173 before deploy", "rebuild V1018 helper v173 before deploy")
        .replace("V930", "V1019")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1020 bounded after-fd subsystem-window live gate")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v173"),
        pass_ok,
        reason.replace("v154", "v173").replace("V930", "V1019"),
        next_step.replace("v154", "v173")
        .replace("V930", "V1019")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1020 bounded after-fd subsystem-window live gate"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
