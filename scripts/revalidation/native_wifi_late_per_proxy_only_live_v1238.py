#!/usr/bin/env python3
"""V1238: bounded late per_proxy-only live gate.

This is the V1237 follow-up that removes the direct
--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc path.  It keeps the
Android-positive actor ordering from V1236:

    service managers -> pm_proxy_helper -> per_mgr -> cnss-daemon -> mdm_helper
    -> late per_proxy after mdm_helper holds /dev/esoc-0

The live gate may start the bounded PM/CNSS/mdm_helper observer stack and the
late pm-proxy actor.  It must not start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP/routes, external ping, send ESOC_NOTIFY, send
ESOC_BOOT_DONE, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_late_per_proxy_branch_snapshot_live_v1237 as v1237


DEFAULT_OUT_DIR = Path("tmp/wifi/v1238-late-per-proxy-only-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1238-late-per-proxy-only-live.txt")
HELPER_MARKER = v1237.HELPER_MARKER
HELPER_SHA256 = v1237.HELPER_SHA256
CNSS_BEFORE_PER_PROXY_FLAG = v1237.CNSS_BEFORE_PER_PROXY_FLAG
LATE_PER_PROXY_FLAG = v1237.LATE_PER_PROXY_FLAG
REMOVED_DIRECT_TRIGGER_FLAG = v1237.SUBSYS_TRIGGER_FLAG
REMOVED_POST_WAIT_FLAG = v1237.POST_WAIT_FLAG
REMOVED_BRANCH_SNAPSHOT_FLAG = v1237.BRANCH_SNAPSHOT_FLAG


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _force_late_per_proxy_only_child_command(original):
    def command(args: Any) -> list[str]:
        base = original(args)
        result: list[str] = []
        skip_next = False
        removed_flags = {
            "--pm-observer-mdm-helper-only-syscall-trace",
            REMOVED_POST_WAIT_FLAG,
            REMOVED_BRANCH_SNAPSHOT_FLAG,
            REMOVED_DIRECT_TRIGGER_FLAG,
        }
        for item in base:
            if skip_next:
                skip_next = False
                continue
            if item == "--capture-mode":
                skip_next = True
                continue
            if item in removed_flags:
                continue
            result.append(item)
        if CNSS_BEFORE_PER_PROXY_FLAG not in result:
            result.append(CNSS_BEFORE_PER_PROXY_FLAG)
        if LATE_PER_PROXY_FLAG not in result:
            result.append(LATE_PER_PROXY_FLAG)
        return result

    return command


def patch_defaults() -> tuple[Any, Any]:
    v1237.v1224.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1237.v1224.LATEST_POINTER = LATEST_POINTER
    v1237.v1224.patch_defaults()
    v1179 = v1237.v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    wrapped = _force_late_per_proxy_only_child_command(v1237.v1106_mod.pm_cnss_child_command)
    v1106.pm_cnss_child_command = wrapped
    v1237.v1106_mod.pm_cnss_child_command = wrapped
    for module in [v1106, v1237.v1106_mod]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER
    return v1165, v1106


def _int_value(value: Any, fallback: int = 0) -> int:
    return v1237._int_value(value, fallback)


def _collect_prefix(text: str, prefix: str) -> dict[str, str]:
    return v1237._collect_prefix(text, prefix)


def _read_run_text(manifest: dict[str, Any]) -> str:
    run_text = v1237.v1224._read_run_text(manifest)
    if manifest.get("command") != "plan" and "pm_service_trigger_observer.begin=1" not in run_text:
        observer_path = repo_path(DEFAULT_OUT_DIR / "host/pm-server-wchan-tracefs-observer.txt")
        try:
            run_text = observer_path.read_text(encoding="utf-8", errors="replace")
            manifest["reclassify_text_fallback"] = str(observer_path)
        except OSError:
            pass
    return run_text


def _analyze_post_pm(text: str) -> dict[str, Any]:
    post_pm = _collect_prefix(text, "post_pm_mdm_helper_esoc_observer.")
    emitted = post_pm.get("begin") == "1" or post_pm.get("end") == "1" or "post_pm_mdm_helper_esoc_observer." in text
    return {
        "emitted": emitted,
        "allowed": _int_value(post_pm.get("allowed"), -1),
        "exec_attempted": _int_value(post_pm.get("exec_attempted"), -1),
        "start_after_cnss": _int_value(post_pm.get("start_after_cnss"), -1),
        "lower_trace_allowed": _int_value(post_pm.get("lower_trace_allowed"), -1),
        "mdm_helper_observable": _int_value(post_pm.get("mdm_helper_observable"), -1),
        "window_snapshot_captured": _int_value(post_pm.get("window_snapshot_captured"), -1),
        "fd_esoc0_count_window": _int_value(post_pm.get("fd_esoc0_count.window"), -1),
        "fd_subsys_esoc0_count_window": _int_value(post_pm.get("fd_subsys_esoc0_count.window"), -1),
        "fd_mhi_pipe_count_window": _int_value(post_pm.get("fd_mhi_pipe_count.window"), -1),
        "ks_count_window": _int_value(post_pm.get("ks_count.window"), -1),
        "mhi_pipe_cmdline_count_window": _int_value(post_pm.get("mhi_pipe_cmdline_count.window"), -1),
        "late_per_proxy_requested": _int_value(post_pm.get("late_per_proxy_requested"), -1),
        "late_per_proxy_gate_positive": _int_value(post_pm.get("late_per_proxy_gate_positive"), -1),
        "late_per_proxy_started": _int_value(post_pm.get("late_per_proxy_started"), -1),
        "late_per_proxy_poll_count": _int_value(post_pm.get("late_per_proxy_poll_count"), -1),
        "late_per_proxy_snapshot_captured": _int_value(post_pm.get("late_per_proxy_snapshot_captured"), -1),
        "lower_artifact_observed": _int_value(post_pm.get("lower_artifact_observed"), -1),
        "lower_trace_samples": _int_value(post_pm.get("lower_trace_samples"), -1),
        "result": post_pm.get("result", ""),
        "reason": post_pm.get("reason", ""),
        "ended": post_pm.get("end") == "1",
    }


def _analyze_pm(text: str) -> dict[str, Any]:
    pm = _collect_prefix(text, "pm_service_trigger_observer.")
    direct_child_trigger = (
        "pm_observer_mdm_power_on.begin=1" in text or
        "pm_observer_mdm_power_on.path=" in text or
        re.search(r"^pm_service_trigger_observer\\.subsys_esoc0_open_attempted=1$", text, re.MULTILINE) is not None
    )
    actor_esoc0_attempt = (
        "pm_service_trigger_observer.syscall_probe.late_per_proxy_poll_" in text and
        "path.value=/dev/subsys_esoc0" in text and
        "wchan=mdm_subsys_powerup" in text
    )
    return {
        "emitted": pm.get("begin") == "1",
        "order": pm.get("order", ""),
        "per_proxy_initial_start_executed": _int_value(pm.get("per_proxy_initial_start_executed"), -1),
        "late_per_proxy_requested": _int_value(pm.get("late_per_proxy_requested"), -1),
        "late_per_proxy_after_mdm_helper_esoc_fd_requested": _int_value(pm.get("late_per_proxy_after_mdm_helper_esoc_fd_requested"), -1),
        "late_per_proxy_gate_positive": _int_value(pm.get("late_per_proxy_gate_positive"), -1),
        "late_per_proxy_started": _int_value(pm.get("late_per_proxy_started"), -1),
        "late_per_proxy_poll_count": _int_value(pm.get("late_per_proxy_poll_count"), -1),
        "late_per_proxy_snapshot_captured": _int_value(pm.get("late_per_proxy_snapshot_captured"), -1),
        "per_mgr_subsys_modem_seen": _int_value(pm.get("per_mgr_subsys_modem_seen"), -1),
        "pm_proxy_helper_subsys_modem_seen": _int_value(pm.get("pm_proxy_helper_subsys_modem_seen"), -1),
        "timed_out": _int_value(pm.get("timed_out"), -1),
        "all_postflight_safe": _int_value(pm.get("all_postflight_safe"), -1),
        "vndservice_provider_seen": _int_value(pm.get("vndservice_provider_seen"), -1),
        "result": pm.get("result", ""),
        "reason": pm.get("reason", ""),
        "ended": pm.get("end") == "1",
        "direct_subsys_trigger_present": direct_child_trigger,
        "pm_service_actor_esoc0_attempt": actor_esoc0_attempt,
        "post_wait_observer_present": "post_wait_req.begin=1" in text,
    }


def _has_lower_progress(manifest: dict[str, Any]) -> bool:
    pm = manifest.get("pm_service_trigger_observer") or {}
    post_pm = manifest.get("post_pm_mdm_helper_observer") or {}
    late = manifest.get("late_per_proxy") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    fields = [
        post_pm.get("fd_subsys_esoc0_count_window"),
        post_pm.get("fd_mhi_pipe_count_window"),
        post_pm.get("ks_count_window"),
        post_pm.get("mhi_pipe_cmdline_count_window"),
        late.get("per_mgr_subsys_esoc0_max"),
        late.get("per_mgr_subsys_modem_max"),
        boundary.get("max_dmesg_wlfw_count"),
        boundary.get("max_ks_count"),
        boundary.get("max_mhi_dev_count"),
    ]
    if boundary.get("wlan0_seen") or pm.get("pm_service_actor_esoc0_attempt"):
        return True
    return any(_int_value(value, 0) > 0 for value in fields)


def decide_v1238(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1238-late-per-proxy-only-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1238 bounded late-per_proxy-only live gate",
        )
    pm = manifest.get("pm_service_trigger_observer") or {}
    post_pm = manifest.get("post_pm_mdm_helper_observer") or {}
    late = manifest.get("late_per_proxy") or {}
    if pm.get("direct_subsys_trigger_present") or pm.get("post_wait_observer_present"):
        return (
            "v1238-direct-trigger-not-removed",
            False,
            "direct subsystem trigger or post-wait observer still appeared in late-only gate output",
            "remove direct trigger/post-wait flags before retrying V1238",
        )
    if _int_value(late.get("requested"), -1) <= 0 and _int_value(pm.get("late_per_proxy_after_mdm_helper_esoc_fd_requested"), -1) <= 0:
        return (
            "v1238-late-per-proxy-flag-missing",
            False,
            "late per_proxy request flag was not observed",
            "verify helper command flag injection",
        )
    if not post_pm.get("emitted"):
        return (
            "v1238-post-pm-mdm-helper-window-missing",
            False,
            "post_pm_mdm_helper_esoc_observer did not emit",
            "inspect helper mode/allow flag injection before retry",
        )
    if not late.get("begin"):
        return (
            "v1238-late-per-proxy-block-not-reached",
            True,
            f"late per_proxy was requested but helper did not enter the late block; post_pm_result={post_pm.get('result')} reason={post_pm.get('reason')}",
            "classify why mdm_helper /dev/esoc-0 gate was not reached in late-only path",
        )
    if _int_value(late.get("gate_positive"), 0) <= 0:
        return (
            "v1238-late-per-proxy-gate-not-positive",
            True,
            "late per_proxy block ran, but mdm_helper /dev/esoc-0 fd gate was not positive",
            "repair mdm_helper esoc fd gate before retrying late per_proxy",
        )
    if _int_value(late.get("started"), 0) <= 0:
        return (
            "v1238-late-per-proxy-start-failed",
            False,
            f"late per_proxy gate was positive but start failed; late={late}",
            "inspect helper child spawn failure before retrying",
        )
    if pm.get("pm_service_actor_esoc0_attempt"):
        if _int_value(pm.get("all_postflight_safe"), 1) <= 0:
            return (
                "v1238-late-per-proxy-reached-pm-service-esoc0-reboot-required",
                True,
                "late per_proxy started and pm-service Binder reached /dev/subsys_esoc0/mdm_subsys_powerup, but no WLFW/wlan0 progress appeared and process cleanup was not proven safe",
                "classify mdm_subsys_powerup hardware response gap and reboot-required cleanup before Wi-Fi HAL/connect",
            )
        return (
            "v1238-late-per-proxy-reached-pm-service-esoc0-no-wlfw",
            True,
            "late per_proxy started and pm-service Binder reached /dev/subsys_esoc0/mdm_subsys_powerup, but no WLFW/wlan0 progress appeared",
            "classify mdm_subsys_powerup hardware response gap before Wi-Fi HAL/connect",
        )
    if _has_lower_progress(manifest):
        return (
            "v1238-late-per-proxy-lower-progress",
            True,
            "late per_proxy started and lower PM/eSoC artifacts appeared",
            "observe WLFW/BDF/wlan0 readiness before Wi-Fi HAL/connect",
        )
    return (
        "v1238-late-per-proxy-started-no-lower-progress",
        True,
        "late per_proxy started after mdm_helper held /dev/esoc-0, but no ks/MHI/GPIO142/WLFW/wlan0 progress appeared",
        "classify per_proxy to pm-service Binder request delivery and pm-service esoc0 call path",
    )


def _reanalyze_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest["_run_dir"] = manifest.get("_run_dir") or str(repo_path(DEFAULT_OUT_DIR))
    manifest["cycle"] = "v1238"
    manifest["reclassified_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1237"
    manifest["cnss_before_per_proxy_flag"] = CNSS_BEFORE_PER_PROXY_FLAG
    manifest["late_per_proxy_flag"] = LATE_PER_PROXY_FLAG
    manifest["removed_direct_trigger_flag"] = REMOVED_DIRECT_TRIGGER_FLAG
    manifest["removed_post_wait_flag"] = REMOVED_POST_WAIT_FLAG
    manifest["removed_branch_snapshot_flag"] = REMOVED_BRANCH_SNAPSHOT_FLAG
    manifest["capture_mode_forced"] = "none"

    run_text = _read_run_text(manifest)
    manifest["pm_service_trigger_observer"] = _analyze_pm(run_text)
    manifest["post_pm_mdm_helper_observer"] = _analyze_post_pm(run_text)
    manifest["late_per_proxy"] = v1237._analyze_late_per_proxy(run_text)
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1237.v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1237.v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_early_compact_trace"] = v1237.v1228._analyze_early_trace(run_text)
    manifest["mdm_helper_ks_mhi_parity"] = v1237.v1224._extract_parity(manifest, run_text)

    decision, passed, reason, next_step = decide_v1238(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def _summary_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    pm = manifest.get("pm_service_trigger_observer") or {}
    post_pm = manifest.get("post_pm_mdm_helper_observer") or {}
    late = manifest.get("late_per_proxy") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    return [
        ["decision", manifest.get("decision", "")],
        ["pass", manifest.get("pass", "")],
        ["direct_trigger_present", pm.get("direct_subsys_trigger_present")],
        ["post_wait_observer_present", pm.get("post_wait_observer_present")],
        ["pm_service_actor_esoc0_attempt", pm.get("pm_service_actor_esoc0_attempt")],
        ["pm_order", pm.get("order")],
        ["post_pm_emitted", post_pm.get("emitted")],
        ["post_pm_result", post_pm.get("result")],
        ["post_pm_reason", post_pm.get("reason")],
        ["mdm_helper_observable", post_pm.get("mdm_helper_observable")],
        ["post_pm_fd_esoc0_count", post_pm.get("fd_esoc0_count_window")],
        ["late_requested", late.get("requested")],
        ["late_begin", late.get("begin")],
        ["late_gate_positive", late.get("gate_positive")],
        ["late_started", late.get("started")],
        ["late_poll_count", late.get("poll_count")],
        ["late_snapshot_captured", late.get("snapshot_captured")],
        ["late_per_mgr_subsys_esoc0_max", late.get("per_mgr_subsys_esoc0_max")],
        ["late_per_mgr_subsys_modem_max", late.get("per_mgr_subsys_modem_max")],
        ["post_pm_fd_mhi_pipe_count", post_pm.get("fd_mhi_pipe_count_window")],
        ["post_pm_ks_count", post_pm.get("ks_count_window")],
        ["boundary_wlan0_seen", boundary.get("wlan0_seen")],
        ["boundary_max_dmesg_wlfw_count", boundary.get("max_dmesg_wlfw_count")],
        ["boundary_max_ks_count", boundary.get("max_ks_count")],
        ["boundary_max_mhi_dev_count", boundary.get("max_mhi_dev_count")],
    ]


def _render_summary(manifest: dict[str, Any]) -> str:
    safety_rows = [
        ["wifi_hal_start_executed", manifest.get("wifi_hal_start_executed")],
        ["scan_connect_executed", manifest.get("scan_connect_executed")],
        ["credential_use_executed", manifest.get("credential_use_executed")],
        ["dhcp_route_executed", manifest.get("dhcp_route_executed")],
        ["external_ping_executed", manifest.get("external_ping_executed")],
        ["wifi_bringup_executed", manifest.get("wifi_bringup_executed")],
        ["flash_executed", manifest.get("flash_executed")],
        ["partition_write_executed", manifest.get("partition_write_executed")],
    ]
    return "\n".join([
        "# V1238 Late per_proxy-only Live Gate",
        "",
        f"- generated: `{manifest.get('generated_at', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        "## Gate Results",
        "",
        markdown_table(["field", "value"], _summary_rows(manifest)),
        "",
        "## Safety Audit",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def reclassify_existing() -> int:
    manifest_path = repo_path(DEFAULT_OUT_DIR / "manifest.json")
    if not manifest_path.exists():
        print(f"error: missing existing V1238 manifest: {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        print(f"error: manifest is not an object: {manifest_path}", file=sys.stderr)
        return 2
    manifest["command"] = "run"
    manifest = _reanalyze_manifest(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (repo_path(DEFAULT_OUT_DIR) / "summary.md").write_text(_render_summary(manifest), encoding="utf-8")
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(DEFAULT_OUT_DIR)) + "\n")
    _print_result(manifest)
    return 0 if manifest.get("pass") else 1


def _print_result(manifest: dict[str, Any]) -> None:
    pm = manifest.get("pm_service_trigger_observer") or {}
    post_pm = manifest.get("post_pm_mdm_helper_observer") or {}
    late = manifest.get("late_per_proxy") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print()
    print(f"direct_trigger_present:   {pm.get('direct_subsys_trigger_present')}")
    print(f"post_wait_observer:       {pm.get('post_wait_observer_present')}")
    print(f"pm_service_esoc0_attempt: {pm.get('pm_service_actor_esoc0_attempt')}")
    print(f"post_pm_result:           {post_pm.get('result')}")
    print(f"mdm_helper_observable:    {post_pm.get('mdm_helper_observable')}")
    print(f"post_pm_fd_esoc0_count:   {post_pm.get('fd_esoc0_count_window')}")
    print(f"late_requested:           {late.get('requested')}")
    print(f"late_begin:               {late.get('begin')}")
    print(f"late_gate_positive:       {late.get('gate_positive')}")
    print(f"late_started:             {late.get('started')}")
    print(f"late_poll_count:          {late.get('poll_count')}")
    print(f"late_per_mgr_esoc0_max:   {late.get('per_mgr_subsys_esoc0_max')}")
    print(f"boundary_wlan0_seen:      {boundary.get('wlan0_seen')}")
    print(f"boundary_wlfw_count:      {boundary.get('max_dmesg_wlfw_count')}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "reclassify":
        return reclassify_existing()

    v1165, v1106 = patch_defaults()
    args = v1106.parse_args()
    if args.command == "run":
        args.allow_tracefs_mount = True
        args.allow_tracefs_write = True
        args.allow_vendor_mount = True
        args.allow_selinuxfs_mount = True
        args.allow_pm_service_trigger_observer = True
        args.allow_cnss_daemon_start = True
        args.assume_yes = True
    if args.helper_timeout_sec == 4:
        args.helper_timeout_sec = 30
    if args.toybox_timeout_sec == 18:
        args.toybox_timeout_sec = 90
    if args.tracefs_duration_sec == 18:
        args.tracefs_duration_sec = 95
    if args.thread_sample_count == 80:
        args.thread_sample_count = 260
    v1165.v1143.v1139.v1113.set_global_defaults(args)

    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["command"] = args.command
    manifest["cycle"] = "v1238"
    manifest["generated_at"] = _now_iso()
    manifest["_run_dir"] = str(store.run_dir)
    manifest = _reanalyze_manifest(manifest)

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    _print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
