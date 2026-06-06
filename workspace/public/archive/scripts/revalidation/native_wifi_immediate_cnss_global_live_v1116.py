#!/usr/bin/env python3
"""V1116 global-holder live gate with immediate CNSS after per_mgr start."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_global_firmware_pm_connect_live_v1113 as v1113
import native_wifi_pm_cnss_voter_surface_live_v1095 as v1095
import native_wifi_pm_connect_path_capture_live_v1110 as v1110
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1116-global-holder-immediate-cnss-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1116-global-holder-immediate-cnss-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "05cf75f9410ec14b07fca0f21de10cf4c08ab618b33770632190099f360497ed"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v210"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1116"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1116/pm-immediate-cnss-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1116/pm-immediate-cnss-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1116/pm-immediate-cnss-output.txt"
PROOF_PREFIX = "/tmp/a90-v1116-"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.extend([
        "--pm-observer-start-cnss-before-per-proxy",
        "--pm-observer-start-cnss-immediate-after-per-mgr",
    ])
    return command


def serial_remote_marker_check(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    step = v1113.holder.run_step(args, store, steps, "execns-helper-usage", ["run", args.helper, "--help"], 30.0)
    text = str(step.get("payload") or "")
    return {
        "file": step["file"],
        "marker_ok": args.helper_marker in text,
        "mode_ok": v1106.base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
        "start_cnss_immediate_after_per_mgr_flag_ok": "--pm-observer-start-cnss-immediate-after-per-mgr" in text,
        "transport": "cmdv1-serial",
    }


def patch_defaults() -> None:
    v1113.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1113.LATEST_POINTER = LATEST_POINTER
    v1113.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1113.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1113.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1113.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1113.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1113.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1113.PROOF_PREFIX = PROOF_PREFIX
    v1113.patch_defaults()
    v1106.remote_marker_check = serial_remote_marker_check
    v1106.pm_cnss_child_command = pm_cnss_child_command


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    return v1110.cnss_return_values(tracefs, label)


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


def decide_v1116(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1116-global-holder-immediate-cnss-plan-ready",
            True,
            "plan-only; no deploy, tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "deploy helper v210, then run V1116 with explicit allow flags",
        )

    analysis = manifest.get("analysis") or {}
    global_fw = analysis.get("global_firmware") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    usage = analysis.get("execns_usage") or {}
    blockers = analysis.get("global_preflight_blockers") or []
    register_ret = cnss_return_values(tracefs, "pm_client_register_ret")
    connect_ret = cnss_return_values(tracefs, "pm_client_connect_ret")
    register_entries = cnss_label_count(tracefs, "pm_client_register_entry")
    connect_entries = cnss_label_count(tracefs, "pm_client_connect_entry")
    cnss_hits = int(str(tracefs.get("cnss_daemon_hit_count") or "0"), 0)
    services = global_fw.get("qrtr_services_after_observer") or {}
    marker_counts = (global_fw.get("markers") or {}).get("counts") or {}

    if blockers:
        return ("v1116-global-preflight-blocked", False, f"blockers={blockers}", "clear global firmware preflight blockers")
    if not global_fw.get("observer_executed"):
        return ("v1116-observer-not-executed", False, f"global={global_fw}", "run only after global holder and QRTR RX are true")
    if not all((global_fw.get("mounted_hits") or {}).values()):
        return ("v1116-global-firmware-mount-missing", False, f"mounted_hits={global_fw.get('mounted_hits')}", "repair global firmware mounts")
    if not global_fw.get("holder_opened"):
        return ("v1116-global-modem-holder-missing", False, "global /dev/subsys_modem holder did not open", "repair holder precondition")
    cleanup = global_fw.get("reboot_cleanup") or {}
    if not (cleanup.get("version_seen") and cleanup.get("status_healthy")):
        return ("v1116-reboot-cleanup-unhealthy", False, f"cleanup={cleanup}", "verify native health before continuing")
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1116-execns-helper-sha-mismatch", False, "remote execns helper is not v210", "deploy helper v210")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_flag_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
        and usage.get("start_cnss_immediate_after_per_mgr_flag_ok")
    ):
        return ("v1116-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v210")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1116-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1116-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if contract.get("start_cnss_immediate_after_per_mgr") != "1":
        return (
            "v1116-immediate-cnss-contract-missing",
            False,
            f"contract_value={contract.get('start_cnss_immediate_after_per_mgr')}",
            "repair child command flags before retry",
        )
    if contract.get("child.per_mgr.post_start_probe_wait_ms") != "20":
        return (
            "v1116-per-mgr-early-probe-missing",
            False,
            f"wait_ms={contract.get('child.per_mgr.post_start_probe_wait_ms')}",
            "repair helper v210 early probe branch",
        )
    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return (
            "v1116-pre-cnss-per-proxy-not-skipped",
            False,
            f"per_proxy_start_executed={contract.get('per_proxy_start_executed')} skipped={contract.get('child.per_proxy.start_skipped')}",
            "repair no-pre-CNSS per_proxy order",
        )
    if contract.get("cnss_daemon_start_executed") != "1":
        return (
            "v1116-cnss-daemon-not-started",
            False,
            f"cnss={contract.get('cnss_daemon_start_executed')}",
            "inspect immediate branch and child output",
        )

    if services.get("69") or marker_counts.get("wlfw") or marker_counts.get("wlan0"):
        return (
            "v1116-immediate-cnss-wlfw-advance",
            True,
            f"services={services} marker_counts={marker_counts}",
            "capture BDF/fw-ready/interface before any scan/connect",
        )
    if "0x0" in connect_ret:
        return (
            "v1116-immediate-cnss-pm-connect-returned-ok",
            True,
            f"register_ret={register_ret} connect_ret={connect_ret}",
            "classify lower PM/eSoC side effects before Wi-Fi HAL",
        )
    if connect_entries > 0 or connect_ret:
        return (
            "v1116-immediate-cnss-pm-connect-path-reached",
            True,
            f"register_entries={register_entries} connect_entries={connect_entries} register_ret={register_ret} connect_ret={connect_ret}",
            "classify PM connect result and lower subsystem side effects",
        )
    if register_entries > 0 or register_ret:
        return (
            "v1116-immediate-cnss-pm-register-path-reached",
            True,
            f"register_entries={register_entries} register_ret={register_ret} cnss_hits={cnss_hits}",
            "trace transition from PM register to PM connect under immediate order",
        )
    if contract.get("child.per_mgr.post_start_observable") == "0" and contract.get("child.per_mgr.exited") == "1":
        return (
            "v1116-per-mgr-exits-before-20ms-sample",
            True,
            f"per_mgr_exit={contract.get('child.per_mgr.exit_code')} signal={contract.get('child.per_mgr.signal')} cnss_hits={cnss_hits}",
            "classify pm-service immediate lifetime or start CNSS with zero-delay fork ordering",
        )
    if cnss_hits > 0:
        return (
            "v1116-cnss-hit-no-pm-client-entry",
            True,
            f"cnss_hits={cnss_hits}",
            "inspect cnss-daemon pre-PM-client startup path under immediate order",
        )
    return (
        "v1116-immediate-cnss-no-pm-client-entry",
        True,
        (
            f"cnss_hits={cnss_hits} "
            f"per_mgr_ready={contract.get('child.per_mgr.post_start_ready')} "
            f"cnss={contract.get('cnss_daemon_start_executed')}"
        ),
        "inspect child output and consider zero-delay CNSS fork ordering",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    global_fw = analysis.get("global_firmware") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    state_rows = [
        ["mounted_hits", json.dumps(global_fw.get("mounted_hits", {}), sort_keys=True)],
        ["holder_opened", global_fw.get("holder_opened", "")],
        ["qrtr_rx_seen", (global_fw.get("qrtr_rx_wait") or {}).get("seen", "")],
        ["mss", f"{global_fw.get('mss_before', '')}->{global_fw.get('mss_after_holder', '')}->{global_fw.get('mss_after_observer', '')}"],
        ["mdm3", f"{global_fw.get('mdm3_before', '')}->{global_fw.get('mdm3_after_holder', '')}->{global_fw.get('mdm3_after_observer', '')}"],
        ["reboot_cleanup", json.dumps(global_fw.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V1116 Global Holder Immediate CNSS Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- global_modem_holder_opened: `{manifest['global_modem_holder_opened']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Global Holder State",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Immediate CNSS Contract",
        "",
        "```json",
        json.dumps({
            "tracefs_result": tracefs.get("result", ""),
            "start_cnss_immediate_after_per_mgr": contract.get("start_cnss_immediate_after_per_mgr", ""),
            "per_mgr_post_start_probe_wait_ms": contract.get("child.per_mgr.post_start_probe_wait_ms", ""),
            "per_mgr_post_start_observable": contract.get("child.per_mgr.post_start_observable", ""),
            "per_mgr_exited": contract.get("child.per_mgr.exited", ""),
            "per_proxy_start_executed": contract.get("per_proxy_start_executed", ""),
            "per_proxy_start_skipped": contract.get("child.per_proxy.start_skipped", ""),
            "cnss_daemon_start_executed": contract.get("cnss_daemon_start_executed", ""),
            "register_ret": cnss_return_values(tracefs, "pm_client_register_ret"),
            "connect_ret": cnss_return_values(tracefs, "pm_client_connect_ret"),
            "cnss_register_entries": cnss_label_count(tracefs, "pm_client_register_entry"),
            "cnss_connect_entries": cnss_label_count(tracefs, "pm_client_connect_entry"),
            "qrtr_services": global_fw.get("qrtr_services_after_observer", {}),
            "marker_counts": (global_fw.get("markers") or {}).get("counts") or {},
        }, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1106.parse_args()
    v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1116"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1116(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    global_fw = (manifest.get("analysis") or {}).get("global_firmware") or {}
    contract = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {}).get("pm_contract") or {}
    manifest["firmware_mounts_executed"] = bool(global_fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(global_fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(global_fw.get("reboot_cleanup"))
    manifest["cnss_daemon_start_executed"] = contract.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
    manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
    manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
