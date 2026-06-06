#!/usr/bin/env python3
"""V1035 deploy-only wrapper for a90_android_execns_probe v176."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1035-execns-helper-v176-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1034-execns-helper-v176-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "dff34476d956574be59628f1177179cb8ef87a04dda0c68e97cc5afcf5310f2d"
base.HELPER_MARKER = "a90_android_execns_probe v176"
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
    "approve v1035 deploy execns helper v176 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1035-execns-helper-v176-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v176"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1035"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1035 Execns Helper v176 Deploy")
        .replace("helper v154", "helper v176")
        .replace("local-helper-v154", "local-helper-v176")
        .replace("remote-helper-v154", "remote-helper-v176")
        .replace("execns-helper-v154", "execns-helper-v176")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1034 helper v176 before deploy")
        .replace("V930", "V1035")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun V1033 PM SELinux domain proof")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v176"),
        pass_ok,
        reason.replace("v154", "v176").replace("V930", "V1035"),
        next_step.replace("v154", "v176")
        .replace("V930", "V1035")
        .replace("run one V931 matrix order below Wi-Fi HAL", "rerun V1033 PM SELinux domain proof"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
