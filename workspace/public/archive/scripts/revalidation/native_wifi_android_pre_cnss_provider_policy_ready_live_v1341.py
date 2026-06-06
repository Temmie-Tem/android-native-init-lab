#!/usr/bin/env python3
"""V1341 bounded Android-order pre-CNSS provider gate after V490 policy load.

Runs the V1340-selected repair path:

1. mount Android system/vendor read-only surfaces;
2. mount SELinuxfs;
3. refresh current-boot V490 policy-load proof with helper v279;
4. run the Android-order pre-CNSS provider observer with vndservice readiness
   and provider queries added by helper v279.

The gate still forbids Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, manual eSoC open, PMIC/GPIO writes, flash, boot image writes, and
partition writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import native_wifi_android_pre_cnss_provider_observer_live_v1339 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1341-android-pre-cnss-provider-policy-ready-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1341-android-pre-cnss-provider-policy-ready-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe_v279")
DEFAULT_HELPER_SHA256 = "2ec7c9584e0adb09755e1066ee01a986e3b7fd719c11b8a96aaf5c500d9dd15a"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v279"
DEFAULT_TOYBOX_TIMEOUT_SEC = 70
DEFAULT_HELPER_TIMEOUT_SEC = 30
DEFAULT_V490_OUT_DIR = Path("tmp/wifi/v1341-v490-policy-load")
MODE = base.MODE
EXPECTED_ORDER = (
    "servicemanager,hwservicemanager,vndservicemanager,vndservice_ready_query,"
    "per_proxy_helper,qrtr_ns,rmt_storage,tftp_server,pd_mapper,per_mgr,"
    "vndservice_query,per_proxy,vndservice_query,mdm_helper,cnss_diag,cnss_daemon"
)
V490_APPROVAL = (
    "approve v490 native SELinux policy-load proof only; "
    "no init reexec, no daemon start and no Wi-Fi bring-up"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v490-out-dir", type=Path, default=DEFAULT_V490_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=base.v857.DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=base.v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=base.v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--helper-timeout-sec", type=int, default=DEFAULT_HELPER_TIMEOUT_SEC)
    parser.add_argument("--toybox-timeout-sec", type=int, default=DEFAULT_TOYBOX_TIMEOUT_SEC)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-policy-load", action="store_true")
    parser.add_argument("--allow-android-pre-cnss-provider-observe-only", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    missing = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-policy-load", args.allow_policy_load),
        (
            "--allow-android-pre-cnss-provider-observe-only",
            args.allow_android_pre_cnss_provider_observe_only,
        ),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def helper_command(args: argparse.Namespace) -> list[str]:
    command = base.helper_command(args)
    command[command.index("--timeout-sec") + 1] = str(min(max(args.helper_timeout_sec, 10), 30))
    return command


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    return base.local_helper_info(args)


def read_step_file(store: EvidenceStore, step: dict[str, Any]) -> str:
    return base.read_step_file(store, step)


def run_v490_policy_load(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    out_dir = repo_path(args.v490_out_dir)
    command = [
        "python3",
        "scripts/revalidation/native_selinux_policy_load_proof_v490.py",
        "--out-dir",
        str(args.v490_out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        "A90 Linux init 0.9.68 (v724)",
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--toybox",
        args.toybox,
        "--approval-phrase",
        V490_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=220,
    )
    duration = time.monotonic() - started
    output = base.v857.redact(result.stdout)
    store.write_text("host/v490-policy-load.txt", output.rstrip() + "\n")
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "name": "v490-policy-load",
        "command": command,
        "rc": result.returncode,
        "ok": result.returncode == 0 and manifest.get("decision") == "v490-selinux-policy-load-proof-pass",
        "status": "ok" if result.returncode == 0 else "failed",
        "duration_sec": round(duration, 3),
        "file": "host/v490-policy-load.txt",
        "manifest": str(args.v490_out_dir / "manifest.json"),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "policy_load_executed": manifest.get("policy_load_executed"),
        "wifi_bringup_executed": manifest.get("wifi_bringup_executed"),
    }


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    base.v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    base.v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    if args.allow_mountsystem_ro:
        base.v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    if args.allow_selinuxfs_mount:
        base.mount_selinuxfs(args, store, steps)
    analysis["remote_helper"] = base.remote_helper_state(args, store, steps)
    analysis["v490_policy_load"] = run_v490_policy_load(args, store)
    analysis["pre_surface"] = base.post_surface(args, store, steps, "pre")
    helper_step = base.v857.run_device(
        args,
        store,
        steps,
        "android-pre-cnss-provider-policy-ready",
        helper_command(args),
        timeout=args.toybox_timeout_sec + 35.0,
    )
    helper_text = read_step_file(store, helper_step)
    analysis["helper"] = base.helper_surface(helper_text)
    analysis["post_surface"] = base.post_surface(args, store, steps, "post")
    base.v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    base.v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)

    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("all_postflight_safe") == "0"
        or bool([line for line in post.get("actor_hits", []) if "a90_android_execns_probe" in line])
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = base.reboot_cleanup(args, store, "V1341 provider-ready actor not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "cleanup needed but --allow-cleanup-reboot not set", "healthy": False}
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def step_failures(steps: list[dict[str, Any]], helper: dict[str, Any]) -> list[str]:
    contract = helper.get("contract") or {}
    helper_has_evidence = contract.get("begin") == "1"
    ignored = {"remote-helper-usage"}
    if helper_has_evidence:
        ignored.add("android-pre-cnss-provider-policy-ready")
    return [step["name"] for step in steps if not step.get("ok") and step.get("name") not in ignored]


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1341-plan-helper-v279-missing", False, f"local={local}", "build and deploy helper v279 before V1341"
        return "v1341-policy-ready-provider-plan-ready", True, "plan-only; no device command executed", "run bounded V1341 live observer"
    missing = required_flags(args)
    if missing:
        return "v1341-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1341 flags"
    helper = analysis.get("helper") or {}
    failed_steps = step_failures(steps, helper)
    if failed_steps:
        return "v1341-step-failed", False, f"failed_steps={failed_steps}", "inspect V1341 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1341-helper-v279-remote-mismatch", False, f"remote={remote}", "redeploy helper v279 before V1341"
    policy = analysis.get("v490_policy_load") or {}
    if not policy.get("ok"):
        return "v1341-policy-load-failed", False, f"policy={policy}", "repair V490 current-boot policy load before V1341"
    if helper.get("forbidden_true"):
        return "v1341-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    if helper.get("forbidden_terms"):
        return "v1341-forbidden-term-detected", False, f"terms={helper.get('forbidden_terms')}", "stop and audit helper output before retry"
    contract = helper.get("contract") or {}
    keys = helper.get("keys") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1341-helper-mode-not-executed", False, f"contract={contract}", "fix V1341 helper command before retry"
    if contract.get("order") != EXPECTED_ORDER or contract.get("android_pre_cnss_provider_observe_only") != "1":
        return "v1341-helper-contract-gap", False, f"contract={contract}", "audit helper v279 V1341 mode wiring"
    if contract.get("manual_subsys_esoc0_open") != "0":
        return "v1341-manual-esoc-open-violation", False, f"contract={contract}", "stop and audit helper before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1341-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify native recovery before continuing"

    provider_after_mgr = keys.get("wifi_companion_start.android_pre_cnss_provider.per_mgr.provider_seen") == "1"
    provider_after_proxy = keys.get("wifi_companion_start.android_pre_cnss_provider.per_proxy.provider_seen") == "1"
    per_mgr_domain = keys.get("wifi_hal_composite_child.per_mgr.selinux_current.after", "")
    per_proxy_domain = keys.get("wifi_hal_composite_child.per_proxy.selinux_current.after", "")
    auto_open = contract.get("per_mgr_subsys_esoc0_window") not in ("", "-1", "0")
    ks_seen = contract.get("ks_window") not in ("", "-1", "0") or contract.get("mhi_cmdline_window") not in ("", "-1", "0")
    post = analysis.get("post_surface") or {}
    wlfw_seen = bool(post.get("qrtr_wlfw_hits")) or any(
        re.search(r"wlfw|bdf|wlan0|fw ready", line, re.IGNORECASE)
        for line in post.get("dmesg_focus_hits", [])
    )
    if wlfw_seen:
        return (
            "v1341-wlfw-surface-observed-after-policy-provider-gate",
            True,
            f"contract={contract}",
            "classify WLFW/BDF/wlan0 surface before any Wi-Fi HAL or scan work",
        )
    if auto_open or ks_seen:
        return (
            "v1341-provider-gate-advanced-to-esoc-or-ks-no-wlfw",
            True,
            f"provider_mgr={provider_after_mgr} provider_proxy={provider_after_proxy} auto_open={auto_open} ks_seen={ks_seen}",
            "classify why eSoC/ks path did not publish WLFW",
        )
    if provider_after_mgr or provider_after_proxy:
        return (
            "v1341-provider-positive-no-lower-transition",
            True,
            f"provider_mgr={provider_after_mgr} provider_proxy={provider_after_proxy} domains={per_mgr_domain}/{per_proxy_domain}",
            "next gate should preserve provider-positive setup and classify PM request/actionability toward subsys_esoc0",
        )
    return (
        "v1341-provider-still-not-registered-after-policy-ready",
        True,
        f"provider_mgr={provider_after_mgr} provider_proxy={provider_after_proxy} domains={per_mgr_domain}/{per_proxy_domain}",
        "inspect vndservice query stdout/stderr and PM child domains before another lower retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    steps = manifest.get("steps", [])
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in steps]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)[:2000]] for key, value in (manifest.get("analysis") or {}).items()]
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    keys = helper.get("keys") or {}
    provider_rows = [
        ["v490", (manifest.get("analysis") or {}).get("v490_policy_load", {}).get("decision", "")],
        ["vnd_ready_query", keys.get("wifi_vndservice_query.android_pre_cnss_provider_vndservicemanager_ready.result", "")],
        ["provider_after_per_mgr", keys.get("wifi_companion_start.android_pre_cnss_provider.per_mgr.provider_seen", "")],
        ["provider_after_per_proxy", keys.get("wifi_companion_start.android_pre_cnss_provider.per_proxy.provider_seen", "")],
        ["per_mgr_domain", keys.get("wifi_hal_composite_child.per_mgr.selinux_current.after", "")],
        ["per_proxy_domain", keys.get("wifi_hal_composite_child.per_proxy.selinux_current.after", "")],
        ["helper_result", contract.get("result", "")],
    ]
    return "\n".join([
        "# V1341 Android-order Pre-CNSS Provider Policy-ready Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- mode: `{MODE}`",
        f"- manual_esoc_open_executed: `{manifest['manual_esoc_open_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        "",
        "## Provider Gate",
        "",
        markdown_table(["item", "value"], provider_rows),
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- V490 policy load is the only global mutation; it performs no init reexec, daemon start, or Wi-Fi bring-up.",
        "- The V1341 helper starts only the bounded pre-CNSS provider/CNSS observer chain.",
        "- No manual `/dev/subsys_esoc0` open, eSoC ioctl/notify/BOOT_DONE, PMIC/GPIO write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args):
        steps, analysis = execute(args, store)
    decision, passed, reason, next_step = decide(args, local, steps, analysis)
    helper = (analysis.get("helper") or {}).get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    wifi_hal_started = str(helper.get("wifi_hal") or "0") != "0"
    scan_connect_started = str(helper.get("scan_connect_linkup") or "0") == "1"
    external_ping_started = str(helper.get("external_ping") or "0") == "1"
    policy = analysis.get("v490_policy_load") or {}
    return {
        "cycle": "v1341",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "local_helper": local,
        "steps": steps,
        "analysis": analysis,
        "device_commands_executed": args.command == "run" and not required_flags(args),
        "deploy_executed": False,
        "policy_load_executed": policy.get("policy_load_executed") is True,
        "manual_esoc_open_executed": helper.get("manual_subsys_esoc0_open") == "1",
        "live_esoc_ioctl_executed": False,
        "pm_actor_executed": args.command == "run" and not required_flags(args),
        "cnss_daemon_start_executed": helper.get("child_started", "0") not in ("", "0"),
        "wifi_hal_start_executed": wifi_hal_started,
        "scan_connect_executed": scan_connect_started,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": external_ping_started,
        "wifi_bringup_executed": any((wifi_hal_started, scan_connect_started, external_ping_started)),
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "flash_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"policy_load_executed: {manifest['policy_load_executed']}")
    print(f"manual_esoc_open_executed: {manifest['manual_esoc_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"cleanup_reboot_executed: {manifest['cleanup_reboot_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
