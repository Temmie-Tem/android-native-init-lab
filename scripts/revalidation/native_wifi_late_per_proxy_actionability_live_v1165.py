#!/usr/bin/env python3
"""V1165 bounded late pm-proxy actionability live gate.

This V1143 derivative keeps the global-firmware outer holder, post-policy
CNSS PM path, post-PM mdm_helper lower trace, and helper cleanup.  It uses
helper v217 to extend the late pm-proxy window and record per-poll process state:

    --pm-observer-start-per-proxy-after-mdm-helper-esoc-fd

The live gate may start PM/CNSS actors, mdm_helper, and a bounded late
pm-proxy after mdm_helper has /dev/esoc-0.  It must not start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP/routes, external ping, write
boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_post_pm_lower_trace_live_v1143 as v1143
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1165-late-per-proxy-actionability-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1165-late-per-proxy-actionability-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "559adaf4b2acd4c0a84d6f4082eb9bdd085717b9a875eec8766d803b51257a6f"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v217"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1165"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1165/late-per-proxy-actionability-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1165/late-per-proxy-actionability-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1165/late-per-proxy-actionability-output.txt"
PROOF_PREFIX = "/tmp/a90-v1165-"
LATE_PER_PROXY_FLAG = "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd"

_base_child_command = v1143.pm_post_lower_trace_child_command
_base_remote_marker_check = v1143.serial_remote_marker_check_v1143
_base_tracefs_collector_script = v1143.tracefs_collector_script_v1143
_base_parse_tracefs_output = v1143.parse_tracefs_output_v1143


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _append_unique(command: list[str], flag: str) -> None:
    if flag not in command:
        command.append(flag)


def pm_late_per_proxy_child_command(args: Any) -> list[str]:
    command = _base_child_command(args)
    _append_unique(command, LATE_PER_PROXY_FLAG)
    return command


def serial_remote_marker_check_v1165(
    args: Any,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    info = _base_remote_marker_check(args, store, steps)
    step_file = info.get("file", "")
    text = ""
    if step_file:
        text = (store.run_dir / str(step_file)).read_text(encoding="utf-8", errors="replace")
    info["late_per_proxy_flag_ok"] = LATE_PER_PROXY_FLAG in text
    return info


def tracefs_collector_script_v1165(args: Any) -> str:
    return _base_tracefs_collector_script(args)


def _collect_prefix(keys: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def _is_positive(value: Any) -> bool:
    try:
        return int(str(value), 0) > 0
    except ValueError:
        return str(value) not in {"", "-1", "0", "False", "false", "none", "None"}


def parse_tracefs_output_v1165(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output(text)
    keys = v1143.v1139.v1113.v1106.parse_keys(text)
    pm = _collect_prefix(keys, "pm_service_trigger_observer.")
    late = _collect_prefix(keys, "pm_service_trigger_observer.late_per_proxy.")
    post_late = _collect_prefix(keys, "post_pm_mdm_helper_esoc_observer.late_per_proxy.")
    late_polls = {
        key: value
        for key, value in pm.items()
        if "late_per_proxy_poll_" in key
    }
    parsed["pm_service_trigger_observer"] = pm
    parsed["late_per_proxy"] = late
    parsed["post_pm_late_per_proxy"] = post_late
    parsed["late_per_proxy_polls"] = late_polls
    return parsed


def patch_defaults() -> None:
    v1143.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1143.LATEST_POINTER = LATEST_POINTER
    v1143.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1143.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1143.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1143.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1143.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1143.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1143.PROOF_PREFIX = PROOF_PREFIX
    v1143.pm_post_lower_trace_child_command = pm_late_per_proxy_child_command
    v1143.serial_remote_marker_check_v1143 = serial_remote_marker_check_v1165
    v1143.tracefs_collector_script_v1143 = tracefs_collector_script_v1165
    v1143.parse_tracefs_output_v1143 = parse_tracefs_output_v1165
    v1143.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def late_per_proxy(manifest: dict[str, Any]) -> dict[str, str]:
    tfs = tracefs(manifest)
    value = tfs.get("late_per_proxy") or {}
    late = {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}
    pm = tfs.get("pm_service_trigger_observer") or {}
    if isinstance(pm, dict):
        for key, item in pm.items():
            key_text = str(key)
            if key_text.startswith("late_per_proxy_"):
                late.setdefault(key_text[len("late_per_proxy_"):], str(item))
    return late


def late_polls(manifest: dict[str, Any]) -> dict[str, str]:
    value = tracefs(manifest).get("late_per_proxy_polls") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def _positive_poll_values(polls: dict[str, str], suffix: str) -> list[str]:
    return [
        value
        for key, value in polls.items()
        if key.endswith(suffix) and _is_positive(value)
    ]


def _poll_values(polls: dict[str, str], suffix: str) -> list[str]:
    return [
        value
        for key, value in sorted(polls.items())
        if key.endswith(suffix)
    ]


def _trace_action_lines(tfs: dict[str, Any]) -> list[str]:
    wanted = (
        "pm_server_connect_impl_state_check",
        "pm_server_connect_impl_start_vote",
        "pm_server_connect_impl_return",
        "pm_server_connect_impl_ret",
        "pm_server_connect_ret",
    )
    return [
        str(line)
        for line in tfs.get("trace_lines", [])
        if any(label in str(line) for label in wanted)
    ][:24]


def decide_v1165(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1165-late-per-proxy-actionability-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded late pm-proxy actionability live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1143.decide_v1143(args, manifest)
    analysis = manifest.get("analysis") or {}
    usage = analysis.get("execns_usage") or {}
    tfs = tracefs(manifest)
    late = late_per_proxy(manifest)
    polls = late_polls(manifest)
    values = v1143.v1139.contract(manifest)
    post = v1143.v1139.post_pm(manifest)
    queue = tfs.get("mdm_helper_queue_timing") or {}
    queue = {str(key): str(value) for key, value in queue.items()} if isinstance(queue, dict) else {}
    deferred_per_proxy_expected = (
        base_decision.endswith("-pre-cnss-per-proxy-not-skipped")
        and values.get("per_proxy_initial_start_executed") == "0"
        and values.get("child.per_proxy.start_skipped") == "1"
        and values.get("child.per_proxy.skip_reason") == "deferred-until-mdm-helper-esoc-fd"
        and values.get("late_per_proxy_after_mdm_helper_esoc_fd_requested") == "1"
    )

    if not usage.get("late_per_proxy_flag_ok"):
        return (
            "v1165-helper-late-per-proxy-flag-missing",
            False,
            f"usage={usage}",
            "redeploy helper v217 or inspect helper usage output",
        )
    if not base_pass and not deferred_per_proxy_expected:
        return (
            base_decision.replace("v1143", "v1165", 1).replace("v1139", "v1165", 1),
            False,
            base_reason,
            base_next,
        )
    if late.get("begin") != "1":
        if post.get("mdm_helper_observable") == "0" or values.get("child.per_mgr.exit_code") == "0":
            return (
                "v1165-pm-service-exited-before-late-per-proxy",
                True,
                f"per_mgr_exit={values.get('child.per_mgr.exit_code')} post={post} late={late}",
                "classify why pm-service exits before mdm_helper /dev/esoc-0 readiness in the v217 late gate",
            )
        return (
            "v1165-late-per-proxy-not-reached",
            True,
            f"base_decision={base_decision} post_result={post.get('result', '')} late={late}",
            "restore post-PM mdm_helper readiness before retrying late pm-proxy",
        )
    if late.get("gate_positive") != "1":
        return (
            "v1165-late-per-proxy-gate-not-opened",
            True,
            f"late={late}",
            "classify why mdm_helper /dev/esoc-0 readiness was not positive in the late-start window",
        )
    if late.get("started") != "1":
        return (
            "v1165-late-per-proxy-start-missing",
            False,
            f"late={late}",
            "inspect helper output; gate was positive but pm-proxy did not start",
        )
    if late.get("snapshot_captured") != "1":
        return (
            "v1165-late-per-proxy-snapshot-incomplete",
            False,
            f"late={late}",
            "inspect helper cleanup and rerun only after state is clean",
        )

    per_mgr_esoc = _positive_poll_values(polls, "per_mgr_subsys_esoc0_count")
    queue_esoc = [
        value
        for key, value in queue.items()
        if "late_per_proxy_poll_" in key and key.endswith(".per_mgr_subsys_esoc0_count") and _is_positive(value)
    ]
    lower_values = [
        value
        for key, value in queue.items()
        if "late_per_proxy_poll_" in key and (
            key.endswith(".mdm_helper_mhi_pipe_count") or
            key.endswith(".ks_count") or
            key.endswith(".mhi_pipe_cmdline_count")
        ) and _is_positive(value)
    ]
    if lower_values:
        return (
            "v1165-late-per-proxy-lower-artifact-observed",
            True,
            f"late={late} lower_values={lower_values}",
            "preserve evidence; next gate should check WLFW/service69/wlan0 before any scan/connect",
        )
    if per_mgr_esoc or queue_esoc:
        return (
            "v1165-late-per-proxy-esoc-trigger-observed",
            True,
            f"per_mgr_esoc={per_mgr_esoc} queue_esoc={queue_esoc} late={late}",
            "classify whether eSoC trigger progresses to MHI/ks/WLFW after a longer bounded observation",
        )
    return (
        "v1165-late-per-proxy-actionability-gap",
        True,
        "late pm-proxy stayed alive through the bounded window, PM server connect/start-vote returned success, but pm-service never opened /dev/subsys_esoc0",
        "inspect per-proxy exit/stdout/stderr state and PM server action arguments before changing the trigger path",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    fw = v1143.v1139.global_firmware(manifest)
    tfs = tracefs(manifest)
    values = v1143.v1139.contract(manifest)
    post = v1143.v1139.post_pm(manifest)
    lower = v1143.lower_trace(manifest)
    late = late_per_proxy(manifest)
    polls = late_polls(manifest)
    counts = (fw.get("markers") or {}).get("counts") or {}
    action_lines = _trace_action_lines(tfs)
    state_rows = [
        ["mounted_hits", json.dumps(fw.get("mounted_hits", {}), sort_keys=True)],
        ["holder_opened", fw.get("holder_opened", "")],
        ["mss", f"{fw.get('mss_before', '')}->{fw.get('mss_after_holder', '')}->{fw.get('mss_after_observer', '')}"],
        ["mdm3", f"{fw.get('mdm3_before', '')}->{fw.get('mdm3_after_holder', '')}->{fw.get('mdm3_after_observer', '')}"],
        ["qrtr_rx_seen", (fw.get("qrtr_rx_wait") or {}).get("seen", "")],
        ["qrtr_services", json.dumps(fw.get("qrtr_services_after_observer", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(fw.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    late_rows = [
        ["tracefs_result", tfs.get("result", "")],
        ["mode", values.get("mode", "")],
        ["register_ret", json.dumps(v1143.v1139.cnss_return_values(manifest, "pm_client_register_ret"))],
        ["connect_ret", json.dumps(v1143.v1139.cnss_return_values(manifest, "pm_client_connect_ret"))],
        ["post_result", post.get("result", "")],
        ["mdm_helper_observable", post.get("mdm_helper_observable", "")],
        ["lower_begin_end", f"{lower.get('begin', '')}/{lower.get('end', '')}"],
        ["late_begin", late.get("begin", "")],
        ["late_gate_positive", late.get("gate_positive", "")],
        ["late_start_attempted", late.get("start_attempted", "")],
        ["late_started", late.get("started", "")],
        ["late_instrumentation", late.get("instrumentation", "")],
        ["late_poll_max", late.get("poll_max", "")],
        ["late_poll_interval_ms", late.get("poll_interval_ms", "")],
        ["late_snapshot_captured", late.get("snapshot_captured", "")],
        ["late_poll_count", tfs.get("pm_service_trigger_observer", {}).get("late_per_proxy_poll_count", "") if isinstance(tfs.get("pm_service_trigger_observer"), dict) else ""],
        ["per_proxy_alive_by_poll", json.dumps(_poll_values(polls, "per_proxy_alive"))],
        ["per_proxy_exit_code_by_poll", json.dumps(_poll_values(polls, "per_proxy_exit_code"))],
        ["per_proxy_signal_by_poll", json.dumps(_poll_values(polls, "per_proxy_signal"))],
        ["per_proxy_stdout_open_by_poll", json.dumps(_poll_values(polls, "per_proxy_stdout_open"))],
        ["per_proxy_stderr_open_by_poll", json.dumps(_poll_values(polls, "per_proxy_stderr_open"))],
        ["poll_esoc_hits", json.dumps(_positive_poll_values(polls, "per_mgr_subsys_esoc0_count"))],
        ["pm_server_connect_hits", json.dumps(tfs.get("connect_impl_hits_by_comm", {}), sort_keys=True)],
        ["pm_server_action_lines", json.dumps(action_lines)],
        ["marker_counts", json.dumps(counts, sort_keys=True)],
    ]
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1165 Late pm-proxy Actionability Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- helper_late_per_proxy_flag: `{LATE_PER_PROXY_FLAG}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- global_modem_holder_opened: `{manifest['global_modem_holder_opened']}`",
        f"- post_pm_mdm_helper_executed: `{manifest['post_pm_mdm_helper_executed']}`",
        f"- late_per_proxy_started: `{manifest['late_per_proxy_started']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
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
        "## Late pm-proxy Surface",
        "",
        markdown_table(["key", "value"], late_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1143.v1139.v1113.v1106.parse_args()
    v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1165"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1165(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1143.v1139.global_firmware(manifest)
    values = v1143.v1139.contract(manifest)
    post = v1143.v1139.post_pm(manifest)
    lower = v1143.lower_trace(manifest)
    late = late_per_proxy(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
    manifest["post_pm_mdm_helper_lower_trace_emitted"] = lower.get("begin") == "1"
    manifest["late_per_proxy_started"] = late.get("started") == "1"
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = values.get("wifi_hal_start_executed") == "1" or post.get("wifi_hal_start_executed") == "1" or lower.get("wifi_hal_start_executed") == "1"
    manifest["scan_connect_executed"] = values.get("scan_connect_linkup") == "1" or post.get("scan_connect_linkup") == "1" or lower.get("scan_connect_linkup") == "1"
    manifest["credential_use_executed"] = lower.get("credentials") == "1"
    manifest["dhcp_route_executed"] = lower.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = values.get("external_ping") == "1" or post.get("external_ping") == "1" or lower.get("external_ping") == "1"
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
    print(f"post_pm_mdm_helper_lower_trace_emitted: {manifest['post_pm_mdm_helper_lower_trace_emitted']}")
    print(f"late_per_proxy_started: {manifest['late_per_proxy_started']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
