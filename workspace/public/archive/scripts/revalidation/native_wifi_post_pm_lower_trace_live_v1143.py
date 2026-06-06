#!/usr/bin/env python3
"""V1143 bounded post-PM mdm_helper lower-trace live gate.

This is a narrow V1139 derivative. It keeps the same global-firmware outer
holder and post-policy CNSS PM path, but requires helper v215 and enables the
V1141 lower-trace flag:

    --allow-post-pm-mdm-helper-lower-trace

The live gate may start PM/CNSS actors and mdm_helper in the bounded helper
window. It must not start Wi-Fi HAL, scan/connect/link-up, use credentials,
run DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_post_pm_mdm_helper_esoc_live_v1139 as v1139
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1143-post-pm-lower-trace-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1143-post-pm-lower-trace-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "7bf107db54e4e3b2f9bbee196d40564ab4c62b2de1bcaa392ba843a6a6f3419e"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v215"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1143"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1143/post-pm-lower-trace-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1143/post-pm-lower-trace-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1143/post-pm-lower-trace-output.txt"
PROOF_PREFIX = "/tmp/a90-v1143-"
LOWER_TRACE_FLAG = "--allow-post-pm-mdm-helper-lower-trace"

_base_child_command = v1139.pm_post_mdm_helper_child_command
_base_remote_marker_check = v1139.serial_remote_marker_check
_base_tracefs_collector_script = v1139.tracefs_collector_script_v1139
_base_parse_tracefs_output = v1139.parse_tracefs_output_v1139


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _append_unique(command: list[str], flag: str) -> None:
    if flag not in command:
        command.append(flag)


def _replace_or_append_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError:
        command.extend([option, value])
        return
    if index + 1 >= len(command):
        raise RuntimeError(f"helper command has {option} without value")
    command[index + 1] = value


def pm_post_lower_trace_child_command(args: Any) -> list[str]:
    command = _base_child_command(args)
    _append_unique(command, LOWER_TRACE_FLAG)
    return command


def serial_remote_marker_check_v1143(
    args: Any,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    info = _base_remote_marker_check(args, store, steps)
    step_file = info.get("file", "")
    text = ""
    if step_file:
        text = (store.run_dir / str(step_file)).read_text(encoding="utf-8", errors="replace")
    info["lower_trace_flag_ok"] = LOWER_TRACE_FLAG in text
    info["capture_mode_option_ok"] = "--capture-mode" in text
    return info


def tracefs_collector_script_v1143(args: Any) -> str:
    script = _base_tracefs_collector_script(args)
    needle = r"post_pm_mdm_helper_esoc_observer\.|"
    replacement = (
        r"post_pm_mdm_helper_esoc_observer\.|"
        r"post_pm_mdm_helper_lower_trace\.|"
        r"capture\.post_pm_mdm_helper_lower_trace|"
    )
    if needle not in script:
        raise RuntimeError("V1139 collector grep pattern changed")
    return script.replace(needle, replacement)


def _collect_prefix(keys: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def parse_tracefs_output_v1143(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output(text)
    keys = v1139.v1113.v1106.parse_keys(text)
    lower = _collect_prefix(keys, "post_pm_mdm_helper_lower_trace.")
    lower_capture = _collect_prefix(keys, "capture.post_pm_mdm_helper_lower_trace")
    lower_forbidden = {
        key: value
        for key, value in lower.items()
        if key in {
            "subsys_esoc0_open_attempted",
            "wifi_hal_start_executed",
            "scan_connect_linkup",
            "credentials",
            "dhcp_routing",
            "external_ping",
        } and value not in ("0", "False", "false", "")
    }
    parsed["post_pm_mdm_helper_lower_trace"] = lower
    parsed["post_pm_mdm_helper_lower_trace_capture"] = lower_capture
    parsed["post_pm_mdm_helper_lower_trace_forbidden_true"] = lower_forbidden
    return parsed


def patch_defaults() -> None:
    v1139.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1139.LATEST_POINTER = LATEST_POINTER
    v1139.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1139.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1139.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1139.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1139.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1139.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1139.PROOF_PREFIX = PROOF_PREFIX
    v1139.pm_post_mdm_helper_child_command = pm_post_lower_trace_child_command
    v1139.serial_remote_marker_check = serial_remote_marker_check_v1143
    v1139.tracefs_collector_script_v1139 = tracefs_collector_script_v1143
    v1139.parse_tracefs_output_v1139 = parse_tracefs_output_v1143
    v1139.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def lower_trace(manifest: dict[str, Any]) -> dict[str, str]:
    value = tracefs(manifest).get("post_pm_mdm_helper_lower_trace") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def decide_v1143(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1143-post-pm-lower-trace-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded lower-trace live with helper v215 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1139.decide_v1139(args, manifest)
    tfs = tracefs(manifest)
    lower = lower_trace(manifest)
    usage = (manifest.get("analysis") or {}).get("execns_usage") or {}
    forbidden = tfs.get("post_pm_mdm_helper_lower_trace_forbidden_true") or {}

    if not usage.get("lower_trace_flag_ok"):
        return (
            "v1143-helper-lower-trace-flag-missing",
            False,
            f"usage={usage}",
            "redeploy helper v215 or inspect helper usage output",
        )
    if forbidden:
        return (
            "v1143-forbidden-lower-trace-action-observed",
            False,
            f"forbidden={forbidden}",
            "stop and audit helper lower-trace contract",
        )
    if not base_pass:
        return (base_decision.replace("v1139", "v1143", 1), False, base_reason, base_next)
    if lower.get("begin") != "1":
        return (
            "v1143-lower-trace-not-emitted",
            True,
            f"base_decision={base_decision} lower={lower}",
            "classify why mdm_helper was not alive long enough for lower trace",
        )
    if lower.get("end") != "1":
        return (
            "v1143-lower-trace-incomplete",
            False,
            f"lower={lower}",
            "inspect helper output and cleanup state before retry",
        )

    samples = str((tracefs(manifest).get("post_pm_mdm_helper") or {}).get("lower_trace_samples", ""))
    fd_subsys = [value for key, value in lower.items() if key.endswith(".fd_subsys_esoc0_count")]
    fd_mhi = [value for key, value in lower.items() if key.endswith(".fd_mhi_pipe_count")]
    ks = [value for key, value in lower.items() if key.endswith(".ks_count")]
    advanced = any(value not in ("", "-1", "0") for value in fd_subsys + fd_mhi + ks)
    if advanced:
        return (
            "v1143-post-pm-lower-trace-advanced",
            True,
            f"samples={samples} fd_subsys={fd_subsys} fd_mhi={fd_mhi} ks={ks}",
            "preserve lower evidence before any Wi-Fi HAL or scan/connect gate",
        )
    return (
        "v1143-post-pm-lower-trace-no-advance",
        True,
        f"samples={samples} lower={lower}",
        "classify mdm_helper /dev/esoc-0 stall using wchan/syscall/fd evidence",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    fw = v1139.global_firmware(manifest)
    tfs = tracefs(manifest)
    values = v1139.contract(manifest)
    post = v1139.post_pm(manifest)
    lower = lower_trace(manifest)
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
    lower_rows = [
        ["tracefs_result", tfs.get("result", "")],
        ["mode", values.get("mode", "")],
        ["register_ret", json.dumps(v1139.cnss_return_values(manifest, "pm_client_register_ret"))],
        ["connect_ret", json.dumps(v1139.cnss_return_values(manifest, "pm_client_connect_ret"))],
        ["post_result", post.get("result", "")],
        ["mdm_helper_observable", post.get("mdm_helper_observable", "")],
        ["lower_trace_samples", post.get("lower_trace_samples", "")],
        ["lower_begin_end", f"{lower.get('begin', '')}/{lower.get('end', '')}"],
        ["sample_00_alive", lower.get("sample_00.alive", "")],
        ["sample_00_state", lower.get("sample_00.state", "")],
        ["sample_00_fd_esoc0", lower.get("sample_00.fd_esoc0_count", "")],
        ["sample_00_fd_subsys_esoc0", lower.get("sample_00.fd_subsys_esoc0_count", "")],
        ["sample_00_fd_mhi_pipe", lower.get("sample_00.fd_mhi_pipe_count", "")],
        ["sample_00_ks", lower.get("sample_00.ks_count", "")],
        ["sample_02_fd_subsys_esoc0", lower.get("sample_02.fd_subsys_esoc0_count", "")],
        ["sample_02_fd_mhi_pipe", lower.get("sample_02.fd_mhi_pipe_count", "")],
        ["sample_02_ks", lower.get("sample_02.ks_count", "")],
        ["marker_counts", json.dumps(counts, sort_keys=True)],
    ]
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1143 Post-PM mdm_helper Lower-Trace Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- helper_lower_trace_flag: `{LOWER_TRACE_FLAG}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- global_modem_holder_opened: `{manifest['global_modem_holder_opened']}`",
        f"- post_pm_mdm_helper_executed: `{manifest['post_pm_mdm_helper_executed']}`",
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
        "## Lower Trace Surface",
        "",
        markdown_table(["key", "value"], lower_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1139.v1113.v1106.parse_args()
    v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1143"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1143(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1139.global_firmware(manifest)
    values = v1139.contract(manifest)
    post = v1139.post_pm(manifest)
    lower = lower_trace(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
    manifest["post_pm_mdm_helper_lower_trace_emitted"] = lower.get("begin") == "1"
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
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
