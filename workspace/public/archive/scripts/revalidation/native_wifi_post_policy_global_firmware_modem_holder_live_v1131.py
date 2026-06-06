#!/usr/bin/env python3
"""V1131 post-policy global firmware PM observer modem-holder live gate.

This reuses the V1121 global firmware mount-only live runner, but switches the
remote helper to v213 and enables the PM observer scoped `/dev/subsys_modem`
pre-holder flags added in V1130.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_only_provider_live_v1121 as v1121
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-cnss-pm-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1131-post-policy-global-firmware-modem-holder-cnss-pm-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v213"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1131"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1131/pm-global-firmware-modem-holder-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1131/pm-global-firmware-modem-holder-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1131/pm-global-firmware-modem-holder-output.txt"
PROOF_PREFIX = "/tmp/a90-v1131-"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1121.v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.extend([
        "--pm-observer-start-cnss-before-per-proxy",
        "--allow-pm-observer-modem-pre-holder",
        "--pm-observer-modem-pre-holder",
    ])
    return command


def serial_remote_marker_check(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    step = v1121.v1113.holder.run_step(args, store, steps, "execns-helper-usage", ["run", args.helper, "--help"], 30.0)
    text = str(step.get("payload") or "")
    return {
        "file": step["file"],
        "marker_ok": args.helper_marker in text,
        "mode_ok": v1121.v1106.base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
        "start_cnss_zero_delay_after_per_mgr_flag_ok": "--pm-observer-start-cnss-zero-delay-after-per-mgr" in text,
        "modem_pre_holder_allow_flag_ok": "--allow-pm-observer-modem-pre-holder" in text,
        "modem_pre_holder_flag_ok": "--pm-observer-modem-pre-holder" in text,
        "transport": "cmdv1-serial",
    }


def patch_defaults() -> None:
    v1121.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1121.LATEST_POINTER = LATEST_POINTER
    v1121.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1121.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1121.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1121.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1121.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1121.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1121.PROOF_PREFIX = PROOF_PREFIX
    v1121.v1106.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1121.v1106.LATEST_POINTER = LATEST_POINTER
    v1121.v1106.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1121.v1106.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1121.v1106.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1121.v1106.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1121.v1106.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1121.v1106.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1121.v1106.remote_sha_check = v1121.serial_remote_sha_check
    v1121.v1106.remote_marker_check = serial_remote_marker_check
    v1121.v1106.pm_cnss_child_command = pm_cnss_child_command
    v1121.v1106.run_live = v1121.run_live_with_mount_only


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    value = tracefs(manifest).get("pm_contract") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def firmware_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("firmware_mount_only") or {}
    return value if isinstance(value, dict) else {}


def cnss_return_values(manifest: dict[str, Any], label: str) -> list[str]:
    return v1121.cnss_return_values(tracefs(manifest), label)


def contract_value(values: dict[str, str], key: str) -> str:
    return values.get(key) or values.get(f"pm_service_trigger_observer.{key}", "")


def holder_confirmed(values: dict[str, str]) -> bool:
    return (
        contract_value(values, "modem_pre_holder_confirmed") == "1"
        or contract_value(values, "modem_pre_holder_confirmed_final") == "1"
    )


def modem_holder_fields(values: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in sorted(values.items())
        if key.startswith("modem_pre_holder") or key.startswith("pm_service_trigger_observer.modem_pre_holder")
    }


def decide_v1131(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1131-global-firmware-modem-holder-plan-ready",
            True,
            "plan-only; no device command, tracefs write, PM actor, CNSS actor, reboot, or Wi-Fi action executed",
            "run V401/V490 current-boot preconditions, then run V1131 with explicit allow flags",
        )

    analysis = manifest.get("analysis") or {}
    fw = firmware_summary(manifest)
    tfs = tracefs(manifest)
    values = contract(manifest)
    usage = analysis.get("execns_usage") or {}
    cleanup = fw.get("reboot_cleanup") or {}
    marker_counts = (fw.get("markers") or {}).get("counts") or {}
    services = fw.get("qrtr_services_after_observer") or {}
    register_ret = cnss_return_values(manifest, "pm_client_register_ret")
    connect_ret = cnss_return_values(manifest, "pm_client_connect_ret")
    provider_seen = values.get("vndservice_provider_seen") == "1"
    holder_fields = modem_holder_fields(values)

    if (analysis.get("global_preflight_blockers") or []):
        return (
            "v1131-global-preflight-blocked",
            False,
            f"blockers={analysis.get('global_preflight_blockers')}",
            "clear global firmware preflight blockers before retry",
        )
    if not fw.get("observer_executed"):
        return ("v1131-observer-not-executed", False, f"firmware_mount_only={fw}", "inspect mount setup before retry")
    if not all((fw.get("mounted_hits") or {}).values()):
        return ("v1131-firmware-mounts-missing", False, f"mounted_hits={fw.get('mounted_hits')}", "repair firmware mount setup")
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1131-execns-helper-sha-mismatch", False, "remote execns helper is not v213", "redeploy helper v213")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
        and usage.get("modem_pre_holder_allow_flag_ok")
        and usage.get("modem_pre_holder_flag_ok")
    ):
        return ("v1131-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v213")
    if tfs.get("result") != "tracefs-uprobe-pass":
        return ("v1131-tracefs-uprobe-failed", False, f"tracefs result={tfs.get('result')}", "inspect tracefs collector transcript")
    if tfs.get("forbidden_true"):
        return ("v1131-forbidden-action-observed", False, f"forbidden={tfs.get('forbidden_true')}", "stop and audit helper contract")
    if values.get("per_proxy_start_executed") != "0" or values.get("child.per_proxy.start_skipped") != "1":
        return (
            "v1131-pre-cnss-per-proxy-not-skipped",
            False,
            f"per_proxy_start_executed={values.get('per_proxy_start_executed')} skipped={values.get('child.per_proxy.start_skipped')}",
            "repair no-pre-CNSS per_proxy order",
        )
    if values.get("start_cnss_before_per_proxy") != "1" or values.get("cnss_daemon_start_executed") != "1":
        return (
            "v1131-cnss-before-per-proxy-contract-missing",
            False,
            f"start_cnss_before_per_proxy={values.get('start_cnss_before_per_proxy')} cnss={values.get('cnss_daemon_start_executed')}",
            "repair child command flags before retry",
        )
    if contract_value(values, "modem_pre_holder_requested") != "1":
        return (
            "v1131-modem-holder-not-requested",
            False,
            f"holder={holder_fields}",
            "verify V1131 child command appended modem pre-holder flags",
        )
    if contract_value(values, "modem_pre_holder_allowed") != "1":
        return (
            "v1131-modem-holder-not-allowed",
            False,
            f"holder={holder_fields}",
            "verify allow flag is present before retry",
        )
    if contract_value(values, "modem_pre_holder_start_attempted") != "1":
        return (
            "v1131-modem-holder-not-started",
            False,
            f"holder={holder_fields}",
            "inspect helper fork path before retry",
        )
    if not holder_confirmed(values):
        return (
            "v1131-modem-holder-not-confirmed",
            True,
            f"holder={holder_fields} provider_seen={provider_seen} register_ret={register_ret} connect_ret={connect_ret}",
            "classify why O_NONBLOCK /dev/subsys_modem holder did not confirm before another lower-state retry",
        )
    if services.get("69") or marker_counts.get("wlfw") or marker_counts.get("wlan0"):
        return (
            "v1131-modem-holder-advances-wlfw-surface",
            True,
            f"holder_confirmed=1 services={services} marker_counts={marker_counts}",
            "capture BDF/fw-ready/interface before any scan/connect",
        )
    if provider_seen and "0x0" in register_ret and "0x0" in connect_ret:
        return (
            "v1131-modem-holder-confirmed-lower-state-still-blocked",
            True,
            (
                f"holder_confirmed=1 register_ret={register_ret} connect_ret={connect_ret} "
                f"mss={fw.get('mss_after_observer')} mdm3={fw.get('mdm3_after_observer')}"
            ),
            "classify eSoC/mdm3 transition below confirmed /dev/subsys_modem first-opener",
        )
    if provider_seen and register_ret:
        return (
            "v1131-modem-holder-provider-register-returned",
            True,
            f"holder_confirmed=1 register_ret={register_ret} connect_ret={connect_ret}",
            "trace provider-side register/connect return before changing lower trigger",
        )
    return (
        "v1131-modem-holder-live-inconclusive",
        True,
        f"holder={holder_fields} provider_seen={provider_seen} register_ret={register_ret} connect_ret={connect_ret}",
        "inspect V1131 trace lines before changing PM/eSoC order",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    fw = firmware_summary(manifest)
    tfs = tracefs(manifest)
    values = contract(manifest)
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    holder_fields = modem_holder_fields(values)
    state_rows = [
        ["mounted_hits", json.dumps(fw.get("mounted_hits", {}), sort_keys=True)],
        ["mss", f"{fw.get('mss_before', '')}->{fw.get('mss_after_observer', '')}"],
        ["mdm3", f"{fw.get('mdm3_before', '')}->{fw.get('mdm3_after_observer', '')}"],
        ["qrtr_services", json.dumps(fw.get("qrtr_services_after_observer", {}), sort_keys=True)],
        ["holder", json.dumps(holder_fields, sort_keys=True)],
        ["reboot_cleanup", json.dumps(fw.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V1131 Post-policy Global Firmware Modem-holder Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- modem_pre_holder_requested: `{manifest['modem_pre_holder_requested']}`",
        f"- modem_pre_holder_confirmed: `{manifest['modem_pre_holder_confirmed']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Lower State",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Provider and CNSS PM Path",
        "",
        "```json",
        json.dumps({
            "tracefs_result": tfs.get("result", ""),
            "provider_seen": values.get("vndservice_provider_seen", ""),
            "register_ret": cnss_return_values(manifest, "pm_client_register_ret"),
            "connect_ret": cnss_return_values(manifest, "pm_client_connect_ret"),
            "cnss_register_entries": v1121.cnss_label_count(tfs, "pm_client_register_entry"),
            "cnss_connect_entries": v1121.cnss_label_count(tfs, "pm_client_connect_entry"),
            "post_provider_mdm3_state": values.get("post_provider_surface.after_cnss_daemon.mdm3_state", ""),
            "marker_counts": (fw.get("markers") or {}).get("counts") or {},
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
    args = v1121.v1106.parse_args()
    v1121.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1121.v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1131"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1131(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = firmware_summary(manifest)
    values = contract(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = False
    manifest["modem_pre_holder_requested"] = contract_value(values, "modem_pre_holder_requested") == "1"
    manifest["modem_pre_holder_confirmed"] = holder_confirmed(values)
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = values.get("wifi_hal_start_executed") == "1"
    manifest["scan_connect_executed"] = values.get("scan_connect_linkup") == "1"
    manifest["external_ping_executed"] = values.get("external_ping") == "1"
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"modem_pre_holder_requested: {manifest['modem_pre_holder_requested']}")
    print(f"modem_pre_holder_confirmed: {manifest['modem_pre_holder_confirmed']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
