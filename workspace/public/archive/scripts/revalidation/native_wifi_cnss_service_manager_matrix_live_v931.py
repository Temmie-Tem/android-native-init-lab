#!/usr/bin/env python3
"""V931 bounded CNSS/service-manager matrix live proof.

Runs deployed helper v154 in the V929 matrix mode. The default order is
`after-mdm-helper-esoc-fd`: preserve the mdm_helper `/dev/esoc-0` lower window,
then start service-manager before CNSS actors. It remains below Wi-Fi HAL and
below scan/connect.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_cnss_before_esoc_capture_v923 as v923
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import markdown_table


base = v923.base

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v931-cnss-service-manager-matrix-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v931-cnss-service-manager-matrix-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v929-execns-helper-v154-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "f87fb6032a4333f4b3dfabc9766b8620bf6e3f2acc9c1081b09738933cc7c9ab"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v154"
base.MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.PREFIX = "cnss_before_esoc"
base.FORBIDDEN_TRUE_KEYS = (
    f"{base.PREFIX}.pm_proxy_helper_start_executed",
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

DEFAULT_PROPERTY_ROOT = v923.DEFAULT_PROPERTY_ROOT
DEFAULT_SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd"


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
    parser.add_argument(
        "--service-manager-order",
        choices=(
            "none",
            "before-cnss",
            "after-cnss",
            "after-mdm-helper-esoc-fd",
            "after-mdm-helper-esoc-fd-with-pm-proxy",
            "after-mdm-helper-esoc-fd-with-pm-full-contract",
        ),
        default=DEFAULT_SERVICE_MANAGER_ORDER,
    )
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-mdm-helper-cnss-service-manager-matrix", action="store_true")
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
        ("--allow-mdm-helper-cnss-service-manager-matrix", args.allow_mdm_helper_cnss_service_manager_matrix),
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
        "compact",
        "--service-manager-order",
        args.service_manager_order,
        "--allow-mdm-helper-cnss-service-manager-matrix",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def decide(
    args: argparse.Namespace,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v931-plan-helper-v154-missing", False, f"local={local}", "deploy helper v154 before V931"
        return "v931-cnss-service-manager-matrix-plan-ready", True, "plan-only; no device command executed", "run bounded V931 matrix proof"
    missing = required_flags(args)
    if missing:
        return "v931-cnss-service-manager-matrix-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V931 flags"
    helper = analysis.get("helper") or {}
    failed_steps = v923.step_failures(steps, helper)
    if failed_steps:
        return "v931-step-failed", False, f"failed_steps={failed_steps}", "inspect V931 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v931-helper-v154-remote-mismatch", False, f"remote={remote}", "redeploy helper v154 before V931"
    if helper.get("forbidden_true"):
        return "v931-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v931-helper-mode-not-executed", False, f"contract={contract}", "fix V931 helper command before retry"
    if contract.get("matrix_mode") != "1" or contract.get("service_manager_order") != args.service_manager_order:
        return "v931-matrix-order-mismatch", False, f"contract={contract}", "fix V931 helper order command before retry"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v931-runtime-actors-not-attempted", False, f"contract={contract}", "repair actor ordering before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v931-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    result = contract.get("result")
    if result == "wlfw-precondition-observed-trigger-clean":
        return "v931-wlfw-precondition-observed-trigger-clean", True, f"contract={contract}", "inspect WLFW/BDF/wlan0 before any HAL/scan/connect work"
    if result in {"wlfw-precondition-missing-no-open", "wlfw-precondition-missing-no-open-output-truncated"}:
        return "v931-wlfw-precondition-missing-no-open", True, f"contract={contract}", "classify Binder/lower publication deltas and choose next matrix order"
    if result == "mdm-helper-esoc-fd-missing-no-open":
        return "v931-mdm-helper-esoc-fd-missing-no-open", True, f"contract={contract}", "classify mdm_helper esoc fd regression under service-manager matrix"
    if result == "reboot-required":
        return "v931-reboot-required-cleaned", True, f"contract={contract}", "inspect pre-reboot matrix evidence"
    return "v931-cnss-service-manager-matrix-review", False, f"contract={contract}", "inspect V931 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V931 CNSS Service-Manager Matrix Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- service_manager_order: `{manifest['service_manager_order']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- cnss_diag_start_executed: `{manifest['cnss_diag_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wlfw_precondition_observed: `{manifest['wlfw_precondition_observed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
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
        "- Permits only selinuxfs mount/cleanup, private property shim, `/vendor/bin/pm-service`, `/vendor/bin/mdm_helper`, service-manager trio according to the selected order, `/vendor/bin/cnss_diag`, `/vendor/bin/cnss-daemon -n -l`, and the WLFW-gated `/dev/subsys_esoc0` child open.",
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, controller eSoC notify, and controller BOOT_DONE are forbidden.",
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
        "service_manager_order": args.service_manager_order,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "selinuxfs_mount_executed": args.command == "run" and args.allow_selinuxfs_mount,
        "selinuxfs_umount_executed": bool((analysis.get("selinuxfs_umount") or {}).get("ok")),
        "per_mgr_light_start_executed": contract.get("per_mgr_start_attempted") == "1",
        "mdm_helper_start_executed": contract.get("mdm_helper_start_attempted") == "1",
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "cnss_diag_start_executed": contract.get("cnss_diag_start_attempted") == "1" or contract.get("cnss_diag_started") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_attempted") == "1" or contract.get("cnss_daemon_started") == "1",
        "wlfw_precondition_observed": contract.get("wlfw_precondition_observed") == "1",
        "ks_start_executed": _int_key(contract, "ks_count.window") > 0 or _int_key(contract, "ks_count.final") > 0,
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "subsys_esoc0_controller_open_attempted": contract.get("subsys_esoc0_controller_open_attempted") == "1",
        "notify_attempted": contract.get("notify_attempted") == "1",
        "boot_done_attempted": contract.get("boot_done_attempted") == "1",
        "live_esoc_ioctl_executed": False,
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
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
