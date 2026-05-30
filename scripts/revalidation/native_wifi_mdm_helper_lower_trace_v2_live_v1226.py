#!/usr/bin/env python3
"""V1226: mdm_helper lower-trace v2 live gate.

V1225 selected the post-WAIT/no-MHI gap.  The helper already supports
``ptrace-lite`` syscall return tracing for ``mdm_helper`` when
``--allow-post-pm-mdm-helper-lower-trace`` is active, but V1224 ran the same
PM/CNSS path with ``capture_mode=none``.  This runner keeps the V1224 live path
and only forces helper ``--capture-mode ptrace-lite`` so the evidence includes
``mdm_helper`` syscall/return records around ``/dev/esoc-0`` and
``ESOC_WAIT_FOR_REQ``.  If the coarse helper ``ptrace-lite`` mode perturbs the
V1224 path before ``mdm_helper`` becomes observable, the runner records that as
an instrumentation blocker rather than treating it as lower-Wi-Fi progress.

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
import native_wifi_post_esoc_power_boundary_v1222 as v1222
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod


DEFAULT_OUT_DIR = Path("tmp/wifi/v1226-mdm-helper-lower-trace-v2-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1226-mdm-helper-lower-trace-v2-live.txt")

HELPER_MARKER = v1221.HELPER_MARKER_V253
HELPER_SHA256 = v1221.HELPER_SHA256_V253

SYSCALL_RE = re.compile(r"^pm_service_trigger_observer\.syscall\.(?P<child>[^.]+)\.record_(?P<idx>\d+)\.(?P<key>[^=]+)=(?P<value>.*)$")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")

ESOC_IOCTL_NAMES = {
    0x0000CC07: "ESOC_REG_ENGINE_7",
    0x0000CC08: "ESOC_REG_ENGINE_8",
    0x8004CC02: "ESOC_WAIT_FOR_REQ",
    0x4004CC03: "ESOC_NOTIFY",
    0x8004CC04: "ESOC_GET_STATUS",
    0x8004CC05: "ESOC_GET_ERR_FATAL",
    0x8004CC06: "ESOC_WAIT_FOR_CRASH",
    0xC008CC09: "ESOC_GET_LINK_ID",
}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _force_ptrace_child_command(original):
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
            result.append(item)
        result.extend(["--capture-mode", "ptrace-lite"])
        return result

    return command


def patch_defaults() -> None:
    v1224.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1224.LATEST_POINTER = LATEST_POINTER
    v1224.patch_defaults()
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    wrapped = _force_ptrace_child_command(v1106_mod.pm_cnss_child_command)
    v1106.pm_cnss_child_command = wrapped
    v1106_mod.pm_cnss_child_command = wrapped


def _read_run_text(manifest: dict[str, Any]) -> str:
    chunks: list[str] = []
    run_dir = manifest.get("_run_dir", "")
    for step in manifest.get("steps", []):
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            try:
                chunks.append(Path(run_dir, step_file).read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace"))
            except OSError:
                pass
        text = step.get("text", "") or step.get("payload", "") or ""
        if text:
            chunks.append(str(text).replace("\0", "\n"))
    return "\n".join(chunks)


def _parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = KEY_RE.match(line)
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def _int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def _collect_syscalls(text: str, child_name: str) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, str]] = {}
    for raw_line in text.splitlines():
        match = SYSCALL_RE.match(raw_line.strip())
        if not match or match.group("child") != child_name:
            continue
        index = int(match.group("idx"))
        grouped.setdefault(index, {})[match.group("key")] = match.group("value")
    records: list[dict[str, Any]] = []
    for index in sorted(grouped):
        raw = grouped[index]
        record: dict[str, Any] = {"index": index, **raw}
        if raw.get("name") == "ioctl":
            request = _int_value(raw.get("arg1"), -1) & 0xFFFFFFFF
            record["ioctl_request_hex"] = f"0x{request:08x}"
            record["ioctl_name"] = ESOC_IOCTL_NAMES.get(request, "unknown")
            record["is_esoc_wait_for_req"] = request == 0x8004CC02
        records.append(record)
    return records


def _records_with_name(records: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [record for record in records if record.get("name") == name]


def _count_paths(records: list[dict[str, Any]], needle: str) -> int:
    count = 0
    for record in records:
        path_text = record.get("path.text", "") or record.get("ret_fd.target", "") or record.get("fd.target", "")
        if needle in str(path_text):
            count += 1
    return count


def _analyze_trace(manifest: dict[str, Any], run_text: str) -> dict[str, Any]:
    keys = _parse_keys(run_text)
    parity = v1224._extract_parity(manifest, run_text)
    boundary = v1222._analyze_boundary(manifest, run_text)
    mdm_records = _collect_syscalls(run_text, "mdm_helper")
    per_mgr_records = _collect_syscalls(run_text, "per_mgr")
    wait_records = [record for record in mdm_records if record.get("is_esoc_wait_for_req")]
    wait_success_records = [
        record for record in wait_records
        if _int_value(record.get("ret"), -1) == 4 and _int_value(record.get("error"), -1) == 0
    ]
    ioctl_records = _records_with_name(mdm_records, "ioctl")
    open_records = _records_with_name(mdm_records, "openat")
    exec_records = [
        record for record in mdm_records
        if record.get("name") in {"execve", "execveat"}
    ]
    error_records = [
        record for record in mdm_records
        if _int_value(record.get("error"), 0) != 0
    ]
    child_prefix = "pm_service_trigger_observer.child.mdm_helper."
    child = {
        key[len(child_prefix):]: value
        for key, value in keys.items()
        if key.startswith(child_prefix)
    }
    ptrace = {
        "capture_mode_seen": "capture_mode=ptrace-lite" in run_text,
        "trace_syscalls": _int_value(child.get("trace_syscalls"), 0),
        "syscall_trace_started": _int_value(child.get("syscall_trace_started"), 0),
        "syscall_trace_stop_limited": _int_value(child.get("syscall_trace_stop_limited"), 0),
        "syscall_stop_count": _int_value(child.get("syscall_stop_count"), 0),
        "syscall_record_count": _int_value(child.get("syscall_record_count"), 0),
        "syscall_error_count": _int_value(child.get("syscall_error_count"), 0),
        "syscall_trace_truncated": _int_value(child.get("syscall_trace_truncated"), 0),
    }
    trigger = {
        "subsys_esoc0_open_attempted": _int_value(keys.get("pm_service_trigger_observer.subsys_esoc0_open_attempted"), 0),
        "mdm_helper_start_executed": _int_value(keys.get("pm_service_trigger_observer.mdm_helper_start_executed"), 0),
        "cnss_daemon_start_executed": _int_value(keys.get("pm_service_trigger_observer.cnss_daemon_start_executed"), 0),
        "per_mgr_trace_syscalls": _int_value(keys.get("pm_service_trigger_observer.child.per_mgr.trace_syscalls"), 0),
        "per_mgr_syscall_trace_started": _int_value(keys.get("pm_service_trigger_observer.child.per_mgr.syscall_trace_started"), 0),
        "per_mgr_syscall_trace_truncated": _int_value(keys.get("pm_service_trigger_observer.child.per_mgr.syscall_trace_truncated"), 0),
        "per_mgr_syscall_record_count": _int_value(keys.get("pm_service_trigger_observer.child.per_mgr.syscall_record_count"), 0),
        "per_proxy_exit_code": _int_value(keys.get("pm_service_trigger_observer.child.per_proxy.exit_code"), -999),
        "per_proxy_signal": _int_value(keys.get("pm_service_trigger_observer.child.per_proxy.signal"), -999),
    }
    interesting_records = [
        record for record in mdm_records
        if record.get("name") in {"openat", "ioctl", "socket", "connect", "exit", "exit_group"}
    ][:24]
    return {
        "ptrace": ptrace,
        "trigger": trigger,
        "mdm_helper_record_count": len(mdm_records),
        "per_mgr_record_count": len(per_mgr_records),
        "mdm_helper_ioctl_count": len(ioctl_records),
        "mdm_helper_openat_count": len(open_records),
        "mdm_helper_exec_count": len(exec_records),
        "mdm_helper_error_count": len(error_records),
        "mdm_helper_esoc_open_records": _count_paths(open_records, "/dev/esoc-0"),
        "mdm_helper_mhi_open_records": _count_paths(open_records, "/dev/mhi_0305_01.01.00_pipe_10"),
        "wait_for_req_record_count": len(wait_records),
        "wait_for_req_success_count": len(wait_success_records),
        "wait_for_req_records": wait_records,
        "interesting_mdm_helper_records": interesting_records,
        "parity": parity,
        "boundary": boundary,
    }


def decide_v1226(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1226-lower-trace-v2-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1226 bounded ptrace-lite lower trace gate",
        )
    trace = manifest.get("mdm_helper_lower_trace_v2") or {}
    ptrace = trace.get("ptrace") or {}
    trigger = trace.get("trigger") or {}
    parity = trace.get("parity") or {}
    boundary = trace.get("boundary") or {}
    if not ptrace.get("capture_mode_seen"):
        return (
            "v1226-ptrace-mode-not-used",
            False,
            f"ptrace={ptrace}",
            "repair V1226 child command capture-mode override",
        )
    post_pm = parity.get("post_pm") or {}
    if (
        post_pm.get("result") == "mdm-helper-not-observable"
        and trigger.get("mdm_helper_start_executed") == 1
        and trigger.get("subsys_esoc0_open_attempted") == 0
    ):
        return (
            "v1226-ptrace-lite-perturbed-mdm-helper-window",
            True,
            (
                "coarse ptrace-lite capture changed the V1224 PM/CNSS path: "
                "mdm_helper was started but not observable in the post-PM window, "
                "and pm-service never attempted /dev/subsys_esoc0"
            ),
            "V1227 should add mdm_helper-only syscall tracing or compact helper-side ESOC_WAIT_FOR_REQ event capture without per_mgr ptrace perturbation",
        )
    if not ptrace.get("syscall_trace_started") or trace.get("mdm_helper_record_count", 0) <= 0:
        return (
            "v1226-mdm-helper-syscall-trace-missing",
            False,
            f"ptrace={ptrace}",
            "repair helper capture-mode/trace_syscalls gate before another live retry",
        )
    if trace.get("wait_for_req_success_count", 0) > 0 and parity.get("ks_or_mhi_present"):
        return (
            "v1226-wait-req-and-ks-mhi-progress",
            True,
            "ESOC_WAIT_FOR_REQ returned request bytes and ks/MHI appeared",
            "V1227 should observe WLFW/BDF/wlan0 readiness before Wi-Fi HAL",
        )
    if trace.get("wait_for_req_success_count", 0) > 0:
        return (
            "v1226-wait-req-returned-no-ks-mhi",
            True,
            (
                "mdm_helper syscall trace captured ESOC_WAIT_FOR_REQ returning 4 bytes, "
                "but ks/MHI/WLFW/wlan0 stayed absent"
            ),
            "V1227 should classify mdm_helper post-request sleep branch and missing ks/MHI launch trigger",
        )
    if ptrace.get("syscall_trace_truncated"):
        return (
            "v1226-mdm-helper-syscall-truncated-before-wait",
            True,
            f"mdm_helper syscall trace truncated before ESOC_WAIT_FOR_REQ; record_count={trace.get('mdm_helper_record_count')}",
            "V1227 should narrow syscall filtering or raise helper syscall record limits around ioctl/openat only",
        )
    if parity.get("mdm_helper_esoc_present") and not parity.get("ks_or_mhi_present") and boundary.get("max_dmesg_modem_down_count", 0) > 0:
        return (
            "v1226-mdm-helper-traced-no-wait-before-crash",
            True,
            (
                "mdm_helper syscall tracing ran and /dev/esoc-0 was held, but ESOC_WAIT_FOR_REQ was not captured "
                "before the same no-ks/MHI crash boundary"
            ),
            "V1227 should add ioctl-focused child tracing or helper-side compact WAIT_FOR_REQ event capture",
        )
    return (
        "v1226-lower-trace-v2-inconclusive",
        False,
        f"trace={trace}",
        "inspect full V1226 child output and add a narrower parser or helper marker",
    )


def _render_summary(manifest: dict[str, Any]) -> str:
    trace = manifest.get("mdm_helper_lower_trace_v2") or {}
    ptrace = trace.get("ptrace") or {}
    trigger = trace.get("trigger") or {}
    parity = trace.get("parity") or {}
    boundary = trace.get("boundary") or {}
    rows = [
        ["decision", manifest.get("decision", "")],
        ["pass", manifest.get("pass", "")],
        ["capture_mode_seen", ptrace.get("capture_mode_seen")],
        ["trace_syscalls", ptrace.get("trace_syscalls")],
        ["syscall_trace_started", ptrace.get("syscall_trace_started")],
        ["syscall_record_count", ptrace.get("syscall_record_count")],
        ["syscall_error_count", ptrace.get("syscall_error_count")],
        ["syscall_trace_truncated", ptrace.get("syscall_trace_truncated")],
        ["subsys_esoc0_open_attempted", trigger.get("subsys_esoc0_open_attempted")],
        ["mdm_helper_start_executed", trigger.get("mdm_helper_start_executed")],
        ["per_mgr_syscall_trace_started", trigger.get("per_mgr_syscall_trace_started")],
        ["per_mgr_syscall_trace_truncated", trigger.get("per_mgr_syscall_trace_truncated")],
        ["per_mgr_syscall_record_count", trigger.get("per_mgr_syscall_record_count")],
        ["per_proxy_exit_code", trigger.get("per_proxy_exit_code")],
        ["post_pm_result", (parity.get("post_pm") or {}).get("result")],
        ["post_pm_reason", (parity.get("post_pm") or {}).get("reason")],
        ["mdm_helper_record_count", trace.get("mdm_helper_record_count")],
        ["mdm_helper_ioctl_count", trace.get("mdm_helper_ioctl_count")],
        ["mdm_helper_openat_count", trace.get("mdm_helper_openat_count")],
        ["mdm_helper_esoc_open_records", trace.get("mdm_helper_esoc_open_records")],
        ["mdm_helper_mhi_open_records", trace.get("mdm_helper_mhi_open_records")],
        ["wait_for_req_record_count", trace.get("wait_for_req_record_count")],
        ["wait_for_req_success_count", trace.get("wait_for_req_success_count")],
        ["ks_or_mhi_present", parity.get("ks_or_mhi_present")],
        ["ks_count_window", parity.get("ks_count_window")],
        ["mhi_pipe_count_window", parity.get("mdm_helper_mhi_pipe_count_window")],
        ["mdm3_state_transitions", json.dumps(boundary.get("mdm3_state_transitions", []), ensure_ascii=False)],
        ["max_dmesg_modem_down_count", boundary.get("max_dmesg_modem_down_count")],
        ["max_dmesg_wlfw_count", boundary.get("max_dmesg_wlfw_count")],
        ["wlan0_seen", boundary.get("wlan0_seen")],
    ]
    record_rows = []
    for record in trace.get("interesting_mdm_helper_records", [])[:16]:
        record_rows.append([
            record.get("index"),
            record.get("name"),
            record.get("ioctl_name", ""),
            record.get("ret"),
            record.get("error_name", record.get("error", "")),
            record.get("path.text", record.get("ret_fd.target", record.get("fd.target", ""))),
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
        "# V1226 mdm_helper Lower Trace v2 Live Gate",
        "",
        f"- generated: `{manifest.get('generated_at', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        "## Trace Results",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Interesting mdm_helper Records",
        "",
        markdown_table(["idx", "name", "ioctl", "ret", "error", "path/fd"], record_rows),
        "",
        "## Safety Audit",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

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
    manifest["cycle"] = "v1226"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1224"
    manifest["capture_mode_forced"] = "ptrace-lite"
    manifest["_run_dir"] = str(store.run_dir)

    run_text = _read_run_text(manifest)
    manifest["private_cnss_daemon"] = v1221._parse_prefixed_lines(run_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_lower_trace_v2"] = _analyze_trace(manifest, run_text)

    decision, passed, reason, next_step = decide_v1226(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    trace = manifest["mdm_helper_lower_trace_v2"]
    ptrace = trace["ptrace"]
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"capture_mode_seen:          {ptrace.get('capture_mode_seen')}")
    print(f"syscall_trace_started:      {ptrace.get('syscall_trace_started')}")
    print(f"syscall_record_count:       {ptrace.get('syscall_record_count')}")
    print(f"mdm_helper_record_count:    {trace.get('mdm_helper_record_count')}")
    print(f"wait_for_req_record_count:  {trace.get('wait_for_req_record_count')}")
    print(f"wait_for_req_success_count: {trace.get('wait_for_req_success_count')}")
    print(f"ks_or_mhi_present:          {trace.get('parity', {}).get('ks_or_mhi_present')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
