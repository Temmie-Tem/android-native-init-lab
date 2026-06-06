#!/usr/bin/env python3
"""V1121 firmware mount-only provider lifetime live gate.

This gate keeps the V1108 provider-positive/no-pre-CNSS-per_proxy order but
adds global firmware mounts.  It intentionally does not open a global
`/dev/subsys_modem` holder, because V1120 proved the holder window currently
breaks `vendor.qcom.PeripheralManager` lookup for `cnss-daemon`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_global_firmware_pm_connect_live_v1113 as v1113
import native_wifi_pm_cnss_voter_surface_live_v1095 as v1095
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1121-firmware-mount-only-provider-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1121-firmware-mount-only-provider-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "6bcf4ad606453f56c4cc25744f6ab90ff6b4cb89942b13c4cc86a7b2f024e44d"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v211"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1121"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1121/pm-mount-only-provider-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1121/pm-mount-only-provider-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1121/pm-mount-only-provider-output.txt"
PROOF_PREFIX = "/tmp/a90-v1121-"

ORIGINAL_V1106_RUN_LIVE = v1106.run_live


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def proof_id(args: argparse.Namespace) -> str:
    explicit = getattr(args, "proof_id", None)
    if explicit:
        return v1113.safe_name(str(explicit))
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.append("--pm-observer-start-cnss-before-per-proxy")
    return command


def serial_remote_sha_check(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    path: str,
    expected: str,
) -> dict[str, Any]:
    step = v1113.holder.run_step(args, store, steps, name, ["run", args.toybox, "sha256sum", path], 30.0)
    text = str(step.get("payload") or "")
    return {"file": step["file"], "ok": expected in text, "expected": expected, "transport": "cmdv1-serial"}


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
        "start_cnss_zero_delay_after_per_mgr_flag_ok": "--pm-observer-start-cnss-zero-delay-after-per-mgr" in text,
        "transport": "cmdv1-serial",
    }


def patch_defaults() -> None:
    v1106.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1106.LATEST_POINTER = LATEST_POINTER
    v1106.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1106.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1106.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1106.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1106.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1106.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1106.remote_sha_check = serial_remote_sha_check
    v1106.remote_marker_check = serial_remote_marker_check
    v1106.pm_cnss_child_command = pm_cnss_child_command
    v1106.run_live = run_live_with_mount_only


def mount_firmware_only(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    preflight: dict[str, Any],
    proof_base: str,
) -> dict[str, Any]:
    before = v1113.holder.run_step(args, store, steps, "mount-only-dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    mount_results: list[str] = []
    for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
        item = v1113.holder.run_step(args, store, steps, f"mount-only-{name}", command, timeout, proof_base)
        mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
    v1113.holder.run_step(args, store, steps, "mount-only-proc-mounts-mounted", ["cat", "/proc/mounts"], 20.0, proof_base)
    v1113.holder.run_step(args, store, steps, "mount-only-firmware-class-path-mounted", ["cat", v1113.holder.FIRMWARE_CLASS_PATH], 10.0, proof_base)
    for path in v1113.holder.GLOBAL_MODEM_BLOB_PATHS + v1113.holder.WLAN_FIRMWARE_PATHS:
        v1113.holder.run_step(args, store, steps, f"mount-only-stat-{v1113.safe_name(path)}", ["stat", path], 10.0, proof_base)
    return {
        "proof_base": proof_base,
        "mount_results": mount_results,
        "dmesg_before": str(before.get("payload") or ""),
    }


def mount_only_summary(
    steps: list[dict[str, Any]],
    setup: dict[str, Any],
    reboot: dict[str, Any] | None,
    observer_executed: bool,
    observer_error: str,
) -> dict[str, Any]:
    mounted = mountv.parse_mounts(v1113.step_payload(steps, "mount-only-proc-mounts-mounted"))
    dmesg_delta = ""
    before = setup.get("dmesg_before", "")
    after = v1113.step_payload(steps, "mount-only-dmesg-after-observer")
    if before and after:
        dmesg_delta = v1113.holder.dmesg_delta(before, after)
    return {
        "proof_base": setup.get("proof_base", ""),
        "mount_results": setup.get("mount_results", []),
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": v1113.step_payload(steps, "mount-only-firmware-class-path-mounted").strip(),
        "modem_blob_visible": {
            path: v1113.holder.path_exists(v1113.step_payload(steps, f"mount-only-stat-{v1113.safe_name(path)}"))
            for path in v1113.holder.GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: v1113.holder.path_exists(v1113.step_payload(steps, f"mount-only-stat-{v1113.safe_name(path)}"))
            for path in v1113.holder.WLAN_FIRMWARE_PATHS
        },
        "mss_before": v1113.step_payload(steps, "global-mss-state-before").strip(),
        "mss_after_observer": v1113.step_payload(steps, "mount-only-mss-state-after-observer").strip(),
        "mdm3_before": v1113.step_payload(steps, "global-mdm3-state-before").strip(),
        "mdm3_after_observer": v1113.step_payload(steps, "mount-only-mdm3-state-after-observer").strip(),
        "qrtr_services_after_observer": v1113.holder.qrtr_service_counts(
            v1113.step_payload(steps, "mount-only-proc-net-qrtr-after-observer")
        ),
        "markers": v1113.holder.marker_summary(dmesg_delta) if dmesg_delta else {},
        "observer_executed": observer_executed,
        "observer_error": observer_error,
        "reboot_cleanup": reboot or {},
    }


def run_live_with_mount_only(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    v1113.set_global_defaults(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    preflight = v1113.capture_global_preflight(args, store, steps)
    blockers = v1113.global_preflight_blockers(preflight, steps)
    analysis["global_preflight"] = preflight
    analysis["global_preflight_blockers"] = blockers
    if blockers:
        analysis["firmware_mount_only"] = {"blockers": blockers, "observer_executed": False}
        analysis["tracefs_uprobe"] = {"result": "v1121-global-preflight-blocked"}
        return steps, analysis

    label = proof_id(args)
    proof_base = PROOF_PREFIX + label
    setup: dict[str, Any] = {}
    reboot: dict[str, Any] | None = None
    observer_executed = False
    observer_error = ""
    try:
        setup = mount_firmware_only(args, store, steps, preflight, proof_base)
        observer_executed = True
        v1113.holder.run_step(args, store, steps, "mount-only-hide-before-observer", ["hide"], 10.0, proof_base)
        observer_steps, observer_analysis = ORIGINAL_V1106_RUN_LIVE(args, store)
        steps.extend(observer_steps)
        analysis.update(observer_analysis)
        v1113.holder.run_step(args, store, steps, "mount-only-mss-state-after-observer", ["cat", v1113.holder.MSS_STATE], 10.0, proof_base)
        v1113.holder.run_step(args, store, steps, "mount-only-mdm3-state-after-observer", ["cat", v1113.holder.MDM3_STATE], 10.0, proof_base)
        v1113.holder.run_step(args, store, steps, "mount-only-proc-net-qrtr-after-observer", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0, proof_base)
        v1113.holder.run_step(args, store, steps, "mount-only-proc-net-dev-after-observer", ["cat", "/proc/net/dev"], 10.0, proof_base)
        v1113.holder.run_step(args, store, steps, "mount-only-dmesg-after-observer", ["run", args.toybox, "dmesg"], 60.0, proof_base)
    except Exception as exc:  # noqa: BLE001 - evidence runner must preserve failure reason
        observer_error = repr(exc)
        analysis.setdefault("tracefs_uprobe", {"result": "v1121-observer-exception", "error": observer_error})
    finally:
        reboot = v1113.holder.reboot_and_wait(args, store)

    analysis["firmware_mount_only"] = mount_only_summary(steps, setup, reboot, observer_executed, observer_error)
    return steps, analysis


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    return v1113.cnss_return_values(tracefs, label)


def cnss_label_count(tracefs: dict[str, Any], label: str) -> int:
    total = 0
    for comm, count in ((tracefs.get("by_label_comm") or {}).get(label) or {}).items():
        if "cnss" not in str(comm):
            continue
        try:
            total += int(count)
        except (TypeError, ValueError):
            continue
    return total


def decide_v1121(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1121-firmware-mount-only-provider-plan-ready",
            True,
            "plan-only; no device command, tracefs write, PM actor, CNSS actor, reboot, or Wi-Fi action executed",
            "run V1121 with explicit firmware mount, tracefs, PM, CNSS, and cleanup allow flags",
        )

    analysis = manifest.get("analysis") or {}
    fw = analysis.get("firmware_mount_only") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    usage = analysis.get("execns_usage") or {}
    blockers = analysis.get("global_preflight_blockers") or []
    register_ret = cnss_return_values(tracefs, "pm_client_register_ret")
    connect_ret = cnss_return_values(tracefs, "pm_client_connect_ret")
    provider_seen = contract.get("vndservice_provider_seen") == "1"
    cleanup = fw.get("reboot_cleanup") or {}
    marker_counts = (fw.get("markers") or {}).get("counts") or {}
    services = fw.get("qrtr_services_after_observer") or {}
    mdm3_state = contract.get("post_provider_surface.after_cnss_daemon.mdm3_state") or fw.get("mdm3_after_observer", "")

    if blockers:
        return ("v1121-global-preflight-blocked", False, f"blockers={blockers}", "clear global firmware preflight blockers")
    if not fw.get("observer_executed"):
        return ("v1121-observer-not-executed", False, f"firmware_mount_only={fw}", "inspect mount-only setup before retry")
    if not all((fw.get("mounted_hits") or {}).values()):
        return ("v1121-firmware-mounts-missing", False, f"mounted_hits={fw.get('mounted_hits')}", "repair firmware mount-only setup")
    if not (cleanup.get("version_seen") and cleanup.get("status_healthy")):
        return ("v1121-reboot-cleanup-unhealthy", False, f"cleanup={cleanup}", "verify native health before continuing")
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1121-execns-helper-sha-mismatch", False, "remote execns helper is not v211", "deploy helper v211")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_flag_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
    ):
        return ("v1121-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v211")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1121-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1121-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return (
            "v1121-pre-cnss-per-proxy-not-skipped",
            False,
            f"per_proxy_start_executed={contract.get('per_proxy_start_executed')} skipped={contract.get('child.per_proxy.start_skipped')}",
            "repair no-pre-CNSS per_proxy order",
        )
    if contract.get("start_cnss_before_per_proxy") != "1" or contract.get("cnss_daemon_start_executed") != "1":
        return (
            "v1121-cnss-before-per-proxy-contract-missing",
            False,
            f"start_cnss_before_per_proxy={contract.get('start_cnss_before_per_proxy')} cnss={contract.get('cnss_daemon_start_executed')}",
            "repair child command flags before retry",
        )

    if services.get("69") or marker_counts.get("wlfw") or marker_counts.get("wlan0"):
        return (
            "v1121-firmware-mount-only-wlfw-advance",
            True,
            f"services={services} marker_counts={marker_counts}",
            "capture BDF/fw-ready/interface before any scan/connect",
        )
    if provider_seen and "0x0" in register_ret and "0x0" in connect_ret:
        return (
            "v1121-firmware-mount-only-provider-cnss-connect-ok",
            True,
            f"provider_seen=1 register_ret={register_ret} connect_ret={connect_ret} mdm3_state={mdm3_state}",
            "classify lower PM/eSoC side effects with firmware mounts but no global holder",
        )
    if provider_seen and register_ret:
        return (
            "v1121-firmware-mount-only-provider-register-returned",
            True,
            f"provider_seen=1 register_ret={register_ret} connect_ret={connect_ret} mdm3_state={mdm3_state}",
            "trace provider-side register return before changing PM order",
        )
    if not provider_seen:
        return (
            "v1121-firmware-mount-only-provider-still-missing",
            True,
            f"provider_seen=0 per_mgr_exited={contract.get('child.per_mgr.exited')} exit={contract.get('child.per_mgr.exit_code')}",
            "compare mount-only per_mgr lifetime against V1108 provider-positive evidence",
        )
    return (
        "v1121-firmware-mount-only-inconclusive",
        True,
        f"provider_seen={provider_seen} register_ret={register_ret} connect_ret={connect_ret} mdm3_state={mdm3_state}",
        "inspect V1121 trace lines before changing provider order",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    fw = analysis.get("firmware_mount_only") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    state_rows = [
        ["mounted_hits", json.dumps(fw.get("mounted_hits", {}), sort_keys=True)],
        ["mss", f"{fw.get('mss_before', '')}->{fw.get('mss_after_observer', '')}"],
        ["mdm3", f"{fw.get('mdm3_before', '')}->{fw.get('mdm3_after_observer', '')}"],
        ["qrtr_services", json.dumps(fw.get("qrtr_services_after_observer", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(fw.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V1121 Firmware Mount-only Provider Live",
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
        "## Firmware Mount-only State",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Provider and CNSS PM Path",
        "",
        "```json",
        json.dumps({
            "tracefs_result": tracefs.get("result", ""),
            "provider_seen": contract.get("vndservice_provider_seen", ""),
            "per_mgr_exited": contract.get("child.per_mgr.exited", ""),
            "per_mgr_exit_code": contract.get("child.per_mgr.exit_code", ""),
            "per_proxy_start_executed": contract.get("per_proxy_start_executed", ""),
            "per_proxy_start_skipped": contract.get("child.per_proxy.start_skipped", ""),
            "register_ret": cnss_return_values(tracefs, "pm_client_register_ret"),
            "connect_ret": cnss_return_values(tracefs, "pm_client_connect_ret"),
            "cnss_register_entries": cnss_label_count(tracefs, "pm_client_register_entry"),
            "cnss_connect_entries": cnss_label_count(tracefs, "pm_client_connect_entry"),
            "post_provider_mdm3_state": contract.get("post_provider_surface.after_cnss_daemon.mdm3_state", ""),
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
    args = v1106.parse_args()
    v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1121"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1121(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = (manifest.get("analysis") or {}).get("firmware_mount_only") or {}
    contract = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {}).get("pm_contract") or {}
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = False
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
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
