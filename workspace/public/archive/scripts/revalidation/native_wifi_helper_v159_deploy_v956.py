#!/usr/bin/env python3
"""V956 deploy-only wrapper for a90_android_execns_probe v159."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v956-execns-helper-v159-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v955-execns-helper-v159-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "c4eb155c9fa1e105d80a040689dcedc9370b0340b60ac624980ccaf20e9c94d6"
base.HELPER_MARKER = "a90_android_execns_probe v159"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
base.ORDER_ENUM = "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|after-mdm-helper-esoc-fd-with-pm-proxy"
base.APPROVAL_PHRASE = (
    "approve v956 deploy execns helper v159 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v956-execns-helper-v159-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v159"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v956"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V956 Execns Helper v159 Deploy")
        .replace("helper v154", "helper v159")
        .replace("V930", "V956")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v159"),
        pass_ok,
        reason.replace("v154", "v159").replace("V930", "V956"),
        next_step.replace("v154", "v159").replace("V930", "V956"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
