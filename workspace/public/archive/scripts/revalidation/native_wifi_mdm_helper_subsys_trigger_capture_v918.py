#!/usr/bin/env python3
"""V918 bounded wait-gated mdm_helper /dev/subsys_esoc0 trigger capture proof.

Runs deployed helper v151 in wifi-companion-mdm-helper-runtime-subsys-trigger-capture
mode. Permitted live actions are selinuxfs mount/cleanup, private property shim,
`/vendor/bin/pm-service`, `/vendor/bin/mdm_helper`, and a bounded child open of
`/dev/subsys_esoc0` only after `mdm_helper` is observable with `/dev/esoc-0`.
No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, controller eSoC notify, or BOOT_DONE spoofing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_ks_contract_live_v900 as base
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import markdown_table


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v918-mdm-helper-subsys-trigger-capture-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v918-mdm-helper-subsys-trigger-capture-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v918-execns-helper-v151-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "aa8e833c292b1b906ec375a6eff9f2c2bd5691b9bfbffb951d6774a6b4ff06c8"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v151"
base.MODE = "wifi-companion-mdm-helper-runtime-subsys-trigger-capture"
base.PREFIX = "mdm_helper_subsys_trigger"

DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"

base.FORBIDDEN_TRUE_KEYS = (
    f"{base.PREFIX}.pm_proxy_helper_start_executed",
    f"{base.PREFIX}.service_manager_start_executed",
    f"{base.PREFIX}.cnss_start_executed",
    f"{base.PREFIX}.wifi_hal_start_executed",
    f"{base.PREFIX}.scan_connect_linkup",
    f"{base.PREFIX}.credentials",
    f"{base.PREFIX}.dhcp_routing",
    f"{base.PREFIX}.external_ping",
    f"{base.PREFIX}.subsys_esoc0_controller_open_attempted",
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
    parser.add_argument("--property-root", default=DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=16)
    parser.add_argument("--toybox-timeout-sec", type=int, default=36)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-mdm-helper-subsys-trigger-capture", action="store_true")
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
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-mdm-helper-subsys-trigger-capture", args.allow_mdm_helper_subsys_trigger_capture),
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
        "--property-root",
        args.property_root,
        "--allow-mdm-helper-subsys-trigger-capture",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def selinuxfs_probe_command(args: argparse.Namespace) -> list[str]:
    return base.v855.shell_cmd(
        args,
        (
            "echo filesystems; "
            "$BB cat /proc/filesystems 2>/dev/null | $BB grep -i selinux || true; "
            "echo mounts; "
            "$BB cat /proc/mounts 2>/dev/null | $BB grep -i selinux || true; "
            "echo status; "
            "$BB ls -l /sys/fs/selinux/status 2>&1 || true"
        ).replace("$BB", args.busybox),
    )


def selinuxfs_mount_command(args: argparse.Namespace) -> list[str]:
    return base.v855.shell_cmd(
        args,
        (
            "$BB mkdir -p /sys/fs/selinux; "
            "if $BB test ! -e /sys/fs/selinux/status; then "
            "$BB mount -t selinuxfs selinuxfs /sys/fs/selinux; "
            "fi; "
            "$BB ls -l /sys/fs/selinux/status /sys/fs/selinux/enforce 2>&1"
        ).replace("$BB", args.busybox),
    )


def selinuxfs_umount_command(args: argparse.Namespace) -> list[str]:
    return base.v855.shell_cmd(
        args,
        (
            "if $BB cat /proc/mounts 2>/dev/null | $BB grep -q ' /sys/fs/selinux '; then "
            "$BB umount /sys/fs/selinux; "
            "fi; "
            "$BB cat /proc/mounts 2>/dev/null | $BB grep -i selinux || true"
        ).replace("$BB", args.busybox),
    )


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
            if key.startswith("mdm_helper_runtime_contract.path_visibility.")
        },
        "mhi_mirror": {
            key: value
            for key, value in keys.items()
            if key.startswith("mdm_helper_runtime_contract.mhi_mirror.")
        },
        "snapshots": {
            key: value
            for key, value in keys.items()
            if key.startswith("mdm_helper_runtime_contract.snapshot.")
        },
        "wifi_surface": {
            key: value
            for key, value in keys.items()
            if key.startswith("wifi_companion_start.") or key.startswith("wifi_icnss_edge.")
        },
        "node_status": {
            key: value
            for key, value in keys.items()
            if key.startswith("android_node.")
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
    v857.run_device(args, store, steps, "pre-selinuxfs-state", selinuxfs_probe_command(args), timeout=12.0)
    if args.allow_selinuxfs_mount:
        v857.run_device(args, store, steps, "mount-selinuxfs", selinuxfs_mount_command(args), timeout=12.0)
    v857.run_device(args, store, steps, "property-root-stat", ["stat", args.property_root], timeout=12.0)
    analysis["remote_helper"] = base.remote_helper_state(args, store, steps)
    helper_step = v857.run_device(args, store, steps, "mdm-helper-subsys-trigger", helper_command(args), timeout=args.toybox_timeout_sec + 25.0)
    analysis["helper"] = helper_surface(base.read_step_file(store, helper_step))
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = base.post_surface(args, store, steps)
    if args.allow_selinuxfs_mount:
        analysis["selinuxfs_umount"] = v857.run_device(args, store, steps, "umount-selinuxfs", selinuxfs_umount_command(args), timeout=12.0)
    contract = (analysis.get("helper") or {}).get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("result") == "reboot-required"
        or contract.get("all_postflight_safe") == "0"
        or bool(post.get("helper_process_hits"))
        or bool(post.get("actor_hits"))
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = base.reboot_cleanup(args, store, "mdm_helper subsys-trigger actor not proven stopped")
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
            return "v918-plan-helper-v150-missing", False, f"local={local}", "build and deploy helper v150 before V918"
        return "v918-mdm-helper-subsys-trigger-plan-ready", True, "plan-only; no device command executed", "run bounded V918 wait-gated subsys trigger capture proof"
    missing = required_flags(args)
    if missing:
        return "v918-mdm-helper-subsys-trigger-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V918 flags"
    helper = analysis.get("helper") or {}
    failed_steps = base.step_failures(steps, helper)
    if failed_steps:
        return "v918-step-failed", False, f"failed_steps={failed_steps}", "inspect V918 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v918-helper-v150-remote-mismatch", False, f"remote={remote}", "redeploy helper v150 before V918"
    if helper.get("forbidden_true"):
        return "v918-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v918-helper-mode-not-executed", False, f"contract={contract}", "fix V918 helper command before retry"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v918-runtime-actors-not-attempted", False, f"contract={contract}", "repair actor ordering before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v918-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    result = contract.get("result")
    if result == "trigger-window-captured":
        return "v918-subsys-trigger-window-captured", True, f"contract={contract}", "inspect WLFW/BDF/wlan0 and mdm3 deltas before any HAL/scan/connect work"
    if result == "trigger-not-attempted-no-esoc-fd":
        return "v918-trigger-not-attempted-no-esoc-fd", True, f"contract={contract}", "classify why bounded gate still did not catch /dev/esoc-0 under native runtime inputs"
    if result == "mdm-helper-not-observable":
        return "v918-mdm-helper-not-observable-clean", True, f"contract={contract}", "classify mdm_helper startup/runtime dependency before retry"
    if result == "reboot-required":
        return "v918-reboot-required-cleaned", True, f"contract={contract}", "inspect pre-reboot subsys trigger evidence"
    if result in {"property-shim-setup-failed", "manual-review-required"}:
        return "v918-subsys-trigger-setup-failed", False, f"contract={contract}", "repair property/per_mgr/mdm_helper trigger setup before retry"
    return "v918-mdm-helper-subsys-trigger-review", False, f"contract={contract}", "inspect V918 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V918 mdm_helper Subsys Trigger Capture",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_root: `{manifest['property_root']}`",
        f"- selinuxfs_mount_executed: `{manifest['selinuxfs_mount_executed']}`",
        f"- selinuxfs_umount_executed: `{manifest['selinuxfs_umount_executed']}`",
        f"- per_mgr_light_start_executed: `{manifest['per_mgr_light_start_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- subsys_esoc0_controller_open_attempted: `{manifest['subsys_esoc0_controller_open_attempted']}`",
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
        "- Permits only selinuxfs mount/cleanup, private property shim, `/vendor/bin/pm-service`, `/vendor/bin/mdm_helper`, and the gated `/dev/subsys_esoc0` child open.",
        "- `pm_proxy_helper`, service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, controller eSoC notify, and controller BOOT_DONE are forbidden.",
        "- No module load/unload, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi link-up.",
        "",
    ])


def _int_key(contract: dict[str, Any], key: str) -> int:
    value = str(contract.get(key) or "0")
    return int(value) if value.lstrip("-").isdigit() else 0


def build_manifest(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    local = base.local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    will_execute = args.command == "run" and not required_flags(args)
    if will_execute:
        steps, analysis = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "mode": base.MODE,
        "property_root": args.property_root,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "selinuxfs_mount_executed": args.command == "run" and args.allow_selinuxfs_mount,
        "selinuxfs_umount_executed": bool((analysis.get("selinuxfs_umount") or {}).get("ok")),
        "per_mgr_light_start_executed": contract.get("per_mgr_start_attempted") == "1",
        "mdm_helper_start_executed": contract.get("mdm_helper_start_attempted") == "1",
        "ks_start_executed": _int_key(contract, "ks_count.window") > 0 or _int_key(contract, "ks_count.final") > 0,
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "subsys_esoc0_controller_open_attempted": contract.get("subsys_esoc0_controller_open_attempted") == "1",
        "notify_attempted": contract.get("notify_attempted") == "1",
        "boot_done_attempted": contract.get("boot_done_attempted") == "1",
        "live_esoc_ioctl_executed": False,
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "service_manager_start_executed": False,
        "cnss_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


base.parse_args = parse_args
base.required_flags = required_flags
base.helper_command = helper_command
base.helper_surface = helper_surface
base.execute = execute
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
