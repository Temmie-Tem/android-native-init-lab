#!/usr/bin/env python3
"""V959 bounded full-surface pm-proxy matrix capture with helper v159."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_pm_proxy_matrix_capture_v957 as v957


v931 = v957.v931

v931.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v959-pm-proxy-full-surface-live")
v931.base.LATEST_POINTER = Path("tmp/wifi/latest-v959-pm-proxy-full-surface-live.txt")

ORIGINAL_DECIDE = v931.decide
ORIGINAL_RENDER_SUMMARY = v931.render_summary
ORIGINAL_HELPER_COMMAND = v931.helper_command


def helper_command(args: Any) -> list[str]:
    command = ORIGINAL_HELPER_COMMAND(args)
    for index, value in enumerate(command):
        if value == "--cnss-surface-mode" and index + 1 < len(command):
            command[index + 1] = "full"
            break
    return command


def v959_label(label: str) -> str:
    if label.startswith("v957-"):
        return "v959-" + label[len("v957-") :]
    if label.startswith("v931-"):
        return "v959-" + label[len("v931-") :]
    return label


def decide(
    args: Any,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v959-plan-helper-v159-missing", False, f"local={local}", "deploy helper v159 before V959"
        return "v959-pm-proxy-full-surface-plan-ready", True, "plan-only; no device command executed", "run bounded V959 full-surface capture"
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    if pass_ok and contract.get("surface_mode") != "full":
        return "v959-full-surface-not-executed", False, f"contract={contract}", "fix V959 helper command before retry"
    return (
        v959_label(decision),
        pass_ok,
        reason,
        "classify V959 full-surface evidence before any pm_proxy_helper, /dev/subsys_esoc0, HAL, scan, DHCP, or external ping work",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    text = text.replace("# V957 PM-Proxy Matrix Live", "# V959 PM-Proxy Full-Surface Matrix Live")
    return text.replace("V957", "V959")


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
