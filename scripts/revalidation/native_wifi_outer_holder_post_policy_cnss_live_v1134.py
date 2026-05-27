#!/usr/bin/env python3
"""V1134 outer global holder plus post-policy CNSS PM observer live gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_global_firmware_pm_connect_live_v1113 as v1113
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1134-outer-holder-post-policy-cnss-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1134-outer-holder-post-policy-cnss-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v213"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1134"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1134/outer-holder-post-policy-cnss-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1134/outer-holder-post-policy-cnss-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1134/outer-holder-post-policy-cnss-output.txt"
PROOF_PREFIX = "/tmp/a90-v1134-"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1113.v1106.v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.append("--pm-observer-start-cnss-before-per-proxy")
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
        "mode_ok": v1113.v1106.base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
        "start_cnss_zero_delay_after_per_mgr_flag_ok": "--pm-observer-start-cnss-zero-delay-after-per-mgr" in text,
        "modem_pre_holder_allow_flag_present": "--allow-pm-observer-modem-pre-holder" in text,
        "modem_pre_holder_flag_present": "--pm-observer-modem-pre-holder" in text,
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
    v1113.v1111.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1113.v1111.LATEST_POINTER = LATEST_POINTER
    v1113.v1111.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1113.v1111.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1113.v1111.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1113.v1111.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1113.v1111.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1113.v1111.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1113.v1111.patch_defaults()
    v1113.v1106.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1113.v1106.LATEST_POINTER = LATEST_POINTER
    v1113.v1106.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1113.v1106.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1113.v1106.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1113.v1106.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1113.v1106.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1113.v1106.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1113.v1106.v1095.patch_defaults()
    v1113.v1106.remote_sha_check = v1113.serial_remote_sha_check
    v1113.v1106.remote_marker_check = serial_remote_marker_check
    v1113.v1106.pm_cnss_child_command = pm_cnss_child_command
    v1113.v1106.run_live = v1113.run_live_with_global_firmware


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    value = tracefs(manifest).get("pm_contract") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def global_firmware(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("global_firmware") or {}
    return value if isinstance(value, dict) else {}


def cnss_return_values(manifest: dict[str, Any], label: str) -> list[str]:
    return v1113.cnss_return_values(tracefs(manifest), label)


def contract_value(values: dict[str, str], key: str) -> str:
    return values.get(key) or values.get(f"pm_service_trigger_observer.{key}", "")


def modem_pre_holder_requested(values: dict[str, str]) -> bool:
    return contract_value(values, "modem_pre_holder_requested") == "1"


def decide_v1134(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1134-outer-holder-post-policy-cnss-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, CNSS daemon, reboot, or Wi-Fi action executed",
            "run V401/V490 current-boot preconditions, then run V1134 live with explicit allow flags",
        )

    analysis = manifest.get("analysis") or {}
    fw = global_firmware(manifest)
    tfs = tracefs(manifest)
    values = contract(manifest)
    usage = analysis.get("execns_usage") or {}
    blockers = analysis.get("global_preflight_blockers") or []
    register_ret = cnss_return_values(manifest, "pm_client_register_ret")
    connect_ret = cnss_return_values(manifest, "pm_client_connect_ret")
    blocked = v1113.blocked_open_candidates(values)
    candidates = v1113.v1110.path_candidates(values)
    services = fw.get("qrtr_services_after_observer") or {}
    marker_counts = (fw.get("markers") or {}).get("counts") or {}

    if blockers:
        return ("v1134-global-preflight-blocked", False, f"blockers={blockers}", "clear global holder preflight blockers")
    if tfs.get("result") == "v1113-qrtr-rx-not-observed":
        return ("v1134-outer-holder-qrtr-rx-missing", False, "outer holder did not produce QRTR RX", "restore V731/V1113 lower prerequisite")
    if tfs.get("result") == "v1113-observer-exception":
        return ("v1134-observer-exception", False, str(tfs.get("error", "")), "inspect preserved observer exception")
    if not fw.get("observer_executed"):
        return ("v1134-observer-not-executed", False, f"global={fw}", "run observer only after holder and QRTR RX")
    if not all((fw.get("mounted_hits") or {}).values()):
        return ("v1134-global-firmware-mount-missing", False, f"mounted_hits={fw.get('mounted_hits')}", "repair global firmware mounts")
    if not fw.get("holder_opened"):
        return ("v1134-outer-holder-missing", False, "outer /dev/subsys_modem holder did not open", "repair holder setup")
    if "ONLINE" not in {fw.get("mss_after_holder"), fw.get("mss_after_observer")}:
        return ("v1134-outer-holder-mss-not-online", False, f"mss={fw}", "do not run PM observer until mss reaches ONLINE")
    if not (fw.get("qrtr_rx_wait") or {}).get("seen"):
        return ("v1134-outer-holder-qrtr-rx-missing", False, f"qrtr={fw.get('qrtr_rx_wait')}", "restore QRTR RX before observer")
    cleanup = fw.get("reboot_cleanup") or {}
    if not (cleanup.get("version_seen") and cleanup.get("status_healthy")):
        return ("v1134-reboot-cleanup-unhealthy", False, f"cleanup={cleanup}", "verify native health before continuing")
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1134-execns-helper-sha-mismatch", False, "remote execns helper is not v213", "redeploy helper v213")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
    ):
        return ("v1134-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy/rebuild helper v213")
    if tfs.get("result") != "tracefs-uprobe-pass":
        return ("v1134-tracefs-uprobe-failed", False, f"tracefs result={tfs.get('result')}", "inspect tracefs collector transcript")
    if tfs.get("forbidden_true"):
        return ("v1134-forbidden-action-observed", False, f"forbidden={tfs.get('forbidden_true')}", "stop and audit helper contract")
    if modem_pre_holder_requested(values):
        return ("v1134-helper-private-holder-unexpected", False, "helper-private modem pre-holder was requested", "remove pre-holder flags")
    if values.get("per_proxy_start_executed") != "0" or values.get("child.per_proxy.start_skipped") != "1":
        return ("v1134-pre-cnss-per-proxy-not-skipped", False, f"contract={values}", "repair no-pre-CNSS per_proxy order")
    if values.get("start_cnss_before_per_proxy") != "1" or values.get("cnss_daemon_start_executed") != "1":
        return (
            "v1134-cnss-before-per-proxy-contract-missing",
            False,
            f"start_cnss_before_per_proxy={values.get('start_cnss_before_per_proxy')} cnss={values.get('cnss_daemon_start_executed')}",
            "repair child command flags",
        )
    if services.get("69") or marker_counts.get("wlfw") or marker_counts.get("wlan0"):
        return (
            "v1134-outer-holder-cnss-wlfw-advance",
            True,
            f"services={services} marker_counts={marker_counts}",
            "capture BDF/FW-ready/interface before any scan/connect",
        )
    if "0x0" in register_ret and "0x0" in connect_ret and blocked:
        return (
            "v1134-cnss-pm-connect-still-subsys-modem-blocked",
            True,
            f"register_ret={register_ret} connect_ret={connect_ret} blocked={blocked[:4]}",
            "classify why PM server still opens /dev/subsys_modem despite outer holder",
        )
    if "0x0" in register_ret and "0x0" in connect_ret:
        return (
            "v1134-cnss-pm-connect-no-wlfw-delta",
            True,
            f"register_ret={register_ret} connect_ret={connect_ret} services={services} marker_counts={marker_counts} candidates={candidates[:4]}",
            "classify mdm3/eSoC/WLFW publication gap under combined holder+CNSS gate",
        )
    return (
        "v1134-cnss-pm-connect-not-reproduced",
        True,
        f"register_ret={register_ret} connect_ret={connect_ret} provider={values.get('vndservice_provider_seen')}",
        "classify provider/CNSS readiness regression under outer holder",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    fw = global_firmware(manifest)
    tfs = tracefs(manifest)
    values = contract(manifest)
    counts = (fw.get("markers") or {}).get("counts") or {}
    state_rows = [
        ["mounted_hits", json.dumps(fw.get("mounted_hits", {}), sort_keys=True)],
        ["holder_opened", fw.get("holder_opened", "")],
        ["mss", f"{fw.get('mss_before', '')}->{fw.get('mss_after_holder', '')}->{fw.get('mss_after_observer', '')}"],
        ["mdm3", f"{fw.get('mdm3_before', '')}->{fw.get('mdm3_after_holder', '')}->{fw.get('mdm3_after_observer', '')}"],
        ["qrtr_rx_seen", (fw.get("qrtr_rx_wait") or {}).get("seen", "")],
        ["qrtr_services", json.dumps(fw.get("qrtr_services_after_observer", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(fw.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    pm_rows = [
        ["tracefs_result", tfs.get("result", "")],
        ["provider_seen", values.get("vndservice_provider_seen", "")],
        ["register_ret", json.dumps(cnss_return_values(manifest, "pm_client_register_ret"))],
        ["connect_ret", json.dumps(cnss_return_values(manifest, "pm_client_connect_ret"))],
        ["private_holder_requested", str(modem_pre_holder_requested(values))],
        ["blocked_subsys_modem", json.dumps(v1113.blocked_open_candidates(values)[:8], sort_keys=True)],
        ["marker_counts", json.dumps(counts, sort_keys=True)],
    ]
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1134 Outer Holder Post-policy CNSS Live",
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
        f"- helper_private_holder_requested: `{manifest['helper_private_holder_requested']}`",
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
        "## PM/CNSS Surface",
        "",
        markdown_table(["key", "value"], pm_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1113.v1106.parse_args()
    v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1113.v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1134"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1134(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = global_firmware(manifest)
    values = contract(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["helper_private_holder_requested"] = modem_pre_holder_requested(values)
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
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"helper_private_holder_requested: {manifest['helper_private_holder_requested']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
