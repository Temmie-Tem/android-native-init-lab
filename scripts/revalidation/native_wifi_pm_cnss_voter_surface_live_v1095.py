#!/usr/bin/env python3
"""V1095 PM provider plus CNSS voter lower-surface live gate."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_post_provider_surface_live_v1093 as v1093


DEFAULT_OUT_DIR = Path("tmp/wifi/v1095-pm-cnss-voter-surface-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1095-pm-cnss-voter-surface-live.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1095-execns-helper-v206-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "7920eeb353e1d6f09ded42efc84e7a8549fdb407cdd8236307422ebf2a9108e4"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v206"
DEVICE_WORK_DIR = "/cache/a90-runtime/v1095"
DEVICE_SCRIPT = f"{DEVICE_WORK_DIR}/pm-cnss-voter-surface.sh"
DEVICE_OUTPUT = f"{DEVICE_WORK_DIR}/pm-cnss-voter-surface-output.txt"
SUMMARY_HEADING = "# V1095 PM Provider CNSS Voter Surface Live"

original_helper_command = v1093.helper_command


def parse_int(value: str | None, fallback: int = 0) -> int:
    try:
        return int(value or "")
    except ValueError:
        return fallback


def helper_command(args: argparse.Namespace) -> list[str]:
    command = original_helper_command(args)
    command.extend([
        "--pm-observer-continue-after-provider",
        "--pm-observer-start-cnss-after-provider",
    ])
    return command


def run_helper_script(args: argparse.Namespace,
                      store: v1093.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    return v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "pm-cnss-voter-surface-script",
        ["run", args.busybox, "sh", DEVICE_SCRIPT],
        timeout=args.toybox_timeout_sec + 20.0,
    )


def remote_helper_state(args: argparse.Namespace,
                        store: v1093.EvidenceStore,
                        steps: list[dict[str, Any]]) -> dict[str, Any]:
    sha = v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "remote-helper-sha",
        ["run", args.toybox, "sha256sum", args.helper],
        timeout=30.0,
    )
    usage = v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "remote-helper-usage",
        ["run", args.helper],
        timeout=30.0,
        allow_error=True,
    )
    sha_text = (store.run_dir / sha["file"]).read_text(encoding="utf-8", errors="replace")
    usage_text = (store.run_dir / usage["file"]).read_text(encoding="utf-8", errors="replace")
    return {
        "sha_ok": args.helper_sha256 in sha_text,
        "marker_ok": args.helper_marker in usage_text,
        "mode_ok": v1093.base.DEFAULT_MODE in usage_text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in usage_text,
        "sha_file": sha["file"],
        "usage_file": usage["file"],
    }


def post_surface(args: argparse.Namespace,
                 store: v1093.EvidenceStore,
                 steps: list[dict[str, Any]]) -> dict[str, Any]:
    ps = v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "post-ps",
        ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"],
        timeout=25.0,
    )
    net = v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "post-proc-net-dev",
        ["run", args.toybox, "cat", "/proc/net/dev"],
        timeout=20.0,
    )
    subsys = v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "post-subsys-state",
        ["run", args.toybox, "cat", "/sys/bus/msm_subsys/devices/subsys9/state"],
        timeout=20.0,
        allow_error=True,
    )
    dmesg = v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "post-dmesg-wifi-esoc-tail",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"{args.busybox} dmesg | "
                f"{args.busybox} grep -Ei 'wlfw|wlan0|bdf|qcwlan|icnss|cnss|esoc|mdm' | "
                f"{args.busybox} tail -60"
            ),
        ],
        timeout=25.0,
        allow_error=True,
    )
    ps_text = (store.run_dir / ps["file"]).read_text(encoding="utf-8", errors="replace")
    net_text = (store.run_dir / net["file"]).read_text(encoding="utf-8", errors="replace")
    subsys_text = (store.run_dir / subsys["file"]).read_text(encoding="utf-8", errors="replace")
    dmesg_text = (store.run_dir / dmesg["file"]).read_text(encoding="utf-8", errors="replace")
    actor_lines = [line.strip() for line in ps_text.splitlines() if v1093.base.ACTOR_RE.search(line)]
    return {
        "actor_hits": actor_lines[:24],
        "pm_actor_hits": [
            line
            for line in actor_lines
            if "pm_proxy_helper" in line or "pm-service" in line or "pm-proxy" in line
        ][:12],
        "cnss_actor_hits": [line for line in actor_lines if "cnss" in line][:12],
        "forbidden_actor_hits": [
            line
            for line in actor_lines
            if "mdm_helper" in line or "wificond" in line or "wifi@" in line or "supplicant" in line
        ][:12],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if v1093.base.WIFI_RE.search(line)][:16],
        "helper_process_hits": [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line][:16],
        "subsys_state_tail": subsys_text.splitlines()[-32:],
        "wlfw_or_wlan_dmesg_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if re.search(r"wlfw|wlan0|bdf|qcwlan|icnss|cnss", line, re.IGNORECASE)
        ][-60:],
    }


def required_query_phases(query: dict[str, str]) -> dict[str, bool]:
    phases = v1093.required_query_phases(query)
    phases["after_cnss_daemon"] = any(
        key.startswith("wifi_vndservice_query.pm_observer_after_cnss_daemon_probe.") and
        key.endswith(".exec_attempted") and
        value == "1"
        for key, value in query.items()
    )
    return phases


def filtered_forbidden(helper: dict[str, Any]) -> dict[str, str]:
    forbidden = dict(helper.get("forbidden_true") or {})
    forbidden.pop("pm_service_trigger_observer.cnss_daemon_start_executed", None)
    return forbidden


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1095-plan-helper-v206-missing", False, f"local={local}", "build/deploy helper v206 before V1095"
        return "v1095-pm-cnss-voter-surface-plan-ready", True, "plan-only; no device command executed", "run bounded V1095 observer live gate"
    missing = v1093.base.required_flags(args)
    if missing:
        return "v1095-pm-cnss-voter-surface-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1095 flags"
    helper = analysis.get("helper") or {}
    failed_steps = v1093.base.step_failures(steps, helper)
    if failed_steps:
        return "v1095-step-failed", False, f"failed_steps={failed_steps}", "inspect V1095 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok") and remote.get("start_cnss_flag_ok")):
        return "v1095-helper-v206-remote-mismatch", False, f"remote={remote}", "redeploy helper v206 before V1095"
    forbidden = filtered_forbidden(helper)
    if forbidden or helper.get("post_provider_forbidden_true"):
        return (
            "v1095-forbidden-action-detected",
            False,
            f"forbidden={forbidden} post={helper.get('post_provider_forbidden_true')}",
            "stop and audit helper before retry",
        )
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1095-helper-mode-not-executed", False, f"contract={contract}", "fix V1095 helper command before retry"
    if contract.get("continue_after_provider") != "1" or contract.get("start_cnss_after_provider") != "1":
        return (
            "v1095-cnss-voter-flags-not-enabled",
            False,
            f"continue={contract.get('continue_after_provider')} start_cnss={contract.get('start_cnss_after_provider')}",
            "fix V1095 helper command",
        )
    if contract.get("cnss_daemon_start_executed") != "1":
        return "v1095-cnss-daemon-not-started", False, "helper did not enter CNSS voter phase", "inspect provider continuation"
    if contract.get("vndservicemanager_readiness.ready") != "1":
        return (
            "v1095-vndservicemanager-readiness-gap",
            True,
            f"checked={contract.get('vndservicemanager_readiness.checked')} ready={contract.get('vndservicemanager_readiness.ready')}",
            "repair service-manager readiness before retrying CNSS voter gate",
        )
    query = helper.get("vndservice_query") or {}
    phases = required_query_phases(query)
    if not all(phases.values()):
        return "v1095-query-phase-missing", False, f"phases={phases}", "inspect PM observer launch order"
    post = helper.get("post_provider_surface") or {}
    after_cnss_surface = post.get("after_cnss_daemon.begin") == "1" and post.get("after_cnss_daemon.end") == "1"
    if not after_cnss_surface:
        return (
            "v1095-after-cnss-daemon-surface-missing",
            False,
            "CNSS voter query ran but lower-surface snapshot is absent",
            "inspect full helper output before retry",
        )

    per_mgr_fd = parse_int(contract.get("after_cnss_daemon.per_mgr_subsys_modem_count"), -1)
    pm_proxy_helper_fd = parse_int(contract.get("after_cnss_daemon.pm_proxy_helper_subsys_modem_count"), -1)
    mdm3_state = post.get("after_cnss_daemon.mdm3_state", "")
    wlan0_exists = post.get("after_cnss_daemon.wlan0_exists", "")
    wlfw_seen = helper.get("wlfw_service69_seen") is True
    reason = (
        f"phases={phases} per_mgr_fd={per_mgr_fd} "
        f"pm_proxy_helper_fd={pm_proxy_helper_fd} mdm3_state={mdm3_state} "
        f"wlfw_service69_seen={wlfw_seen}"
    )
    if "ONLINE" in mdm3_state or wlan0_exists == "1" or wlfw_seen:
        return (
            "v1095-cnss-voter-lower-progress-observed",
            True,
            reason,
            "classify WLAN-PD/WLFW transition before Wi-Fi HAL or scan/connect",
        )
    if per_mgr_fd > 0 or pm_proxy_helper_fd > 0:
        return (
            "v1095-cnss-voter-pm-fd-progress-with-mdm3-still-offline",
            True,
            reason,
            "combine PM fd-positive contract with bounded eSoC trigger classifier",
        )
    return (
        "v1095-cnss-voter-no-pm-fd-mdm3-still-offline",
        True,
        reason,
        "classify missing CNSS voter request or lower eSoC trigger before Wi-Fi HAL",
    )


def patch_defaults() -> None:
    v1093.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1093.LATEST_POINTER = LATEST_POINTER
    v1093.DEFAULT_LOCAL_HELPER = DEFAULT_LOCAL_HELPER
    v1093.DEFAULT_HELPER_SHA256 = DEFAULT_HELPER_SHA256
    v1093.DEFAULT_HELPER_MARKER = DEFAULT_HELPER_MARKER
    v1093.DEVICE_WORK_DIR = DEVICE_WORK_DIR
    v1093.DEVICE_SCRIPT = DEVICE_SCRIPT
    v1093.DEVICE_OUTPUT = DEVICE_OUTPUT
    v1093.CYCLE_LABEL = "v1095"
    v1093.SUMMARY_HEADING = SUMMARY_HEADING
    v1093.helper_command = helper_command
    v1093.run_helper_script = run_helper_script
    v1093.base.remote_helper_state = remote_helper_state
    v1093.base.post_surface = post_surface
    v1093.decide = decide


if __name__ == "__main__":
    patch_defaults()
    raise SystemExit(v1093.main())
