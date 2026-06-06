#!/usr/bin/env python3
"""V927 compact CNSS-before-eSoC mdm_helper trigger capture proof.

Runs deployed helper v153 in the V923 CNSS-before-eSoC mode, but forces compact
CNSS surface output so the final contract keys are not lost to the command
transcript limit. It keeps the same hard gates: no service-manager, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, controller eSoC notify,
or BOOT_DONE spoofing.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_mdm_helper_cnss_before_esoc_capture_v923 as v923


base = v923.base

ORIGINAL_HELPER_COMMAND = v923.helper_command
ORIGINAL_DECIDE = v923.decide
ORIGINAL_RENDER_SUMMARY = v923.render_summary

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v927-mdm-helper-cnss-before-esoc-compact-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v925-execns-helper-v153-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "ef9b5b779909be67a6cf9a29e14f5445505220ec6a9c651c888ff48acda1326e"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v153"
base.MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.PREFIX = "cnss_before_esoc"
v923.__doc__ = __doc__


def _retag(value: str) -> str:
    return (
        value.replace("V923", "V927")
        .replace("v923", "v927")
        .replace("helper v152", "helper v153")
        .replace("helper-v152", "helper-v153")
    )


def helper_command(args: v923.argparse.Namespace) -> list[str]:
    command = ORIGINAL_HELPER_COMMAND(args)
    insert_at = command.index("--allow-mdm-helper-cnss-before-subsys-trigger-capture")
    command[insert_at:insert_at] = ["--cnss-surface-mode", "compact"]
    return command


def decide(
    args: v923.argparse.Namespace,
    local: dict[str, object],
    steps: list[dict[str, object]],
    analysis: dict[str, object],
) -> tuple[str, bool, str, str]:
    decision, ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    return _retag(decision), ok, _retag(reason), _retag(next_step)


def render_summary(manifest: dict[str, object]) -> str:
    summary = ORIGINAL_RENDER_SUMMARY(manifest)
    summary = _retag(summary)
    return summary.replace(
        "# V927 mdm_helper Subsys Trigger Capture",
        "# V927 compact CNSS-before-eSoC mdm_helper Trigger Capture",
    )


v923.helper_command = helper_command
v923.decide = decide
v923.render_summary = render_summary
base.helper_command = helper_command
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
