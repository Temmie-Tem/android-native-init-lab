#!/usr/bin/env python3
"""V1027 bounded PM full-contract live classifier.

Runs deployed helper v174 with
`--service-manager-order after-mdm-helper-esoc-fd-with-pm-full-contract`.
This permits PM helper/service actors, mdm_helper, service-manager trio, CNSS
diagnostic actors, and the existing WLFW-precondition gated subsystem child. It
does not start Wi-Fi HAL, scan/connect, use credentials, route traffic, or ping.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_cnss_service_manager_matrix_live_v931 as v931
from a90_kernel_tools import markdown_table


base = v931.base
v923 = v931.v923
v857 = v931.v857

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1027-pm-full-contract-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1027-pm-full-contract-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1025-execns-helper-v174-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "07b9efdebddd955e388026afa2afed86cd52d762dcc4ac36638318f4661fe78f"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v174"
base.MODE = "wifi-companion-mdm-helper-cnss-service-manager-matrix"
base.PREFIX = "cnss_before_esoc"
base.FORBIDDEN_TRUE_KEYS = (
    f"{base.PREFIX}.wifi_hal_start_executed",
    f"{base.PREFIX}.wificond_start_executed",
    f"{base.PREFIX}.scan_connect_linkup",
    f"{base.PREFIX}.credentials",
    f"{base.PREFIX}.dhcp_routing",
    f"{base.PREFIX}.external_ping",
    f"{base.PREFIX}.subsys_esoc0_controller_open_attempted",
    f"{base.PREFIX}.reg_req_eng_attempted",
    f"{base.PREFIX}.notify_attempted",
    f"{base.PREFIX}.boot_done_attempted",
    f"{base.PREFIX}.iwifi_start",
    f"{base.PREFIX}.qcwlanstate_write",
)

DEFAULT_PROPERTY_ROOT = v931.DEFAULT_PROPERTY_ROOT
DEFAULT_SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd-with-pm-full-contract"
DEFAULT_SUBSYS_TRIGGER_GATE = "wlfw-precondition"


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
        choices=(DEFAULT_SERVICE_MANAGER_ORDER,),
        default=DEFAULT_SERVICE_MANAGER_ORDER,
    )
    parser.add_argument(
        "--subsys-trigger-gate",
        choices=(DEFAULT_SUBSYS_TRIGGER_GATE,),
        default=DEFAULT_SUBSYS_TRIGGER_GATE,
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
        "--subsys-trigger-gate",
        args.subsys_trigger_gate,
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
            return "v1027-plan-helper-v174-missing", False, f"local={local}", "build/deploy helper v174 before V1027"
        return "v1027-pm-full-contract-plan-ready", True, "plan-only; no device command executed", "run bounded V1027 PM full-contract classifier"
    missing = required_flags(args)
    if missing:
        return "v1027-pm-full-contract-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1027 flags"
    helper = analysis.get("helper") or {}
    failed_steps = v923.step_failures(steps, helper)
    if failed_steps:
        return "v1027-step-failed", False, f"failed_steps={failed_steps}", "inspect V1027 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1027-helper-v174-remote-mismatch", False, f"remote={remote}", "redeploy helper v174 before V1027"
    if helper.get("forbidden_true"):
        return "v1027-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1027-helper-mode-not-executed", False, f"contract={contract}", "fix V1027 helper command before retry"
    if contract.get("matrix_mode") != "1" or contract.get("service_manager_order") != args.service_manager_order:
        return "v1027-matrix-order-mismatch", False, f"contract={contract}", "fix V1027 helper order command before retry"
    if contract.get("subsys_trigger_gate") != args.subsys_trigger_gate:
        return "v1027-subsys-gate-mismatch", False, f"contract={contract}", "fix V1027 helper gate command before retry"
    if contract.get("pm_full_contract_matrix") != "1":
        return "v1027-pm-full-contract-matrix-missing", False, f"contract={contract}", "repair helper v174 matrix selection"
    if contract.get("pm_proxy_helper_start_executed") != "1" or contract.get("pm_proxy_started") != "1":
        return "v1027-pm-actors-not-started", False, f"contract={contract}", "inspect PM actor startup output"
    if contract.get("per_mgr_start_attempted") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v1027-runtime-actors-not-attempted", False, f"contract={contract}", "repair actor ordering before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1027-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    result = contract.get("result")
    if result == "pm-full-contract-missing-no-open" or contract.get("pm_full_contract_seen") != "1":
        return "v1027-pm-full-contract-missing-no-open", True, f"contract={contract}", "repair PM fd contract before subsystem retry"
    if result == "mdm-helper-esoc-fd-missing-no-open":
        return "v1027-mdm-helper-esoc-fd-missing-no-open", True, f"contract={contract}", "classify mdm_helper fd regression under PM full contract"
    if result == "wlfw-precondition-observed-trigger-clean":
        return "v1027-wlfw-precondition-observed-trigger-clean", True, f"contract={contract}", "inspect WLFW/BDF/wlan0 before scan/connect"
    if result in {"wlfw-precondition-missing-no-open", "wlfw-precondition-missing-no-open-output-truncated"}:
        return "v1027-pm-full-contract-seen-wlfw-missing", True, f"contract={contract}", "run post-provider-no-wlfw subsystem retry as next bounded gate"
    if result == "reboot-required":
        return "v1027-reboot-required-cleaned", True, f"contract={contract}", "inspect pre-reboot PM full-contract evidence"
    return "v1027-pm-full-contract-review", False, f"contract={contract}", "inspect V1027 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V1027 PM Full-Contract Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- service_manager_order: `{manifest['service_manager_order']}`",
        f"- subsys_trigger_gate: `{manifest['subsys_trigger_gate']}`",
        f"- pm_proxy_helper_start_executed: `{manifest['pm_proxy_helper_start_executed']}`",
        f"- pm_proxy_start_executed: `{manifest['pm_proxy_start_executed']}`",
        f"- pm_full_contract_seen: `{manifest['pm_full_contract_seen']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- cnss_diag_start_executed: `{manifest['cnss_diag_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wlfw_precondition_observed: `{manifest['wlfw_precondition_observed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
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
        "- Permits only current-boot selinuxfs mount/cleanup, private property shim, `pm_proxy_helper`, `/vendor/bin/pm-service`, `/vendor/bin/pm-proxy`, `/vendor/bin/mdm_helper`, service-manager trio, `/vendor/bin/cnss_diag`, `/vendor/bin/cnss-daemon -n -l`, and the existing WLFW-precondition-gated `/dev/subsys_esoc0` child open.",
        "- Wi-Fi HAL, `wificond`, `IWifi.start`, `qcwlanstate`, scan/connect, credentials, DHCP/routes, external ping, controller eSoC notify, and controller BOOT_DONE are forbidden.",
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
        "service_manager_order": args.service_manager_order,
        "subsys_trigger_gate": args.subsys_trigger_gate,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "selinuxfs_mount_executed": args.command == "run" and args.allow_selinuxfs_mount,
        "selinuxfs_umount_executed": bool((analysis.get("selinuxfs_umount") or {}).get("ok")),
        "pm_proxy_helper_start_executed": contract.get("pm_proxy_helper_start_executed") == "1",
        "pm_proxy_start_executed": contract.get("pm_proxy_start_attempted") == "1" or contract.get("pm_proxy_started") == "1",
        "pm_full_contract_seen": contract.get("pm_full_contract_seen") == "1",
        "per_mgr_light_start_executed": contract.get("per_mgr_start_attempted") == "1",
        "mdm_helper_start_executed": contract.get("mdm_helper_start_attempted") == "1",
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "cnss_diag_start_executed": contract.get("cnss_diag_start_attempted") == "1" or contract.get("cnss_diag_started") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_attempted") == "1" or contract.get("cnss_daemon_started") == "1",
        "wlfw_precondition_observed": contract.get("wlfw_precondition_observed") == "1",
        "ks_start_executed": False,
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "subsys_esoc0_controller_open_attempted": contract.get("subsys_esoc0_controller_open_attempted") == "1",
        "notify_attempted": contract.get("notify_attempted") == "1",
        "boot_done_attempted": contract.get("boot_done_attempted") == "1",
        "live_esoc_ioctl_executed": False,
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "wifi_hal_start_executed": False,
        "wificond_start_executed": False,
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
