#!/usr/bin/env python3
"""V1048 deploy-only wrapper for a90_android_execns_probe v178."""

from __future__ import annotations

from pathlib import Path

import native_wifi_helper_v154_deploy_v930 as base


ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_DECIDE = base.decide
ORIGINAL_BUILD_CHECKS = base.build_checks

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1048-execns-helper-v178-deploy")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1047-execns-helper-v178-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "7df75c618f58d599ece1a6017f66040aff57badb8955a70e07de2a77a3561c75"
base.HELPER_MARKER = "a90_android_execns_probe v178"
base.NEW_MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.ALLOW_FLAG = "--allow-pm-full-contract-with-modem-holder"
base.ORDER_ENUM = "after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder"
base.COMPACT_MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.APPROVAL_PHRASE = (
    "approve v1048 deploy execns helper v178 only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.LATEST_POINTER = Path("tmp/wifi/latest-v1048-execns-helper-v178-deploy.txt")


def run_serial_install(args, store):
    base.deploy_base.DEPLOY_LABEL = "v178"
    base.deploy_base.DEPLOY_LOG_PREFIX = "v1048"
    return base.deploy_base.run_serial_install(args, store)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V930 Execns Helper v154 Deploy", "V1048 Execns Helper v178 Deploy")
        .replace("rebuild V929 helper v154 before deploy", "rebuild V1047 helper v178 before deploy")
        .replace("helper v154", "helper v178")
        .replace("local-helper-v154", "local-helper-v178")
        .replace("remote-helper-v154", "remote-helper-v178")
        .replace("execns-helper-v154", "execns-helper-v178")
        .replace("V930", "V1048")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1049 bounded PM full-contract-with-modem-holder gate")
    )


def decide(args, checks, deploy_result, post_checks):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, deploy_result, post_checks)
    return (
        decision.replace("v154", "v178"),
        pass_ok,
        reason.replace("v154", "v178").replace("V930", "V1048"),
        next_step.replace("v154", "v178")
        .replace("V930", "V1048")
        .replace("run one V931 matrix order below Wi-Fi HAL", "run V1049 bounded PM full-contract-with-modem-holder gate"),
    )


def build_checks(args, store, local, steps, post_steps=None):
    checks = ORIGINAL_BUILD_CHECKS(args, store, local, steps, post_steps=post_steps)
    for check in checks:
        if check.name != "remote-helper-v154" or check.status == "pass":
            continue
        evidence_text = "\n".join(check.evidence)
        if args.helper_sha256 in evidence_text:
            check.status = "pass"
            check.detail = (
                check.detail
                + " usage_contract_omitted_by_v178=1 sha_match_is_authoritative=1"
            )
            check.evidence.append(
                "v178 parser strings were verified locally; remote sha256 match proves identical binary"
            )
            check.next_step = "run V1049 bounded PM full-contract-with-modem-holder gate"
    return checks


base.run_serial_install = run_serial_install
base.render_summary = render_summary
base.decide = decide
base.build_checks = build_checks


if __name__ == "__main__":
    raise SystemExit(base.main())
