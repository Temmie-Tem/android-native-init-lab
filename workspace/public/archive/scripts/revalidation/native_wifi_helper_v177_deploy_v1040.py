#!/usr/bin/env python3
"""V1040 deploy-only wrapper for a90_android_execns_probe v177."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1040-execns-helper-v177-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1039-execns-helper-v177-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795"
base.HELPER_MARKER = "a90_android_execns_probe v177"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--require-android-selinux-exec-match"
base.ORDER_ENUM = (
    "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|"
    "after-mdm-helper-esoc-fd-with-pm-proxy|after-mdm-helper-esoc-fd-with-pm-full-contract|"
    "after-mdm-helper-esoc-fd-with-wifi-surface|"
    "after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window"
)
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1040 deploy execns helper v177 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1040-execns-helper-v177-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v177"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1040"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1040 Execns Helper v177 Deploy")
        .replace("helper v154", "helper v177")
        .replace("local-helper-v154", "local-helper-v177")
        .replace("remote-helper-v154", "remote-helper-v177")
        .replace("execns-helper-v154", "execns-helper-v177")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1039 helper v177 before deploy")
        .replace("V930", "V1040")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun the bounded PM full-contract live proof")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v177"),
        pass_ok,
        reason.replace("v154", "v177").replace("V930", "V1040"),
        next_step.replace("v154", "v177")
        .replace("V930", "V1040")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun the bounded PM full-contract live proof"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
