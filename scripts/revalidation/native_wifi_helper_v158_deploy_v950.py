#!/usr/bin/env python3
"""V950 deploy-only wrapper for a90_android_execns_probe v158."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v950-execns-helper-v158-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v949-execns-helper-v158-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "dfd70d5bb7cdfeb52ea5843da3ff01560c4cd1d890d9cd7e65269a287c2e724d"
base.HELPER_MARKER = "a90_android_execns_probe v158"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-mdm-helper-cnss-service-manager-matrix"
base.APPROVAL_PHRASE = (
    "approve v950 deploy execns helper v158 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v950-execns-helper-v158-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v158"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v950"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V950 Execns Helper v158 Deploy")
        .replace("helper v154", "helper v158")
        .replace("V930", "V950")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v158"),
        pass_ok,
        reason.replace("v154", "v158").replace("V930", "V950"),
        next_step.replace("v154", "v158").replace("V930", "V950"),
    )


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide


if __name__ == "__main__":
    raise SystemExit(base.main())
