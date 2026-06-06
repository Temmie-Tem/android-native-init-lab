#!/usr/bin/env python3
"""V1232: bounded mdm_helper post-WAIT_FOR_REQ ks/MHI observer live gate.

This is a V1228 derivative.  It preserves the non-ptrace PM/CNSS path, uses
helper v256, and adds only the post-WAIT_FOR_REQ observer flag:

    --pm-observer-mdm-helper-post-wait-req-ks-observer

The live gate may start the bounded PM/CNSS/mdm_helper observer stack and may
open the existing subsystem-trigger child used by V1228.  It must not start
Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP/routes, external
ping, send ESOC_NOTIFY, send ESOC_BOOT_DONE, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import re
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1232-mdm-helper-post-wait-req-ks-observer-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1232-mdm-helper-post-wait-req-ks-observer-live.txt")
HELPER_MARKER = "a90_android_execns_probe v256"
HELPER_SHA256 = "56ab12b7c7951f2fd5ff9132d6d9662b77560fc2cd55da712115b99b2ec029e9"
POST_WAIT_PREFIX = "post_wait_req."
POST_WAIT_FLAG = "--pm-observer-mdm-helper-post-wait-req-ks-observer"
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


def decide_v1232(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1232-post-wait-req-observer-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1232 bounded post-WAIT_FOR_REQ observer",
        )
    post_wait = manifest.get("mdm_helper_post_wait_req") or {}
    early = manifest.get("mdm_helper_early_compact_trace") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    if not post_wait.get("emitted"):
        return (
            "v1232-post-wait-req-not-emitted",
            False,
            "helper output did not include post_wait_req.begin=1",
            "verify helper v256 deployment and command flag injection",
        )
    if post_wait.get("forbidden"):
        return (
            "v1232-post-wait-req-forbidden-action",
            False,
            f"forbidden={post_wait.get('forbidden')}",
            "stop and inspect helper safety gates before retry",
        )
    if _post_wait_has_ks_or_mhi(post_wait):
        return (
            "v1232-post-wait-req-ks-mhi-progress",
            True,
            "post-WAIT_FOR_REQ observer saw ks or MHI pipe evidence",
            "observe WLFW/BDF/wlan0 readiness before Wi-Fi HAL",
        )
    transition = max(
        _int_value((post_wait.get("summary") or {}).get("transition_detected"), -1),
        _int_value((post_wait.get("sample_max") or {}).get("transition_detected"), -1),
    )
    if transition > 0:
        return (
            "v1232-wait-req-returned-no-ks-mhi",
            True,
            "mdm_helper left ESOC_WAIT_FOR_REQ but no ks/MHI pipe appeared in bounded post-transition window",
            "classify mdm_helper branch after WAIT_FOR_REQ return and Android ks launch conditions",
        )
    if early.get("wait_for_req_thread_count", 0) > 0 or post_wait.get("initial_wait_for_req_thread_count", 0) > 0:
        return (
            "v1232-still-waiting-for-req-no-transition",
            True,
            "mdm_helper stayed in ESOC_WAIT_FOR_REQ for the bounded pre-transition observer window; ks/MHI did not appear",
            "move next gate to GPIO142/PCIe/AP2MDM response timing rather than ks launch",
        )
    if parity.get("pm_service_subsys_esoc0_attempt"):
        return (
            "v1232-post-wait-req-no-wait-thread-with-pm-trigger",
            True,
            "pm-service attempted subsys_esoc0, but post-wait observer did not see a WAIT_FOR_REQ thread",
            "compare early trace and post-wait timing; consider denser first-second observer",
        )
    return (
        "v1232-post-wait-req-inconclusive",
        False,
        f"post_wait={post_wait} early={early}",
        "inspect full child output and repair V1232 parser or live path",
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
    ]
    return "\n".join([
        "# V1232 mdm_helper Post-WAIT_FOR_REQ ks/MHI Observer Live Gate",
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
    manifest["cycle"] = "v1232"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1228"
    manifest["post_wait_flag"] = POST_WAIT_FLAG
    manifest["subsys_trigger_flag"] = SUBSYS_TRIGGER_FLAG
    manifest["capture_mode_forced"] = "none"
    manifest["_run_dir"] = str(store.run_dir)

    run_text = v1224._read_run_text(manifest)
    manifest["private_cnss_daemon"] = v1221._parse_prefixed_lines(run_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_ks_mhi_parity"] = v1224._extract_parity(manifest, run_text)
    manifest["mdm_helper_early_compact_trace"] = v1228._analyze_early_trace(run_text)
    manifest["mdm_helper_post_wait_req"] = _analyze_post_wait(run_text)

    decision, passed, reason, next_step = decide_v1232(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    post_wait = manifest["mdm_helper_post_wait_req"]
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
    print(f"pm_service_subsys_esoc0_attempt:{parity.get('pm_service_subsys_esoc0_attempt')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
