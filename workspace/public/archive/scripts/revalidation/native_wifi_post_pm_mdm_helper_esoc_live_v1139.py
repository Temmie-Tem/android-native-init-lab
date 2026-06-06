#!/usr/bin/env python3
"""V1139 post-PM mdm_helper/eSoC observer live gate.

This runner reuses the V1134 global-firmware outer holder plus post-policy
CNSS PM observer path, but switches the execns helper into the guarded
``wifi-companion-post-pm-mdm-helper-esoc-observer`` mode added in V1137.

It may start service-manager, PM actors, cnss-daemon, and mdm_helper inside a
bounded helper window. It must not start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP/routes, external ping, write boot/partitions, or flash.
Cleanup follows the inherited V1113/V1134 bounded reboot cleanup.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_global_firmware_pm_connect_live_v1113 as v1113
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1139-post-pm-mdm-helper-esoc-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1139-post-pm-mdm-helper-esoc-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "4dd6dea42fddfc1b70732e5695323421a0abf505530ab2d437c6e5418a75638f"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v214"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1139"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1139/post-pm-mdm-helper-esoc-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1139/post-pm-mdm-helper-esoc-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1139/post-pm-mdm-helper-esoc-output.txt"
PROOF_PREFIX = "/tmp/a90-v1139-"
POST_PM_MODE = "wifi-companion-post-pm-mdm-helper-esoc-observer"
POST_PM_ALLOW_FLAG = "--allow-post-pm-mdm-helper-esoc-observer"
POST_PM_START_FLAG = "--pm-observer-start-mdm-helper-after-cnss"

ORIGINAL_TRACEFS_COLLECTOR_SCRIPT = v1113.v1106.tracefs_collector_script
ORIGINAL_PARSE_TRACEFS_OUTPUT = v1113.v1106.parse_tracefs_output


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _replace_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError as exc:
        raise RuntimeError(f"helper command missing {option}") from exc
    if index + 1 >= len(command):
        raise RuntimeError(f"helper command has {option} without value")
    command[index + 1] = value


def _append_unique(command: list[str], flag: str) -> None:
    if flag not in command:
        command.append(flag)


def _remove_flag(command: list[str], flag: str) -> None:
    while flag in command:
        command.pop(command.index(flag))


def _remove_option(command: list[str], option: str) -> None:
    while option in command:
        index = command.index(option)
        del command[index:index + 2]


def pm_post_mdm_helper_child_command(args: argparse.Namespace) -> list[str]:
    command = v1113.v1106.v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    _replace_option(command, "--mode", POST_PM_MODE)
    _remove_flag(command, "--allow-qrtr-ns-readback")
    _remove_option(command, "--qrtr-readback-matrix")
    _append_unique(command, "--pm-observer-start-cnss-before-per-proxy")
    _append_unique(command, POST_PM_ALLOW_FLAG)
    _append_unique(command, POST_PM_START_FLAG)
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
        "mode_ok": POST_PM_MODE in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
        "post_pm_allow_flag_ok": POST_PM_ALLOW_FLAG in text,
        "post_pm_start_flag_ok": POST_PM_START_FLAG in text,
        "transport": "cmdv1-serial",
    }


def tracefs_collector_script_v1139(args: argparse.Namespace) -> str:
    script = ORIGINAL_TRACEFS_COLLECTOR_SCRIPT(args)
    old = r"pm_service_trigger_observer\.|wifi_vndservice_query\.|wifi_companion_qrtr_readback\.|v1106\."
    new = (
        r"pm_service_trigger_observer\.|post_pm_mdm_helper_esoc_observer\.|"
        r"mdm_helper_queue_timing\.|mdm_helper_provider_readiness\.|"
        r"wifi_companion_start\.subsys_hold\.|wifi_companion_start\.cnss2_focus\.|"
        r"pm_provider_lower_surface\.|wifi_vndservice_query\.|"
        r"wifi_companion_qrtr_readback\.|v1106\."
    )
    if old not in script:
        raise RuntimeError("V1106 collector child-summary grep pattern changed")
    return script.replace(old, new)


def _collect_prefix(keys: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def parse_tracefs_output_v1139(text: str) -> dict[str, Any]:
    parsed = ORIGINAL_PARSE_TRACEFS_OUTPUT(text)
    keys = v1113.v1106.parse_keys(text)
    post = _collect_prefix(keys, "post_pm_mdm_helper_esoc_observer.")
    queue = _collect_prefix(keys, "mdm_helper_queue_timing.")
    provider = _collect_prefix(keys, "mdm_helper_provider_readiness.")
    subsys_hold = _collect_prefix(keys, "wifi_companion_start.subsys_hold.")
    cnss2_focus = _collect_prefix(keys, "wifi_companion_start.cnss2_focus.")
    lower_surface = _collect_prefix(keys, "pm_provider_lower_surface.")
    post_forbidden = {
        key: value
        for key, value in post.items()
        if key in {
            "wifi_hal_start_executed",
            "scan_connect_linkup",
            "credentials",
            "dhcp_routing",
            "external_ping",
        } and value not in ("0", "False", "false", "")
    }
    parsed["post_pm_mdm_helper"] = post
    parsed["post_pm_mdm_helper_forbidden_true"] = post_forbidden
    parsed["mdm_helper_queue_timing"] = queue
    parsed["mdm_helper_provider_readiness"] = provider
    parsed["post_pm_subsys_hold"] = subsys_hold
    parsed["post_pm_cnss2_focus"] = cnss2_focus
    parsed["post_pm_lower_surface"] = lower_surface
    return parsed


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
    v1113.v1106.pm_cnss_child_command = pm_post_mdm_helper_child_command
    v1113.v1106.tracefs_collector_script = tracefs_collector_script_v1139
    v1113.v1106.parse_tracefs_output = parse_tracefs_output_v1139
    v1113.v1106.run_live = v1113.run_live_with_global_firmware


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    value = tracefs(manifest).get("pm_contract") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def post_pm(manifest: dict[str, Any]) -> dict[str, str]:
    value = tracefs(manifest).get("post_pm_mdm_helper") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def global_firmware(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("global_firmware") or {}
    return value if isinstance(value, dict) else {}


def cnss_return_values(manifest: dict[str, Any], label: str) -> list[str]:
    return v1113.cnss_return_values(tracefs(manifest), label)


def _filtered_forbidden(trace: dict[str, Any]) -> dict[str, str]:
    forbidden = {
        str(key): str(value)
        for key, value in (trace.get("forbidden_true") or {}).items()
    }
    forbidden.pop("mdm_helper_start_executed", None)
    forbidden.update({
        f"post_pm_mdm_helper_esoc_observer.{key}": value
        for key, value in (trace.get("post_pm_mdm_helper_forbidden_true") or {}).items()
    })
    return forbidden


def decide_v1139(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1139-post-pm-mdm-helper-esoc-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run current-boot V490 precondition, then V1139 bounded live with explicit allow flags",
        )

    analysis = manifest.get("analysis") or {}
    fw = global_firmware(manifest)
    tfs = tracefs(manifest)
    values = contract(manifest)
    post = post_pm(manifest)
    usage = analysis.get("execns_usage") or {}
    blockers = analysis.get("global_preflight_blockers") or []
    register_ret = cnss_return_values(manifest, "pm_client_register_ret")
    connect_ret = cnss_return_values(manifest, "pm_client_connect_ret")
    services = fw.get("qrtr_services_after_observer") or {}
    marker_counts = (fw.get("markers") or {}).get("counts") or {}
    forbidden = _filtered_forbidden(tfs)

    if blockers:
        return ("v1139-global-preflight-blocked", False, f"blockers={blockers}", "clear global holder preflight blockers")
    if tfs.get("result") == "v1113-qrtr-rx-not-observed":
        return ("v1139-outer-holder-qrtr-rx-missing", False, "outer holder did not produce QRTR RX", "restore lower prerequisite before post-PM mdm_helper gate")
    if tfs.get("result") == "v1113-observer-exception":
        return ("v1139-observer-exception", False, str(tfs.get("error", "")), "inspect preserved observer exception")
    if not fw.get("observer_executed"):
        return ("v1139-observer-not-executed", False, f"global={fw}", "run observer only after holder and QRTR RX")
    if not all((fw.get("mounted_hits") or {}).values()):
        return ("v1139-global-firmware-mount-missing", False, f"mounted_hits={fw.get('mounted_hits')}", "repair global firmware mounts")
    if not fw.get("holder_opened"):
        return ("v1139-outer-holder-missing", False, "outer /dev/subsys_modem holder did not open", "repair holder setup")
    if "ONLINE" not in {fw.get("mss_after_holder"), fw.get("mss_after_observer")}:
        return ("v1139-outer-holder-mss-not-online", False, f"mss={fw}", "do not run PM observer until mss reaches ONLINE")
    if not (fw.get("qrtr_rx_wait") or {}).get("seen"):
        return ("v1139-outer-holder-qrtr-rx-missing", False, f"qrtr={fw.get('qrtr_rx_wait')}", "restore QRTR RX before observer")
    cleanup = fw.get("reboot_cleanup") or {}
    if not (cleanup.get("version_seen") and cleanup.get("status_healthy")):
        return ("v1139-reboot-cleanup-unhealthy", False, f"cleanup={cleanup}", "verify native health before continuing")
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1139-execns-helper-sha-mismatch", False, "remote execns helper is not v214", "redeploy helper v214")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
        and usage.get("post_pm_allow_flag_ok")
        and usage.get("post_pm_start_flag_ok")
    ):
        return ("v1139-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy/rebuild helper v214")
    if tfs.get("result") != "tracefs-uprobe-pass":
        return ("v1139-tracefs-uprobe-failed", False, f"tracefs result={tfs.get('result')}", "inspect tracefs collector transcript")
    if forbidden:
        return ("v1139-forbidden-action-observed", False, f"forbidden={forbidden}", "stop and audit helper contract")
    if values.get("mode") != POST_PM_MODE:
        return ("v1139-helper-mode-not-executed", False, f"mode={values.get('mode')}", "repair child command mode replacement")
    if values.get("per_proxy_start_executed") != "0" or values.get("child.per_proxy.start_skipped") != "1":
        return ("v1139-pre-cnss-per-proxy-not-skipped", False, f"contract={values}", "repair no-pre-CNSS per_proxy order")
    if values.get("start_cnss_before_per_proxy") != "1" or values.get("mdm_helper_start_executed") != "1":
        return (
            "v1139-post-pm-mdm-helper-order-missing",
            False,
            f"start_cnss_before_per_proxy={values.get('start_cnss_before_per_proxy')} mdm_helper={values.get('mdm_helper_start_executed')}",
            "repair child command flags",
        )
    post_tail_complete = bool(post.get("result") and post.get("end") == "1")
    post_head_complete = (
        post.get("begin") == "1"
        and post.get("allowed") == "1"
        and post.get("start_after_cnss") == "1"
    )
    if not (post_head_complete or post_tail_complete):
        return ("v1139-post-pm-mdm-helper-prefix-missing", False, f"post={post}", "inspect collector child summary and helper output")
    if post.get("exec_attempted") != "1" or post.get("end") != "1":
        return ("v1139-post-pm-mdm-helper-exec-incomplete", False, f"post={post}", "inspect mdm_helper post-PM observer output")

    post_result = post.get("result", "")
    lower_artifact = post.get("lower_artifact_observed") == "1"
    mdm_helper_observable = post.get("mdm_helper_observable") == "1"
    if services.get("69") or marker_counts.get("wlfw") or marker_counts.get("wlan0"):
        return (
            "v1139-post-pm-mdm-helper-wlfw-advance",
            True,
            f"services={services} marker_counts={marker_counts} post={post}",
            "capture BDF/FW-ready/interface before any scan/connect",
        )
    if lower_artifact:
        return (
            "v1139-post-pm-mdm-helper-lower-artifact-observed",
            True,
            f"post_result={post_result} post={post}",
            "classify which eSoC/MHI/ks artifact appeared before Wi-Fi HAL",
        )
    if mdm_helper_observable:
        return (
            "v1139-mdm-helper-observed-no-lower-publication",
            True,
            f"post_result={post_result} register_ret={register_ret} connect_ret={connect_ret} post={post}",
            "classify why post-PM mdm_helper does not publish eSoC/MHI/WLFW artifacts",
        )
    return (
        "v1139-mdm-helper-not-observable",
        True,
        f"post_result={post_result} register_ret={register_ret} connect_ret={connect_ret} post={post}",
        "classify mdm_helper early exit/runtime contract under post-PM CNSS path",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    fw = global_firmware(manifest)
    tfs = tracefs(manifest)
    values = contract(manifest)
    post = post_pm(manifest)
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
    post_rows = [
        ["tracefs_result", tfs.get("result", "")],
        ["mode", values.get("mode", "")],
        ["provider_seen", values.get("vndservice_provider_seen", "")],
        ["register_ret", json.dumps(cnss_return_values(manifest, "pm_client_register_ret"))],
        ["connect_ret", json.dumps(cnss_return_values(manifest, "pm_client_connect_ret"))],
        ["post_result", post.get("result", "")],
        ["mdm_helper_observable", post.get("mdm_helper_observable", "")],
        ["lower_artifact_observed", post.get("lower_artifact_observed", "")],
        ["fd_esoc0", post.get("fd_esoc0_count.window", "")],
        ["fd_subsys_esoc0", post.get("fd_subsys_esoc0_count.window", "")],
        ["fd_mhi_pipe", post.get("fd_mhi_pipe_count.window", "")],
        ["ks_count", post.get("ks_count.window", "")],
        ["mhi_pipe_cmdline", post.get("mhi_pipe_cmdline_count.window", "")],
        ["marker_counts", json.dumps(counts, sort_keys=True)],
    ]
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1139 Post-PM mdm_helper eSoC Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- helper_mode: `{POST_PM_MODE}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- global_modem_holder_opened: `{manifest['global_modem_holder_opened']}`",
        f"- post_pm_mdm_helper_executed: `{manifest['post_pm_mdm_helper_executed']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- credential_use_executed: `{manifest['credential_use_executed']}`",
        f"- dhcp_route_executed: `{manifest['dhcp_route_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Global Holder State",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Post-PM mdm_helper Surface",
        "",
        markdown_table(["key", "value"], post_rows),
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
    manifest["cycle"] = "v1139"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1139(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = global_firmware(manifest)
    values = contract(manifest)
    post = post_pm(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = values.get("wifi_hal_start_executed") == "1" or post.get("wifi_hal_start_executed") == "1"
    manifest["scan_connect_executed"] = values.get("scan_connect_linkup") == "1" or post.get("scan_connect_linkup") == "1"
    manifest["credential_use_executed"] = post.get("credentials") == "1"
    manifest["dhcp_route_executed"] = post.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = values.get("external_ping") == "1" or post.get("external_ping") == "1"
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
    print(f"post_pm_mdm_helper_executed: {manifest['post_pm_mdm_helper_executed']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
