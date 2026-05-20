#!/usr/bin/env python3
"""V495 native Wi-Fi active-session surface proof.

This runner is the first V49 gate after V494. It starts the private
service-manager/HAL/CNSS/IWifi.start surface in a bounded helper-owned window,
observes whether a WLAN/wiphy/rfkill surface stays visible during that active
window, then proves cleanup. It does not read credentials, scan, connect,
request DHCP, mutate routes, or send external packets.
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
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v495-native-wifi-active-session-surface")
base.DEFAULT_HELPER_SHA256 = "1faae7fd5e27e8aa302c62640588991177ec95d3c942e102fae845c9f89dfa89"
base.HELPER_LABEL = "v49"
base.APPROVAL_PHRASE = (
    "approve v495 native active-session surface proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

ACTIVE_KEY_RE = re.compile(r"^wifi_active_session\.([A-Za-z0-9_.]+)=(.*)$")


def _extract_v494_manifest_arg() -> Path | None:
    value: str | None = None
    stripped = [sys.argv[0]]
    index = 1
    while index < len(sys.argv):
        item = sys.argv[index]
        if item == "--v494-manifest":
            if index + 1 >= len(sys.argv):
                raise SystemExit("--v494-manifest requires a path")
            value = sys.argv[index + 1]
            index += 2
            continue
        if item.startswith("--v494-manifest="):
            value = item.split("=", 1)[1]
            index += 1
            continue
        stripped.append(item)
        index += 1
    sys.argv[:] = stripped
    return Path(value) if value else None


def parse_args() -> base.argparse.Namespace:
    v494_manifest = _extract_v494_manifest_arg()
    args = _BASE_PARSE_ARGS()
    args.v494_manifest = v494_manifest
    return args


def _load_v494_manifest(args: base.argparse.Namespace) -> dict[str, Any]:
    path = getattr(args, "v494_manifest", None)
    result: dict[str, Any] = {
        "path": str(path) if path else "",
        "present": False,
        "valid": False,
        "decision": "",
        "branch": "",
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "reason": "missing-v494-manifest",
    }
    if path is None:
        return result
    if not path.exists():
        result["reason"] = "v494-manifest-not-found"
        return result
    result["present"] = True
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - preserve parse issue
        result["reason"] = f"v494-manifest-read-failed-{exc}"
        return result
    result["decision"] = str(manifest.get("decision", ""))
    result["branch"] = str(manifest.get("branch", ""))
    result["wifi_bringup_executed"] = bool(manifest.get("wifi_bringup_executed"))
    result["scan_connect_executed"] = bool(manifest.get("scan_connect_executed"))
    result["external_ping_executed"] = bool(manifest.get("external_ping_executed"))
    result["valid"] = (
        manifest.get("decision") == "v494-native-wifi-active-session-contract-ready"
        and manifest.get("pass") is True
        and manifest.get("wifi_bringup_executed") is False
        and manifest.get("scan_connect_executed") is False
        and manifest.get("external_ping_executed") is False
    )
    result["reason"] = "v494-active-session-ready" if result["valid"] else "v494-contract-ready-required"
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
        "wifi-active-session-surface",
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
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["helper_mode"] = "wifi-active-session-surface"
    plan["v494_active_session_manifest"] = str(getattr(args, "v494_manifest", "") or "")
    plan["precondition"] = {
        "decision": "v494-native-wifi-active-session-contract-ready",
        "branch": "active-session-needed",
    }
    plan["active_session_attempt"] = {
        "starts": ["private servicemanager", "private hwservicemanager", "legacy Wi-Fi HAL", "CNSS"],
        "calls": ["IServiceManager.get(IWifi/default)", "IWifi.start() once if handle is non-null"],
        "observes": ["wlan* netdev", "phy* wiphy", "/proc/net/wireless", "Wi-Fi rfkill"],
        "keeps_alive_until": "bounded --max-runtime-sec window before cleanup",
        "blocks": ["credentials", "scan/connect", "DHCP", "route changes", "external ping"],
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
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v49" in helper_usage
        and "wifi-active-session-surface" in helper_usage
        and "--allow-iwifi-start-only" in helper_usage
    )
    for check in checks:
        if check.name == "helper-v32":
            check.name = "helper-v49-active-session"
            check.status = "pass" if helper_ready else "blocked"
            check.detail = f"sha_match={args.helper_sha256 in helper_sha} marker={'a90_android_execns_probe v49' in helper_usage} mode={'wifi-active-session-surface' in helper_usage} allow={'--allow-iwifi-start-only' in helper_usage}"
            check.evidence = [line for line in helper_sha.splitlines() if args.helper in line][:2]
            check.next_step = "deploy helper v49 before V495 live run"
    v494 = _load_v494_manifest(args)
    base.add_check(
        checks,
        "v494-active-session-contract-ready",
        "pass" if v494["valid"] else "blocked",
        "blocker",
        f"path={v494['path']} present={v494['present']} decision={v494['decision']} branch={v494['branch']} reason={v494['reason']}",
        [v494["path"]],
        "run V490/V491/V492/V493/V494 first; pass the V494 contract-ready manifest to --v494-manifest",
    )
    return checks


def parse_active_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = ACTIVE_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    command = base.build_native_run_command(args)
    record = base.run_capture(args, "run-active-session-surface", command, timeout=args.timeout + args.max_runtime_sec + 45.0)
    rel = "native/run-active-session-surface.txt"
    store.write_text(rel, base.strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    composite_keys = base.parse_composite_keys(text)
    iwifi_keys = v466.parse_iwifi_keys(text)
    active_keys = parse_active_keys(text)
    surface = v466.parse_surface_keys(text)
    return {
        "capture": base.capture_to_manifest(record),
        "file": rel,
        "keys": composite_keys,
        "iwifi": iwifi_keys,
        "active_session": active_keys,
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
        "timed_out": composite_keys.get("timed_out") == "1",
        "all_postflight_safe": composite_keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": composite_keys.get("all_observable_at_timeout") == "1",
    }


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v495-native-active-session-plan-ready", True, "plan-only; no device command executed", "deploy helper v49 and run preflight", False
    blocked = base.blockers(checks)
    if blocked:
        return "v495-native-active-session-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before active-session proof", False
    if args.command == "preflight":
        return "v495-native-active-session-preflight-ready", True, "read-only preflight is ready; live run still needs exact approval", "run approved V495 active-session surface proof", False
    if not base.approved(args):
        return "v495-native-active-session-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "v495-native-active-session-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    if live_result.get("surface_present_after_cleanup"):
        return "v495-native-active-session-surface-leaked", False, "WLAN surface remained after cleanup", "inspect device state before scan/connect work", True
    if live_result.get("iwifi_result") == "service-null" and post.get("clean"):
        return "v495-native-active-session-service-null", True, "IWifi/default handle was not returned while cleanup was clean", "inspect registration namespace mismatch", True
    if live_result.get("iwifi_transaction_executed") and not live_result.get("iwifi_start_ok") and post.get("clean"):
        return "v495-native-active-session-transaction-failed", True, "IWifi.start transaction executed but reply was not clean; cleanup passed", "inspect raw hwbinder transcript and HAL stderr", True
    if (
        live_result.get("active_session_started")
        and live_result.get("iwifi_start_ok")
        and (live_result.get("surface_present_after_iwifi_start") or live_result.get("surface_present_during"))
        and post.get("clean")
    ):
        return "v495-native-active-session-surface-observed-cleaned", True, "bounded active session created WLAN surface and cleanup was clean", "advance to V496 native scan-only proof", True
    if live_result.get("iwifi_start_ok") and post.get("clean"):
        return "v495-native-active-session-no-surface-delta", True, "IWifi.start returned cleanly but no WLAN surface appeared", "route to driver/CNSS mode-set primitive before scan/connect", True
    return "v495-native-active-session-review-required", False, f"helper_result={live_result.get('helper_result')} iwifi_result={live_result.get('iwifi_result')}", "inspect helper output before widening scope", True


def refusal_manifest(args: base.argparse.Namespace, v465: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v495-native-active-session-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no live command executed",
        "next_step": "rerun with exact V495 approval after V494 contract-ready proof",
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "v494_active_session_gate": _load_v494_manifest(args),
        "plan": build_plan(args),
        "steps": [],
        "checks": [asdict(base.Check("approval-gate", "needs-operator", "approval", base.APPROVAL_PHRASE, [base.APPROVAL_PHRASE], "approve before active-session proof"))],
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
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "v494_active_session_gate": _load_v494_manifest(args),
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
    active_rows: list[list[str]] = []
    surface_rows: list[list[str]] = []
    live = manifest.get("live_result") or {}
    for key, value in sorted((live.get("active_session") or {}).items()):
        active_rows.append([key, value])
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
        "# V495 Native Wi-Fi Active-Session Surface",
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
        "## Active Session Keys",
        "",
        base.markdown_table(["key", "value"], active_rows) if active_rows else "- none",
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
