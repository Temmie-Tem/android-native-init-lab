#!/usr/bin/env python3
"""V951 bounded matrix provider-readiness capture using deployed helper v158."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_cnss_service_manager_matrix_live_v931 as v931


v931.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v951-matrix-provider-readiness-before-cnss-live")
v931.base.LATEST_POINTER = Path("tmp/wifi/latest-v951-matrix-provider-readiness-before-cnss-live.txt")
v931.base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v949-execns-helper-v158-build/a90_android_execns_probe")
v931.base.DEFAULT_HELPER_SHA256 = "dfd70d5bb7cdfeb52ea5843da3ff01560c4cd1d890d9cd7e65269a287c2e724d"
v931.base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v158"
v931.DEFAULT_SERVICE_MANAGER_ORDER = "before-cnss"

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


def v951_label(label: str) -> str:
    if label.startswith("v931-"):
        return "v951-" + label[len("v931-") :]
    return label


def decide(
    args: Any,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v951-plan-helper-v158-missing", False, f"local={local}", "deploy helper v158 before V951"
        return "v951-matrix-provider-readiness-plan-ready", True, "plan-only; no device command executed", "run bounded V951 matrix provider-readiness capture"
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    provider = helper.get("provider_readiness") or {}
    if pass_ok and not provider:
        return "v951-provider-readiness-missing", False, f"base_decision={decision}", "repair helper v158 matrix provider-readiness capture before retry"
    return (
        v951_label(decision),
        pass_ok,
        f"{reason} provider_keys={len(provider)}",
        "classify V951 matrix provider-readiness evidence before any pm_proxy_helper, /dev/subsys_esoc0, HAL, or scan work",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    text = text.replace("# V931 CNSS Service-Manager Matrix Live", "# V951 Matrix Provider-Readiness Before-CNSS Live")
    return text.replace("V931", "V951").replace("helper v154", "helper v158")


v931.v923.helper_surface = helper_surface
v931.decide = decide
v931.render_summary = render_summary
v931.base.decide = decide
v931.base.render_summary = render_summary
v931.v923.decide = decide
v931.v923.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v931.base.main())
