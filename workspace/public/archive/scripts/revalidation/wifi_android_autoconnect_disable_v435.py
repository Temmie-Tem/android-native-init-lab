#!/usr/bin/env python3
"""V435 bounded Android Wi-Fi auto-connect disable proof.

V435 is the first containment cleanup gate after V434 selected `contain-first`.
It may run exactly one Android Wi-Fi mutation: `cmd wifi set-wifi-enabled
disabled`.  It then verifies Wi-Fi status, route/DNS/connectivity, and listener
surface without scan/connect, credentials, external packet probes, server
exposure, route mutation, rfkill/sysfs writes, daemon starts, reboot, or flash.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_android_autoconnect_containment_v433 import (
    default_route_wlan,
    global_listener_observed,
    route_get_wlan,
)
from wifi_android_control_gate_v432 import (
    CaptureRecord,
    adb_base,
    adb_shell_command,
    capture_command,
    display_command,
    evidence_text,
    read_capture_file_text,
    read_capture_text,
    redact_text,
    wifi_status_disabled,
    wifi_status_enabled,
    wlan0_has_ip,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v435-android-wifi-autoconnect-disable")
DISABLE_COMMAND = "cmd wifi set-wifi-enabled disabled"
FORBIDDEN_PATTERNS = (
    re.compile(r"\bcmd\s+wifi\s+(?:connect-network|add-network|forget-network|start-scan|force-country-code|set-scan-always-available)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\s+enable\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bwpa_cli\b", re.IGNORECASE),
    re.compile(r"\b(?:ping|curl|wget|nc|netcat|telnet|iperf3?|nslookup|dig|host)\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\bsetprop\b", re.IGNORECASE),
)
CAPTURES: tuple[tuple[str, str, int], ...] = (
    (
        "wifi-status",
        "cmd wifi status 2>&1 || true",
        25,
    ),
    (
        "wifi-settings",
        "for s in wifi_on wifi_scan_always_enabled airplane_mode_on captive_portal_mode; do echo \"global.$s=$(settings get global $s 2>/dev/null)\"; done; "
        "for s in location_mode; do echo \"secure.$s=$(settings get secure $s 2>/dev/null)\"; done",
        20,
    ),
    (
        "route-state",
        "ip route show table all 2>/dev/null || true; echo '--- rules ---'; ip rule show 2>/dev/null || true",
        25,
    ),
    (
        "route-get-external-readonly",
        "ip route get 1.1.1.1 2>/dev/null || true; ip route get 8.8.8.8 2>/dev/null || true",
        20,
    ),
    (
        "netdev-state",
        "ip -o addr show wlan0 2>/dev/null || true; ip -o link show wlan0 2>/dev/null || true; "
        "for f in operstate carrier mtu address; do [ -e /sys/class/net/wlan0/$f ] && echo \"$f=$(cat /sys/class/net/wlan0/$f 2>/dev/null)\"; done",
        25,
    ),
    (
        "connectivity-filtered",
        "dumpsys connectivity 2>/dev/null | grep -Ei 'NetworkAgentInfo|WIFI|VALIDATED|DefaultNetwork|mDefault|LinkProperties|Routes|Dns|Capabilities|internet|metered|score' | head -180 || true",
        35,
    ),
    (
        "listening-sockets-readonly",
        "ss -lntu 2>/dev/null || netstat -lntu 2>/dev/null || true",
        25,
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--disable-settle-sleep", type=float, default=20.0)
    parser.add_argument("--allow-wifi-disable", action="store_true")
    parser.add_argument("--i-understand-android-wifi-setting-mutation", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def validate_command_guard() -> None:
    commands = "\n".join(command for _, command, _ in CAPTURES) + "\n" + DISABLE_COMMAND
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(commands):
            raise RuntimeError(f"forbidden Wi-Fi/server/probe command pattern found: {pattern.pattern}")


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_wifi_disable:
        missing.append("--allow-wifi-disable")
    if not args.i_understand_android_wifi_setting_mutation:
        missing.append("--i-understand-android-wifi-setting-mutation")
    return not missing, missing


def adb_state(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures = [
        capture_command(store, "adb-devices", [*adb_base(args), "devices", "-l"], args.timeout),
        capture_command(store, "adb-get-state", [*adb_base(args), "get-state"], args.timeout),
    ]
    state_text = read_capture_text(captures, "adb-get-state").strip()
    state = state_text.splitlines()[-1].strip() if state_text else ""
    if captures[1].rc is None and ("No such file" in captures[1].error or "No such file" in state_text):
        state = "adb-missing"
    return captures, state


def capture_phase(args: argparse.Namespace, store: EvidenceStore, phase: str) -> list[CaptureRecord]:
    captures: list[CaptureRecord] = []
    for name, shell_command, timeout in CAPTURES:
        captures.append(
            capture_command(
                store,
                f"{phase}-{name}",
                adb_shell_command(args, shell_command),
                max(timeout, args.timeout),
            )
        )
    return captures


def parse_settings(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in evidence_text(text).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def phase_text(store: EvidenceStore, captures: list[CaptureRecord], phase: str, suffix: str) -> str:
    name = f"{phase}-{suffix}"
    for capture in captures:
        if capture.name == name:
            return read_capture_file_text(store, captures, name)
    return ""


def phase_state(store: EvidenceStore, captures: list[CaptureRecord], phase: str) -> dict[str, Any]:
    status_text = phase_text(store, captures, phase, "wifi-status")
    settings_text = phase_text(store, captures, phase, "wifi-settings")
    route_text = phase_text(store, captures, phase, "route-state")
    route_get_text = phase_text(store, captures, phase, "route-get-external-readonly")
    netdev_text = phase_text(store, captures, phase, "netdev-state")
    connectivity_text = phase_text(store, captures, phase, "connectivity-filtered")
    socket_text = phase_text(store, captures, phase, "listening-sockets-readonly")
    settings = parse_settings(settings_text)
    disabled = wifi_status_disabled(status_text) or settings.get("global.wifi_on") == "0"
    enabled = (wifi_status_enabled(status_text) or settings.get("global.wifi_on") == "1") and not disabled
    return {
        "enabled_by_status": enabled,
        "disabled_by_status": disabled,
        "wlan0_has_ip": wlan0_has_ip(netdev_text),
        "default_route_wlan": default_route_wlan(route_text),
        "route_get_wlan": route_get_wlan(route_get_text),
        "connectivity_validated_wifi": active_connectivity_validated_wifi(connectivity_text),
        "dns_surface_wlan": active_dns_surface_wlan(connectivity_text),
        "global_listener_observed": global_listener_observed(socket_text),
        "settings": settings,
        "status_lines": matching_lines(status_text, r"Wifi is|Wi-Fi is|disabled|enabled|connected|Supplicant|SSID|BSSID"),
        "route_lines": matching_lines(route_text + "\n" + route_get_text, r"default|wlan0|src|via|uid|table"),
        "connectivity_lines": matching_lines(connectivity_text, r"wifi|validated|default|dns|route|internet|score"),
    }


def active_connectivity_validated_wifi(text: str) -> bool:
    for line in evidence_text(text).splitlines():
        lowered = line.lower()
        if "networkagentinfo{" not in lowered:
            continue
        if "wifi connected" in lowered and ("validated" in lowered or "internet" in lowered):
            return True
    return False


def active_dns_surface_wlan(text: str) -> bool:
    for line in evidence_text(text).splitlines():
        lowered = line.lower()
        if "networkagentinfo{" not in lowered:
            continue
        if "wlan0" in lowered and ("dnsaddresses" in lowered or " dns" in lowered):
            return True
    return False


def matching_lines(text: str, pattern: str, limit: int = 120) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in evidence_text(text).splitlines():
        line = raw_line.strip()
        if not line or "grep -" in line:
            continue
        if not regex.search(line):
            continue
        redacted = redact_text(line)
        if redacted in seen:
            continue
        seen.add(redacted)
        lines.append(redacted)
        if len(lines) >= limit:
            break
    return lines


def classify(pre: dict[str, Any], post: dict[str, Any], disable_ok: bool) -> dict[str, Any]:
    route_exposure_gone = not post["default_route_wlan"] and not post["route_get_wlan"]
    connectivity_gone = not post["connectivity_validated_wifi"] and not post["dns_surface_wlan"]
    listener_safe = not post["global_listener_observed"]
    if not disable_ok:
        decision = "v435-android-wifi-disable-command-failed"
        pass_ok = False
        reason = "Wi-Fi disable command did not return success"
        next_gate = "review disable command output before retry"
    elif post["disabled_by_status"] and route_exposure_gone and connectivity_gone and listener_safe:
        decision = "v435-android-wifi-autoconnect-contained-pass"
        pass_ok = True
        reason = "Wi-Fi disable completed and post-cleanup route/DNS/connectivity exposure was removed"
        next_gate = "V436 Android Wi-Fi disabled persistence check or controlled re-enable policy"
    elif post["disabled_by_status"]:
        decision = "v435-android-wifi-disable-partial-containment"
        pass_ok = False
        reason = "Wi-Fi reports disabled, but post-cleanup route/DNS/connectivity exposure was not fully removed"
        next_gate = "rerun with longer settle or inspect stale connectivity state"
    else:
        decision = "v435-android-wifi-disable-not-contained"
        pass_ok = False
        reason = "Wi-Fi did not report disabled after the containment command"
        next_gate = "review Android Wi-Fi framework state before retry"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "pre": pre,
        "post": post,
        "route_exposure_gone": route_exposure_gone,
        "connectivity_gone": connectivity_gone,
        "listener_safe": listener_safe,
    }


def guardrails() -> list[str]:
    return [
        "exactly one mutating Wi-Fi operation is allowed: cmd wifi set-wifi-enabled disabled",
        "no scan/connect, credentials, DHCP/routing mutation, external packet probes, server exposure, or new listeners",
        "no rfkill/sysfs write, module operation, setprop, direct daemon start, reboot, or flash in this collector",
        "post-cleanup route/DNS/connectivity/listener state is verified read-only",
    ]


def run_plan(args: argparse.Namespace) -> dict[str, Any]:
    ok, missing = approval_ok(args)
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v435-android-wifi-disable-plan-ready",
        "pass": True,
        "reason": "bounded Android Wi-Fi auto-connect disable plan generated",
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "disable_command": DISABLE_COMMAND,
        "captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in CAPTURES],
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    ok, missing = approval_ok(args)
    if state == "device" and ok:
        decision = "v435-android-wifi-disable-preflight-ready"
        pass_ok = True
        reason = "Android ADB is online and disable approval flags are present"
    elif state == "device":
        decision = "v435-android-wifi-disable-approval-required"
        pass_ok = False
        reason = "Android ADB is online, but disable approval flags are missing"
    else:
        decision = "v435-android-wifi-disable-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ok, missing = approval_ok(args)
    captures, state = adb_state(args, store)
    if not ok:
        decision = "v435-android-wifi-disable-approval-required"
        pass_ok = False
        reason = "disable approval flags are missing"
        classification: dict[str, Any] = {"next_gate": "rerun with explicit disable approval flags"}
        disable_capture = None
    elif state != "device":
        decision = "v435-android-wifi-disable-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        classification = {"next_gate": "boot Android before V435"}
        disable_capture = None
    else:
        captures.extend(capture_phase(args, store, "pre"))
        disable_capture = capture_command(store, "disable-wifi", adb_shell_command(args, DISABLE_COMMAND), args.timeout)
        captures.append(disable_capture)
        if args.disable_settle_sleep > 0:
            time.sleep(args.disable_settle_sleep)
        captures.extend(capture_phase(args, store, "post"))
        pre = phase_state(store, captures, "pre")
        post = phase_state(store, captures, "post")
        classification = classify(pre, post, disable_capture.ok)
        decision = classification["decision"]
        pass_ok = classification["pass"]
        reason = classification["reason"]

    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "adb_state": state,
        "disable_settle_sleep": args.disable_settle_sleep,
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "disable_capture": asdict(disable_capture) if disable_capture else None,
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": disable_capture is not None,
        "wifi_disable_executed": disable_capture is not None,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification", {})
    captures = manifest.get("captures", [])
    capture_rows = [
        [
            item["name"],
            "ok" if item.get("ok") else ("plan" if "ok" not in item else "fail"),
            str(item.get("rc", "-")),
            f"{item.get('duration_sec', 0.0):.3f}s" if "duration_sec" in item else "-",
            item.get("file", "-"),
        ]
        for item in captures
    ]
    state_rows: list[list[str]] = []
    for phase in ("pre", "post"):
        phase_state_data = classification.get(phase) or {}
        for key in (
            "enabled_by_status",
            "disabled_by_status",
            "wlan0_has_ip",
            "default_route_wlan",
            "route_get_wlan",
            "connectivity_validated_wifi",
            "dns_surface_wlan",
            "global_listener_observed",
        ):
            state_rows.append([f"{phase}.{key}", str(phase_state_data.get(key, "-"))])
    evidence_rows: list[list[str]] = []
    for phase in ("pre", "post"):
        phase_state_data = classification.get(phase) or {}
        for key in ("status_lines", "route_lines", "connectivity_lines"):
            for line in phase_state_data.get(key, [])[:18]:
                evidence_rows.append([f"{phase}.{key}", line])
    return "\n".join(
        [
            "# V435 Android Wi-Fi Auto-connect Disable Proof",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- approval_ok: `{manifest.get('approval_ok', '-')}`",
            f"- missing_approval_flags: `{', '.join(manifest.get('missing_approval_flags', [])) or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## State Summary",
            "",
            markdown_table(["item", "value"], state_rows if state_rows else [["-", "-"]]),
            "",
            "## Evidence Lines",
            "",
            markdown_table(["source", "line"], evidence_rows if evidence_rows else [["-", "-"]]),
            "",
            "## Captures",
            "",
            markdown_table(["name", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    validate_command_guard()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = run_plan(args)
    elif args.command == "preflight":
        manifest = run_preflight(args, store)
    else:
        manifest = run_capture_mode(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_disable_executed: {manifest['wifi_disable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
