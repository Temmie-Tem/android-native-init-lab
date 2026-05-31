#!/usr/bin/env python3
"""V1228: non-ptrace mdm_helper early compact trace live gate.

V1227 proved that pre-gate ptrace stops ``mdm_helper`` before it opens
``/dev/esoc-0``.  V1228 returns to the V1224 non-ptrace PM/CNSS path and uses
helper v255 read-only ``/proc`` compact samples during the early mdm_helper
``/dev/esoc-0`` polling window.

Safety remains unchanged: no Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, boot image write, flash, or partition write.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_mdm_helper_ks_mhi_parity_live_v1224 as v1224
import native_wifi_private_cnss_daemon_sdx50m_live_v1221 as v1221
import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod
import native_wifi_post_esoc_power_boundary_v1222 as v1222


DEFAULT_OUT_DIR = Path("tmp/wifi/v1228-mdm-helper-early-compact-trace-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1228-mdm-helper-early-compact-trace-live.txt")
HELPER_MARKER = "a90_android_execns_probe v255"
HELPER_SHA256 = "8701add8d4e106616d61abbf6cd9b87eb26def99c619b49e79251ed8026439d1"
EARLY_TRACE_PREFIX = "post_pm_mdm_helper_early_trace."


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _force_non_ptrace_child_command(original):
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
        return result

    return command


def patch_defaults() -> tuple[Any, Any]:
    v1224.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1224.LATEST_POINTER = LATEST_POINTER
    v1224.patch_defaults()
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    wrapped = _force_non_ptrace_child_command(v1106_mod.pm_cnss_child_command)
    v1106.pm_cnss_child_command = wrapped
    v1106_mod.pm_cnss_child_command = wrapped
    for module in [v1106, v1106_mod]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER
    return v1165, v1106


def _collect_early_trace(text: str) -> dict[str, str]:
    keys = v1224._parse_keys(text)
    return {
        key[len(EARLY_TRACE_PREFIX):]: value
        for key, value in keys.items()
        if key.startswith(EARLY_TRACE_PREFIX)
    }


def _int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def _early_sample_indexes(early: dict[str, str]) -> list[int]:
    indexes: set[int] = set()
    for key in early:
        match = re.match(r"sample_(\d+)\.", key)
        if match:
            indexes.add(int(match.group(1)))
    return sorted(indexes)


def _early_trace_samples(early: dict[str, str]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in _early_sample_indexes(early):
        prefix = f"sample_{index:03d}."
        thread_indexes: set[int] = set()
        for key in early:
            match = re.match(rf"{re.escape(prefix)}thread_(\d+)\.", key)
            if match:
                thread_indexes.add(int(match.group(1)))
        threads = []
        for thread_index in sorted(thread_indexes):
            thread_prefix = f"{prefix}thread_{thread_index:02d}."
            threads.append({
                "index": thread_index,
                "tid": early.get(thread_prefix + "tid", ""),
                "comm": early.get(thread_prefix + "comm", ""),
                "wchan": early.get(thread_prefix + "wchan", ""),
                "nr": _int_value(early.get(thread_prefix + "nr"), -1),
                "name": early.get(thread_prefix + "name", ""),
                "arg0": early.get(thread_prefix + "arg0", ""),
                "arg1": early.get(thread_prefix + "arg1", ""),
                "ioctl_name": early.get(thread_prefix + "ioctl_name", ""),
            })
        samples.append({
            "index": index,
            "monotonic_ms": _int_value(early.get(prefix + "monotonic_ms"), -1),
            "pid": _int_value(early.get(prefix + "pid"), -1),
            "alive": early.get(prefix + "alive", ""),
            "state": early.get(prefix + "state", ""),
            "fd_esoc0_count": _int_value(early.get(prefix + "fd_esoc0_count"), -1),
            "fd_subsys_esoc0_count": _int_value(early.get(prefix + "fd_subsys_esoc0_count"), -1),
            "fd_mhi_pipe_count": _int_value(early.get(prefix + "fd_mhi_pipe_count"), -1),
            "thread_count": _int_value(early.get(prefix + "thread_count"), -1),
            "shown": _int_value(early.get(prefix + "shown"), -1),
            "threads": threads,
        })
    return samples


def _analyze_early_trace(text: str) -> dict[str, Any]:
    early = _collect_early_trace(text)
    samples = _early_trace_samples(early)
    thread_rows = [
        thread
        for sample in samples
        for thread in sample.get("threads", [])
    ]
    wait_threads = [
        thread for thread in thread_rows
        if thread.get("name") == "ioctl" and thread.get("ioctl_name") == "ESOC_WAIT_FOR_REQ"
    ]
    esoc_open_samples = [
        sample for sample in samples
        if _int_value(sample.get("fd_esoc0_count"), -1) > 0
    ]
    mhi_samples = [
        sample for sample in samples
        if _int_value(sample.get("fd_mhi_pipe_count"), -1) > 0
    ]
    return {
        "emitted": early.get("begin") == "1",
        "mode": early.get("mode", ""),
        "sample_count_declared": _int_value(early.get("sample_count"), -1),
        "sample_count": len(samples),
        "truncated": early.get("truncated", ""),
        "esoc0_found": early.get("esoc0_found", ""),
        "forbidden": {
            key: early.get(key)
            for key in (
                "subsys_esoc0_open_attempted",
                "wifi_hal_start_executed",
                "scan_connect_linkup",
                "credentials",
                "dhcp_routing",
                "external_ping",
            )
            if early.get(key) not in (None, "0")
        },
        "max_fd_esoc0_count": max((_int_value(sample.get("fd_esoc0_count"), -1) for sample in samples), default=-1),
        "max_fd_subsys_esoc0_count": max((_int_value(sample.get("fd_subsys_esoc0_count"), -1) for sample in samples), default=-1),
        "max_fd_mhi_pipe_count": max((_int_value(sample.get("fd_mhi_pipe_count"), -1) for sample in samples), default=-1),
        "wait_for_req_thread_count": len(wait_threads),
        "wait_for_req_threads": wait_threads[:12],
        "esoc_open_sample_indexes": [sample["index"] for sample in esoc_open_samples[:16]],
        "mhi_sample_indexes": [sample["index"] for sample in mhi_samples[:16]],
        "first_samples": samples[:12],
    }


def decide_v1228(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1228-early-compact-trace-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "deploy helper v255, then run V1228 non-ptrace early compact trace",
        )
    early = manifest.get("mdm_helper_early_compact_trace") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    if not early.get("emitted"):
        return (
            "v1228-early-trace-not-emitted",
            False,
            "helper output did not include post_pm_mdm_helper_early_trace.begin=1",
            "verify helper v255 deployment and V1224 lower-trace flag path",
        )
    if early.get("forbidden"):
        return (
            "v1228-early-trace-forbidden-action",
            False,
            f"forbidden={early.get('forbidden')}",
            "stop and inspect helper safety gates before retry",
        )
    if early.get("wait_for_req_thread_count", 0) > 0 and parity.get("ks_or_mhi_present"):
        return (
            "v1228-early-wait-req-and-ks-mhi-progress",
            True,
            "early compact trace saw ESOC_WAIT_FOR_REQ and ks/MHI appeared",
            "observe WLFW/BDF/wlan0 readiness before Wi-Fi HAL",
        )
    if early.get("wait_for_req_thread_count", 0) > 0:
        return (
            "v1228-early-wait-for-req-observed-no-ks-mhi",
            True,
            "early compact trace saw mdm_helper blocked in ESOC_WAIT_FOR_REQ, but ks/MHI stayed absent",
            "classify ESOC request handling and missing ks/MHI image-link launch",
        )
    if early.get("max_fd_esoc0_count", -1) > 0 and parity.get("pm_service_subsys_esoc0_attempt"):
        if _int_value(boundary.get("max_dmesg_modem_down_count")) > 0:
            return (
                "v1228-early-esoc-observed-no-wait-before-crash",
                True,
                "non-ptrace path preserved /dev/esoc-0 and /dev/subsys_esoc0 evidence, but no ESOC_WAIT_FOR_REQ thread state was sampled before modem-down markers",
                "add delayed attach after /dev/esoc-0 or compact in-process ioctl timestamp capture",
            )
        return (
            "v1228-early-esoc-observed-no-wait-window",
            True,
            "non-ptrace path preserved /dev/esoc-0 and /dev/subsys_esoc0 evidence, but no ESOC_WAIT_FOR_REQ thread state was sampled",
            "increase early compact cadence or add delayed attach after /dev/esoc-0",
        )
    return (
        "v1228-early-compact-trace-inconclusive",
        False,
        f"early={early} parity={parity}",
        "inspect V1228 full output and repair parser or live path",
    )


def _render_summary(manifest: dict[str, Any]) -> str:
    early = manifest.get("mdm_helper_early_compact_trace") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    rows = [
        ["decision", manifest.get("decision", "")],
        ["pass", manifest.get("pass", "")],
        ["early_emitted", early.get("emitted")],
        ["early_mode", early.get("mode")],
        ["early_sample_count", early.get("sample_count")],
        ["early_truncated", early.get("truncated")],
        ["early_esoc0_found", early.get("esoc0_found")],
        ["early_max_fd_esoc0_count", early.get("max_fd_esoc0_count")],
        ["early_max_fd_subsys_esoc0_count", early.get("max_fd_subsys_esoc0_count")],
        ["early_max_fd_mhi_pipe_count", early.get("max_fd_mhi_pipe_count")],
        ["wait_for_req_thread_count", early.get("wait_for_req_thread_count")],
        ["pm_service_subsys_esoc0_attempt", parity.get("pm_service_subsys_esoc0_attempt")],
        ["mdm_helper_esoc_present", parity.get("mdm_helper_esoc_present")],
        ["ks_or_mhi_present", parity.get("ks_or_mhi_present")],
        ["max_dmesg_modem_down_count", boundary.get("max_dmesg_modem_down_count")],
        ["max_dmesg_wlfw_count", boundary.get("max_dmesg_wlfw_count")],
        ["wlan0_seen", boundary.get("wlan0_seen")],
    ]
    sample_rows = []
    for sample in early.get("first_samples", [])[:8]:
        threads = sample.get("threads", [])
        first_thread = threads[0] if threads else {}
        sample_rows.append([
            sample.get("index"),
            sample.get("alive"),
            sample.get("state"),
            sample.get("fd_esoc0_count"),
            sample.get("fd_subsys_esoc0_count"),
            sample.get("fd_mhi_pipe_count"),
            first_thread.get("name", ""),
            first_thread.get("ioctl_name", ""),
            first_thread.get("wchan", ""),
        ])
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
        "# V1228 mdm_helper Early Compact Trace Live Gate",
        "",
        f"- generated: `{manifest.get('generated_at', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        "## Gate Results",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Early Samples",
        "",
        markdown_table(
            ["idx", "alive", "state", "esoc0_fd", "subsys_esoc0_fd", "mhi_fd", "first_syscall", "first_ioctl", "first_wchan"],
            sample_rows,
        ),
        "",
        "## Safety Audit",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


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
    manifest["cycle"] = "v1228"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1224"
    manifest["capture_mode_forced"] = "none"
    manifest["_run_dir"] = str(store.run_dir)

    run_text = v1224._read_run_text(manifest)
    manifest["private_cnss_daemon"] = v1221._parse_prefixed_lines(run_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_ks_mhi_parity"] = v1224._extract_parity(manifest, run_text)
    manifest["mdm_helper_early_compact_trace"] = _analyze_early_trace(run_text)

    decision, passed, reason, next_step = decide_v1228(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    early = manifest["mdm_helper_early_compact_trace"]
    parity = manifest["mdm_helper_ks_mhi_parity"]
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"early_emitted:                  {early.get('emitted')}")
    print(f"early_sample_count:             {early.get('sample_count')}")
    print(f"early_max_fd_esoc0_count:       {early.get('max_fd_esoc0_count')}")
    print(f"wait_for_req_thread_count:      {early.get('wait_for_req_thread_count')}")
    print(f"pm_service_subsys_esoc0_attempt:{parity.get('pm_service_subsys_esoc0_attempt')}")
    print(f"ks_or_mhi_present:              {parity.get('ks_or_mhi_present')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
