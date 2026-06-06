#!/usr/bin/env python3
"""V947 bounded mdm_helper provider-readiness capture using deployed helper v157."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_runtime_contract_capture_v908 as runner


ORIGINAL_HELPER_SURFACE = runner.helper_surface
ORIGINAL_RENDER_SUMMARY = runner.render_summary

runner.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v947-provider-readiness-capture-live")
runner.base.LATEST_POINTER = Path("tmp/wifi/latest-v947-provider-readiness-capture-live.txt")
runner.base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v945-execns-helper-v157-build/a90_android_execns_probe")
runner.base.DEFAULT_HELPER_SHA256 = "308b0f37bfe1265874afdc141f07c8d0b638e6d80c5093af03641f54e96371c2"
runner.base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v157"


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
    surface["provider_readiness"] = {
        key: value
        for key, value in keys.items()
        if key.startswith("mdm_helper_provider_readiness.")
    }
    return surface


def decide(args, local, steps, analysis):
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v947-plan-helper-v157-missing", False, f"local={local}", "build and deploy helper v157 before V947"
        return "v947-provider-readiness-plan-ready", True, "plan-only; no device command executed", "run bounded V947 provider-readiness capture"
    missing = runner.required_flags(args)
    if missing:
        return "v947-provider-readiness-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V947 flags"
    helper = analysis.get("helper") or {}
    failed_steps = runner.base.step_failures(steps, helper)
    if failed_steps:
        return "v947-step-failed", False, f"failed_steps={failed_steps}", "inspect V947 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v947-helper-v157-remote-mismatch", False, f"remote={remote}", "redeploy helper v157 before V947"
    if helper.get("forbidden_true"):
        return "v947-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    provider = helper.get("provider_readiness") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v947-helper-mode-not-executed", False, f"contract={contract}", "fix V947 helper command before retry"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v947-runtime-actors-not-attempted", False, f"contract={contract}", "repair runtime-contract actor ordering before retry"
    if not provider:
        return "v947-provider-readiness-missing", False, f"contract={contract}", "repair helper v157 provider-readiness capture before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v947-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    return (
        "v947-provider-readiness-captured",
        True,
        f"contract_result={contract.get('result')} provider_keys={len(provider)}",
        "classify V947 provider-readiness evidence before starting pm_proxy_helper or opening /dev/subsys_esoc0",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    return (
        text.replace("V908 mdm_helper Runtime Contract Capture", "V947 Provider-Readiness Capture")
        .replace("V908", "V947")
        .replace("helper v148", "helper v157")
    )


runner.helper_surface = helper_surface
runner.decide = decide
runner.render_summary = render_summary
runner.base.helper_surface = helper_surface
runner.base.decide = decide
runner.base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(runner.base.main())
