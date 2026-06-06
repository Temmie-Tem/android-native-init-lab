#!/usr/bin/env python3
"""V466 raw hwbinder IWifi.start surface runner.

This runner starts only the private service-manager/HAL/CNSS trio, issues one
bounded raw hwbinder `android.hardware.wifi@1.0::IWifi/default.start()` call,
and snapshots native WLAN surfaces. It does not read credentials, scan,
connect, request DHCP, change routes, or send external packets.
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_surface_composite_v464 as v464


base = v464.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v466-raw-hwbinder-iwifi-start-surface")
base.DEFAULT_HELPER_SHA256 = "29ce77fa7215287b3f3948fe19a3667330df52156d2fa8750220fb971d5fb685"
base.DEFAULT_V404 = Path("tmp/wifi/v465-iwifi-start-contract-refresh-20260520-235400/manifest.json")
base.HELPER_LABEL = "v32"
base.APPROVAL_PHRASE = (
    "approve v466 raw hwbinder IWifi.start surface proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

IWIFI_KEY_RE = re.compile(r"^iwifi_start\.([A-Za-z0-9_.]+)=(.*)$")
SURFACE_KEY_RE = re.compile(
    r"^wifi_surface_composite\.(before|after_iwifi_start|during|after_cleanup)\.([A-Za-z0-9_]+)=(.*)$"
)
_BASE_PARSE_ARGS = base.parse_args
_V464_BUILD_PLAN = base.build_plan


def parse_args() -> base.argparse.Namespace:
    args = _BASE_PARSE_ARGS()
    if "--target-profile" not in sys.argv:
        args.target_profile = "vendor-wifi-hal-legacy"
    return args


def build_helper_argv(args: base.argparse.Namespace, *, include_data_wifi: bool = False) -> list[str]:
    del include_data_wifi
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-iwifi-start-surface",
        "--target-profile",
        args.target_profile,
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        args.property_root,
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]
    if base.approved(args):
        argv.extend([
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-cnss-start-only",
            "--allow-iwifi-start-only",
        ])
    return argv


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _V464_BUILD_PLAN(args)
    plan["helper_mode"] = "wifi-iwifi-start-surface"
    plan["target_profile_default"] = "vendor-wifi-hal-legacy"
    plan["raw_hwbinder_contract"] = {
        "service_manager": "android.hidl.manager@1.0::IServiceManager/manager",
        "get_code": 1,
        "get_args": ["android.hardware.wifi@1.0::IWifi", "default"],
        "iwifi_start_code": 3,
    }
    plan["surface_attempt"] = {
        "starts": ["servicemanager", "hwservicemanager", "android.hardware.wifi@1.0-service", "cnss-daemon -n -l"],
        "calls": ["IServiceManager.get(IWifi/default)", "IWifi.start() once if handle is non-null"],
        "observes": ["wlan* netdev", "phy* wiphy", "/proc/net/wireless", "Wi-Fi rfkill"],
        "blocks": ["credentials", "scan/connect", "DHCP", "route changes", "external ping"],
    }
    return plan


def build_checks(args: base.argparse.Namespace, store: base.EvidenceStore, steps: list[base.Step],
                 v465: dict[str, Any]) -> list[base.Check]:
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight after helper v32 deploy")
        return checks

    version = base.step_text(store, steps, "version")
    status = base.step_text(store, steps, "status")
    selftest = base.step_text(store, steps, "selftest")
    helper_sha = base.step_text(store, steps, "sha-helper")
    helper_usage = base.step_text(store, steps, "helper-usage")
    ps = base.step_text(store, steps, "ps")
    netdev = base.step_text(store, steps, "proc-net-dev")
    mounts = base.step_text(store, steps, "proc-mounts")
    processes = [line.strip() for line in ps.splitlines() if base.SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if base.WIFI_RE.search(line)]
    selinuxfs_mounted = "/sys/fs/selinux" in mounts and " selinuxfs " in mounts
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v32" in helper_usage
        and "wifi-iwifi-start-surface" in helper_usage
        and "--allow-iwifi-start-only" in helper_usage
    )

    base.add_check(checks, "v465-contract-ready", "pass" if v465.get("decision") == "v465-iwifi-start-contract-ready-raw-hwbinder-next" and v465.get("pass") else "warn", "warning", f"decision={v465.get('decision')} pass={v465.get('pass')}", [str(v465.get("path", ""))], "refresh V465 if missing; V466 still has its own guards")
    base.add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    base.add_check(checks, "native-clean", "pass" if base.step_ok(steps, "status") and base.step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before live run")
    base.add_check(checks, "helper-v32", "pass" if helper_ready else "blocked", "blocker", "remote helper must be v32 with raw hwbinder IWifi mode", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v32 before V466 live run")
    base.add_check(checks, "selinuxfs-runtime-surface", "pass" if base.step_ok(steps, "stat-selinux-status") and selinuxfs_mounted else "blocked", "blocker", f"mounted={selinuxfs_mounted} status={base.step_ok(steps, 'stat-selinux-status')}", [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3], "mount selinuxfs runtime surface before V466")
    base.add_check(checks, "runtime-materials", "pass" if base.step_ok(steps, "stat-real-ld-config") and base.step_ok(steps, "stat-real-apex-libraries") and base.step_ok(steps, "stat-property-root") else "blocked", "blocker", f"ld={base.step_ok(steps, 'stat-real-ld-config')} apex={base.step_ok(steps, 'stat-real-apex-libraries')} property={base.step_ok(steps, 'stat-property-root')}", [], "restore private runtime materialization inputs")
    base.add_check(checks, "system-ext-vndk-v30", "pass" if base.step_ok(steps, "stat-system-ext-vndk-v30") and base.step_ok(steps, "stat-system-ext-wifi-1-0") else "blocked", "blocker", "system_ext VNDK v30 and android.hardware.wifi@1.0.so must exist", [], "restore system_ext VNDK v30 source")
    base.add_check(checks, "service-manager-binaries", "pass" if base.step_ok(steps, "stat-servicemanager") and base.step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={base.step_ok(steps, 'stat-servicemanager')} hwservicemanager={base.step_ok(steps, 'stat-hwservicemanager')}", [], "core managers must be visible")
    base.add_check(checks, "vendor-block-source", "pass" if base.step_ok(steps, "stat-vendor-block") or base.step_ok(steps, "stat-vendor-block-sysfs") else "blocked", "blocker", f"devnode={base.step_ok(steps, 'stat-vendor-block')} sysfs={base.step_ok(steps, 'stat-vendor-block-sysfs')}", [], "helper needs vendor source for private mount")
    base.add_check(checks, "process-surface-clean", "pass" if not processes else "blocked", "blocker", f"process_count={len(processes)}", processes[:8], "do not run over existing manager/HAL/CNSS processes")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if base.approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == base.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [base.APPROVAL_PHRASE], "exact phrase and flags required before raw hwbinder IWifi.start")
    return checks


def parse_iwifi_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = IWIFI_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def parse_surface_keys(text: str) -> dict[str, dict[str, str]]:
    snapshots: dict[str, dict[str, str]] = {"before": {}, "after_iwifi_start": {}, "during": {}, "after_cleanup": {}}
    for raw_line in text.splitlines():
        match = SURFACE_KEY_RE.match(raw_line.strip())
        if match:
            snapshots[match.group(1)][match.group(2)] = match.group(3).strip()
    return snapshots


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    command = base.build_native_run_command(args)
    record = base.run_capture(args, "run-iwifi-start-surface", command, timeout=args.timeout + args.max_runtime_sec + 45.0)
    rel = "native/run-iwifi-start-surface.txt"
    store.write_text(rel, base.strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    composite_keys = base.parse_composite_keys(text)
    iwifi_keys = parse_iwifi_keys(text)
    surface = parse_surface_keys(text)
    return {
        "capture": base.capture_to_manifest(record),
        "file": rel,
        "keys": composite_keys,
        "iwifi": iwifi_keys,
        "surface": surface,
        "surface_present_after_iwifi_start": v464.surface_present(surface["after_iwifi_start"]),
        "surface_present_during": v464.surface_present(surface["during"]),
        "surface_present_after_cleanup": v464.surface_present(surface["after_cleanup"]),
        "helper_result": composite_keys.get("result", "missing"),
        "helper_reason": composite_keys.get("reason", ""),
        "iwifi_result": iwifi_keys.get("result", "missing"),
        "iwifi_transaction_executed": iwifi_keys.get("transaction_executed") == "1",
        "iwifi_start_ok": iwifi_keys.get("start_transaction_ok") == "1",
        "timed_out": composite_keys.get("timed_out") == "1",
        "all_postflight_safe": composite_keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": composite_keys.get("all_observable_at_timeout") == "1",
    }


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v466-raw-hwbinder-iwifi-start-plan-ready", True, "plan-only; no device command executed", "deploy helper v32 and run preflight", False
    blocked = base.blockers(checks)
    if blocked:
        return "v466-raw-hwbinder-iwifi-start-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before raw hwbinder IWifi.start", False
    if args.command == "preflight":
        return "v466-raw-hwbinder-iwifi-start-preflight-ready", True, "read-only preflight is ready; live run still needs exact approval", "run approved V466 IWifi.start surface proof", False
    if not base.approved(args):
        return "v466-raw-hwbinder-iwifi-start-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "v466-raw-hwbinder-iwifi-start-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    if live_result.get("surface_present_after_cleanup"):
        return "v466-raw-hwbinder-iwifi-start-surface-leaked", False, "WLAN surface remained after cleanup", "inspect device state before any further Wi-Fi work", True
    if live_result.get("iwifi_result") == "service-null" and post.get("clean"):
        return "v466-raw-hwbinder-iwifi-start-service-null", True, "IWifi/default handle was not returned while bounded process cleanup was clean", "route to service registration or Android-side HAL mapping", True
    if live_result.get("iwifi_transaction_executed") and not live_result.get("iwifi_start_ok") and post.get("clean"):
        return "v466-raw-hwbinder-iwifi-start-transaction-failed", True, "IWifi.start transaction executed but reply was not clean; cleanup passed", "inspect raw hwbinder transcript and HAL stderr", True
    if live_result.get("iwifi_start_ok") and (live_result.get("surface_present_after_iwifi_start") or live_result.get("surface_present_during")) and post.get("clean"):
        return "v466-raw-hwbinder-iwifi-start-surface-observed-cleaned", True, "IWifi.start created a WLAN surface and cleanup was clean", "advance to native scan-only gate; keep credentials blocked", True
    if live_result.get("iwifi_start_ok") and post.get("clean"):
        return "v466-raw-hwbinder-iwifi-start-no-surface-delta", True, "IWifi.start transaction returned cleanly but no WLAN surface appeared", "route to driver/CNSS mode-set primitive before scan/connect", True
    return "v466-raw-hwbinder-iwifi-start-review-required", False, f"helper_result={live_result.get('helper_result')} iwifi_result={live_result.get('iwifi_result')}", "inspect helper output before widening scope", True


def refusal_manifest(args: base.argparse.Namespace, v465: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v466-raw-hwbinder-iwifi-start-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no live command executed",
        "next_step": "rerun with exact approval only after helper v32 deploy and preflight",
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "plan": build_plan(args),
        "steps": [],
        "checks": [asdict(base.Check("approval-gate", "needs-operator", "approval", base.APPROVAL_PHRASE, [base.APPROVAL_PHRASE], "approve before raw hwbinder IWifi.start"))],
        "live_result": None,
        "postflight": None,
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "cnss_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_bringup_executed": False,
    }


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    v465 = base.load_json(args.v404_manifest)
    if args.command == "run" and not base.approved(args):
        return refusal_manifest(args, v465)
    steps: list[base.Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.run_preflight(args, store)
    checks = build_checks(args, store, steps, v465)
    if args.command == "run" and base.approved(args) and not base.blockers(checks):
        live_result = run_live(args, store)
        post = base.postflight(args, store)
    decision, pass_ok, reason, next_step, daemon_started = decide(args, checks, live_result, post)
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "plan": build_plan(args),
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "live_result": live_result,
        "postflight": post,
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" and (args.command != "run" or base.approved(args)),
        "device_mutations": daemon_started,
        "daemon_start_executed": daemon_started,
        "wifi_hal_start_executed": daemon_started,
        "cnss_start_executed": daemon_started,
        "iwifi_start_executed": bool((live_result or {}).get("iwifi_transaction_executed")),
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "wificond, supplicant, or hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], "<br>".join(c["evidence"]), c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    surface_rows: list[list[str]] = []
    live = manifest.get("live_result") or {}
    for phase, fields in (live.get("surface") or {}).items():
        surface_rows.append([
            phase,
            str(fields.get("wlan_count", "0")),
            str(fields.get("phy_count", "0")),
            str(fields.get("proc_wireless_count", "0")),
            str(fields.get("wifi_rfkill_count", "0")),
            str(fields.get("wlan_names", "")),
            str(fields.get("phy_names", "")),
        ])
    iwifi_rows = [[key, value] for key, value in sorted((live.get("iwifi") or {}).items())]
    return "\n".join([
        "# V466 Raw hwbinder IWifi.start Surface",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- cnss_start_executed: `{manifest['cnss_start_executed']}`",
        f"- iwifi_start_executed: `{manifest['iwifi_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- credentials_read: `{manifest['credentials_read']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        base.markdown_table(["name", "status", "severity", "detail", "evidence", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        base.markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## IWifi Keys",
        "",
        base.markdown_table(["key", "value"], iwifi_rows) if iwifi_rows else "- none",
        "",
        "## Surface Snapshots",
        "",
        base.markdown_table(["phase", "wlan", "phy", "wireless", "wifi-rfkill", "wlan-names", "phy-names"], surface_rows) if surface_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Command",
        "",
        "`" + " ".join(manifest["plan"]["command"]) + "`",
        "",
    ]) + "\n"


base.parse_args = parse_args
base.build_helper_argv = build_helper_argv
base.build_plan = build_plan
base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.refusal_manifest = refusal_manifest
base.build_manifest = build_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
