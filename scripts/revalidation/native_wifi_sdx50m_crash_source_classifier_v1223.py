#!/usr/bin/env python3
"""V1223 host-only SDX50M crash-source classifier.

V1222 proved the private CNSS ``SDX50M`` path reaches ``/dev/subsys_esoc0``
and then fails before WLFW/BDF/``wlan0``.  This classifier does not contact the
device.  It joins V1222 with older Android/native evidence to decide whether
the remaining blocker is still CNSS/PM selection, or the lower Android-like
``mdm_helper``/``ks`` MHI image-link contract around eSoC power-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1223-sdx50m-crash-source-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1223-sdx50m-crash-source-classifier.txt")
DEFAULT_V1222_MANIFEST = Path("tmp/wifi/v1222-post-esoc-power-boundary-live/manifest.json")
DEFAULT_V904_MANIFEST = Path("tmp/wifi/v904-mdm-helper-runtime-input-parity/manifest.json")
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1222-manifest", type=Path, default=DEFAULT_V1222_MANIFEST)
    parser.add_argument("--v904-manifest", type=Path, default=DEFAULT_V904_MANIFEST)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def int_field(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def extract_v1222(manifest: dict[str, Any]) -> dict[str, Any]:
    boundary = manifest.get("post_esoc_boundary") or {}
    thread = manifest.get("thread_analysis") or {}
    states = boundary.get("mdm3_state_transitions") or []
    if not isinstance(states, list):
        states = []
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "cnss_registered_sdx50m": bool(thread.get("cnss_registered_sdx50m")),
        "cnss_registered_peripherals": thread.get("cnss_registered_peripherals") or [],
        "mdm_subsys_powerup_any": bool(thread.get("mdm_subsys_powerup_any")),
        "mdm_subsys_powerup_late": bool(thread.get("mdm_subsys_powerup_late")),
        "late_pm_wchans": thread.get("late_pm_wchans") or [],
        "esoc_open_seen": bool(boundary.get("esoc_open_seen")),
        "esoc_syscall_seen": bool(boundary.get("esoc_syscall_seen")),
        "dmesg_esoc_seen": bool(boundary.get("dmesg_esoc_seen")),
        "syscall_paths": boundary.get("syscall_paths") or [],
        "post_hold_count": int_field(boundary, "post_hold_count"),
        "mdm3_state_transitions": states,
        "mdm3_offlining": "OFFLINING" in states,
        "wlan0_seen": bool(boundary.get("wlan0_seen")),
        "service69_seen": bool(boundary.get("service69_seen")),
        "max_dmesg_wlfw_count": int_field(boundary, "max_dmesg_wlfw_count"),
        "max_dmesg_modem_down_count": int_field(boundary, "max_dmesg_modem_down_count"),
        "max_dmesg_esoc_open_count": int_field(boundary, "max_dmesg_esoc_open_count"),
        "cnss_daemon_start_executed": bool(manifest.get("cnss_daemon_start_executed")),
        "wifi_hal_start_executed": bool(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
        "credential_use_executed": bool(manifest.get("credential_use_executed")),
        "dhcp_route_executed": bool(manifest.get("dhcp_route_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
        "wifi_bringup_executed": bool(manifest.get("wifi_bringup_executed")),
        "flash_executed": bool(manifest.get("flash_executed")),
        "partition_write_executed": bool(manifest.get("partition_write_executed")),
    }


def extract_v904(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    classification = manifest.get("classification") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "android_contract": bool(classification.get("android_contract")),
        "native_negative": bool(classification.get("native_negative")),
        "android": {
            "boot_completed": bool(android.get("boot_completed")),
            "mdm_helper_context": android.get("mdm_helper_context", ""),
            "has_mdm_helper_esoc_fd": bool(android.get("has_mdm_helper_esoc_fd")),
            "has_ks_mhi_pipe": bool(android.get("has_ks_mhi_pipe")),
            "has_per_mgr_subsys_esoc0_fd": bool(android.get("has_per_mgr_subsys_esoc0_fd")),
            "has_per_mgr_subsys_modem_fd": bool(android.get("has_per_mgr_subsys_modem_fd")),
            "has_per_mgr_running_trigger": bool(android.get("has_per_mgr_running_trigger")),
            "has_mdm_helper_init_service": bool(android.get("has_mdm_helper_init_service")),
            "has_mdm_helper_selinux": bool(android.get("has_mdm_helper_selinux")),
            "holder_lines": android.get("holder_lines") or [],
            "service_lines": android.get("service_lines") or [],
        },
        "native": {
            "result": native.get("result", ""),
            "reason": native.get("reason", ""),
            "attr_current_final": native.get("attr_current_final", ""),
            "fd_esoc0_count_window": int_field(native, "fd_esoc0_count_window"),
            "fd_esoc0_count_final": int_field(native, "fd_esoc0_count_final"),
            "fd_mhi_pipe_count_window": int_field(native, "fd_mhi_pipe_count_window"),
            "fd_mhi_pipe_count_final": int_field(native, "fd_mhi_pipe_count_final"),
            "ks_count_window": int_field(native, "ks_count_window"),
            "fd_targets_final": native.get("fd_targets_final") or [],
        },
    }


def extract_v896(manifest: dict[str, Any]) -> dict[str, Any]:
    classification = manifest.get("classification") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "android_positive_control": classification.get("android_positive_control", ""),
        "native_negative_control": classification.get("native_negative_control", ""),
        "missing_native_contract": classification.get("missing_native_contract", ""),
    }


def classify(v1222: dict[str, Any], v904: dict[str, Any], v896: dict[str, Any]) -> dict[str, Any]:
    v1222_post_esoc_crash = (
        v1222["pass"]
        and v1222["esoc_open_seen"]
        and v1222["mdm_subsys_powerup_any"]
        and v1222["mdm3_offlining"]
        and not v1222["service69_seen"]
        and not v1222["wlan0_seen"]
        and v1222["max_dmesg_wlfw_count"] == 0
        and v1222["max_dmesg_modem_down_count"] > 0
    )
    pm_selection_repaired = (
        v1222["cnss_registered_sdx50m"]
        and v1222["esoc_open_seen"]
        and "/dev/subsys_esoc0" in v1222["syscall_paths"]
    )
    android_image_link_contract = (
        v904["pass"]
        and v904["android_contract"]
        and v904["android"]["has_mdm_helper_esoc_fd"]
        and v904["android"]["has_ks_mhi_pipe"]
        and v904["android"]["has_per_mgr_subsys_esoc0_fd"]
        and v904["android"]["has_per_mgr_running_trigger"]
        and v904["android"]["has_mdm_helper_selinux"]
    )
    direct_native_missing_contract = (
        v904["pass"]
        and v904["native_negative"]
        and v904["native"]["result"] == "mdm-helper-no-esoc-fd"
        and v904["native"]["fd_esoc0_count_final"] == 0
        and v904["native"]["fd_mhi_pipe_count_final"] == 0
        and v904["native"]["ks_count_window"] == 0
    )
    v896_positive = v896["pass"] and "Android reaches mdm3 ONLINE" in v896["android_positive_control"]
    safety_holds = (
        not v1222["wifi_hal_start_executed"]
        and not v1222["scan_connect_executed"]
        and not v1222["credential_use_executed"]
        and not v1222["dhcp_route_executed"]
        and not v1222["external_ping_executed"]
        and not v1222["wifi_bringup_executed"]
        and not v1222["flash_executed"]
        and not v1222["partition_write_executed"]
    )
    checks = {
        "v1222_post_esoc_crash": v1222_post_esoc_crash,
        "pm_selection_repaired": pm_selection_repaired,
        "android_image_link_contract": android_image_link_contract,
        "direct_native_missing_contract": direct_native_missing_contract,
        "v896_android_positive_control": v896_positive,
        "safety_holds": safety_holds,
    }
    if all(checks.values()):
        return {
            "decision": "v1223-sdx50m-crash-source-contract-gap-classified",
            "pass": True,
            "reason": (
                "Native now reaches SDX50M eSoC power-up via pm-service but crashes before WLFW; "
                "Android success includes the init-managed mdm_helper/ks MHI image-link contract "
                "that direct native mdm_helper lacked."
            ),
            "next_step": (
                "V1224 should run a bounded live parity gate that proves mdm_helper owns /dev/esoc-0 "
                "and ks/MHI appears before or while pm-service opens /dev/subsys_esoc0; keep Wi-Fi HAL, "
                "scan/connect, credentials, DHCP/routes, and external ping blocked."
            ),
            "missing_contract": (
                "Android-equivalent init-managed mdm_helper/ks MHI image-link lifetime/order around "
                "pm-service eSoC open"
            ),
            "checks": checks,
        }
    return {
        "decision": "v1223-sdx50m-crash-source-classifier-incomplete",
        "pass": False,
        "reason": f"classification checks did not all pass: {checks}",
        "next_step": "repair missing or stale V1222/V904/V896 evidence before designing the next live gate",
        "missing_contract": "",
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v1222 = manifest["v1222"]
    v904 = manifest["v904"]
    v896 = manifest["v896"]
    classification = manifest["classification"]
    v1222_rows = [
        ["decision", v1222["decision"]],
        ["pass", v1222["pass"]],
        ["cnss_registered_peripherals", json.dumps(v1222["cnss_registered_peripherals"], ensure_ascii=False)],
        ["esoc_open_seen", v1222["esoc_open_seen"]],
        ["syscall_paths", json.dumps(v1222["syscall_paths"], ensure_ascii=False)],
        ["mdm_subsys_powerup_any", v1222["mdm_subsys_powerup_any"]],
        ["mdm3_state_transitions", json.dumps(v1222["mdm3_state_transitions"], ensure_ascii=False)],
        ["max_dmesg_modem_down_count", v1222["max_dmesg_modem_down_count"]],
        ["max_dmesg_wlfw_count", v1222["max_dmesg_wlfw_count"]],
        ["wlan0_seen", v1222["wlan0_seen"]],
    ]
    android = v904["android"]
    android_rows = [
        ["mdm_helper_context", android["mdm_helper_context"]],
        ["has_mdm_helper_esoc_fd", android["has_mdm_helper_esoc_fd"]],
        ["has_ks_mhi_pipe", android["has_ks_mhi_pipe"]],
        ["has_per_mgr_subsys_esoc0_fd", android["has_per_mgr_subsys_esoc0_fd"]],
        ["has_per_mgr_subsys_modem_fd", android["has_per_mgr_subsys_modem_fd"]],
        ["has_per_mgr_running_trigger", android["has_per_mgr_running_trigger"]],
        ["has_mdm_helper_init_service", android["has_mdm_helper_init_service"]],
        ["has_mdm_helper_selinux", android["has_mdm_helper_selinux"]],
    ]
    native = v904["native"]
    native_rows = [
        ["result", native["result"]],
        ["attr_current_final", native["attr_current_final"]],
        ["fd_esoc0_count_final", native["fd_esoc0_count_final"]],
        ["fd_mhi_pipe_count_final", native["fd_mhi_pipe_count_final"]],
        ["ks_count_window", native["ks_count_window"]],
        ["fd_targets_final", json.dumps(native["fd_targets_final"], ensure_ascii=False)],
    ]
    check_rows = [[key, value] for key, value in classification["checks"].items()]
    holder_lines = [[line] for line in android["holder_lines"][:10]]
    safety_rows = [
        ["device_contact", manifest["device_contact"]],
        ["live_action_executed", manifest["live_action_executed"]],
        ["wifi_hal_start_executed", manifest["wifi_hal_start_executed"]],
        ["scan_connect_executed", manifest["scan_connect_executed"]],
        ["credential_use_executed", manifest["credential_use_executed"]],
        ["dhcp_route_executed", manifest["dhcp_route_executed"]],
        ["external_ping_executed", manifest["external_ping_executed"]],
        ["wifi_bringup_executed", manifest["wifi_bringup_executed"]],
        ["boot_image_write_executed", manifest["boot_image_write_executed"]],
    ]
    return "\n".join([
        "# V1223 SDX50M Crash Source Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- missing_contract: {manifest['missing_contract']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["input", "path", "decision"],
            [
                ["V1222", manifest["v1222_manifest"], v1222["decision"]],
                ["V904", manifest["v904_manifest"], v904["decision"]],
                ["V896", manifest["v896_manifest"], v896["decision"]],
            ],
        ),
        "",
        "## V1222 Post-eSoC Boundary",
        "",
        markdown_table(["field", "value"], v1222_rows),
        "",
        "## Android Success Contract",
        "",
        markdown_table(["field", "value"], android_rows),
        "",
        "## Direct Native Negative Contract",
        "",
        markdown_table(["field", "value"], native_rows),
        "",
        "## Classification Checks",
        "",
        markdown_table(["check", "value"], check_rows),
        "",
        "## Selected Android FD Lines",
        "",
        markdown_table(["line"], holder_lines),
        "",
        "## Interpretation",
        "",
        "- V1222 moves past CNSS peripheral selection: `SDX50M` registration and `/dev/subsys_esoc0` entry are observed.",
        "- The native failure occurs after eSoC power-up starts and before WLFW service 69, BDF transfer, FW-ready, or `wlan0`.",
        "- Android success includes `vendor_mdm_helper` owning `/dev/esoc-0` and `ks` reaching `/dev/mhi_0305_01.01.00_pipe_10` while `pm-service` owns subsystem nodes.",
        "- Direct native `mdm_helper` without the Android init/SELinux/per_mgr contract produced no `/dev/esoc-0`, no `ks`, and no MHI pipe.",
        "- The next live gate should prove that image-link contract is active before expanding toward Wi-Fi HAL or network connection.",
        "",
        "## Safety Audit",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v1222_manifest = load_json(args.v1222_manifest)
    v904_manifest = load_json(args.v904_manifest)
    v896_manifest = load_json(args.v896_manifest)
    v1222 = extract_v1222(v1222_manifest)
    v904 = extract_v904(v904_manifest)
    v896 = extract_v896(v896_manifest)
    classification = classify(v1222, v904, v896)
    manifest = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "missing_contract": classification["missing_contract"],
        "host": collect_host_metadata(),
        "v1222_manifest": str(args.v1222_manifest),
        "v904_manifest": str(args.v904_manifest),
        "v896_manifest": str(args.v896_manifest),
        "v1222": v1222,
        "v904": v904,
        "v896": v896,
        "classification": classification,
        "device_contact": False,
        "live_action_executed": False,
        "android_boot_executed": False,
        "adb_command_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_contact: {manifest['device_contact']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
