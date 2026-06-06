#!/usr/bin/env python3
"""V1094 PM observer per-proxy post-provider lower-surface live gate."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_pm_post_provider_surface_live_v1093 as v1093


DEFAULT_OUT_DIR = Path("tmp/wifi/v1094-pm-per-proxy-surface-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1094-pm-per-proxy-surface-live.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1094-execns-helper-v205-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "0b93ada5ceaf868cd907d3ad2fcd5986485024fa05bdfe3780daee945984af0f"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v205"
DEVICE_WORK_DIR = "/cache/a90-runtime/v1094"
DEVICE_SCRIPT = f"{DEVICE_WORK_DIR}/pm-per-proxy-surface.sh"
DEVICE_OUTPUT = f"{DEVICE_WORK_DIR}/pm-per-proxy-surface-output.txt"
SUMMARY_HEADING = "# V1094 PM Observer Per-Proxy Surface Live"

original_helper_command = v1093.helper_command
def parse_int(value: str | None, fallback: int = 0) -> int:
    try:
        return int(value or "")
    except ValueError:
        return fallback


def helper_command(args: argparse.Namespace) -> list[str]:
    command = original_helper_command(args)
    command.append("--pm-observer-continue-after-provider")
    return command


def run_helper_script(args: argparse.Namespace,
                      store: v1093.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    return v1093.base.run_a90ctl(
        args,
        store,
        steps,
        "pm-per-proxy-surface-script",
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
                f"{args.busybox} tail -40"
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
        "actor_hits": actor_lines[:20],
        "pm_actor_hits": [
            line
            for line in actor_lines
            if "pm_proxy_helper" in line or "pm-service" in line or "pm-proxy" in line
        ][:12],
        "forbidden_actor_hits": [
            line
            for line in actor_lines
            if "mdm_helper" in line or "cnss" in line or "wificond" in line or "wifi@" in line
        ][:12],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if v1093.base.WIFI_RE.search(line)][:16],
        "helper_process_hits": [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line][:16],
        "subsys_state_tail": subsys_text.splitlines()[-32:],
        "wlfw_or_wlan_dmesg_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if v1093.base.re.search(r"wlfw|wlan0|bdf|qcwlan|icnss|cnss", line, v1093.base.re.IGNORECASE)
        ][-40:],
    }


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1094-plan-helper-v205-missing", False, f"local={local}", "build/deploy helper v205 before V1094"
        return "v1094-pm-per-proxy-surface-plan-ready", True, "plan-only; no device command executed", "run bounded V1094 observer live gate"
    missing = v1093.base.required_flags(args)
    if missing:
        return "v1094-pm-per-proxy-surface-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1094 flags"
    helper = analysis.get("helper") or {}
    failed_steps = v1093.base.step_failures(steps, helper)
    if failed_steps:
        return "v1094-step-failed", False, f"failed_steps={failed_steps}", "inspect V1094 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1094-helper-v205-remote-mismatch", False, f"remote={remote}", "redeploy helper v205 before V1094"
    if helper.get("forbidden_true") or helper.get("post_provider_forbidden_true"):
        return (
            "v1094-forbidden-action-detected",
            False,
            f"forbidden={helper.get('forbidden_true')} post={helper.get('post_provider_forbidden_true')}",
            "stop and audit helper before retry",
        )
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1094-helper-mode-not-executed", False, f"contract={contract}", "fix V1094 helper command before retry"
    if contract.get("continue_after_provider") != "1":
        return "v1094-continue-after-provider-not-enabled", False, "helper did not receive continue flag", "fix V1094 helper command"
    if contract.get("vndservicemanager_readiness.ready") != "1":
        return (
            "v1094-vndservicemanager-readiness-gap",
            True,
            f"checked={contract.get('vndservicemanager_readiness.checked')} ready={contract.get('vndservicemanager_readiness.ready')}",
            "repair service-manager readiness before retrying PM per-proxy gate",
        )
    query = helper.get("vndservice_query") or {}
    phases = v1093.required_query_phases(query)
    if not phases["after_per_mgr"]:
        return "v1094-after-per-mgr-query-missing", False, f"phases={phases}", "inspect PM observer launch order"
    if not phases["after_per_proxy"]:
        return (
            "v1094-after-per-proxy-query-missing",
            False,
            f"phases={phases} result={contract.get('result')}",
            "inspect per_proxy lifecycle and observer continuation",
        )
    post = helper.get("post_provider_surface") or {}
    after_proxy_surface = post.get("after_per_proxy.begin") == "1" and post.get("after_per_proxy.end") == "1"
    if not after_proxy_surface:
        return (
            "v1094-after-per-proxy-surface-missing",
            False,
            "per_proxy query ran but lower-surface snapshot is absent",
            "inspect full helper output before retry",
        )

    per_mgr_fd = parse_int(contract.get("after_per_proxy.per_mgr_subsys_modem_count"), -1)
    pm_proxy_helper_fd = parse_int(contract.get("after_per_proxy.pm_proxy_helper_subsys_modem_count"), -1)
    mdm3_state = post.get("after_per_proxy.mdm3_state", "")
    wlan0_exists = post.get("after_per_proxy.wlan0_exists", "")
    wlfw_seen = helper.get("wlfw_service69_seen") is True
    reason = (
        f"phases={phases} per_mgr_fd={per_mgr_fd} "
        f"pm_proxy_helper_fd={pm_proxy_helper_fd} mdm3_state={mdm3_state} "
        f"wlfw_service69_seen={wlfw_seen}"
    )
    if "ONLINE" in mdm3_state or wlan0_exists == "1" or wlfw_seen:
        return (
            "v1094-per-proxy-lower-surface-progress-observed",
            True,
            reason,
            "classify WLAN-PD/WLFW transition before Wi-Fi HAL or scan/connect",
        )
    if per_mgr_fd > 0 or pm_proxy_helper_fd > 0:
        return (
            "v1094-per-proxy-pm-fd-progress-with-mdm3-still-offline",
            True,
            reason,
            "combine PM fd-positive contract with lower eSoC trigger classifier",
        )
    return (
        "v1094-per-proxy-no-pm-fd-mdm3-still-offline",
        True,
        reason,
        "classify missing PM client/voter trigger before raw eSoC retry",
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
    v1093.CYCLE_LABEL = "v1094"
    v1093.SUMMARY_HEADING = SUMMARY_HEADING
    v1093.helper_command = helper_command
    v1093.run_helper_script = run_helper_script
    v1093.base.remote_helper_state = remote_helper_state
    v1093.base.post_surface = post_surface
    v1093.decide = decide


if __name__ == "__main__":
    patch_defaults()
    raise SystemExit(v1093.main())
