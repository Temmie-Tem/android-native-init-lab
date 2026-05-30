#!/usr/bin/env python3
"""V1227: focused mdm_helper-only lower syscall trace live gate.

V1226 proved that the existing broad PM-observer ``ptrace-lite`` mode perturbs
the V1224 path before ``mdm_helper`` becomes observable.  V1227 requires helper
v254 and forces ``--pm-observer-mdm-helper-only-syscall-trace`` so only
``mdm_helper`` is ptraced while the V1224 PM/CNSS ordering remains intact.

Safety remains unchanged: no Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, boot image write, flash, or partition write.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_mdm_helper_lower_trace_v2_live_v1226 as v1226


DEFAULT_OUT_DIR = Path("tmp/wifi/v1227-mdm-helper-focused-trace-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1227-mdm-helper-focused-trace-live.txt")
HELPER_MARKER = "a90_android_execns_probe v254"
HELPER_SHA256 = "6dd38887f6431db6748ff60d90600deb1650a37c735f05f21824d3e1b58bda8c"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _force_focused_ptrace_child_command(original):
    def command(args: Any) -> list[str]:
        base = original(args)
        result: list[str] = []
        skip_next = False
        for item in base:
            if skip_next:
                skip_next = False
                continue
            if item == "--capture-mode":
                skip_next = True
                continue
            if item == "--pm-observer-mdm-helper-only-syscall-trace":
                continue
            result.append(item)
        result.extend([
            "--capture-mode",
            "ptrace-lite",
            "--pm-observer-mdm-helper-only-syscall-trace",
        ])
        return result

    return command


def patch_defaults() -> Any:
    v1226.v1224.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1226.v1224.LATEST_POINTER = LATEST_POINTER
    v1226.v1224.patch_defaults()
    v1179 = v1226.v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    wrapped = _force_focused_ptrace_child_command(v1226.v1106_mod.pm_cnss_child_command)
    v1106.pm_cnss_child_command = wrapped
    v1226.v1106_mod.pm_cnss_child_command = wrapped
    for module in [v1106, v1226.v1106_mod]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER
    return v1165, v1106


def decide_v1227(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1227-mdm-helper-focused-trace-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "deploy helper v254, then run V1227 focused mdm_helper-only trace",
        )
    trace = manifest.get("mdm_helper_focused_trace") or {}
    ptrace = trace.get("ptrace") or {}
    trigger = trace.get("trigger") or {}
    parity = trace.get("parity") or {}
    post_pm = parity.get("post_pm") or {}
    flag_seen = manifest.get("mdm_helper_only_syscall_trace_seen")
    if not flag_seen:
        return (
            "v1227-focused-flag-not-used",
            False,
            "helper output did not show pm_observer_mdm_helper_only_syscall_trace=1",
            "repair V1227 command override or deploy helper v254",
        )
    if not ptrace.get("capture_mode_seen"):
        return (
            "v1227-ptrace-mode-not-used",
            False,
            f"ptrace={ptrace}",
            "repair V1227 capture-mode override",
        )
    if trace.get("wait_for_req_success_count", 0) > 0 and parity.get("ks_or_mhi_present"):
        return (
            "v1227-wait-req-and-ks-mhi-progress",
            True,
            "focused mdm_helper trace captured ESOC_WAIT_FOR_REQ and ks/MHI appeared",
            "observe WLFW/BDF/wlan0 readiness before Wi-Fi HAL",
        )
    if trace.get("wait_for_req_success_count", 0) > 0:
        return (
            "v1227-wait-req-returned-no-ks-mhi",
            True,
            "focused mdm_helper trace captured ESOC_WAIT_FOR_REQ returning 4 bytes, but ks/MHI stayed absent",
            "classify mdm_helper post-request sleep branch and missing ks/MHI launch trigger",
        )
    if ptrace.get("syscall_trace_started") and trace.get("mdm_helper_record_count", 0) > 0:
        return (
            "v1227-mdm-helper-traced-no-wait-record",
            True,
            "focused tracing captured mdm_helper syscalls but not ESOC_WAIT_FOR_REQ before the same no-ks/MHI boundary",
            "narrow ioctl capture or add helper-side compact WAIT_FOR_REQ marker",
        )
    if (
        ptrace.get("syscall_trace_started")
        and ptrace.get("syscall_stop_count", 0) > 0
        and trace.get("mdm_helper_record_count", 0) == 0
        and post_pm.get("mdm_helper_observable") == "1"
        and post_pm.get("fd_esoc0_count.window") == "0"
        and manifest.get("mdm_helper_ptrace_stop_seen")
    ):
        return (
            "v1227-focused-ptrace-stops-mdm-helper-before-esoc",
            True,
            "mdm_helper-only ptrace starts, but the observer sees mdm_helper stopped in ptrace_stop before /dev/esoc-0 opens",
            "replace pre-gate ptrace with delayed attach or compact helper-side ESOC_WAIT_FOR_REQ event capture",
        )
    if (
        post_pm.get("result") == "mdm-helper-not-observable"
        and trigger.get("mdm_helper_start_executed") == 1
        and trigger.get("subsys_esoc0_open_attempted") == 0
    ):
        return (
            "v1227-focused-trace-still-perturbed-mdm-helper-window",
            True,
            "even mdm_helper-only ptrace changed the V1224 window before /dev/subsys_esoc0",
            "replace ptrace with compact helper-side event capture",
        )
    return (
        "v1227-focused-trace-inconclusive",
        False,
        f"ptrace={ptrace} trigger={trigger}",
        "inspect V1227 output and add a narrower marker",
    )


def _render_summary(manifest: dict[str, Any]) -> str:
    return (
        v1226._render_summary(manifest)
        .replace("V1226", "V1227")
        .replace("v1226-", "v1227-")
        .replace("mdm_helper_lower_trace_v2", "mdm_helper_focused_trace")
    )


def main() -> int:
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
    manifest["cycle"] = "v1227"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1224"
    manifest["capture_mode_forced"] = "ptrace-lite"
    manifest["mdm_helper_only_syscall_trace_forced"] = True
    manifest["_run_dir"] = str(store.run_dir)

    run_text = v1226._read_run_text(manifest)
    manifest["private_cnss_daemon"] = v1226.v1221._parse_prefixed_lines(run_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1226.v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1226.v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_focused_trace"] = v1226._analyze_trace(manifest, run_text)
    manifest["mdm_helper_lower_trace_v2"] = manifest["mdm_helper_focused_trace"]
    manifest["mdm_helper_only_syscall_trace_seen"] = (
        "pm_observer_mdm_helper_only_syscall_trace=1" in run_text
    )
    manifest["mdm_helper_ptrace_stop_seen"] = "wchan=ptrace_stop" in run_text

    decision, passed, reason, next_step = decide_v1227(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    trace = manifest["mdm_helper_focused_trace"]
    ptrace = trace["ptrace"]
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"focused_flag_seen:         {manifest.get('mdm_helper_only_syscall_trace_seen')}")
    print(f"capture_mode_seen:         {ptrace.get('capture_mode_seen')}")
    print(f"syscall_trace_started:     {ptrace.get('syscall_trace_started')}")
    print(f"syscall_record_count:      {ptrace.get('syscall_record_count')}")
    print(f"mdm_helper_record_count:   {trace.get('mdm_helper_record_count')}")
    print(f"wait_for_req_record_count: {trace.get('wait_for_req_record_count')}")
    print(f"ks_or_mhi_present:         {trace.get('parity', {}).get('ks_or_mhi_present')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
