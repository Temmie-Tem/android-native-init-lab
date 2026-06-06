#!/usr/bin/env python3
"""V1010 reduced mdm_helper runtime-contract proof with service-defaults SELinux."""

from __future__ import annotations

from pathlib import Path

import native_wifi_mdm_helper_runtime_contract_capture_v908 as v908


base = v908.base
ORIGINAL_HELPER_COMMAND = v908.helper_command
ORIGINAL_DECIDE = v908.decide
ORIGINAL_RENDER_SUMMARY = v908.render_summary

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1010-mdm-helper-runtime-contract-service-defaults-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1010-mdm-helper-runtime-contract-service-defaults-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1006-execns-helper-v171-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "347f38ab24d67bf300bd6dccd033a081328ec5afdd711b49f3d0d2f9328cf3a1"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v171"


def helper_command(args):
    command = ORIGINAL_HELPER_COMMAND(args)
    if "--android-selinux-context-mode" not in command:
        command.extend(["--android-selinux-context-mode", "service-defaults"])
    return command


def decide(args, local, steps, analysis):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    return (
        decision.replace("v908", "v1010").replace("V908", "V1010").replace("v148", "v171"),
        pass_ok,
        reason.replace("v908", "v1010").replace("V908", "V1010").replace("v148", "v171"),
        next_step.replace("v908", "v1010").replace("V908", "V1010").replace("v148", "v171"),
    )


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V908 mdm_helper Runtime Contract Capture", "V1010 mdm_helper Runtime Contract Service-defaults")
        .replace("V908", "V1010")
        .replace("v908", "v1010")
        .replace("helper v148", "helper v171")
        .replace("a90_android_execns_probe v148", "a90_android_execns_probe v171")
        + "\n## V1010 Delta\n\n"
        + "- Uses the reduced V911 order: property shim, `per_mgr_light`, `mdm_helper`.\n"
        + "- Forces `--android-selinux-context-mode service-defaults`.\n"
        + "- Still forbids service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.\n"
    )


v908.helper_command = helper_command
v908.decide = decide
v908.render_summary = render_summary
base.helper_command = helper_command
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
