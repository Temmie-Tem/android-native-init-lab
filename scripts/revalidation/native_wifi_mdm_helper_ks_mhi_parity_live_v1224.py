#!/usr/bin/env python3
"""V1224: bounded mdm_helper/ks/MHI parity gate around SDX50M eSoC open.

V1223 classified the next missing contract as Android-like ``mdm_helper`` /
``ks`` MHI image-link lifetime around the ``pm-service`` eSoC open.  This
runner reuses the V1222 bounded private-CNSS SDX50M live path, but promotes the
already-emitted post-PM/lower-trace lines into first-class manifest fields:

* whether ``mdm_helper`` owns ``/dev/esoc-0``;
* whether ``pm-service`` attempts or owns ``/dev/subsys_esoc0``;
* whether ``ks`` or ``/dev/mhi_0305_01.01.00_pipe_10`` appears;
* whether WLFW/BDF/``wlan0`` appears before the crash/stall boundary.

Safety remains unchanged: no Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, boot image write, or vendor partition write.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_post_esoc_power_boundary_v1222 as v1222
import native_wifi_private_cnss_daemon_sdx50m_live_v1221 as v1221
import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod


DEFAULT_OUT_DIR = Path("tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1224-mdm-helper-ks-mhi-parity-live.txt")

POST_PM_PREFIX = "post_pm_mdm_helper_esoc_observer."
QUEUE_PREFIX = "mdm_helper_queue_timing."
LOWER_TRACE_PREFIX = "post_pm_mdm_helper_lower_trace."


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_defaults() -> None:
    v1222.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1222.LATEST_POINTER = LATEST_POINTER
    v1222.patch_defaults()


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
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            keys[key] = value.strip()
    return keys


def _collect_prefix(keys: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def _int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback


def _sample_indexes(lower: dict[str, str]) -> list[int]:
    indexes: set[int] = set()
    for key in lower:
        match = re.match(r"sample_(\d+)\.", key)
        if match:
            indexes.add(int(match.group(1)))
    return sorted(indexes)


def _lower_trace_samples(lower: dict[str, str]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in _sample_indexes(lower):
        prefix = f"sample_{index:02d}."
        sample = {
            "index": index,
            "alive": lower.get(prefix + "alive", ""),
            "state": lower.get(prefix + "state", ""),
            "fd_esoc0_count": _int_value(lower.get(prefix + "fd_esoc0_count"), -1),
            "fd_subsys_esoc0_count": _int_value(lower.get(prefix + "fd_subsys_esoc0_count"), -1),
            "fd_mhi_pipe_count": _int_value(lower.get(prefix + "fd_mhi_pipe_count"), -1),
            "ks_count": _int_value(lower.get(prefix + "ks_count"), -1),
            "mhi_cmdline_count": _int_value(lower.get(prefix + "mhi_cmdline_count"), -1),
        }
        samples.append(sample)
    return samples


def _max_sample(samples: list[dict[str, Any]], field: str) -> int:
    return max((_int_value(sample.get(field), -1) for sample in samples), default=-1)


def _extract_parity(manifest: dict[str, Any], text: str) -> dict[str, Any]:
    keys = _parse_keys(text)
    post_pm = _collect_prefix(keys, POST_PM_PREFIX)
    queue = _collect_prefix(keys, QUEUE_PREFIX)
    lower = _collect_prefix(keys, LOWER_TRACE_PREFIX)
    samples = _lower_trace_samples(lower)
    boundary = manifest.get("post_esoc_boundary") or {}
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    syscall_paths = [
        value
        for key, value in contract.items()
        if key.startswith("syscall_probe.after_cnss_daemon.")
        and key.endswith(".path.value")
    ]
    post_mdm_esoc = _int_value(post_pm.get("fd_esoc0_count.window"), -1)
    post_mhi = _int_value(post_pm.get("fd_mhi_pipe_count.window"), -1)
    post_ks = _int_value(post_pm.get("ks_count.window"), -1)
    queue_per_mgr_subsys_esoc0 = _int_value(queue.get("post_pm_window.per_mgr_subsys_esoc0_count"), -1)
    queue_per_mgr_subsys_modem = _int_value(queue.get("post_pm_window.per_mgr_subsys_modem_count"), -1)
    queue_mdm_esoc = _int_value(queue.get("post_pm_window.mdm_helper_esoc0_count"), -1)
    max_lower_mdm_esoc = _max_sample(samples, "fd_esoc0_count")
    max_lower_mhi = _max_sample(samples, "fd_mhi_pipe_count")
    max_lower_ks = _max_sample(samples, "ks_count")
    max_lower_mhi_cmdline = _max_sample(samples, "mhi_cmdline_count")
    pm_service_subsys_esoc0_attempt = "/dev/subsys_esoc0" in syscall_paths
    mdm_helper_esoc_present = post_mdm_esoc > 0 or queue_mdm_esoc > 0 or max_lower_mdm_esoc > 0
    ks_or_mhi_present = (
        post_mhi > 0
        or post_ks > 0
        or max_lower_mhi > 0
        or max_lower_ks > 0
        or max_lower_mhi_cmdline > 0
    )
    wlfw_or_wlan0_present = (
        bool(boundary.get("service69_seen"))
        or bool(boundary.get("wlan0_seen"))
        or _int_value(boundary.get("max_dmesg_wlfw_count")) > 0
    )
    return {
        "post_pm": post_pm,
        "queue": queue,
        "lower_trace": lower,
        "lower_trace_samples": samples,
        "lower_trace_sample_count": len(samples),
        "syscall_paths": syscall_paths,
        "pm_service_subsys_esoc0_attempt": pm_service_subsys_esoc0_attempt,
        "pm_service_subsys_esoc0_fd_count": queue_per_mgr_subsys_esoc0,
        "pm_service_subsys_modem_fd_count": queue_per_mgr_subsys_modem,
        "mdm_helper_esoc0_count_window": max(post_mdm_esoc, queue_mdm_esoc, max_lower_mdm_esoc),
        "mdm_helper_mhi_pipe_count_window": max(post_mhi, max_lower_mhi),
        "ks_count_window": max(post_ks, max_lower_ks),
        "mhi_cmdline_count_window": max_lower_mhi_cmdline,
        "mdm_helper_esoc_present": mdm_helper_esoc_present,
        "ks_or_mhi_present": ks_or_mhi_present,
        "wlfw_or_wlan0_present": wlfw_or_wlan0_present,
        "post_pm_result": post_pm.get("result", ""),
        "post_pm_reason": post_pm.get("reason", ""),
        "post_pm_all_postflight_safe": post_pm.get("all_postflight_safe", ""),
        "post_pm_lower_artifact_observed": post_pm.get("lower_artifact_observed", ""),
    }


def decide_v1224(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1224-mdm-helper-ks-mhi-parity-plan-ready",
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1224 bounded live parity gate",
        )
    if not manifest.get("steps"):
        return (
            "v1224-live-not-executed",
            False,
            f"base_decision={manifest.get('decision', '')} base_reason={manifest.get('reason', '')}",
            "rerun with the required V1106 allow flags and explicit run command",
        )

    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    if not parity.get("pm_service_subsys_esoc0_attempt"):
        return (
            "v1224-pm-service-esoc-open-not-observed",
            False,
            f"syscall_paths={parity.get('syscall_paths')}",
            "return to V1222 SDX50M PM selection gate",
        )
    if not parity.get("mdm_helper_esoc_present"):
        return (
            "v1224-mdm-helper-esoc-missing",
            False,
            f"post_pm={parity.get('post_pm')} queue={parity.get('queue')}",
            "repair mdm_helper start/domain/device-node path before another eSoC open",
        )
    if parity.get("ks_or_mhi_present") and parity.get("wlfw_or_wlan0_present"):
        return (
            "v1224-ks-mhi-wlfw-progress",
            True,
            "mdm_helper esoc, ks/MHI, and WLFW/wlan0 indicators appeared",
            "V1225: bounded WLFW-to-wlan0 readiness gate before Wi-Fi HAL",
        )
    if parity.get("ks_or_mhi_present"):
        return (
            "v1224-ks-mhi-present-before-wlfw",
            True,
            f"ks_count={parity.get('ks_count_window')} mhi_pipe={parity.get('mdm_helper_mhi_pipe_count_window')}",
            "V1225: extend BDF/WLFW readiness observer before Wi-Fi HAL",
        )
    if _int_value(boundary.get("max_dmesg_modem_down_count")) > 0:
        return (
            "v1224-mdm-helper-esoc-present-ks-mhi-absent-crash",
            True,
            (
                "mdm_helper owns /dev/esoc-0 and pm-service attempts /dev/subsys_esoc0, "
                "but ks/MHI never appears before modem-down/crash markers"
            ),
            "V1225: classify why mdm_helper stays before ks/MHI under SDX50M power-up; focus on esoc ioctl/wchan, MHI device creation, and Android mdm_helper timing",
        )
    return (
        "v1224-mdm-helper-esoc-present-ks-mhi-absent-no-crash",
        True,
        "mdm_helper owns /dev/esoc-0 and pm-service attempts /dev/subsys_esoc0, but ks/MHI is absent",
        "V1225: add focused mdm_helper ioctl/wchan trace and MHI device polling",
    )


def _render_summary(manifest: dict[str, Any]) -> str:
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    thread = manifest.get("thread_analysis") or {}
    rows = [
        ["decision", manifest.get("decision", "")],
        ["pass", manifest.get("pass", "")],
        ["pm_service_subsys_esoc0_attempt", parity.get("pm_service_subsys_esoc0_attempt")],
        ["pm_service_subsys_esoc0_fd_count", parity.get("pm_service_subsys_esoc0_fd_count")],
        ["pm_service_subsys_modem_fd_count", parity.get("pm_service_subsys_modem_fd_count")],
        ["mdm_helper_esoc_present", parity.get("mdm_helper_esoc_present")],
        ["mdm_helper_esoc0_count_window", parity.get("mdm_helper_esoc0_count_window")],
        ["ks_or_mhi_present", parity.get("ks_or_mhi_present")],
        ["ks_count_window", parity.get("ks_count_window")],
        ["mdm_helper_mhi_pipe_count_window", parity.get("mdm_helper_mhi_pipe_count_window")],
        ["mhi_cmdline_count_window", parity.get("mhi_cmdline_count_window")],
        ["lower_trace_sample_count", parity.get("lower_trace_sample_count")],
        ["post_pm_result", parity.get("post_pm_result")],
        ["post_pm_reason", parity.get("post_pm_reason")],
        ["cnss_registered_peripherals", json.dumps(thread.get("cnss_registered_peripherals", []), ensure_ascii=False)],
        ["mdm3_state_transitions", json.dumps(boundary.get("mdm3_state_transitions", []), ensure_ascii=False)],
        ["max_dmesg_modem_down_count", boundary.get("max_dmesg_modem_down_count")],
        ["max_dmesg_wlfw_count", boundary.get("max_dmesg_wlfw_count")],
        ["wlan0_seen", boundary.get("wlan0_seen")],
    ]
    sample_rows = [
        [
            sample.get("index"),
            sample.get("alive"),
            sample.get("state"),
            sample.get("fd_esoc0_count"),
            sample.get("fd_subsys_esoc0_count"),
            sample.get("fd_mhi_pipe_count"),
            sample.get("ks_count"),
            sample.get("mhi_cmdline_count"),
        ]
        for sample in parity.get("lower_trace_samples", [])[:10]
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
    ]
    return "\n".join([
        "# V1224 mdm_helper / ks / MHI Parity Live Gate",
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
        "## Lower Trace Samples",
        "",
        markdown_table(
            ["idx", "alive", "state", "esoc0_fd", "subsys_esoc0_fd", "mhi_fd", "ks", "mhi_cmd"],
            sample_rows,
        ),
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
    if args.helper_timeout_sec == 4:
        args.helper_timeout_sec = 30
    if args.toybox_timeout_sec == 18:
        args.toybox_timeout_sec = 70
    if args.tracefs_duration_sec == 18:
        args.tracefs_duration_sec = 95
    if args.thread_sample_count == 80:
        args.thread_sample_count = 260
    v1165.v1143.v1139.v1113.set_global_defaults(args)

    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1224"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = v1221.HELPER_MARKER_V253
    manifest["helper_sha256"] = v1221.HELPER_SHA256_V253
    manifest["based_on_cycle"] = "v1222"
    manifest["_run_dir"] = str(store.run_dir)

    run_text = _read_run_text(manifest)
    manifest["private_cnss_daemon"] = v1221._parse_prefixed_lines(run_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = v1222._analyze_boundary(manifest, run_text)
    manifest["mdm_helper_ks_mhi_parity"] = _extract_parity(manifest, run_text)
    decision, passed, reason, next_step = decide_v1224(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    parity = manifest["mdm_helper_ks_mhi_parity"]
    boundary = manifest["post_esoc_boundary"]
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"pm_service_subsys_esoc0_attempt: {parity.get('pm_service_subsys_esoc0_attempt')}")
    print(f"mdm_helper_esoc_present:         {parity.get('mdm_helper_esoc_present')}")
    print(f"mdm_helper_esoc0_count_window:   {parity.get('mdm_helper_esoc0_count_window')}")
    print(f"ks_or_mhi_present:               {parity.get('ks_or_mhi_present')}")
    print(f"ks_count_window:                 {parity.get('ks_count_window')}")
    print(f"mhi_pipe_count_window:           {parity.get('mdm_helper_mhi_pipe_count_window')}")
    print(f"lower_trace_sample_count:        {parity.get('lower_trace_sample_count')}")
    print(f"mdm3_state_transitions:          {boundary.get('mdm3_state_transitions')}")
    print(f"max_dmesg_modem_down_count:      {boundary.get('max_dmesg_modem_down_count')}")
    print(f"max_dmesg_wlfw_count:            {boundary.get('max_dmesg_wlfw_count')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
