#!/usr/bin/env python3
"""V1004 bounded live proof for helper v170 service-window subsystem trigger mode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_android_service_window_live_v970 as v970
import native_wifi_mdm_helper_cnss_before_esoc_capture_v923 as v923
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import markdown_table


base = v970.base

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1004-android-service-window-subsys-trigger-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1004-android-service-window-subsys-trigger-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "edbccfef2fd117c5264c140ff5b2f4cec5424c917151607cecc309268cd9c254"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v170"
base.MODE = "wifi-companion-android-wifi-service-window-subsys-trigger-capture"
base.PREFIX = "android_wifi_service_window"

DEFAULT_PROPERTY_ROOT = v923.DEFAULT_PROPERTY_ROOT

base.FORBIDDEN_TRUE_KEYS = (
    f"{base.PREFIX}.qcwlanstate_write",
    f"{base.PREFIX}.iwifi_start",
    f"{base.PREFIX}.esoc_ioctl_attempted",
    f"{base.PREFIX}.scan_connect_linkup",
    f"{base.PREFIX}.credentials",
    f"{base.PREFIX}.dhcp_routing",
    f"{base.PREFIX}.external_ping",
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
    parser.add_argument("--helper-timeout-sec", type=int, default=18)
    parser.add_argument("--toybox-timeout-sec", type=int, default=46)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-android-wifi-service-window", action="store_true")
    parser.add_argument("--allow-android-wifi-service-window-subsys-trigger-capture", action="store_true")
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
        ("--allow-android-wifi-service-window", args.allow_android_wifi_service_window),
        (
            "--allow-android-wifi-service-window-subsys-trigger-capture",
            args.allow_android_wifi_service_window_subsys_trigger_capture,
        ),
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
        "--cnss-surface-mode",
        "full",
        "--allow-android-wifi-service-window",
        "--allow-android-wifi-service-window-subsys-trigger-capture",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def step_failures(steps: list[dict[str, Any]], helper: dict[str, Any]) -> list[str]:
    contract = helper.get("contract") or {}
    helper_has_evidence = contract.get("begin") == "1" and contract.get("end") == "1"
    ignored = {"remote-helper-usage"}
    if helper_has_evidence:
        ignored.add("mdm-helper-cnss-before-esoc")
    return [step["name"] for step in steps if not step.get("ok") and step.get("name") not in ignored]


def decide(
    args: argparse.Namespace,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1004-plan-helper-v170-missing", False, f"local={local}", "build/deploy helper v170 before V1004"
        return "v1004-service-window-subsys-trigger-plan-ready", True, "plan-only; no device command executed", "run current-boot SELinux refresh, then bounded V1004 live proof"
    missing = required_flags(args)
    if missing:
        return "v1004-service-window-subsys-trigger-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1004 flags"
    helper = analysis.get("helper") or {}
    failed_steps = step_failures(steps, helper)
    if failed_steps:
        return "v1004-step-failed", False, f"failed_steps={failed_steps}", "inspect V1004 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1004-helper-v170-remote-mismatch", False, f"remote={remote}", "redeploy helper v170 before V1004"
    if helper.get("forbidden_true"):
        return "v1004-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1" or contract.get("exec_attempted") != "1":
        return "v1004-helper-mode-not-executed", False, f"contract={contract}", "fix V1004 helper command before retry"
    expected_started = all(
        contract.get(key) == "1"
        for key in (
            "service_manager_start_executed",
            "wifi_hal_start_executed",
            "wificond_start_executed",
            "mdm_helper_start_executed",
            "cnss_daemon_start_executed",
        )
    )
    if not expected_started or contract.get("child_started") != "14":
        return "v1004-service-window-actors-not-started", False, f"contract={contract}", "repair service-window actor order before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1004-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery cleanup before continuing"
    result = contract.get("result")
    if result == "subsys-trigger-window-captured":
        return (
            "v1004-service-window-subsys-trigger-captured",
            True,
            f"contract={contract}",
            "classify trigger child state, WLFW/BDF/wlan0, and mdm3 deltas before any scan/connect",
        )
    if result == "subsys-trigger-not-attempted-no-mdm-helper-esoc-fd":
        return (
            "v1004-mdm-helper-esoc-fd-missing-no-trigger",
            True,
            f"contract={contract}",
            "classify why mdm_helper did not hold /dev/esoc-0 inside the Android service window",
        )
    if result == "subsys-trigger-start-failed":
        return "v1004-subsys-trigger-start-failed", False, f"contract={contract}", "inspect trigger child setup before retry"
    if result == "start-only-reboot-required":
        return "v1004-service-window-cleanup-rebooted", True, f"contract={contract}", "inspect pre-cleanup trigger evidence"
    if result == "wlfw-precondition-observed":
        return "v1004-wlfw-precondition-observed", True, f"contract={contract}", "classify WLFW/BDF/wlan0 evidence before scan/connect"
    if result == "service-window-no-wlfw":
        return "v1004-service-window-no-wlfw", True, f"contract={contract}", "subsystem trigger did not execute; inspect gate evidence"
    if result == "start-only-runtime-gap":
        return "v1004-service-window-runtime-gap", True, f"contract={contract}", "classify which service-window actor exited before timeout"
    return "v1004-service-window-subsys-trigger-review", False, f"contract={contract}", "inspect V1004 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V1004 Android Service-Window Subsys Trigger Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_root: `{manifest['property_root']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wificond_start_executed: `{manifest['wificond_start_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- subsys_trigger_started: `{manifest['subsys_trigger_started']}`",
        f"- wlfw_precondition_observed: `{manifest['wlfw_precondition_observed']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        f"- qcwlanstate_write_executed: `{manifest['qcwlanstate_write_executed']}`",
        f"- esoc_ioctl_attempted: `{manifest['esoc_ioctl_attempted']}`",
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
        "- Permits service-manager trio, QRTR companion stack, Wi-Fi HAL service processes, `wificond`, `mdm_helper`, `cnss_diag`, `cnss-daemon`, and a service-window gated `/dev/subsys_esoc0` child open.",
        "- `qcwlanstate`, `IWifi.start`, eSoC ioctl, scan/connect, credentials, DHCP/routes, and external ping are forbidden.",
        "- No module load/unload, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi link-up.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    local = base.local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    will_execute = args.command == "run" and not required_flags(args)
    if will_execute:
        steps, analysis = v923.execute(args, store)
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
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "wifi_hal_start_executed": contract.get("wifi_hal_start_executed") == "1",
        "wificond_start_executed": contract.get("wificond_start_executed") == "1",
        "mdm_helper_start_executed": contract.get("mdm_helper_start_executed") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_executed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "subsys_trigger_started": contract.get("subsys_trigger.started") == "1",
        "wlfw_precondition_observed": contract.get("wlfw_precondition_observed") == "1",
        "ks_start_executed": False,
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "qcwlanstate_write_executed": contract.get("qcwlanstate_write") == "1",
        "iwifi_start_executed": contract.get("iwifi_start") == "1",
        "esoc_ioctl_attempted": contract.get("esoc_ioctl_attempted") == "1",
        "live_esoc_ioctl_executed": False,
        "scan_connect_executed": contract.get("scan_connect_linkup") == "1",
        "credential_use_executed": contract.get("credentials") == "1",
        "dhcp_route_executed": contract.get("dhcp_routing") == "1",
        "external_ping_executed": contract.get("external_ping") == "1",
        "wifi_bringup_executed": False,
    }


base.parse_args = parse_args
base.required_flags = required_flags
base.helper_command = helper_command
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest
v923.required_flags = required_flags
v923.helper_command = helper_command
v923.decide = decide
v923.render_summary = render_summary
v923.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
