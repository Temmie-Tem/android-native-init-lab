#!/usr/bin/env python3
"""V1093 PM observer post-provider lower-surface live gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
from pathlib import Path
from typing import Any

import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1093-pm-post-provider-surface-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1093-pm-post-provider-surface-live.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1093-execns-helper-v203-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "3b8d0bd04cf0c4519d907833acdd8aac88c2db61f388872342ee35a91de5b594"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v203"
DEVICE_WORK_DIR = "/cache/a90-runtime/v1093"
DEVICE_SCRIPT = f"{DEVICE_WORK_DIR}/pm-post-provider-surface.sh"
DEVICE_OUTPUT = f"{DEVICE_WORK_DIR}/pm-post-provider-surface-output.txt"
QRTR_READBACK_MATRIX = "wlfw:69:0,1;serv74:74:0,1;serv180:180:0,1"
CYCLE_LABEL = "v1093"
SUMMARY_HEADING = "# V1093 PM Observer Post-Provider Surface Live"
original_helper_surface = base.helper_surface


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_base_defaults() -> None:
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_LOCAL_HELPER = DEFAULT_LOCAL_HELPER
    base.DEFAULT_HELPER_SHA256 = DEFAULT_HELPER_SHA256
    base.DEFAULT_HELPER_MARKER = DEFAULT_HELPER_MARKER
    base.LATEST_POINTER = LATEST_POINTER
    base.helper_surface = helper_surface
    base.execute = execute
    base.decide = decide


def parse_int(value: str | None, fallback: int = 0) -> int:
    try:
        return int(value or "")
    except ValueError:
        return fallback


def collect_prefixed(keys: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def readback_service69_seen(readback: dict[str, str]) -> bool:
    if any(".readback.event." in key and key.endswith(".service") and value == "69"
           for key, value in readback.items()):
        return True
    for key, value in readback.items():
        if not key.endswith(".readback.service_events") or parse_int(value) <= 0:
            continue
        case_prefix = key.removesuffix(".readback.service_events")
        if readback.get(f"{case_prefix}.label") == "wlfw":
            return True
    return False


def helper_surface(text: str) -> dict[str, Any]:
    surface = original_helper_surface(text)
    keys = base.parse_keys(text)
    query = {
        key: value
        for key, value in keys.items()
        if key.startswith("wifi_vndservice_query.")
    }
    query_results = {
        key: value
        for key, value in query.items()
        if key.endswith(".result")
    }
    provider_seen = any(
        key.endswith(".vendor_qcom_peripheral_manager_seen") and value == "1"
        for key, value in query.items()
    )
    query_executed = any(key.endswith(".exec_attempted") and value == "1" for key, value in query.items())
    post_provider = collect_prefixed(
        keys,
        "pm_service_trigger_observer.post_provider_surface.",
    )
    qrtr_readback = collect_prefixed(keys, "wifi_companion_qrtr_readback.")
    post_provider_forbidden = {
        key: value
        for key, value in post_provider.items()
        if key.endswith((
            "wifi_hal_start_executed",
            "scan_connect_linkup",
            "external_ping",
            "subsys_esoc0_open_attempted",
        )) and value not in ("0", "False", "false", "")
    }
    surface["vndservice_query"] = query
    surface["vndservice_query_results"] = query_results
    surface["vndservice_provider_seen"] = provider_seen
    surface["vndservice_query_executed"] = query_executed
    surface["post_provider_surface"] = post_provider
    surface["post_provider_present"] = (
        post_provider.get("after_provider.begin") == "1" and
        post_provider.get("after_provider.end") == "1"
    )
    surface["post_provider_forbidden_true"] = post_provider_forbidden
    surface["qrtr_readback"] = qrtr_readback
    surface["wlfw_service69_seen"] = readback_service69_seen(qrtr_readback)
    return surface


def required_query_phases(query: dict[str, str]) -> dict[str, bool]:
    return {
        "after_per_mgr": any(
            key.startswith("wifi_vndservice_query.pm_observer_after_per_mgr_probe.") and
            key.endswith(".exec_attempted") and
            value == "1"
            for key, value in query.items()
        ),
        "after_per_proxy": any(
            key.startswith("wifi_vndservice_query.pm_observer_after_per_proxy_probe.") and
            key.endswith(".exec_attempted") and
            value == "1"
            for key, value in query.items()
        ),
    }


def helper_command(args: argparse.Namespace) -> list[str]:
    command = base.helper_command(args)
    command.extend([
        "--allow-qrtr-ns-readback",
        "--qrtr-readback-matrix",
        QRTR_READBACK_MATRIX,
    ])
    return command


def append_device_file(args: argparse.Namespace,
                       store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       path: str,
                       text: str,
                       label: str) -> None:
    base.run_a90ctl(args, store, steps, f"{label}-rm", ["run", args.busybox, "rm", "-f", path], timeout=12.0, allow_error=True)
    for index in range(0, len(text), 1200):
        chunk = text[index:index + 1200]
        base.run_a90ctl(args, store, steps, f"{label}-append-{index // 1200:03d}", ["appendfile", path, chunk], timeout=15.0)
    base.run_a90ctl(args, store, steps, f"{label}-chmod", ["run", args.busybox, "chmod", "755", path], timeout=12.0)


def device_runner_script(args: argparse.Namespace) -> str:
    helper_argv = " ".join(shlex.quote(part) for part in helper_command(args))
    grep_pattern = (
        r"^(A90_EXECNS_(BEGIN|END|STDOUT_END)|"
        r"pm_service_trigger_observer\.|"
        r"wifi_vndservice_query\.|"
        r"wifi_companion_qrtr_readback\.|"
        r"v1093\.)"
    )
    return f"""#!{args.busybox} sh
BB={shlex.quote(args.busybox)}
OUT={shlex.quote(DEVICE_OUTPUT)}
$BB mkdir -p {shlex.quote(DEVICE_WORK_DIR)}
{helper_argv} > "$OUT" 2>&1
rc=$?
$BB grep -E {shlex.quote(grep_pattern)} "$OUT" || true
echo v1093.full_output=$OUT
echo v1093.helper_rc=$rc
exit $rc
"""


def write_device_runner(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    script = device_runner_script(args)
    store.write_text("host/device-runner-script.txt", script)
    base.run_a90ctl(args, store, steps, "v1093-workdir-mkdir", ["run", args.busybox, "mkdir", "-p", DEVICE_WORK_DIR], timeout=12.0)
    append_device_file(args, store, steps, DEVICE_SCRIPT, script, "v1093-runner-script")


def run_helper_script(args: argparse.Namespace,
                      store: EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    return base.run_tcpctl(
        args,
        store,
        steps,
        "pm-post-provider-surface-script",
        [args.busybox, "sh", DEVICE_SCRIPT],
        timeout=args.toybox_timeout_sec + 60.0,
    )


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    base.run_a90ctl(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-netservice-status", ["netservice", "status"], timeout=12.0)
    if args.allow_mountsystem_ro:
        base.run_a90ctl(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    base.run_a90ctl(args, store, steps, "pre-selinuxfs-state", base.selinuxfs_probe_command(args), timeout=12.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "mount-selinuxfs", base.selinuxfs_mount_command(args), timeout=12.0, allow_error=True)
    base.run_a90ctl(args, store, steps, "property-root-stat", ["stat", args.property_root], timeout=12.0, allow_error=True)
    base.run_a90ctl(args, store, steps, "real-ld-config-stat", ["stat", base.DEFAULT_REAL_LD_CONFIG], timeout=12.0, allow_error=True)
    base.run_a90ctl(args, store, steps, "real-apex-libraries-stat", ["stat", base.DEFAULT_REAL_APEX_LIBRARIES], timeout=12.0, allow_error=True)
    analysis["remote_helper"] = base.remote_helper_state(args, store, steps)
    write_device_runner(args, store, steps)
    helper_step = run_helper_script(args, store, steps)
    helper_text = (store.run_dir / helper_step["file"]).read_text(encoding="utf-8", errors="replace")
    analysis["helper"] = helper_surface(helper_text)
    analysis["device_runner"] = {
        "script": DEVICE_SCRIPT,
        "output": DEVICE_OUTPUT,
        "script_file": "host/device-runner-script.txt",
    }
    base.run_a90ctl(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = base.post_surface(args, store, steps)
    if args.allow_selinuxfs_mount:
        analysis["selinuxfs_umount"] = base.run_a90ctl(
            args,
            store,
            steps,
            "umount-selinuxfs",
            base.selinuxfs_umount_command(args),
            timeout=12.0,
            allow_error=True,
        )
    contract = (analysis.get("helper") or {}).get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("result") == "observer-reboot-required"
        or contract.get("all_postflight_safe") == "0"
        or bool(post.get("helper_process_hits"))
        or bool(post.get("pm_actor_hits"))
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = base.reboot_cleanup(args, store, "PM observer actor not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {
            "requested": False,
            "reason": "cleanup needed but --allow-cleanup-reboot not set",
            "healthy": False,
        }
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1093-plan-helper-v203-missing", False, f"local={local}", "build/deploy helper v203 before V1093"
        return "v1093-pm-post-provider-surface-plan-ready", True, "plan-only; no device command executed", "run bounded V1093 observer live gate"
    missing = base.required_flags(args)
    if missing:
        return "v1093-pm-post-provider-surface-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1093 flags"
    helper = analysis.get("helper") or {}
    failed_steps = base.step_failures(steps, helper)
    if failed_steps:
        return "v1093-step-failed", False, f"failed_steps={failed_steps}", "inspect V1093 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1093-helper-v203-remote-mismatch", False, f"remote={remote}", "redeploy helper v203 before V1093"
    if helper.get("forbidden_true"):
        return "v1093-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    if helper.get("post_provider_forbidden_true"):
        return (
            "v1093-post-provider-forbidden-action-detected",
            False,
            f"forbidden={helper.get('post_provider_forbidden_true')}",
            "stop and audit post-provider snapshot before retry",
        )
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1093-helper-mode-not-executed", False, f"contract={contract}", "fix V1093 helper command before retry"
    if contract.get("vndservicemanager_readiness.ready") != "1":
        return (
            "v1093-vndservicemanager-readiness-gap",
            True,
            f"checked={contract.get('vndservicemanager_readiness.checked')} ready={contract.get('vndservicemanager_readiness.ready')}",
            "repair service-manager readiness before retrying PM provider registration",
        )
    query = helper.get("vndservice_query") or {}
    phases = required_query_phases(query)
    if not phases["after_per_mgr"]:
        return (
            "v1093-vndservice-query-not-executed",
            False,
            f"phases={phases}",
            "inspect helper output and PM observer launch order",
        )
    if helper.get("vndservice_provider_seen") and not helper.get("post_provider_present"):
        return (
            "v1093-post-provider-surface-missing",
            False,
            "provider query succeeded but post-provider lower-surface snapshot is absent",
            "inspect helper v203 output path and retry with full-output capture",
        )
    if helper.get("vndservice_provider_seen"):
        post = helper.get("post_provider_surface") or {}
        mdm3_state = post.get("after_provider.mdm3_state", "")
        wlan0_exists = post.get("after_provider.wlan0_exists", "")
        wlfw_seen = helper.get("wlfw_service69_seen") is True
        if "ONLINE" in mdm3_state or wlan0_exists == "1" or wlfw_seen:
            return (
                "v1093-post-provider-lower-surface-progress-observed",
                True,
                f"mdm3_state={mdm3_state} wlan0_exists={wlan0_exists} wlfw_service69_seen={wlfw_seen}",
                "classify WLAN-PD/WLFW transition before Wi-Fi HAL or scan/connect",
            )
        return (
            "v1093-provider-positive-mdm3-still-not-online",
            True,
            f"phases={phases} mdm3_state={mdm3_state} wlfw_service69_seen={wlfw_seen}",
            "resume lower native MDM3/eSoC trigger analysis; PM provider registration is no longer the blocker",
        )
    return (
        "v1093-pm-provider-registration-not-observed",
        True,
        f"phases={phases} result={contract.get('result')}",
        "compare addService failure with SELinux policy-load and vndservicemanager readiness evidence",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    contract = helper.get("contract") or {}
    query = helper.get("vndservice_query") or {}
    post_provider = helper.get("post_provider_surface") or {}
    qrtr_readback = helper.get("qrtr_readback") or {}
    query_rows = [
        [key, value]
        for key, value in sorted(query.items())
        if key.endswith((".result", ".vendor_qcom_peripheral_manager_seen", ".peripheral_seen", ".exec_attempted", ".exit_code", ".signal", ".timed_out"))
    ]
    post_rows = [
        [key, value]
        for key, value in sorted(post_provider.items())
        if key.startswith("after_provider.") or key.startswith("qipcrtr.")
    ]
    qrtr_rows = [
        [key, value]
        for key, value in sorted(qrtr_readback.items())
        if key.endswith((
            "label",
            "service",
            "instance",
            "readback.service_events",
            "readback.empty_events",
            "readback.timeout",
            "result",
            "send_attempted",
        ))
    ]
    step_rows = [[step["name"], step["ok"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    return "\n".join([
        SUMMARY_HEADING,
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: `{manifest['next_step']}`",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- vndservicemanager_ready: `{contract.get('vndservicemanager_readiness.ready', '')}`",
        f"- provider_seen: `{helper.get('vndservice_provider_seen', False)}`",
        f"- post_provider_present: `{helper.get('post_provider_present', False)}`",
        f"- mdm3_state: `{post_provider.get('after_provider.mdm3_state', '')}`",
        f"- wlfw_service69_seen: `{helper.get('wlfw_service69_seen', False)}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Vndservice Query",
        "",
        markdown_table(["key", "value"], query_rows),
        "",
        "## Post-Provider Surface",
        "",
        markdown_table(["key", "value"], post_rows),
        "",
        "## QRTR Readback",
        "",
        markdown_table(["key", "value"], qrtr_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = base.local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not base.required_flags(args):
        steps, analysis = base.execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    post_provider = helper.get("post_provider_surface") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    return {
        "cycle": CYCLE_LABEL,
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "mode": base.DEFAULT_MODE,
        "property_root": args.property_root,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "pm_proxy_helper_start_executed": contract.get("pm_proxy_helper_start_executed") == "1",
        "pm_service_start_executed": contract.get("per_mgr_start_executed") == "1",
        "pm_proxy_start_executed": contract.get("per_proxy_start_executed") == "1",
        "pm_service_subsys_modem_seen": contract.get("per_mgr_subsys_modem_seen") == "1",
        "pm_proxy_helper_subsys_modem_seen": contract.get("pm_proxy_helper_subsys_modem_seen") == "1",
        "vndservicemanager_ready": contract.get("vndservicemanager_readiness.ready") == "1",
        "vndservice_provider_seen": helper.get("vndservice_provider_seen") is True,
        "post_provider_surface_present": helper.get("post_provider_present") is True,
        "post_provider_mdm3_state": post_provider.get("after_provider.mdm3_state", ""),
        "post_provider_wlan0_exists": post_provider.get("after_provider.wlan0_exists", ""),
        "post_provider_wlfw_service69_seen": helper.get("wlfw_service69_seen") is True,
        "mdm_helper_start_executed": contract.get("mdm_helper_start_executed") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_executed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "wifi_hal_start_executed": contract.get("wifi_hal_start_executed") == "1",
        "scan_connect_executed": contract.get("scan_connect_linkup") == "1",
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": contract.get("external_ping") == "1",
        "wifi_bringup_executed": False,
    }


def main() -> int:
    patch_base_defaults()
    args = base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"vndservicemanager_ready: {manifest['vndservicemanager_ready']}")
    print(f"vndservice_provider_seen: {manifest['vndservice_provider_seen']}")
    print(f"post_provider_surface_present: {manifest['post_provider_surface_present']}")
    print(f"post_provider_mdm3_state: {manifest['post_provider_mdm3_state']}")
    print(f"post_provider_wlfw_service69_seen: {manifest['post_provider_wlfw_service69_seen']}")
    print(f"pm_service_subsys_modem_seen: {manifest['pm_service_subsys_modem_seen']}")
    print(f"pm_proxy_helper_subsys_modem_seen: {manifest['pm_proxy_helper_subsys_modem_seen']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
