#!/usr/bin/env python3
"""V903 bounded mdm_helper-only deep capture proof.

This reuses the V900 live runner skeleton with helper v147 and a reduced mode:
start `/vendor/bin/mdm_helper`, capture its process/socket/fd surface, and never
open `/dev/subsys_esoc0`.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_ks_contract_live_v900 as base
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import markdown_table


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v903-mdm-helper-only-deep-capture-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v903-mdm-helper-only-deep-capture-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v903-execns-helper-v147-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "c2e42c6d6b6446072b42b904176321491c84de9e6c629474db4c09d9489a298d"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v147"
base.MODE = "wifi-companion-mdm-helper-only-deep-capture"
base.PREFIX = "mdm_helper_only_capture"
base.FORBIDDEN_TRUE_KEYS = (
    f"{base.PREFIX}.service_manager_start_executed",
    f"{base.PREFIX}.cnss_start_executed",
    f"{base.PREFIX}.wifi_hal_start_executed",
    f"{base.PREFIX}.scan_connect_linkup",
    f"{base.PREFIX}.credentials",
    f"{base.PREFIX}.dhcp_routing",
    f"{base.PREFIX}.external_ping",
    f"{base.PREFIX}.subsys_esoc0_open_attempted",
    f"{base.PREFIX}.reg_req_eng_attempted",
    f"{base.PREFIX}.notify_attempted",
    f"{base.PREFIX}.boot_done_attempted",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=base.DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v857.DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=base.DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=base.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=base.DEFAULT_HELPER_MARKER)
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    parser.add_argument("--toybox-timeout-sec", type=int, default=22)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-mdm-helper-only-capture", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-mdm-helper-only-capture", args.allow_mdm_helper_only_capture),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.toybox,
        "timeout",
        str(args.toybox_timeout_sec),
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        base.MODE,
        "--null-device-mode",
        "dev-null",
        "--allow-mdm-helper-only-capture",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def helper_surface(text: str) -> dict[str, Any]:
    keys = base.parse_keys(text)
    prefix = base.PREFIX
    interesting = {
        key[len(prefix) + 1:]: value
        for key, value in keys.items()
        if key.startswith(f"{prefix}.")
    }
    return {
        "contract": interesting,
        "path_visibility": {
            key: value
            for key, value in keys.items()
            if key.startswith(f"{prefix}.path_visibility.")
        },
        "node_status": {
            key: value
            for key, value in keys.items()
            if key.startswith("android_node.")
        },
        "fd_match": {
            key: value
            for key, value in keys.items()
            if key.startswith(f"{prefix}.fd_match.")
        },
        "forbidden_true": {key: keys.get(key) for key in base.FORBIDDEN_TRUE_KEYS if keys.get(key) not in (None, "0")},
    }


def execute(args: argparse.Namespace, store: base.EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    if args.allow_mountsystem_ro:
        v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    analysis["remote_helper"] = base.remote_helper_state(args, store, steps)
    helper_step = v857.run_device(args, store, steps, "mdm-helper-only-capture", helper_command(args), timeout=args.toybox_timeout_sec + 25.0)
    analysis["helper"] = helper_surface(base.read_step_file(store, helper_step))
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = base.post_surface(args, store, steps)
    contract = (analysis.get("helper") or {}).get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("result") == "reboot-required"
        or contract.get("all_postflight_safe") == "0"
        or bool(post.get("helper_process_hits"))
        or bool(post.get("mdm_helper_or_ks_hits"))
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = base.reboot_cleanup(args, store, "mdm_helper-only capture not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "cleanup needed but --allow-cleanup-reboot not set", "healthy": False}
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v903-plan-helper-v147-missing", False, f"local={local}", "build and deploy helper v147 before V903"
        return "v903-mdm-helper-only-capture-plan-ready", True, "plan-only; no device command executed", "run bounded V903 mdm_helper-only deep capture proof"
    missing = required_flags(args)
    if missing:
        return "v903-mdm-helper-only-capture-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V903 flags"
    helper = analysis.get("helper") or {}
    failed_steps = base.step_failures(steps, helper)
    if failed_steps:
        return "v903-step-failed", False, f"failed_steps={failed_steps}", "inspect V903 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v903-helper-v147-remote-mismatch", False, f"remote={remote}", "redeploy helper v147 before V903"
    if helper.get("forbidden_true"):
        return "v903-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v903-helper-mode-not-executed", False, f"contract={contract}", "fix V903 helper command before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v903-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    result = contract.get("result")
    if result == "mdm-helper-esoc-fd-observed":
        return "v903-mdm-helper-esoc-fd-observed", True, f"contract={contract}", "classify why mdm_helper does not proceed to ks/MHI before subsystem-open retry"
    if result == "mdm-helper-produced-ks-mhi":
        return "v903-mdm-helper-produced-ks-mhi", True, f"contract={contract}", "inspect mdm3/GPIO142/WLFW/BDF/wlan0 deltas before HAL or scan work"
    if result == "mdm-helper-no-esoc-fd":
        return "v903-mdm-helper-no-esoc-fd", True, f"contract={contract}", "compare Android mdm_helper runtime inputs or property/init context"
    if result == "mdm-helper-not-observable":
        return "v903-mdm-helper-not-observable-clean", True, f"contract={contract}", "classify mdm_helper startup/runtime dependency before retry"
    if result == "reboot-required":
        return "v903-reboot-required-cleaned", True, f"contract={contract}", "inspect pre-reboot mdm_helper-only evidence"
    return "v903-mdm-helper-only-capture-review", False, f"contract={contract}", "inspect V903 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V903 mdm_helper-only Deep Capture Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- ks_start_executed: `{manifest['ks_start_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- live_esoc_ioctl_executed: `{manifest['live_esoc_ioctl_executed']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- Only `/vendor/bin/mdm_helper` start and passive process/fd/socket capture are permitted.",
        "- `/dev/subsys_esoc0` is never opened by this proof.",
        "- No `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `ESOC_NOTIFY`, or `BOOT_DONE`.",
        "- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No module load/unload, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi link-up.",
        "",
    ])


base.parse_args = parse_args
base.required_flags = required_flags
base.helper_command = helper_command
base.helper_surface = helper_surface
base.execute = execute
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
