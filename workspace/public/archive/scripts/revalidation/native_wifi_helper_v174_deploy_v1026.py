#!/usr/bin/env python3
"""V1026 deploy-only wrapper for a90_android_execns_probe v174."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1026-execns-helper-v174-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1025-execns-helper-v174-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "07b9efdebddd955e388026afa2afed86cd52d762dcc4ac36638318f4661fe78f"
base.HELPER_MARKER = "a90_android_execns_probe v174"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
base.ORDER_ENUM = (
    "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|"
    "after-mdm-helper-esoc-fd-with-pm-proxy|after-mdm-helper-esoc-fd-with-pm-full-contract|"
    "after-mdm-helper-esoc-fd-with-wifi-surface|"
    "after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window"
)
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1026 deploy execns helper v174 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1026-execns-helper-v174-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v174"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1026"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1026 Execns Helper v174 Deploy")
        .replace("helper v154", "helper v174")
        .replace("local-helper-v154", "local-helper-v174")
        .replace("remote-helper-v154", "remote-helper-v174")
        .replace("execns-helper-v154", "execns-helper-v174")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1025 helper v174 before deploy")
        .replace("V930", "V1026")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1027 bounded PM full-contract live classifier")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v174"),
        pass_ok,
        reason.replace("v154", "v174").replace("V930", "V1026"),
        next_step.replace("v154", "v174")
        .replace("V930", "V1026")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1027 bounded PM full-contract live classifier"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
