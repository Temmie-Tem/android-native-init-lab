#!/usr/bin/env python3
"""V1054 deploy-only wrapper for a90_android_execns_probe v180."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1054-execns-helper-v180-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1053-execns-helper-v180-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641"
base.HELPER_MARKER = "a90_android_execns_probe v180"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-pm-full-contract-with-modem-holder"
base.ORDER_ENUM = "after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder"
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1054 deploy execns helper v180 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1054-execns-helper-v180-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v180"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1054"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1054 Execns Helper v180 Deploy")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1053 helper v180 before deploy")
        .replace("helper v154", "helper v180")
        .replace("local-helper-v154", "local-helper-v180")
        .replace("remote-helper-v154", "remote-helper-v180")
        .replace("execns-helper-v154", "execns-helper-v180")
        .replace("V930", "V1054")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1055 bounded PM full-contract-with-modem-holder gate")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v180"),
        pass_ok,
        reason.replace("v154", "v180").replace("V930", "V1054"),
        next_step.replace("v154", "v180")
        .replace("V930", "V1054")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1055 bounded PM full-contract-with-modem-holder gate"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
