#!/usr/bin/env python3
"""V464 native WLAN surface composite start-only runner.

This is the first native-init gate that observes Wi-Fi HAL and CNSS together
inside one bounded helper-owned namespace.  It does not read credentials, scan,
connect, request DHCP, change routes, or send external packets.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import wifi_composite_hal_start_only_v405_runner as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v464-native-wlan-surface-composite")
base.DEFAULT_HELPER_SHA256 = "96179d75ee81586cf8f46edb7354eeb8c57569e56a047a2c55e678c794a514e9"
base.DEFAULT_V404 = Path("tmp/wifi/v463-service-order-replay-refresh-v319-20260520-230805/manifest.json")
base.HELPER_LABEL = "v31"
base.APPROVAL_PHRASE = (
    "approve v464 native WLAN surface composite start-only only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
base.SERVICE_PROCESS_RE = re.compile(
    r"\b(servicemanager|hwservicemanager|vndservicemanager|android\.hardware\.wifi|"
    r"vendor\.samsung\.hardware\.wifi|cnss-daemon|cnss_diag)\b",
    re.IGNORECASE,
)
base.READ_ONLY_COMMANDS = base.READ_ONLY_COMMANDS + (
    ("proc-mounts", ["cat", "/proc/mounts"], 10.0),
    ("stat-selinux-status", ["stat", "/sys/fs/selinux/status"], 10.0),
    ("stat-system-ext-vndk-v30", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30"], 10.0),
    ("stat-system-ext-wifi-1-0", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so"], 10.0),
    ("stat-vendor-block", ["stat", "/dev/block/sda29"], 10.0),
    ("stat-vendor-block-sysfs", ["stat", "/sys/class/block/sda29/dev"], 10.0),
    ("stat-cnss-daemon", ["stat", "/mnt/system/vendor/bin/cnss-daemon"], 10.0),
    ("stat-vendor-wifi-hal", ["stat", "/mnt/system/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service"], 10.0),
    ("sys-class-ieee80211", ["run", base.TOYBOX, "ls", "/sys/class/ieee80211"], 10.0),
    ("sys-class-rfkill", ["run", base.TOYBOX, "ls", "/sys/class/rfkill"], 10.0),
    ("proc-net-wireless", ["run", base.TOYBOX, "cat", "/proc/net/wireless"], 10.0),
)

SURFACE_KEY_RE = re.compile(r"^wifi_surface_composite\.(before|during|after_cleanup)\.([A-Za-z0-9_]+)=(.*)$")
_BASE_BUILD_PLAN = base.build_plan


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
        "wifi-surface-composite-start-only",
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
        ])
    return argv


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_mode"] = "wifi-surface-composite-start-only"
    plan["helper_implicit_data_wifi_mode"] = "private-empty"
    plan["surface_attempt"] = {
        "starts": ["servicemanager", "hwservicemanager", "vendor Wi-Fi HAL", "cnss-daemon -n -l"],
        "observes": ["wlan* netdev", "phy* wiphy", "/proc/net/wireless", "Wi-Fi rfkill"],
        "blocks": ["credentials", "scan/connect", "DHCP", "route changes", "external ping"],
    }
    plan["not_approved"] = [
        "wificond/supplicant/hostapd start",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
        "unbounded daemon persistence or boot autostart",
    ]
    return plan


def build_checks(args: base.argparse.Namespace, store: base.EvidenceStore, steps: list[base.Step],
                 v463: dict[str, Any]) -> list[base.Check]:
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight after helper v31 deploy")
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
        and "a90_android_execns_probe v31" in helper_usage
        and "wifi-surface-composite-start-only" in helper_usage
        and "--allow-cnss-start-only" in helper_usage
        and "wifi-hal-composite-start-only" in helper_usage
    )

    base.add_check(
        checks,
        "v463-service-order-gap-mapped",
        "pass" if v463.get("decision") == "wifi-service-order-replay-model-ready" and v463.get("pass") else "warn",
        "warning",
        f"decision={v463.get('decision')} pass={v463.get('pass')}",
        [str(v463.get("path", ""))],
        "refresh V463 model if missing; this runner can still execute its own preflight",
    )
    base.add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    base.add_check(checks, "native-clean", "pass" if base.step_ok(steps, "status") and base.step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before live run")
    base.add_check(checks, "helper-v31", "pass" if helper_ready else "blocked", "blocker", "remote helper must be v31 with surface-composite mode", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v31 before V464 live run")
    base.add_check(checks, "selinuxfs-runtime-surface", "pass" if base.step_ok(steps, "stat-selinux-status") and selinuxfs_mounted else "blocked", "blocker", f"mounted={selinuxfs_mounted} status={base.step_ok(steps, 'stat-selinux-status')}", [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3], "mount selinuxfs runtime surface before V464")
    base.add_check(checks, "runtime-materials", "pass" if base.step_ok(steps, "stat-real-ld-config") and base.step_ok(steps, "stat-real-apex-libraries") and base.step_ok(steps, "stat-property-root") else "blocked", "blocker", f"ld={base.step_ok(steps, 'stat-real-ld-config')} apex={base.step_ok(steps, 'stat-real-apex-libraries')} property={base.step_ok(steps, 'stat-property-root')}", [], "restore private runtime materialization inputs")
    base.add_check(checks, "system-ext-vndk-v30", "pass" if base.step_ok(steps, "stat-system-ext-vndk-v30") and base.step_ok(steps, "stat-system-ext-wifi-1-0") else "blocked", "blocker", "system_ext VNDK v30 and android.hardware.wifi@1.0.so must exist", [], "restore system_ext VNDK v30 source")
    base.add_check(checks, "service-manager-binaries", "pass" if base.step_ok(steps, "stat-servicemanager") and base.step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={base.step_ok(steps, 'stat-servicemanager')} hwservicemanager={base.step_ok(steps, 'stat-hwservicemanager')}", [], "core managers must be visible")
    base.add_check(checks, "vendor-block-source", "pass" if base.step_ok(steps, "stat-vendor-block") or base.step_ok(steps, "stat-vendor-block-sysfs") else "blocked", "blocker", f"devnode={base.step_ok(steps, 'stat-vendor-block')} sysfs={base.step_ok(steps, 'stat-vendor-block-sysfs')}", [], "helper needs either /dev/block/sda29 or /sys/class/block/sda29/dev for private vendor mknod")
    base.add_check(checks, "wifi-runtime-binaries-global-stat", "pass" if base.step_ok(steps, "stat-cnss-daemon") and base.step_ok(steps, "stat-vendor-wifi-hal") else "warn", "warning", f"cnss={base.step_ok(steps, 'stat-cnss-daemon')} hal={base.step_ok(steps, 'stat-vendor-wifi-hal')}", [], "global /mnt/system/vendor is not authoritative; helper private vendor mount is authoritative during live run")
    base.add_check(checks, "process-surface-clean", "pass" if not processes else "blocked", "blocker", f"process_count={len(processes)}", processes[:8], "do not run over existing manager/HAL/CNSS processes")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if base.approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == base.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [base.APPROVAL_PHRASE], "exact phrase and flags required before live surface-composite start-only")
    return checks


def parse_surface_keys(text: str) -> dict[str, dict[str, str]]:
    snapshots: dict[str, dict[str, str]] = {"before": {}, "during": {}, "after_cleanup": {}}
    for raw_line in text.splitlines():
        match = SURFACE_KEY_RE.match(raw_line.strip())
        if match:
            snapshots[match.group(1)][match.group(2)] = match.group(3).strip()
    return snapshots


def surface_count(snapshot: dict[str, str], key: str) -> int:
    try:
        return int(snapshot.get(key, "0"))
    except ValueError:
        return 0


def surface_present(snapshot: dict[str, str]) -> bool:
    return (
        surface_count(snapshot, "wlan_count") > 0
        or surface_count(snapshot, "phy_count") > 0
        or surface_count(snapshot, "proc_wireless_count") > 0
        or surface_count(snapshot, "wifi_rfkill_count") > 0
    )


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    command = base.build_native_run_command(args)
    record = base.run_capture(args, "run-surface-composite", command, timeout=args.timeout + args.max_runtime_sec + 45.0)
    rel = "native/run-surface-composite.txt"
    store.write_text(rel, base.strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    keys = base.parse_composite_keys(text)
    surface = parse_surface_keys(text)
    return {
        "capture": base.capture_to_manifest(record),
        "file": rel,
        "keys": keys,
        "surface": surface,
        "surface_present_during": surface_present(surface["during"]),
        "surface_present_after_cleanup": surface_present(surface["after_cleanup"]),
        "helper_result": keys.get("result", "missing"),
        "helper_reason": keys.get("reason", ""),
        "timed_out": keys.get("timed_out") == "1",
        "all_postflight_safe": keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": keys.get("all_observable_at_timeout") == "1",
        "child_started": keys.get("child_started", ""),
        "cnss_daemon_requested": keys.get("cnss_daemon") == "1",
    }


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v464-native-wlan-surface-plan-ready", True, "plan-only; no device command executed", "run preflight after helper v31 deploy", False
    blocked = base.blockers(checks)
    if blocked:
        return "v464-native-wlan-surface-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before live surface-composite run", False
    if args.command == "preflight":
        return "v464-native-wlan-surface-preflight-ready", True, "read-only preflight is ready; live run still needs exact approval", "run approved V464 surface-composite start-only", False
    if not base.approved(args):
        return "v464-native-wlan-surface-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "v464-native-wlan-surface-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    if live_result.get("surface_present_after_cleanup"):
        return "v464-native-wlan-surface-leaked", False, "WLAN surface remained after cleanup", "inspect device state before any further Wi-Fi work", True
    if live_result.get("surface_present_during") and live_result.get("all_postflight_safe") and post.get("clean"):
        return "v464-native-wlan-surface-observed-cleaned", True, "bounded composite start created WLAN surface and cleanup was clean", "advance to native scan-only gate; keep credentials blocked", True
    if live_result.get("helper_result") in {"start-only-pass", "start-only-runtime-gap"} and live_result.get("all_postflight_safe") and post.get("clean"):
        return "v464-native-wlan-surface-not-observed", True, "bounded composite start stayed clean but did not create wlan/wiphy/rfkill surface", "add the next Android runtime primitive before native scan/connect", True
    return "v464-native-wlan-surface-review-required", False, f"helper_result={live_result.get('helper_result')}", "inspect helper output before widening scope", True


def refusal_manifest(args: base.argparse.Namespace, v463: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v464-native-wlan-surface-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no live command executed",
        "next_step": "rerun with exact approval only after helper v31 deploy and preflight",
        "host": base.collect_host_metadata(),
        "v463": {"path": v463.get("path"), "decision": v463.get("decision"), "pass": v463.get("pass")},
        "plan": base.build_plan(args),
        "steps": [],
        "checks": [asdict(base.Check("approval-gate", "needs-operator", "approval", base.APPROVAL_PHRASE, [base.APPROVAL_PHRASE], "approve before live surface-composite start-only"))],
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
        "wifi_bringup_executed": False,
    }


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    v463 = base.load_json(args.v404_manifest)
    if args.command == "run" and not base.approved(args):
        return refusal_manifest(args, v463)
    steps: list[base.Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.run_preflight(args, store)
    checks = build_checks(args, store, steps, v463)
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
        "v463": {"path": v463.get("path"), "decision": v463.get("decision"), "pass": v463.get("pass")},
        "plan": base.build_plan(args),
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
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "wificond, supplicant, or hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
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
    return "\n".join([
        "# V464 Native WLAN Surface Composite Start-Only",
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
