#!/usr/bin/env python3
"""V957 bounded pm-proxy matrix capture with helper v159."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_cnss_service_manager_matrix_live_v931 as v931


v931.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v957-pm-proxy-matrix-live")
v931.base.LATEST_POINTER = Path("tmp/wifi/latest-v957-pm-proxy-matrix-live.txt")
v931.base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v955-execns-helper-v159-build/a90_android_execns_probe")
v931.base.DEFAULT_HELPER_SHA256 = "c4eb155c9fa1e105d80a040689dcedc9370b0340b60ac624980ccaf20e9c94d6"
v931.base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v159"
v931.DEFAULT_SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd-with-pm-proxy"

ORIGINAL_DECIDE = v931.decide
ORIGINAL_RENDER_SUMMARY = v931.render_summary
ORIGINAL_HELPER_SURFACE = v931.v923.helper_surface


def helper_surface(text: str) -> dict[str, Any]:
    surface = ORIGINAL_HELPER_SURFACE(text)
    keys = v931.base.parse_keys(text)
    surface["provider_readiness"] = {
        key: value
        for key, value in keys.items()
        if key.startswith("mdm_helper_provider_readiness.")
    }
    return surface


def v957_label(label: str) -> str:
    if label.startswith("v931-"):
        return "v957-" + label[len("v931-") :]
    return label


def decide(
    args: Any,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v957-plan-helper-v159-missing", False, f"local={local}", "deploy helper v159 before V957"
        return "v957-pm-proxy-matrix-plan-ready", True, "plan-only; no device command executed", "run bounded V957 pm-proxy matrix capture"
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    provider = helper.get("provider_readiness") or {}
    contract = helper.get("contract") or {}
    if pass_ok and not provider:
        return "v957-provider-readiness-missing", False, f"base_decision={decision}", "repair helper v159 pm-proxy provider-readiness capture before retry"
    if pass_ok and contract.get("pm_proxy_start_attempted") != "1":
        return "v957-pm-proxy-not-attempted", False, f"contract={contract}", "fix V957 service-manager order before retry"
    return (
        v957_label(decision),
        pass_ok,
        f"{reason} provider_keys={len(provider)} pm_proxy_started={contract.get('pm_proxy_started')}",
        "classify V957 pm-proxy matrix evidence before any pm_proxy_helper, /dev/subsys_esoc0, HAL, scan, DHCP, or external ping work",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    text = text.replace("# V931 CNSS Service-Manager Matrix Live", "# V957 PM-Proxy Matrix Live")
    return text.replace("V931", "V957").replace("helper v154", "helper v159")


v931.v923.helper_surface = helper_surface
v931.decide = decide
v931.render_summary = render_summary
v931.base.decide = decide
v931.base.render_summary = render_summary
v931.v923.decide = decide
v931.v923.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v931.base.main())
