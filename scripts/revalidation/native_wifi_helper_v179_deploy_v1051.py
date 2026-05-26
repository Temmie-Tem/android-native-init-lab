#!/usr/bin/env python3
"""V1051 deploy-only wrapper for a90_android_execns_probe v179."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1051-execns-helper-v179-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "9cb6d49849af181a87a5619e7b3ed7f0f513223ef97ce8b0599ce43694453a7b"
base.HELPER_MARKER = "a90_android_execns_probe v179"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-pm-full-contract-with-modem-holder"
base.ORDER_ENUM = "after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder"
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1051 deploy execns helper v179 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1051-execns-helper-v179-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v179"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1051"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1051 Execns Helper v179 Deploy")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1050 helper v179 before deploy")
        .replace("helper v154", "helper v179")
        .replace("local-helper-v154", "local-helper-v179")
        .replace("remote-helper-v154", "remote-helper-v179")
        .replace("execns-helper-v154", "execns-helper-v179")
        .replace("V930", "V1051")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1052 bounded PM full-contract-with-modem-holder gate")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v179"),
        pass_ok,
        reason.replace("v154", "v179").replace("V930", "V1051"),
        next_step.replace("v154", "v179")
        .replace("V930", "V1051")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1052 bounded PM full-contract-with-modem-holder gate"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
