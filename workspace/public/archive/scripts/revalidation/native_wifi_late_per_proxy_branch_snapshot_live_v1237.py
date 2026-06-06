#!/usr/bin/env python3
"""V1237: bounded late per_proxy plus mdm_helper branch snapshot live gate.

This is a V1235 derivative. It preserves the branch snapshot and adds the
late per_proxy trigger after mdm_helper holds /dev/esoc-0:

    --pm-observer-mdm-helper-post-wait-req-ks-observer
    --pm-observer-mdm-helper-post-wait-req-branch-snapshot
    --pm-observer-start-cnss-before-per-proxy
    --pm-observer-start-per-proxy-after-mdm-helper-esoc-fd

The live gate may start the bounded PM/CNSS/mdm_helper observer stack and may
open the existing subsystem-trigger child used by V1228.  It must not start
Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP/routes, external
ping, send ESOC_NOTIFY, send ESOC_BOOT_DONE, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_mdm_helper_early_compact_trace_live_v1228 as v1228
import native_wifi_mdm_helper_ks_mhi_parity_live_v1224 as v1224
import native_wifi_private_cnss_daemon_sdx50m_live_v1221 as v1221
import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod
import native_wifi_post_esoc_power_boundary_v1222 as v1222


DEFAULT_OUT_DIR = Path("tmp/wifi/v1237-late-per-proxy-branch-snapshot-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1237-late-per-proxy-branch-snapshot-live.txt")
HELPER_MARKER = "a90_android_execns_probe v257"
HELPER_SHA256 = "66c3bc5a9cc0daa9a9a04fe7b98ebe2d7aa974798ed131adf82e5b314b2753e5"
POST_WAIT_PREFIX = "post_wait_req."
POST_WAIT_FLAG = "--pm-observer-mdm-helper-post-wait-req-ks-observer"
BRANCH_SNAPSHOT_FLAG = "--pm-observer-mdm-helper-post-wait-req-branch-snapshot"
BRANCH_PREFIX = "post_wait_branch."
CNSS_BEFORE_PER_PROXY_FLAG = "--pm-observer-start-cnss-before-per-proxy"
LATE_PER_PROXY_FLAG = "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd"
SUBSYS_TRIGGER_FLAG = "--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _force_non_ptrace_post_wait_child_command(original):
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
        if POST_WAIT_FLAG not in result:
            result.append(POST_WAIT_FLAG)
        if BRANCH_SNAPSHOT_FLAG not in result:
            result.append(BRANCH_SNAPSHOT_FLAG)
        if CNSS_BEFORE_PER_PROXY_FLAG not in result:
            result.append(CNSS_BEFORE_PER_PROXY_FLAG)
        if LATE_PER_PROXY_FLAG not in result:
            result.append(LATE_PER_PROXY_FLAG)
        if SUBSYS_TRIGGER_FLAG not in result:
            result.append(SUBSYS_TRIGGER_FLAG)
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
    wrapped = _force_non_ptrace_post_wait_child_command(v1106_mod.pm_cnss_child_command)
    v1106.pm_cnss_child_command = wrapped
    v1106_mod.pm_cnss_child_command = wrapped
    for module in [v1106, v1106_mod]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER
    return v1165, v1106


def _int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def _collect_post_wait(text: str) -> dict[str, str]:
    keys = v1224._parse_keys(text)
    return {
        key[len(POST_WAIT_PREFIX):]: value
        for key, value in keys.items()
        if key.startswith(POST_WAIT_PREFIX)
    }


def _collect_branch(text: str) -> dict[str, str]:
    keys = v1224._parse_keys(text)
    return {
        key[len(BRANCH_PREFIX):]: value
        for key, value in keys.items()
        if key.startswith(BRANCH_PREFIX)
    }


def _sample_indexes(post_wait: dict[str, str]) -> list[int]:
    indexes: set[int] = set()
    for key in post_wait:
        match = re.match(r"sample_(\d+)\.", key)
        if match:
            indexes.add(int(match.group(1)))
    return sorted(indexes)


def _post_wait_samples(post_wait: dict[str, str]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in _sample_indexes(post_wait):
        prefix = f"sample_{index:03d}."
        samples.append({
            "index": index,
            "monotonic_ms": _int_value(post_wait.get(prefix + "monotonic_ms"), -1),
            "mdm_helper_pid": _int_value(post_wait.get(prefix + "mdm_helper_pid"), -1),
            "mdm_helper_alive": post_wait.get(prefix + "mdm_helper_alive", ""),
            "mdm_helper_state": post_wait.get(prefix + "mdm_helper_state", ""),
            "mdm_helper_thread_count": _int_value(post_wait.get(prefix + "mdm_helper_thread_count"), -1),
            "wait_for_req_thread_count": _int_value(post_wait.get(prefix + "wait_for_req_thread_count"), -1),
            "transition_detected": _int_value(post_wait.get(prefix + "transition_detected"), -1),
            "transition_sample": _int_value(post_wait.get(prefix + "transition_sample"), -1),
            "fd_esoc0_count": _int_value(post_wait.get(prefix + "fd_esoc0_count"), -1),
            "fd_subsys_esoc0_count": _int_value(post_wait.get(prefix + "fd_subsys_esoc0_count"), -1),
            "fd_mhi_pipe_count": _int_value(post_wait.get(prefix + "fd_mhi_pipe_count"), -1),
            "mhi_pipe_exists": _int_value(post_wait.get(prefix + "mhi_pipe_exists"), -1),
            "mhi_pipe_fd_count": _int_value(post_wait.get(prefix + "mhi_pipe_fd_count"), -1),
            "ks_process_count": _int_value(post_wait.get(prefix + "ks_process_count"), -1),
            "pm_proxy_helper_process_count": _int_value(post_wait.get(prefix + "pm_proxy_helper_process_count"), -1),
            "mhi_pipe_cmdline_count": _int_value(post_wait.get(prefix + "mhi_pipe_cmdline_count"), -1),
        })
    return samples


def _max_sample(samples: list[dict[str, Any]], field: str) -> int:
    return max((_int_value(sample.get(field), -1) for sample in samples), default=-1)


def _analyze_post_wait(text: str) -> dict[str, Any]:
    post_wait = _collect_post_wait(text)
    samples = _post_wait_samples(post_wait)
    forbidden = {
        key: post_wait.get(key)
        for key in (
            "esoc_notify_attempted",
            "boot_done_attempted",
            "wifi_hal_start_executed",
            "scan_connect_linkup",
            "credentials",
            "dhcp_routing",
            "external_ping",
        )
        if post_wait.get(key) not in (None, "0")
    }
    summary_max = {
        "transition_detected": _int_value(post_wait.get("transition_detected"), -1),
        "transition_sample": _int_value(post_wait.get("transition_sample"), -1),
        "ks_process_count": _int_value(post_wait.get("ks_process_count"), -1),
        "mhi_pipe_exists": _int_value(post_wait.get("mhi_pipe_exists"), -1),
        "mhi_pipe_fd_count": _int_value(post_wait.get("mhi_pipe_fd_count"), -1),
        "mhi_pipe_cmdline_count": _int_value(post_wait.get("mhi_pipe_cmdline_count"), -1),
        "mdm_helper_mhi_pipe_fd_count": _int_value(post_wait.get("mdm_helper_mhi_pipe_fd_count"), -1),
    }
    sample_max = {
        "transition_detected": _max_sample(samples, "transition_detected"),
        "ks_process_count": _max_sample(samples, "ks_process_count"),
        "mhi_pipe_exists": _max_sample(samples, "mhi_pipe_exists"),
        "mhi_pipe_fd_count": _max_sample(samples, "mhi_pipe_fd_count"),
        "mhi_pipe_cmdline_count": _max_sample(samples, "mhi_pipe_cmdline_count"),
        "mdm_helper_mhi_pipe_fd_count": _max_sample(samples, "fd_mhi_pipe_count"),
    }
    return {
        "emitted": post_wait.get("begin") == "1",
        "mode": post_wait.get("mode", ""),
        "sample_interval_ms": _int_value(post_wait.get("sample_interval_ms"), -1),
        "pre_transition_max_samples": _int_value(post_wait.get("pre_transition_max_samples"), -1),
        "post_transition_max_samples": _int_value(post_wait.get("post_transition_max_samples"), -1),
        "declared_sample_count": _int_value(post_wait.get("sample_count"), -1),
        "sample_count": len(samples),
        "initial_wait_for_req_thread_count": _int_value(post_wait.get("initial_wait_for_req_thread_count"), -1),
        "post_transition_sample_count": _int_value(post_wait.get("post_transition_sample_count"), -1),
        "summary": summary_max,
        "sample_max": sample_max,
        "forbidden": forbidden,
        "first_samples": samples[:12],
        "last_samples": samples[-12:],
    }


def _post_wait_has_ks_or_mhi(post_wait: dict[str, Any]) -> bool:
    summary = post_wait.get("summary") or {}
    sample_max = post_wait.get("sample_max") or {}
    fields = (
        "ks_process_count",
        "mhi_pipe_exists",
        "mhi_pipe_fd_count",
        "mhi_pipe_cmdline_count",
        "mdm_helper_mhi_pipe_fd_count",
    )
    return any(_int_value(summary.get(field), -1) > 0 or _int_value(sample_max.get(field), -1) > 0 for field in fields)


def _counter_top(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def _analyze_branch(text: str) -> dict[str, Any]:
    branch = _collect_branch(text)
    phase_names = sorted({
        key.split(".", 1)[0]
        for key, value in branch.items()
        if key.endswith(".begin") and value == "1" and "." in key
    })
    syscall_names = Counter(
        value
        for key, value in branch.items()
        if key.endswith(".name") and value and value != "unparsed"
    )
    wchans = Counter(
        value
        for key, value in branch.items()
        if key.endswith(".wchan") and value
    )
    forbidden = {
        key: branch.get(key)
        for key in (
            "esoc_notify_attempted",
            "boot_done_attempted",
            "wifi_hal_start_executed",
            "scan_connect_linkup",
            "credentials",
            "dhcp_routing",
            "external_ping",
        )
        if branch.get(key) not in (None, "0")
    }
    max_wait_threads = max(
        (_int_value(value, -1) for key, value in branch.items() if key.endswith(".wait_for_req_thread_count")),
        default=-1,
    )
    max_esoc0_fd = max(
        (_int_value(value, -1) for key, value in branch.items() if key.endswith(".fd_esoc0_count")),
        default=-1,
    )
    max_mhi_fd = max(
        (_int_value(value, -1) for key, value in branch.items() if key.endswith(".fd_mhi_pipe_count")),
        default=-1,
    )
    return {
        "emitted": branch.get("begin") == "1",
        "mode": branch.get("mode", ""),
        "declared_sample_count": _int_value(branch.get("sample_count"), -1),
        "declared_burst_count": _int_value(branch.get("burst_count"), -1),
        "phase_count": len(phase_names),
        "phase_preview": phase_names[:16],
        "syscall_names": _counter_top(syscall_names),
        "wchan": _counter_top(wchans),
        "execve_count": syscall_names.get("execve", 0) + syscall_names.get("execveat", 0),
        "ioctl_count": syscall_names.get("ioctl", 0),
        "read_count": syscall_names.get("read", 0),
        "write_count": syscall_names.get("write", 0),
        "futex_count": syscall_names.get("futex", 0),
        "nanosleep_count": syscall_names.get("nanosleep", 0) + syscall_names.get("clock_nanosleep", 0),
        "path_value_count": sum(1 for key in branch if key.endswith(".path.value")),
        "path_error_count": sum(1 for key in branch if key.endswith(".path.error") or key.endswith(".path.reason")),
        "max_wait_for_req_thread_count": max_wait_threads,
        "max_fd_esoc0_count": max_esoc0_fd,
        "max_fd_mhi_pipe_count": max_mhi_fd,
        "forbidden": forbidden,
    }


def _collect_prefix(text: str, prefix: str) -> dict[str, str]:
    keys = v1224._parse_keys(text)
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def _analyze_late_per_proxy(text: str) -> dict[str, Any]:
    pm = _collect_prefix(text, "pm_service_trigger_observer.")
    late = _collect_prefix(text, "pm_service_trigger_observer.late_per_proxy.")
    post_late = _collect_prefix(text, "post_pm_mdm_helper_esoc_observer.late_per_proxy.")
    post_pm = _collect_prefix(text, "post_pm_mdm_helper_esoc_observer.")
    poll_keys = {
        key: value
        for key, value in pm.items()
        if key.startswith("late_per_proxy_poll_")
    }
    poll_indexes = sorted({
        int(match.group(1))
        for key in poll_keys
        for match in [re.match(r"late_per_proxy_poll_(\d+)\.", key)]
        if match
    })
    per_proxy_alive_max = max(
        (_int_value(poll_keys.get(f"late_per_proxy_poll_{idx:02d}.per_proxy_alive"), -1) for idx in poll_indexes),
        default=-1,
    )
    per_mgr_subsys_esoc0_max = max(
        (_int_value(value, -1) for key, value in pm.items() if key.endswith("per_mgr_subsys_esoc0_count")),
        default=-1,
    )
    per_mgr_subsys_modem_max = max(
        (_int_value(value, -1) for key, value in pm.items() if key.endswith("per_mgr_subsys_modem_count")),
        default=-1,
    )
    return {
        "requested": max(
            _int_value(pm.get("late_per_proxy_requested"), -1),
            _int_value(pm.get("late_per_proxy_after_mdm_helper_esoc_fd_requested"), -1),
            _int_value(post_pm.get("late_per_proxy_after_mdm_helper_esoc_fd_requested"), -1),
        ),
        "begin": late.get("begin") == "1",
        "gate_positive": _int_value(late.get("gate_positive") or post_late.get("gate_positive"), -1),
        "gate_fd_esoc0_count": _int_value(post_late.get("gate_fd_esoc0_count") or late.get("gate_mdm_helper_esoc0_fd_count"), -1),
        "start_attempted": _int_value(late.get("start_attempted") or post_late.get("start_attempted"), -1),
        "started": _int_value(late.get("started") or post_late.get("started"), -1),
        "pid": _int_value(late.get("pid") or post_late.get("pid"), -1),
        "poll_count": _int_value(pm.get("late_per_proxy_poll_count"), -1),
        "snapshot_captured": _int_value(late.get("snapshot_captured") or post_late.get("snapshot_captured") or pm.get("late_per_proxy_snapshot_captured"), -1),
        "poll_indexes": poll_indexes,
        "poll_sample_count": len(poll_indexes),
        "per_proxy_alive_max": per_proxy_alive_max,
        "per_mgr_subsys_esoc0_max": per_mgr_subsys_esoc0_max,
        "per_mgr_subsys_modem_max": per_mgr_subsys_modem_max,
        "per_mgr_subsys_modem_seen": _int_value(pm.get("per_mgr_subsys_modem_seen"), -1),
        "pm_proxy_helper_subsys_modem_seen": _int_value(pm.get("pm_proxy_helper_subsys_modem_seen"), -1),
        "post_wait_completed_before_late": "post_wait_req.end=1" in text and "post_wait_branch.end=1" in text and late.get("begin") != "1",
    }


def decide_v1237(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1237-post-wait-req-observer-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1237 bounded post-WAIT_FOR_REQ observer",
        )
    post_wait = manifest.get("mdm_helper_post_wait_req") or {}
    branch = manifest.get("mdm_helper_post_wait_branch") or {}
    late = manifest.get("late_per_proxy") or {}
    early = manifest.get("mdm_helper_early_compact_trace") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    if not post_wait.get("emitted"):
        return (
            "v1237-post-wait-req-not-emitted",
            False,
            "helper output did not include post_wait_req.begin=1",
            "verify helper v257 deployment and command flag injection",
        )
    if post_wait.get("forbidden"):
        return (
            "v1237-post-wait-req-forbidden-action",
            False,
            f"forbidden={post_wait.get('forbidden')}",
            "stop and inspect helper safety gates before retry",
        )
    if not branch.get("emitted"):
        return (
            "v1237-post-wait-branch-not-emitted",
            False,
            "helper output did not include post_wait_branch.begin=1",
            "verify helper v257 deployment and branch snapshot flag injection",
        )
    if branch.get("forbidden"):
        return (
            "v1237-post-wait-branch-forbidden-action",
            False,
            f"forbidden={branch.get('forbidden')}",
            "stop and inspect helper branch safety gates before retry",
        )
    if _int_value(late.get("requested"), -1) <= 0:
        return (
            "v1237-late-per-proxy-not-emitted",
            False,
            f"late_per_proxy={late}",
            "verify late per_proxy flag injection and helper command validation",
        )
    if not late.get("begin"):
        if late.get("post_wait_completed_before_late"):
            return (
                "v1237-direct-subsys-trigger-preempted-late-per-proxy",
                True,
                "late per_proxy was requested, but the direct subsys_esoc0 post-wait trigger path completed first and helper never reached the late per_proxy block",
                "split V1238 into a late-per_proxy-only path without direct subsys trigger, or add helper support for late-per_proxy post-wait snapshots",
            )
        return (
            "v1237-late-per-proxy-begin-missing",
            False,
            f"late_per_proxy={late}",
            "inspect helper ordering before retrying",
        )
    if _int_value(late.get("gate_positive"), 0) <= 0:
        return (
            "v1237-late-per-proxy-gate-not-positive",
            True,
            "late per_proxy was requested but mdm_helper /dev/esoc-0 gate did not open",
            "repair mdm_helper esoc fd gate before retrying late per_proxy",
        )
    if _int_value(late.get("started"), 0) <= 0:
        return (
            "v1237-late-per-proxy-not-started",
            False,
            f"late_per_proxy={late}",
            "inspect helper child spawn failure before retrying",
        )
    if _post_wait_has_ks_or_mhi(post_wait):
        return (
            "v1237-post-wait-req-ks-mhi-progress",
            True,
            "post-WAIT_FOR_REQ observer saw ks or MHI pipe evidence",
            "observe WLFW/BDF/wlan0 readiness before Wi-Fi HAL",
        )
    if _int_value(late.get("per_mgr_subsys_esoc0_max"), 0) > 0 or parity.get("pm_service_subsys_esoc0_attempt"):
        return (
            "v1237-late-per-proxy-reached-esoc0-no-ks-mhi",
            True,
            "late per_proxy started and PM path reached /dev/subsys_esoc0, but ks/MHI still stayed absent",
            "classify pm-service Binder return path and eSoC/MDM3 powerup status before Wi-Fi HAL",
        )
    if _int_value(late.get("started"), 0) > 0:
        return (
            "v1237-late-per-proxy-started-no-esoc0-no-ks-mhi",
            True,
            "late per_proxy started after mdm_helper esoc fd, but PM path did not reach /dev/subsys_esoc0 and no ks/MHI appeared",
            "classify per_proxy/per_mgr request delivery and vndservice/provider readiness",
        )
    transition = max(
        _int_value((post_wait.get("summary") or {}).get("transition_detected"), -1),
        _int_value((post_wait.get("sample_max") or {}).get("transition_detected"), -1),
    )
    if transition > 0:
        if _int_value(branch.get("execve_count"), 0) > 0:
            return (
                "v1237-branch-snapshot-exec-attempt-no-ks-mhi",
                True,
                "branch snapshot saw execve/execveat activity after WAIT_FOR_REQ return, but no ks/MHI pipe appeared",
                "inspect private branch transcript for exec path and compare Android ks launch contract",
            )
        if _int_value(branch.get("phase_count"), 0) > 0:
            return (
                "v1237-branch-snapshot-no-exec-no-ks-mhi",
                True,
                "branch snapshot covered the WAIT_FOR_REQ return window but saw no execve/ks/MHI evidence",
                "classify mdm_helper return-code branch and required Android runtime/property/env inputs",
            )
        return (
            "v1237-wait-req-returned-no-ks-mhi",
            True,
            "mdm_helper left ESOC_WAIT_FOR_REQ but no ks/MHI pipe appeared in bounded post-transition window",
            "classify mdm_helper branch after WAIT_FOR_REQ return and Android ks launch conditions",
        )
    if early.get("wait_for_req_thread_count", 0) > 0 or post_wait.get("initial_wait_for_req_thread_count", 0) > 0:
        return (
            "v1237-still-waiting-for-req-no-transition",
            True,
            "mdm_helper stayed in ESOC_WAIT_FOR_REQ for the bounded pre-transition observer window; ks/MHI did not appear",
            "move next gate to GPIO142/PCIe/AP2MDM response timing rather than ks launch",
        )
    if parity.get("pm_service_subsys_esoc0_attempt"):
        return (
            "v1237-post-wait-req-no-wait-thread-with-pm-trigger",
            True,
            "pm-service attempted subsys_esoc0, but post-wait observer did not see a WAIT_FOR_REQ thread",
            "compare early trace and post-wait timing; consider denser first-second observer",
        )
    return (
        "v1237-post-wait-req-inconclusive",
        False,
        f"post_wait={post_wait} early={early}",
        "inspect full child output and repair V1237 parser or live path",
    )


def _render_samples(samples: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            sample.get("index"),
            sample.get("mdm_helper_alive"),
            sample.get("mdm_helper_state"),
            sample.get("wait_for_req_thread_count"),
            sample.get("transition_detected"),
            sample.get("fd_esoc0_count"),
            sample.get("fd_mhi_pipe_count"),
            sample.get("mhi_pipe_exists"),
            sample.get("mhi_pipe_fd_count"),
            sample.get("ks_process_count"),
        ]
        for sample in samples
    ]


def _render_summary(manifest: dict[str, Any]) -> str:
    post_wait = manifest.get("mdm_helper_post_wait_req") or {}
    branch = manifest.get("mdm_helper_post_wait_branch") or {}
    late = manifest.get("late_per_proxy") or {}
    early = manifest.get("mdm_helper_early_compact_trace") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    summary = post_wait.get("summary") or {}
    sample_max = post_wait.get("sample_max") or {}
    rows = [
        ["decision", manifest.get("decision", "")],
        ["pass", manifest.get("pass", "")],
        ["post_wait_emitted", post_wait.get("emitted")],
        ["post_wait_sample_count", post_wait.get("sample_count")],
        ["post_wait_declared_sample_count", post_wait.get("declared_sample_count")],
        ["branch_emitted", branch.get("emitted")],
        ["branch_phase_count", branch.get("phase_count")],
        ["branch_declared_sample_count", branch.get("declared_sample_count")],
        ["branch_declared_burst_count", branch.get("declared_burst_count")],
        ["branch_execve_count", branch.get("execve_count")],
        ["branch_ioctl_count", branch.get("ioctl_count")],
        ["branch_path_value_count", branch.get("path_value_count")],
        ["late_requested", late.get("requested")],
        ["late_gate_positive", late.get("gate_positive")],
        ["late_started", late.get("started")],
        ["late_poll_count", late.get("poll_count")],
        ["late_per_proxy_alive_max", late.get("per_proxy_alive_max")],
        ["late_per_mgr_subsys_esoc0_max", late.get("per_mgr_subsys_esoc0_max")],
        ["late_per_mgr_subsys_modem_max", late.get("per_mgr_subsys_modem_max")],
        ["initial_wait_for_req_thread_count", post_wait.get("initial_wait_for_req_thread_count")],
        ["transition_detected.summary", summary.get("transition_detected")],
        ["transition_detected.sample_max", sample_max.get("transition_detected")],
        ["transition_sample", summary.get("transition_sample")],
        ["ks_process_count.max", max(_int_value(summary.get("ks_process_count"), -1), _int_value(sample_max.get("ks_process_count"), -1))],
        ["mhi_pipe_exists.max", max(_int_value(summary.get("mhi_pipe_exists"), -1), _int_value(sample_max.get("mhi_pipe_exists"), -1))],
        ["mhi_pipe_fd_count.max", max(_int_value(summary.get("mhi_pipe_fd_count"), -1), _int_value(sample_max.get("mhi_pipe_fd_count"), -1))],
        ["early_wait_for_req_thread_count", early.get("wait_for_req_thread_count")],
        ["pm_service_subsys_esoc0_attempt", parity.get("pm_service_subsys_esoc0_attempt")],
        ["boundary_wlan0_seen", boundary.get("wlan0_seen")],
        ["boundary_max_dmesg_wlfw_count", boundary.get("max_dmesg_wlfw_count")],
    ]
    safety_rows = [
        ["wifi_hal_start_executed", manifest.get("wifi_hal_start_executed")],
        ["scan_connect_executed", manifest.get("scan_connect_executed")],
        ["credential_use_executed", manifest.get("credential_use_executed")],
        ["dhcp_route_executed", manifest.get("dhcp_route_executed")],
        ["external_ping_executed", manifest.get("external_ping_executed")],
        ["wifi_bringup_executed", manifest.get("wifi_bringup_executed")],
        ["flash_executed", manifest.get("flash_executed")],
        ["partition_write_executed", manifest.get("partition_write_executed")],
        ["post_wait_forbidden", post_wait.get("forbidden")],
        ["branch_forbidden", branch.get("forbidden")],
    ]
    syscall_rows = [[item["value"], item["count"]] for item in branch.get("syscall_names", [])]
    wchan_rows = [[item["value"], item["count"]] for item in branch.get("wchan", [])]
    return "\n".join([
        "# V1237 mdm_helper Post-WAIT_FOR_REQ Branch Snapshot Live Gate",
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
        "## Branch Syscalls",
        "",
        markdown_table(["syscall", "count"], syscall_rows) if syscall_rows else "- none",
        "",
        "## Branch Wchan",
        "",
        markdown_table(["wchan", "count"], wchan_rows) if wchan_rows else "- none",
        "",
        "## First Samples",
        "",
        markdown_table(
            ["idx", "alive", "state", "wait_threads", "transition", "esoc0_fd", "mhi_fd", "mhi_path", "mhi_global_fd", "ks_count"],
            _render_samples(post_wait.get("first_samples", [])),
        ),
        "",
        "## Last Samples",
        "",
        markdown_table(
            ["idx", "alive", "state", "wait_threads", "transition", "esoc0_fd", "mhi_fd", "mhi_path", "mhi_global_fd", "ks_count"],
            _render_samples(post_wait.get("last_samples", [])),
        ),
        "",
        "## Safety Audit",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def _reanalyze_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest["_run_dir"] = manifest.get("_run_dir") or str(repo_path(DEFAULT_OUT_DIR))
    manifest["cycle"] = "v1237"
    manifest["reclassified_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1235"
    manifest["post_wait_flag"] = POST_WAIT_FLAG
    manifest["branch_snapshot_flag"] = BRANCH_SNAPSHOT_FLAG
    manifest["cnss_before_per_proxy_flag"] = CNSS_BEFORE_PER_PROXY_FLAG
    manifest["late_per_proxy_flag"] = LATE_PER_PROXY_FLAG
    manifest["subsys_trigger_flag"] = SUBSYS_TRIGGER_FLAG
    manifest["capture_mode_forced"] = "none"

    run_text = v1224._read_run_text(manifest)
    if manifest.get("command") != "plan" and "post_wait_req.begin=1" not in run_text:
        observer_path = repo_path(DEFAULT_OUT_DIR / "host/pm-server-wchan-tracefs-observer.txt")
        try:
            run_text = observer_path.read_text(encoding="utf-8", errors="replace")
            manifest["reclassify_text_fallback"] = str(observer_path)
        except OSError:
            pass
    manifest["private_cnss_daemon"] = v1221._parse_prefixed_lines(run_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_ks_mhi_parity"] = v1224._extract_parity(manifest, run_text)
    manifest["mdm_helper_early_compact_trace"] = v1228._analyze_early_trace(run_text)
    manifest["mdm_helper_post_wait_req"] = _analyze_post_wait(run_text)
    manifest["mdm_helper_post_wait_branch"] = _analyze_branch(run_text)
    manifest["late_per_proxy"] = _analyze_late_per_proxy(run_text)

    decision, passed, reason, next_step = decide_v1237(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def reclassify_existing() -> int:
    manifest_path = repo_path(DEFAULT_OUT_DIR / "manifest.json")
    if not manifest_path.exists():
        print(f"error: missing existing V1237 manifest: {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        print(f"error: manifest is not an object: {manifest_path}", file=sys.stderr)
        return 2
    manifest["command"] = "run"
    manifest = _reanalyze_manifest(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path = repo_path(DEFAULT_OUT_DIR / "summary.md")
    summary_path.write_text(_render_summary(manifest), encoding="utf-8")
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(DEFAULT_OUT_DIR)) + "\n")
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"evidence: {repo_path(DEFAULT_OUT_DIR)}")
    return 0 if manifest.get("pass") else 1


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
    manifest["cycle"] = "v1237"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1235"
    manifest["post_wait_flag"] = POST_WAIT_FLAG
    manifest["branch_snapshot_flag"] = BRANCH_SNAPSHOT_FLAG
    manifest["cnss_before_per_proxy_flag"] = CNSS_BEFORE_PER_PROXY_FLAG
    manifest["late_per_proxy_flag"] = LATE_PER_PROXY_FLAG
    manifest["subsys_trigger_flag"] = SUBSYS_TRIGGER_FLAG
    manifest["capture_mode_forced"] = "none"
    manifest["_run_dir"] = str(store.run_dir)

    manifest = _reanalyze_manifest(manifest)

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    decision = manifest.get("decision")
    passed = manifest.get("pass")
    reason = manifest.get("reason")
    next_step = manifest.get("next_step")
    post_wait = manifest["mdm_helper_post_wait_req"]
    branch = manifest["mdm_helper_post_wait_branch"]
    late = manifest["late_per_proxy"]
    parity = manifest["mdm_helper_ks_mhi_parity"]
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"post_wait_emitted:             {post_wait.get('emitted')}")
    print(f"post_wait_sample_count:        {post_wait.get('sample_count')}")
    print(f"transition_detected:           {(post_wait.get('summary') or {}).get('transition_detected')}")
    print(f"ks_process_count:              {(post_wait.get('summary') or {}).get('ks_process_count')}")
    print(f"mhi_pipe_fd_count:             {(post_wait.get('summary') or {}).get('mhi_pipe_fd_count')}")
    print(f"branch_emitted:                {branch.get('emitted')}")
    print(f"branch_phase_count:            {branch.get('phase_count')}")
    print(f"branch_execve_count:           {branch.get('execve_count')}")
    print(f"branch_ioctl_count:            {branch.get('ioctl_count')}")
    print(f"late_per_proxy_requested:      {late.get('requested')}")
    print(f"late_per_proxy_gate_positive:  {late.get('gate_positive')}")
    print(f"late_per_proxy_started:        {late.get('started')}")
    print(f"late_per_mgr_subsys_esoc0_max: {late.get('per_mgr_subsys_esoc0_max')}")
    print(f"pm_service_subsys_esoc0_attempt:{parity.get('pm_service_subsys_esoc0_attempt')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
