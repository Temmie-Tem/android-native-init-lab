#!/usr/bin/env python3
"""V1052 bounded PM full-contract live proof with helper v179 private-root modem pre-holder."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_pm_runtime_domain_guard_live_v1032 as v1032


base = v1032.base
v1027 = v1032.v1027
ORIGINAL_DECIDE = v1032.decide
ORIGINAL_BUILD_MANIFEST = v1032.build_manifest
ORIGINAL_RENDER_SUMMARY = v1032.render_summary
ORIGINAL_HELPER_COMMAND = v1032.helper_command

HELPER_SHA256_V179 = "9cb6d49849af181a87a5619e7b3ed7f0f513223ef97ce8b0599ce43694453a7b"
SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1052-pm-full-contract-with-modem-holder-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1052-pm-full-contract-with-modem-holder-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = HELPER_SHA256_V179
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v179"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=base.DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v1027.v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v1027.v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--busybox", default=v1027.v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v1027.v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=base.DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=base.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=base.DEFAULT_HELPER_MARKER)
    parser.add_argument("--property-root", default=v1027.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=30)
    parser.add_argument("--toybox-timeout-sec", type=int, default=180)
    parser.add_argument(
        "--service-manager-order",
        choices=(SERVICE_MANAGER_ORDER,),
        default=SERVICE_MANAGER_ORDER,
    )
    parser.add_argument(
        "--subsys-trigger-gate",
        choices=(v1027.DEFAULT_SUBSYS_TRIGGER_GATE,),
        default=v1027.DEFAULT_SUBSYS_TRIGGER_GATE,
    )
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-mdm-helper-cnss-service-manager-matrix", action="store_true")
    parser.add_argument("--allow-pm-full-contract-with-modem-holder", action="store_true")
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
        ("--allow-pm-full-contract-with-modem-holder", args.allow_pm_full_contract_with_modem_holder),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def helper_command(args: argparse.Namespace) -> list[str]:
    command = ORIGINAL_HELPER_COMMAND(args)
    insert_at = command.index("--timeout-sec") if "--timeout-sec" in command else len(command)
    command.insert(insert_at, "--allow-pm-full-contract-with-modem-holder")
    return command


def _map_v1052(value: str) -> str:
    return (
        value.replace("v1032", "v1052")
        .replace("V1032", "V1052")
        .replace("v175", "v179")
        .replace("v177", "v179")
        .replace("V1052", "V1052")
    )


def decide(args, local: dict[str, Any], steps: list[dict[str, Any]], analysis: dict[str, Any]):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    if args.command == "plan":
        return "v1052-pm-full-contract-with-modem-holder-plan-ready", pass_ok, _map_v1052(reason), "refresh V401/V490, then run bounded V1052 live gate"

    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    if decision in {
        "v1032-pm-runtime-domain-guard-blocked-clean",
        "v1032-helper-v175-remote-mismatch",
        "v1032-forbidden-action-detected",
        "v1032-helper-mode-not-executed",
        "v1032-runtime-domain-guard-not-enabled",
        "v1032-reboot-cleanup-review",
        "v1032-matrix-order-mismatch",
        "v1032-subsys-gate-mismatch",
        "v1032-pm-full-contract-matrix-missing",
    }:
        return _map_v1052(decision), pass_ok, _map_v1052(reason), _map_v1052(next_step)

    if contract.get("pm_full_contract_with_modem_holder_matrix") != "1":
        return (
            "v1052-modem-holder-matrix-missing",
            False,
            "pm_full_contract_with_modem_holder_matrix!=1",
            "fix helper command or v179 matrix selection before retry",
        )
    if contract.get("modem_pre_holder_confirmed") != "1":
        return (
            "v1052-modem-pre-holder-not-confirmed-clean",
            True,
            (
                "modem_pre_holder_confirmed=0 "
                f"child_chroot={contract.get('modem_pre_holder_child_chroot')} "
                f"open_reported={contract.get('modem_pre_holder_open_reported')} "
                f"result_reported={contract.get('modem_pre_holder_result_reported')} "
                f"opened={contract.get('modem_pre_holder_opened')} "
                f"errno={contract.get('modem_pre_holder_errno')} "
                f"pm_full_contract_seen={contract.get('pm_full_contract_seen')}"
            ),
            "classify why modem pre-holder failed before retrying PM full contract",
        )
    if contract.get("pm_full_contract_seen") == "1":
        return (
            "v1052-modem-holder-pm-full-contract-seen",
            True,
            (
                "modem_pre_holder_confirmed=1 "
                f"pm_proxy_helper_subsys_modem_fd_count={contract.get('pm_proxy_helper_subsys_modem_fd_count')} "
                f"per_mgr_subsys_modem_fd_count={contract.get('per_mgr_subsys_modem_fd_count')}"
            ),
            "classify post-PM-fd WLFW/service-manager path before Wi-Fi HAL or scan/connect",
        )
    return (
        "v1052-modem-holder-confirmed-pm-full-contract-missing",
        True,
        (
            "modem_pre_holder_confirmed=1 but "
            f"pm_proxy_helper_subsys_modem_fd_count={contract.get('pm_proxy_helper_subsys_modem_fd_count')} "
            f"per_mgr_subsys_modem_fd_count={contract.get('per_mgr_subsys_modem_fd_count')}"
        ),
        "inspect v1052 PM fd snapshots before deciding whether holder timing or actor order needs repair",
    )


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("# V1032 PM Runtime-Domain Guard Live", "# V1052 PM Full-Contract with Modem Holder Live")
        .replace("V1032", "V1052")
        .replace("helper `v175`", "helper `v179`")
        .replace("helper v175", "helper v179")
        .replace("v175", "v179")
    )


def build_manifest(args, store):
    manifest = ORIGINAL_BUILD_MANIFEST(args, store)
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    contract = helper.get("contract") or {}
    decision, pass_ok, reason, next_step = decide(
        args,
        manifest.get("local_helper") or {},
        manifest.get("steps") or [],
        manifest.get("analysis") or {},
    )
    manifest["decision"] = decision
    manifest["pass"] = pass_ok
    manifest["reason"] = reason
    manifest["next_step"] = next_step
    manifest["helper_marker"] = args.helper_marker
    manifest["helper_sha256"] = args.helper_sha256
    manifest["rerun_after_v1051_v179_deploy"] = True
    manifest["pm_full_contract_with_modem_holder_expected"] = True
    manifest["modem_pre_holder_confirmed"] = contract.get("modem_pre_holder_confirmed") == "1"
    manifest["modem_pre_holder_opened"] = contract.get("modem_pre_holder_opened") == "1"
    manifest["modem_pre_holder_pid"] = contract.get("modem_pre_holder_pid", "")
    manifest["modem_pre_holder_child_chroot"] = contract.get("modem_pre_holder_child_chroot") == "1"
    manifest["modem_pre_holder_path"] = contract.get("modem_pre_holder_path", "")
    manifest["modem_pre_holder_open_reported"] = contract.get("modem_pre_holder_open_reported") == "1"
    manifest["modem_pre_holder_result_reported"] = contract.get("modem_pre_holder_result_reported") == "1"
    manifest["modem_pre_holder_errno"] = contract.get("modem_pre_holder_errno", "")
    manifest["pm_full_contract_with_modem_holder_matrix"] = contract.get("pm_full_contract_with_modem_holder_matrix") == "1"
    manifest["pm_proxy_helper_subsys_modem_fd_count"] = int(str(contract.get("pm_proxy_helper_subsys_modem_fd_count") or "0"))
    manifest["per_mgr_subsys_modem_fd_count"] = int(str(contract.get("per_mgr_subsys_modem_fd_count") or "0"))
    return manifest


v1032.parse_args = parse_args
v1032.required_flags = required_flags
v1032.helper_command = helper_command
v1032.decide = decide
v1032.render_summary = render_summary
v1032.build_manifest = build_manifest
base.parse_args = parse_args
base.required_flags = required_flags
base.helper_command = helper_command
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest
v1032.v923.required_flags = required_flags
v1032.v923.helper_command = helper_command
v1032.v923.decide = decide
v1032.v923.render_summary = render_summary
v1032.v923.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
