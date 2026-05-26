#!/usr/bin/env python3
"""V963 bounded live proof for helper v160 post-provider subsystem trigger gating."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_pm_proxy_full_surface_capture_v959 as v959


v931 = v959.v931

v931.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v963-post-provider-trigger-live")
v931.base.LATEST_POINTER = Path("tmp/wifi/latest-v963-post-provider-trigger-live.txt")
v931.base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v961-execns-helper-v160-build/a90_android_execns_probe")
v931.base.DEFAULT_HELPER_SHA256 = "2b4d621b111fa8e0e24a3591dd233478ac1d94ca87fa8c0eb1541db4d6d11998"
v931.base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v160"
v931.DEFAULT_SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd-with-pm-proxy"

ORIGINAL_DECIDE = v931.decide
ORIGINAL_RENDER_SUMMARY = v931.render_summary
ORIGINAL_HELPER_COMMAND = v931.helper_command


def helper_command(args: Any) -> list[str]:
    command = ORIGINAL_HELPER_COMMAND(args)
    if "--subsys-trigger-gate" not in command:
        command.extend(["--subsys-trigger-gate", "post-provider-no-wlfw"])
    return command


def v963_label(label: str) -> str:
    for prefix in ("v959-", "v957-", "v931-"):
        if label.startswith(prefix):
            return "v963-" + label[len(prefix) :]
    return label


def decide(
    args: Any,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v963-plan-helper-v160-missing", False, f"local={local}", "deploy helper v160 before V963"
        return "v963-post-provider-trigger-plan-ready", True, "plan-only; no device command executed", "run bounded V963 post-provider trigger proof"

    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    if contract.get("subsys_trigger_gate") != "post-provider-no-wlfw":
        return "v963-trigger-gate-not-executed", False, f"contract={contract}", "fix V963 helper command before retry"
    if helper.get("forbidden_true"):
        return "v963-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v963-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify recovery cleanup before continuing"

    result = contract.get("result")
    if result == "post-provider-no-wlfw-trigger-clean":
        return (
            "v963-post-provider-trigger-clean",
            True,
            f"contract={contract}",
            "classify post-provider trigger evidence before any pm_proxy_helper, Wi-Fi HAL, scan/connect, DHCP, or external ping work",
        )
    if result == "reboot-required" and contract.get("post_provider_no_wlfw_trigger_started") == "1":
        return (
            "v963-post-provider-trigger-reboot-cleaned",
            True,
            f"contract={contract}",
            "classify trigger stall evidence and cleanup reboot before expanding toward HAL or connect",
        )
    if (
        contract.get("subsys_trigger.gate") == "post-provider-no-wlfw"
        and contract.get("subsys_esoc0_open_attempted") == "1"
        and contract.get("subsys_trigger.blocker_capture_attempted") == "1"
        and cleanup.get("healthy")
    ):
        return (
            "v963-post-provider-trigger-stall-cleaned",
            True,
            f"contract={contract}",
            "classify trigger stall wchan/stack before any pm_proxy_helper, Wi-Fi HAL, scan/connect, DHCP, or external ping work",
        )
    return (
        v963_label(decision),
        pass_ok,
        reason,
        "classify V963 post-provider trigger evidence before any pm_proxy_helper, Wi-Fi HAL, scan/connect, DHCP, or external ping work",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    text = text.replace("# V959 PM-Proxy Full-Surface Matrix Live", "# V963 Post-Provider Trigger Live")
    return text.replace("V959", "V963").replace("helper v159", "helper v160")


v931.helper_command = helper_command
v931.base.helper_command = helper_command
v931.v923.helper_command = helper_command
v931.decide = decide
v931.render_summary = render_summary
v931.base.decide = decide
v931.base.render_summary = render_summary
v931.v923.decide = decide
v931.v923.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v931.base.main())
