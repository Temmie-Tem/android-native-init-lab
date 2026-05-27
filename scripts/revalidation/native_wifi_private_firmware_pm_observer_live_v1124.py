#!/usr/bin/env python3
"""V1124 PM observer live gate with helper-private firmware mounts.

This replays the V1108 provider-positive no-pre-CNSS per_proxy order, but asks
helper v212 to mount `apnhlos` and `modem` firmware partitions inside the
private Android runtime namespace only.  It deliberately avoids the global
firmware mount wrapper that V1122 classified as the provider-regression delta.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_cnss_voter_surface_live_v1095 as v1095
import native_wifi_pm_ordering_no_pre_cnss_per_proxy_live_v1108 as v1108
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1124-private-firmware-pm-observer-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1124-private-firmware-pm-observer-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "65fe14f0d7095786d8228750e309e0a1b5d40c33825d1debb87870d9caba0ef3"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v212"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1124"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1124/private-firmware-pm-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1124/private-firmware-pm-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1124/private-firmware-pm-output.txt"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_defaults() -> None:
    v1095.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1123-execns-helper-v212-build/a90_android_execns_probe")
    v1095.DEFAULT_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1095.DEFAULT_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1095.patch_defaults()

    v1106.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1106.LATEST_POINTER = LATEST_POINTER
    v1106.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1106.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1106.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1106.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1106.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1106.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1106.remote_marker_check = remote_marker_check
    v1106.pm_cnss_child_command = pm_cnss_child_command


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.extend([
        "--pm-observer-start-cnss-before-per-proxy",
        "--pm-observer-start-cnss-zero-delay-after-per-mgr",
        "--pm-observer-private-firmware-mounts",
    ])
    return command


def remote_marker_check(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    step = v1106.base.run_tcpctl(args, store, steps, "execns-helper-usage", [args.helper], timeout=30.0)
    text = v1106.step_payload(store, step)
    return {
        "file": step["file"],
        "marker_ok": args.helper_marker in text,
        "mode_ok": v1106.base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
        "start_cnss_zero_delay_after_per_mgr_flag_ok": "--pm-observer-start-cnss-zero-delay-after-per-mgr" in text,
        "private_firmware_mounts_flag_ok": "--pm-observer-private-firmware-mounts" in text,
    }


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    return v1108.cnss_return_values(tracefs, label)


def cnss_label_count(tracefs: dict[str, Any], label: str) -> int:
    total = 0
    by_label = tracefs.get("by_label_comm") or {}
    for comm, count in (by_label.get(label) or {}).items():
        if "cnss" not in str(comm):
            continue
        try:
            total += int(count)
        except (TypeError, ValueError):
            continue
    return total


def decide_v1124(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1124-private-firmware-pm-observer-plan-ready",
            True,
            "plan-only; no deploy, tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "deploy helper v212, then run V1124 with explicit allow flags",
        )

    base_decision = str(manifest.get("decision", ""))
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    usage = analysis.get("execns_usage") or {}

    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1124-execns-helper-sha-mismatch", False, "remote execns helper is not v212", "deploy helper v212")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_flag_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
        and usage.get("start_cnss_zero_delay_after_per_mgr_flag_ok")
        and usage.get("private_firmware_mounts_flag_ok")
    ):
        return ("v1124-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v212")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1124-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1124-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if contract.get("private_firmware_mounts_requested") != "1":
        return ("v1124-private-firmware-flag-not-applied", False, "helper did not report private firmware mount request", "repair V1124 child command")
    if contract.get("private_firmware_mnt_mounted") != "1" or contract.get("private_firmware_modem_mounted") != "1":
        return (
            "v1124-private-firmware-mount-failed",
            False,
            f"firmware_mnt={contract.get('private_firmware_mnt_mounted')} firmware_modem={contract.get('private_firmware_modem_mounted')}",
            "inspect helper setup_error and partition visibility",
        )
    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return (
            "v1124-pre-cnss-per-proxy-not-skipped",
            False,
            f"per_proxy_start_executed={contract.get('per_proxy_start_executed')} skipped={contract.get('child.per_proxy.start_skipped')}",
            "repair helper ordering contract before interpreting live output",
        )
    if contract.get("start_cnss_zero_delay_after_per_mgr") != "1" or contract.get("cnss_daemon_start_executed") != "1":
        return (
            "v1124-zero-delay-cnss-contract-missing",
            False,
            f"zero_delay={contract.get('start_cnss_zero_delay_after_per_mgr')} cnss={contract.get('cnss_daemon_start_executed')}",
            "repair child command flags before retry",
        )

    provider_seen = contract.get("vndservice_provider_seen") == "1"
    cnss_register_entries = cnss_label_count(tracefs, "pm_client_register_entry")
    cnss_connect_entries = cnss_label_count(tracefs, "pm_client_connect_entry")
    cnss_register_returns = cnss_return_values(tracefs, "pm_client_register_ret")
    cnss_connect_returns = cnss_return_values(tracefs, "pm_client_connect_ret")
    mdm3_state = contract.get("post_provider_surface.after_cnss_daemon.mdm3_state") or ""

    if provider_seen and (cnss_connect_entries > 0 or cnss_connect_returns):
        return (
            "v1124-private-firmware-provider-preserved-cnss-connect-reached",
            True,
            f"provider=1 register_ret={cnss_register_returns} connect_entries={cnss_connect_entries} connect_ret={cnss_connect_returns} mdm3_state={mdm3_state}",
            "classify lower modem/eSoC side effects with private firmware mounts before Wi-Fi HAL",
        )
    if provider_seen and cnss_register_returns:
        return (
            "v1124-private-firmware-provider-preserved-cnss-register-returned",
            True,
            f"provider=1 register_entries={cnss_register_entries} register_ret={cnss_register_returns} mdm3_state={mdm3_state}",
            "trace cnss-daemon path after PM register return",
        )
    if provider_seen:
        return (
            "v1124-private-firmware-provider-preserved-cnss-register-pending",
            True,
            f"provider=1 register_entries={cnss_register_entries} base_decision={base_decision} mdm3_state={mdm3_state}",
            "inspect PM server thread state and lower firmware side effects",
        )
    return (
        "v1124-private-firmware-provider-regressed",
        True,
        f"provider=0 per_mgr_exit={contract.get('child.per_mgr.exit_code')} base_decision={base_decision}",
        "trace pm-service early clean exit inside private firmware namespace",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1124 Private Firmware PM Observer Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- base_v1106_decision: `{manifest.get('base_v1106_decision', '')}`",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- private_firmware_mounts_requested: `{contract.get('private_firmware_mounts_requested', '')}`",
        f"- private_firmware_mnt_mounted: `{contract.get('private_firmware_mnt_mounted', '')}`",
        f"- private_firmware_modem_mounted: `{contract.get('private_firmware_modem_mounted', '')}`",
        f"- vndservice_provider_seen: `{contract.get('vndservice_provider_seen', '')}`",
        f"- per_proxy_start_executed: `{contract.get('per_proxy_start_executed', '')}`",
        f"- per_proxy_start_skipped: `{contract.get('child.per_proxy.start_skipped', '')}`",
        f"- start_cnss_zero_delay_after_per_mgr: `{contract.get('start_cnss_zero_delay_after_per_mgr', '')}`",
        f"- cnss_daemon_start_executed: `{contract.get('cnss_daemon_start_executed', '')}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Tracefs",
        "",
        "```json",
        json.dumps({
            "result": tracefs.get("result"),
            "hit_count": tracefs.get("hit_count"),
            "by_comm": tracefs.get("by_comm") or {},
            "return_values_by_comm": tracefs.get("return_values_by_comm") or {},
            "pending_raw_locks_by_comm": tracefs.get("pending_raw_locks_by_comm") or {},
            "completed_raw_locks_by_comm": tracefs.get("completed_raw_locks_by_comm") or {},
            "thread_sample_count": tracefs.get("thread_sample_count") or 0,
        }, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1106.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1124"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1124(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
