#!/usr/bin/env python3
"""V497 native Wi-Fi scan-only surface proof.

This runner is the first V50 gate after the V496 scan-only contract. It starts
the private service-manager/HAL/CNSS/IWifi.start active-session surface in a
bounded helper-owned window, triggers one nl80211 scan inside that same window,
captures only redacted result counts, then proves cleanup. It does not read
credentials, connect, request DHCP, change routes, or send external packets.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_iwifi_start_surface_v466 as v466


base = v466.base
_BASE_PARSE_ARGS = base.parse_args
_BASE_BUILD_CHECKS = base.build_checks
_BASE_BUILD_PLAN = base.build_plan

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v497-native-wifi-scan-only-surface")
base.DEFAULT_HELPER_SHA256 = "265ce1d7ebdc2fae4be071e903134feaed8929eb65bb65f5de7198c690c6a48f"
base.HELPER_LABEL = "v50"
base.APPROVAL_PHRASE = (
    "approve v497 native scan-only proof only; "
    "no connect/link-up/DHCP/routing/external ping"
)

ACTIVE_KEY_RE = re.compile(r"^wifi_active_session\.([A-Za-z0-9_.]+)=(.*)$")
SCAN_KEY_RE = re.compile(r"^wifi_scan_only\.([A-Za-z0-9_.]+)=(.*)$")


def _extract_v496_manifest_arg() -> Path | None:
    value: str | None = None
    stripped = [sys.argv[0]]
    index = 1
    while index < len(sys.argv):
        item = sys.argv[index]
        if item == "--v496-manifest":
            if index + 1 >= len(sys.argv):
                raise SystemExit("--v496-manifest requires a path")
            value = sys.argv[index + 1]
            index += 2
            continue
        if item.startswith("--v496-manifest="):
            value = item.split("=", 1)[1]
            index += 1
            continue
        stripped.append(item)
        index += 1
    sys.argv[:] = stripped
    return Path(value) if value else None


def parse_args() -> base.argparse.Namespace:
    v496_manifest = _extract_v496_manifest_arg()
    args = _BASE_PARSE_ARGS()
    args.v496_manifest = v496_manifest
    return args


def _load_v496_manifest(args: base.argparse.Namespace) -> dict[str, Any]:
    path = getattr(args, "v496_manifest", None)
    result: dict[str, Any] = {
        "path": str(path) if path else "",
        "present": False,
        "valid": False,
        "decision": "",
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "reason": "missing-v496-manifest",
    }
    if path is None:
        return result
    if not path.exists():
        result["reason"] = "v496-manifest-not-found"
        return result
    result["present"] = True
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - preserve parse issue
        result["reason"] = f"v496-manifest-read-failed-{exc}"
        return result
    result["decision"] = str(manifest.get("decision", ""))
    result["wifi_bringup_executed"] = bool(manifest.get("wifi_bringup_executed"))
    result["credentials_read"] = bool(manifest.get("credentials_read"))
    result["scan_connect_executed"] = bool(manifest.get("scan_connect_executed"))
    result["external_ping_executed"] = bool(manifest.get("external_ping_executed"))
    result["valid"] = (
        manifest.get("decision") == "v496-native-scan-only-contract-ready"
        and manifest.get("pass") is True
        and manifest.get("device_commands_executed") is False
        and manifest.get("device_mutations") is False
        and manifest.get("wifi_bringup_executed") is False
        and manifest.get("credentials_read") is False
        and manifest.get("scan_connect_executed") is False
        and manifest.get("external_ping_executed") is False
    )
    result["reason"] = "v496-scan-only-contract-ready" if result["valid"] else "v496-contract-ready-required"
    return result


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
        "wifi-active-session-scan-only",
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
            "--allow-scan-only",
        ])
    return argv


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["helper_mode"] = "wifi-active-session-scan-only"
    plan["v496_scan_only_contract_manifest"] = str(getattr(args, "v496_manifest", "") or "")
    plan["precondition"] = {
        "decision": "v496-native-scan-only-contract-ready",
        "branch": "execns-integrated-nl80211-scan",
    }
    plan["scan_only_attempt"] = {
        "starts": ["private servicemanager", "private hwservicemanager", "legacy Wi-Fi HAL", "CNSS"],
        "calls": [
            "IServiceManager.get(IWifi/default)",
            "IWifi.start() once if handle is non-null",
            "NL80211_CMD_TRIGGER_SCAN once on selected Wi-Fi interface",
            "NL80211_CMD_GET_SCAN redacted count only",
        ],
        "observes": ["wlan* netdev", "phy* wiphy", "/proc/net/wireless", "Wi-Fi rfkill"],
        "keeps_alive_until": "bounded --max-runtime-sec window before cleanup",
        "blocks": ["SSID/PSK reads", "connect/link-up", "DHCP", "route changes", "external ping"],
        "redaction": "SSID/BSSID/frequency/signal/raw BSS attributes are not emitted",
    }
    return plan


def build_checks(args: base.argparse.Namespace,
                 store: base.EvidenceStore,
                 steps: list[base.Step],
                 v465: dict[str, Any]) -> list[base.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, v465)
    if args.command == "plan":
        return checks
    helper_sha = base.step_text(store, steps, "sha-helper")
    helper_usage = base.step_text(store, steps, "helper-usage")
    helper_marker_ready = any(
        marker in helper_usage
        for marker in ("a90_android_execns_probe v50", "a90_android_execns_probe v52", "a90_android_execns_probe v53")
    )
    helper_ready = (
        args.helper_sha256 in helper_sha
        and helper_marker_ready
        and "wifi-active-session-scan-only" in helper_usage
        and "--allow-scan-only" in helper_usage
    )
    for check in checks:
        if check.name == "helper-v32":
            check.name = "helper-v50-scan-only"
            check.status = "pass" if helper_ready else "blocked"
            check.detail = (
                f"sha_match={args.helper_sha256 in helper_sha} "
                f"marker={helper_marker_ready} "
                f"mode={'wifi-active-session-scan-only' in helper_usage} "
                f"allow={'--allow-scan-only' in helper_usage}"
            )
            check.evidence = [line for line in helper_sha.splitlines() if args.helper in line][:2]
            check.next_step = "deploy helper v50 before V497 live run"
    v496 = _load_v496_manifest(args)
    base.add_check(
        checks,
        "v496-scan-only-contract-ready",
        "pass" if v496["valid"] else "blocked",
        "blocker",
        f"path={v496['path']} present={v496['present']} decision={v496['decision']} reason={v496['reason']}",
        [v496["path"]],
        "run V496 preflight and pass the contract-ready manifest to --v496-manifest",
    )
    return checks


def parse_active_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = ACTIVE_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def parse_scan_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = SCAN_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    command = base.build_native_run_command(args)
    record = base.run_capture(args, "run-scan-only-surface", command, timeout=args.timeout + args.max_runtime_sec + 50.0)
    rel = "native/run-scan-only-surface.txt"
    store.write_text(rel, base.strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    composite_keys = base.parse_composite_keys(text)
    iwifi_keys = v466.parse_iwifi_keys(text)
    active_keys = parse_active_keys(text)
    scan_keys = parse_scan_keys(text)
    surface = v466.parse_surface_keys(text)
    return {
        "capture": base.capture_to_manifest(record),
        "file": rel,
        "keys": composite_keys,
        "iwifi": iwifi_keys,
        "active_session": active_keys,
        "scan_only": scan_keys,
        "surface": surface,
        "surface_present_after_iwifi_start": v466.v464.surface_present(surface["after_iwifi_start"]),
        "surface_present_during": v466.v464.surface_present(surface["during"]),
        "surface_present_after_cleanup": v466.v464.surface_present(surface["after_cleanup"]),
        "helper_result": composite_keys.get("result", "missing"),
        "helper_reason": composite_keys.get("reason", ""),
        "iwifi_result": iwifi_keys.get("result", "missing"),
        "iwifi_transaction_executed": iwifi_keys.get("transaction_executed") == "1",
        "iwifi_start_ok": iwifi_keys.get("start_transaction_ok") == "1",
        "active_session_started": active_keys.get("begin") == "1",
        "active_session_cleanup_attempted": active_keys.get("cleanup_attempted") == "1",
        "scan_only_attempted": scan_keys.get("trigger_attempted") == "1",
        "scan_only_result": scan_keys.get("result", "missing"),
        "scan_result_count": scan_keys.get("scan_result_count", ""),
        "raw_results_redacted": scan_keys.get("raw_results_redacted") == "1",
        "connect_linkup": scan_keys.get("connect_linkup") == "1",
        "timed_out": composite_keys.get("timed_out") == "1",
        "all_postflight_safe": composite_keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": composite_keys.get("all_observable_at_timeout") == "1",
    }


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v497-native-scan-only-plan-ready", True, "plan-only; no device command executed", "deploy helper v50 and run preflight", False
    blocked = base.blockers(checks)
    if blocked:
        return "v497-native-scan-only-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before scan-only proof", False
    if args.command == "preflight":
        return "v497-native-scan-only-preflight-ready", True, "read-only preflight is ready; live scan-only run still needs exact approval", "run approved V497 scan-only proof", False
    if not base.approved(args):
        return "v497-native-scan-only-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "v497-native-scan-only-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    if live_result.get("surface_present_after_cleanup"):
        return "v497-native-scan-only-surface-leaked", False, "WLAN surface remained after cleanup", "inspect device state before connect work", True
    if live_result.get("helper_result") == "scan-only-interface-missing" and post.get("clean"):
        return "v497-native-scan-only-interface-missing", True, "nl80211 family is present but no Wi-Fi interface was selectable", "route back to active-session/CNSS surface creation", True
    if live_result.get("helper_result") == "scan-only-trigger-failed" and post.get("clean"):
        return "v497-native-scan-only-trigger-failed", True, "nl80211 trigger scan failed while cleanup passed", "inspect trigger errno and HAL/CNSS runtime state", True
    if live_result.get("helper_result") == "scan-only-dump-failed" and post.get("clean"):
        return "v497-native-scan-only-dump-failed", True, "nl80211 scan dump failed while cleanup passed", "inspect dump errno and driver scan cache behavior", True
    if (
        live_result.get("helper_result") == "scan-only-pass"
        and live_result.get("scan_only_attempted")
        and live_result.get("scan_only_result") == "pass"
        and live_result.get("raw_results_redacted")
        and not live_result.get("connect_linkup")
        and post.get("clean")
    ):
        return "v497-native-scan-only-pass-redacted", True, "nl80211 scan triggered and only redacted counts were captured; cleanup passed", "advance to bounded connect/DHCP planning", True
    return "v497-native-scan-only-review-required", False, f"helper_result={live_result.get('helper_result')} scan_result={live_result.get('scan_only_result')}", "inspect helper output before widening scope", True


def refusal_manifest(args: base.argparse.Namespace, v465: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v497-native-scan-only-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no live command executed",
        "next_step": "rerun with exact V497 approval after V496 contract-ready proof",
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "v496_scan_only_contract": _load_v496_manifest(args),
        "plan": build_plan(args),
        "steps": [],
        "checks": [asdict(base.Check("approval-gate", "needs-operator", "approval", base.APPROVAL_PHRASE, [base.APPROVAL_PHRASE], "approve before scan-only proof"))],
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
        "scan_only_executed": False,
        "connect_executed": False,
        "link_up_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
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
    scan_only_executed = bool((live_result or {}).get("scan_only_attempted"))
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "v496_scan_only_contract": _load_v496_manifest(args),
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
        "scan_only_executed": scan_only_executed,
        "connect_executed": False,
        "link_up_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": scan_only_executed,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "SSID/PSK/env credential reads",
            "connect/link-up/DHCP/routing/external ping",
            "wificond, supplicant, or hostapd start",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], "<br>".join(c["evidence"]), c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    active_rows: list[list[str]] = []
    scan_rows: list[list[str]] = []
    surface_rows: list[list[str]] = []
    live = manifest.get("live_result") or {}
    for key, value in sorted((live.get("active_session") or {}).items()):
        active_rows.append([key, value])
    for key, value in sorted((live.get("scan_only") or {}).items()):
        scan_rows.append([key, value])
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
        "# V497 Native Wi-Fi Scan-Only Surface",
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
        f"- scan_only_executed: `{manifest['scan_only_executed']}`",
        f"- connect_executed: `{manifest['connect_executed']}`",
        f"- link_up_executed: `{manifest['link_up_executed']}`",
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
        "## Active Session Keys",
        "",
        base.markdown_table(["key", "value"], active_rows) if active_rows else "- none",
        "",
        "## Scan-Only Keys",
        "",
        base.markdown_table(["key", "value"], scan_rows) if scan_rows else "- none",
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
