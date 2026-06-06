#!/usr/bin/env python3
"""V943 bounded mdm_helper queue-timing capture using deployed helper v156."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_runtime_contract_capture_v908 as runner


ORIGINAL_HELPER_SURFACE = runner.helper_surface
ORIGINAL_RENDER_SUMMARY = runner.render_summary

runner.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v943-mdm-helper-queue-timing-capture-live")
runner.base.LATEST_POINTER = Path("tmp/wifi/latest-v943-mdm-helper-queue-timing-capture-live.txt")
runner.base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v941-execns-helper-v156-build/a90_android_execns_probe")
runner.base.DEFAULT_HELPER_SHA256 = "ff5a87694bbb9c557aaaaacf61e1ceb0af9dffb3984d9f6887a2f93c8bceceb8"
runner.base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v156"


def helper_surface(text: str) -> dict[str, Any]:
    surface = ORIGINAL_HELPER_SURFACE(text)
    keys = runner.base.parse_keys(text)
    surface["queue_timing"] = {
        key: value
        for key, value in keys.items()
        if key.startswith("mdm_helper_queue_timing.")
    }
    surface["lower_contract"] = {
        key: value
        for key, value in keys.items()
        if key.startswith("mdm_helper_lower_contract.")
    }
    return surface


def decide(args, local, steps, analysis):
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v943-plan-helper-v156-missing", False, f"local={local}", "build and deploy helper v156 before V943"
        return "v943-mdm-helper-queue-timing-plan-ready", True, "plan-only; no device command executed", "run bounded V943 queue-timing capture"
    missing = runner.required_flags(args)
    if missing:
        return "v943-mdm-helper-queue-timing-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V943 flags"
    helper = analysis.get("helper") or {}
    failed_steps = runner.base.step_failures(steps, helper)
    if failed_steps:
        return "v943-step-failed", False, f"failed_steps={failed_steps}", "inspect V943 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v943-helper-v156-remote-mismatch", False, f"remote={remote}", "redeploy helper v156 before V943"
    if helper.get("forbidden_true"):
        return "v943-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    timing = helper.get("queue_timing") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v943-helper-mode-not-executed", False, f"contract={contract}", "fix V943 helper command before retry"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v943-runtime-actors-not-attempted", False, f"contract={contract}", "repair runtime-contract actor ordering before retry"
    if not timing:
        return "v943-queue-timing-missing", False, f"contract={contract}", "repair helper v156 queue-timing capture before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v943-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    return (
        "v943-mdm-helper-queue-timing-captured",
        True,
        f"contract_result={contract.get('result')} queue_timing_keys={len(timing)}",
        "classify V943 queue-timing evidence before any eSoC trigger retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    return (
        text.replace("V908 mdm_helper Runtime Contract Capture", "V943 mdm_helper Queue-Timing Capture")
        .replace("V908", "V943")
        .replace("helper v148", "helper v156")
    )


runner.helper_surface = helper_surface
runner.decide = decide
runner.render_summary = render_summary
runner.base.helper_surface = helper_surface
runner.base.decide = decide
runner.base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(runner.base.main())
