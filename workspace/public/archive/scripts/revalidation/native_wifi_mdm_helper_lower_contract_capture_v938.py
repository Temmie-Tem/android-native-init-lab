#!/usr/bin/env python3
"""V938 bounded mdm_helper lower-contract capture using deployed helper v155."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_runtime_contract_capture_v908 as runner


ORIGINAL_HELPER_SURFACE = runner.helper_surface
ORIGINAL_RENDER_SUMMARY = runner.render_summary

runner.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v938-mdm-helper-lower-contract-capture-live")
runner.base.LATEST_POINTER = Path("tmp/wifi/latest-v938-mdm-helper-lower-contract-capture-live.txt")
runner.base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v936-execns-helper-v155-build/a90_android_execns_probe")
runner.base.DEFAULT_HELPER_SHA256 = "44d7820e7bc33ab9886ea4f5f39248b1902c404c694c48fcd00a3ecc0fb76063"
runner.base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v155"


def helper_surface(text: str) -> dict[str, Any]:
    surface = ORIGINAL_HELPER_SURFACE(text)
    keys = runner.base.parse_keys(text)
    surface["lower_contract"] = {
        key: value
        for key, value in keys.items()
        if key.startswith("mdm_helper_lower_contract.")
    }
    return surface


def decide(args, local, steps, analysis):
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v938-plan-helper-v155-missing", False, f"local={local}", "build and deploy helper v155 before V938"
        return "v938-mdm-helper-lower-contract-plan-ready", True, "plan-only; no device command executed", "run bounded V938 lower-contract capture"
    missing = runner.required_flags(args)
    if missing:
        return "v938-mdm-helper-lower-contract-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V938 flags"
    helper = analysis.get("helper") or {}
    failed_steps = runner.base.step_failures(steps, helper)
    if failed_steps:
        return "v938-step-failed", False, f"failed_steps={failed_steps}", "inspect V938 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v938-helper-v155-remote-mismatch", False, f"remote={remote}", "redeploy helper v155 before V938"
    if helper.get("forbidden_true"):
        return "v938-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    lower = helper.get("lower_contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v938-helper-mode-not-executed", False, f"contract={contract}", "fix V938 helper command before retry"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v938-runtime-actors-not-attempted", False, f"contract={contract}", "repair runtime-contract actor ordering before retry"
    if not lower:
        return "v938-lower-contract-missing", False, f"contract={contract}", "repair helper v155 lower-contract capture before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v938-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    return (
        "v938-mdm-helper-lower-contract-captured",
        True,
        f"contract_result={contract.get('result')} lower_keys={len(lower)}",
        "classify V938 lower-contract evidence before any eSoC trigger retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    return (
        text.replace("V908 mdm_helper Runtime Contract Capture", "V938 mdm_helper Lower-Contract Capture")
        .replace("V908", "V938")
        .replace("helper v148", "helper v155")
    )


runner.helper_surface = helper_surface
runner.decide = decide
runner.render_summary = render_summary
runner.base.helper_surface = helper_surface
runner.base.decide = decide
runner.base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(runner.base.main())
