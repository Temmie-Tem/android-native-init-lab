#!/usr/bin/env python3
"""V1335 bounded native early-CNSS WLFW parity observer.

Runs helper v277 in `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture`
mode with `--subsys-trigger-gate observe-only`. The permitted live actions are
the V923 early-CNSS observer actors and cleanup only; `/dev/subsys_esoc0` must
remain closed even if a WLFW precondition appears.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import native_wifi_mdm_helper_cnss_before_esoc_capture_v923 as v923


base = v923.base

base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v1335-early-cnss-wlfw-parity-observer-live")
base.LATEST_POINTER = base.Path("tmp/wifi/latest-v1335-early-cnss-wlfw-parity-observer-live.txt")
base.DEFAULT_LOCAL_HELPER = base.Path("stage3/linux_init/helpers/a90_android_execns_probe_v277")
base.DEFAULT_HELPER_SHA256 = "3a61125bd3e2bad9cda8dcac2df75184c3df369ada4a9a0010681c49788a6fd9"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v277"
base.MODE = "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
base.PREFIX = "cnss_before_esoc"

v923.base.DEFAULT_OUT_DIR = base.DEFAULT_OUT_DIR
v923.base.LATEST_POINTER = base.LATEST_POINTER
v923.base.DEFAULT_LOCAL_HELPER = base.DEFAULT_LOCAL_HELPER
v923.base.DEFAULT_HELPER_SHA256 = base.DEFAULT_HELPER_SHA256
v923.base.DEFAULT_HELPER_MARKER = base.DEFAULT_HELPER_MARKER
v923.base.MODE = base.MODE
v923.base.PREFIX = base.PREFIX

base.FORBIDDEN_TRUE_KEYS = (
    f"{base.PREFIX}.pm_proxy_helper_start_executed",
    f"{base.PREFIX}.service_manager_start_executed",
    f"{base.PREFIX}.wifi_hal_start_executed",
    f"{base.PREFIX}.wificond_start_executed",
    f"{base.PREFIX}.scan_connect_linkup",
    f"{base.PREFIX}.credentials",
    f"{base.PREFIX}.dhcp_routing",
    f"{base.PREFIX}.external_ping",
    f"{base.PREFIX}.subsys_esoc0_open_attempted",
    f"{base.PREFIX}.subsys_esoc0_controller_open_attempted",
    f"{base.PREFIX}.reg_req_eng_attempted",
    f"{base.PREFIX}.notify_attempted",
    f"{base.PREFIX}.boot_done_attempted",
)

ORIGINAL_PARSE_ARGS = v923.parse_args
ORIGINAL_HELPER_COMMAND = v923.helper_command
ORIGINAL_HELPER_SURFACE = v923.helper_surface
ORIGINAL_RENDER_SUMMARY = v923.render_summary
ORIGINAL_BUILD_MANIFEST = v923.build_manifest


def parse_args() -> argparse.Namespace:
    args = ORIGINAL_PARSE_ARGS()
    if args.out_dir == v923.base.DEFAULT_OUT_DIR:
        args.out_dir = base.DEFAULT_OUT_DIR
    if args.local_helper == v923.base.DEFAULT_LOCAL_HELPER:
        args.local_helper = base.DEFAULT_LOCAL_HELPER
    if args.helper_sha256 == v923.base.DEFAULT_HELPER_SHA256:
        args.helper_sha256 = base.DEFAULT_HELPER_SHA256
    if args.helper_marker == v923.base.DEFAULT_HELPER_MARKER:
        args.helper_marker = base.DEFAULT_HELPER_MARKER
    return args


def helper_command(args: argparse.Namespace) -> list[str]:
    command = ORIGINAL_HELPER_COMMAND(args)
    return command + [
        "--subsys-trigger-gate",
        "observe-only",
        "--cnss-surface-mode",
        "compact",
    ]


def helper_surface(text: str) -> dict[str, Any]:
    surface = ORIGINAL_HELPER_SURFACE(text)
    contract = surface.get("contract") or {}
    if contract.get("subsys_trigger_gate") == "observe-only":
        contract["observe_only_contract"] = "1"
    return surface


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1335-plan-helper-v277-missing", False, f"local={local}", "build and deploy helper v277 before V1335"
        return "v1335-early-cnss-observe-only-plan-ready", True, "plan-only; no device command executed", "run bounded observe-only early-CNSS WLFW parity observer"
    missing = v923.required_flags(args)
    if missing:
        return "v1335-early-cnss-observe-only-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1335 flags"
    helper = analysis.get("helper") or {}
    failed_steps = v923.step_failures(steps, helper)
    if failed_steps:
        return "v1335-step-failed", False, f"failed_steps={failed_steps}", "inspect V1335 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1335-helper-v277-remote-mismatch", False, f"remote={remote}", "redeploy helper v277 before V1335"
    if helper.get("forbidden_true"):
        return "v1335-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1335-helper-mode-not-executed", False, f"contract={contract}", "fix V1335 helper command before retry"
    if contract.get("subsys_trigger_gate") != "observe-only" or contract.get("observe_only_gate") != "1":
        return "v1335-observe-only-contract-missing", False, f"contract={contract}", "audit helper v277 observe-only wiring before retry"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v1335-runtime-actors-not-attempted", False, f"contract={contract}", "repair actor ordering before retry"
    if contract.get("subsys_esoc0_open_attempted") == "1":
        return "v1335-open-gate-violation", False, f"contract={contract}", "observe-only gate failed; stop and audit helper"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1335-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify cleanup before continuing"
    result = contract.get("result")
    if result == "wlfw-precondition-observed-observe-only-no-open":
        return (
            "v1335-native-early-cnss-wlfw-observed-no-open",
            True,
            f"contract={contract}",
            "classify the early-WLFW native state against Android before any eSoC trigger retry",
        )
    if result in {"wlfw-precondition-missing-no-open", "wlfw-precondition-missing-no-open-output-truncated"}:
        return (
            "v1335-native-early-cnss-no-wlfw-observe-only",
            True,
            f"contract={contract}",
            "classify the Android-only early WLFW provider/input that native still lacks",
        )
    if result == "mdm-helper-esoc-fd-missing-no-open":
        return (
            "v1335-mdm-helper-esoc-fd-missing-observe-only",
            True,
            f"contract={contract}",
            "classify why mdm_helper did not reach /dev/esoc-0 before CNSS observation",
        )
    if result == "reboot-required":
        return "v1335-reboot-required-cleaned", True, f"contract={contract}", "inspect pre-cleanup evidence"
    return "v1335-early-cnss-observe-only-review", False, f"contract={contract}", "inspect V1335 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_SUMMARY(manifest)
    text = text.replace("# V923 mdm_helper Subsys Trigger Capture", "# V1335 Early-CNSS WLFW Parity Observer")
    text = text.replace("V923", "V1335")
    text = text.replace("WLFW-gated `/dev/subsys_esoc0` child open", "observe-only gate with `/dev/subsys_esoc0` kept closed")
    text = text.replace("and the WLFW-gated `/dev/subsys_esoc0` child open.", "with `/dev/subsys_esoc0` kept closed even if WLFW appears.")
    return text + "\n- observe-only gate: `/dev/subsys_esoc0` open is forbidden in this cycle.\n"


def build_manifest(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = ORIGINAL_BUILD_MANIFEST(args, store)
    manifest["cycle"] = "v1335"
    manifest["mode"] = base.MODE
    manifest["subsys_trigger_gate"] = "observe-only"
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    contract = helper.get("contract") or {}
    manifest["observe_only_gate"] = contract.get("observe_only_gate") == "1"
    manifest["wlfw_trigger_ready"] = contract.get("wlfw_trigger_ready") == "1"
    manifest["service_manager_start_executed"] = contract.get("service_manager_start_executed") == "1"
    manifest["subsys_esoc0_open_attempted"] = contract.get("subsys_esoc0_open_attempted") == "1"
    manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
    manifest["wificond_start_executed"] = contract.get("wificond_start_executed") == "1"
    manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
    manifest["credential_use_executed"] = contract.get("credentials") == "1"
    manifest["dhcp_route_executed"] = contract.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    manifest["wifi_bringup_executed"] = any(
        manifest.get(key)
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
        )
    )
    return manifest


v923.parse_args = parse_args
v923.helper_command = helper_command
v923.helper_surface = helper_surface
v923.decide = decide
v923.render_summary = render_summary
v923.build_manifest = build_manifest

base.parse_args = parse_args
base.helper_command = helper_command
base.helper_surface = helper_surface
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
