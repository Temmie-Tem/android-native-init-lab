#!/usr/bin/env python3
"""V1012 helper v171 after-fd CNSS/service-manager matrix live proof."""

from __future__ import annotations

from pathlib import Path

import native_wifi_cnss_service_manager_matrix_live_v931 as v931


base = v931.base
ORIGINAL_HELPER_COMMAND = v931.helper_command
ORIGINAL_DECIDE = v931.decide
ORIGINAL_RENDER_SUMMARY = v931.render_summary

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1012-after-fd-cnss-service-manager-matrix-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1012-after-fd-cnss-service-manager-matrix-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1006-execns-helper-v171-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "347f38ab24d67bf300bd6dccd033a081328ec5afdd711b49f3d0d2f9328cf3a1"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v171"
v931.DEFAULT_SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd"


def _retag(value: str) -> str:
    return (
        value.replace("V931", "V1012")
        .replace("v931", "v1012")
        .replace("helper v154", "helper v171")
        .replace("helper-v154", "helper-v171")
    )


def helper_command(args):
    command = ORIGINAL_HELPER_COMMAND(args)
    if "--android-selinux-context-mode" not in command:
        command.extend(["--android-selinux-context-mode", "service-defaults"])
    return command


def decide(args, local, steps, analysis):
    decision, ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    return _retag(decision), ok, _retag(reason), _retag(next_step)


def render_summary(manifest):
    summary = _retag(ORIGINAL_RENDER_SUMMARY(manifest))
    summary = summary.replace(
        "# V1012 CNSS Service-Manager Matrix Live",
        "# V1012 after-fd CNSS Service-Manager Matrix Live",
    )
    return (
        summary
        + "\n## V1012 Delta\n\n"
        + "- Uses helper `v171`.\n"
        + "- Forces `--android-selinux-context-mode service-defaults`.\n"
        + "- Preserves `service_manager_order=after-mdm-helper-esoc-fd`.\n"
        + "- Keeps Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping forbidden.\n"
    )


v931.helper_command = helper_command
v931.decide = decide
v931.render_summary = render_summary
base.helper_command = helper_command
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
