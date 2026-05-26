#!/usr/bin/env python3
"""V996 deploy-only wrapper for a90_android_execns_probe v169."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v996-execns-helper-v169-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v995-execns-helper-v169-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74"
base.HELPER_MARKER = "a90_android_execns_probe v169"
base.NEW_MODE = "selinux-domain-proof"
base.ALLOW_FLAG = "--selinux-context"
base.ORDER_ENUM = "system-wificond|vendor-vndservicemanager"
base.COMPACT_MODE = "--selinux-attr-mode current|exec|both"
base.APPROVAL_PHRASE = (
    "approve v996 deploy execns helper v169 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v996-execns-helper-v169-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v169"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v996"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V996 Execns Helper v169 Deploy")
        .replace("helper v154", "helper v169")
        .replace("local-helper-v154", "local-helper-v169")
        .replace("remote-helper-v154", "remote-helper-v169")
        .replace("execns-helper-v154", "execns-helper-v169")
        .replace("rebuild V929 helper v154 before deploy", "rebuild helper v169 before deploy")
        .replace("V930", "V996")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run fresh current-boot SELinux policy/domain proof")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v169"),
        pass_ok,
        reason.replace("v154", "v169").replace("V930", "V996"),
        next_step.replace("v154", "v169").replace("V930", "V996"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
