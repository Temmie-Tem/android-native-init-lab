#!/usr/bin/env python3
"""V438 bounded Android Wi-Fi re-enable observation.

V438 is the first controlled Wi-Fi re-enable gate after V436/V437 established a
contained Android baseline.  It may run exactly one Android Wi-Fi mutation:
`cmd wifi set-wifi-enabled enabled`.  It then observes status, route, DNS,
connectivity, and listener surfaces without scan/connect, credentials, external
packet probes, server exposure, route mutation, rfkill/sysfs writes, daemon
starts, reboot, or flash.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_android_autoconnect_disable_v435 import (
    CAPTURES as V435_CAPTURES,
    CaptureRecord,
    adb_base,
    adb_shell_command,
    adb_state,
    active_connectivity_validated_wifi,
    active_dns_surface_wlan,
    capture_command,
    default_route_wlan,
    global_listener_observed,
    matching_lines,
    parse_settings,
    phase_state,
    phase_text,
    read_capture_file_text,
    read_capture_text,
    redact_text,
    route_get_wlan,
    wifi_status_disabled,
    wifi_status_enabled,
    wlan0_has_ip,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v438-android-wifi-reenable-observation")
ENABLE_COMMAND = "cmd wifi set-wifi-enabled enabled"
FORBIDDEN_PATTERNS = (
    re.compile(r"\bcmd\s+wifi\s+(?:set-wifi-enabled\s+disabled|connect-network|add-network|forget-network|start-scan|force-country-code|set-scan-always-available)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
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
    *V435_CAPTURES,
    (
        "dumpsys-wifi-filtered",
        "dumpsys wifi 2>/dev/null | grep -Ei 'Wifi is|Wi-Fi is|ClientMode|Supplicant|wlan0|STA|connected|disconnected|NetworkInfo|score|L3Connected|IPv4|NOMINATOR|CMD_START_CONNECT|WIFI_ENABLED' | head -180 || true",
        40,
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
    parser.add_argument("--enable-settle-sleep", type=float, default=35.0)
    parser.add_argument("--allow-wifi-enable", action="store_true")
    parser.add_argument("--i-understand-android-wifi-setting-mutation", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def validate_command_guard() -> None:
    commands = "\n".join(command for _, command, _ in CAPTURES) + "\n" + ENABLE_COMMAND
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(commands):
            raise RuntimeError(f"forbidden Wi-Fi/server/probe command pattern found: {pattern.pattern}")


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_wifi_enable:
        missing.append("--allow-wifi-enable")
    if not args.i_understand_android_wifi_setting_mutation:
        missing.append("--i-understand-android-wifi-setting-mutation")
    return not missing, missing


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


def local_phase_state(store: EvidenceStore, captures: list[CaptureRecord], phase: str) -> dict[str, Any]:
    state = phase_state(store, captures, phase)
    status_text = phase_text(store, captures, phase, "wifi-status")
    settings_text = phase_text(store, captures, phase, "wifi-settings")
    route_text = phase_text(store, captures, phase, "route-state")
    route_get_text = phase_text(store, captures, phase, "route-get-external-readonly")
    netdev_text = phase_text(store, captures, phase, "netdev-state")
    connectivity_text = phase_text(store, captures, phase, "connectivity-filtered")
    socket_text = phase_text(store, captures, phase, "listening-sockets-readonly")
    dumpsys_wifi_text = phase_text(store, captures, phase, "dumpsys-wifi-filtered")
    settings = parse_settings(settings_text)
    disabled = wifi_status_disabled(status_text) or settings.get("global.wifi_on") == "0"
    enabled = (wifi_status_enabled(status_text) or settings.get("global.wifi_on") == "1") and not disabled
    connected = active_connectivity_validated_wifi(connectivity_text) or "Wifi is connected" in status_text or "curState=L3ConnectedState" in dumpsys_wifi_text
    auto_connect = "CMD_START_CONNECT" in dumpsys_wifi_text or "NOMINATOR" in dumpsys_wifi_text or connected
    state.update(
        {
            "enabled_by_status": enabled,
            "disabled_by_status": disabled,
            "wlan0_has_ip": wlan0_has_ip(netdev_text),
            "default_route_wlan": default_route_wlan(route_text),
            "route_get_wlan": route_get_wlan(route_get_text),
            "connectivity_validated_wifi": active_connectivity_validated_wifi(connectivity_text),
            "dns_surface_wlan": active_dns_surface_wlan(connectivity_text),
            "global_listener_observed": global_listener_observed(socket_text),
            "wifi_connected": connected,
            "android_auto_connect_observed": auto_connect,
            "dumpsys_wifi_lines": matching_lines(
                dumpsys_wifi_text,
                r"wifi|clientmode|supplicant|connected|l3connected|ipv4|nominator|cmd_start_connect|wifi_enabled",
            ),
        }
    )
    return state


def classify(pre: dict[str, Any], post: dict[str, Any], enable_ok: bool) -> dict[str, Any]:
    pre_contained = (
        bool(pre.get("disabled_by_status"))
        and not pre.get("wlan0_has_ip")
        and not pre.get("default_route_wlan")
        and not pre.get("route_get_wlan")
        and not pre.get("connectivity_validated_wifi")
        and not pre.get("dns_surface_wlan")
        and not pre.get("global_listener_observed")
    )
    post_exposure = any(
        bool(post.get(key))
        for key in (
            "wlan0_has_ip",
            "default_route_wlan",
            "route_get_wlan",
            "connectivity_validated_wifi",
            "dns_surface_wlan",
        )
    )
    listener_safe = not post.get("global_listener_observed")
    if not enable_ok:
        decision = "v438-android-wifi-reenable-command-failed"
        pass_ok = False
        reason = "Wi-Fi enable command did not return success"
        next_gate = "review enable command output before retry"
    elif not post.get("enabled_by_status") and not post.get("wifi_connected"):
        decision = "v438-android-wifi-reenable-not-enabled"
        pass_ok = False
        reason = "Wi-Fi did not report enabled or connected after the bounded enable command"
        next_gate = "review Android Wi-Fi framework state before retry"
    elif post.get("wifi_connected") or post_exposure:
        decision = "v438-android-wifi-reenable-autoconnect-observed-pass"
        pass_ok = True
        reason = "Bounded Wi-Fi re-enable caused Android to auto-connect or expose route/DNS state; observation captured without scan/connect"
        next_gate = "V439 post-reenable containment cleanup; disable Wi-Fi again before server or scan/connect work"
    else:
        decision = "v438-android-wifi-reenable-enabled-contained-pass"
        pass_ok = True
        reason = "Wi-Fi re-enable completed, but route/DNS/connectivity exposure was not observed"
        next_gate = "V439 decide cleanup or longer enabled observation"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "pre": pre,
        "post": post,
        "pre_contained": pre_contained,
        "post_exposure": post_exposure,
        "listener_safe": listener_safe,
    }


def guardrails() -> list[str]:
    return [
        "exactly one mutating Wi-Fi operation is allowed: cmd wifi set-wifi-enabled enabled",
        "no scan/connect, credentials, DHCP/routing mutation, external packet probes, server exposure, or new listeners",
        "no rfkill/sysfs write, module operation, setprop, direct daemon start, reboot, or flash in this collector",
        "post-enable route/DNS/connectivity/listener state is observation evidence only",
    ]


def run_plan(args: argparse.Namespace) -> dict[str, Any]:
    ok, missing = approval_ok(args)
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v438-android-wifi-reenable-plan-ready",
        "pass": True,
        "reason": "bounded Android Wi-Fi re-enable observation plan generated",
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "enable_command": ENABLE_COMMAND,
        "captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in CAPTURES],
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_enable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    ok, missing = approval_ok(args)
    if state == "device" and ok:
        decision = "v438-android-wifi-reenable-preflight-ready"
        pass_ok = True
        reason = "Android ADB is online and re-enable approval flags are present"
    elif state == "device":
        decision = "v438-android-wifi-reenable-approval-required"
        pass_ok = False
        reason = "Android ADB is online, but re-enable approval flags are missing"
    else:
        decision = "v438-android-wifi-reenable-waiting-for-android"
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
        "wifi_enable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ok, missing = approval_ok(args)
    captures, state = adb_state(args, store)
    if not ok:
        decision = "v438-android-wifi-reenable-approval-required"
        pass_ok = False
        reason = "re-enable approval flags are missing"
        classification: dict[str, Any] = {"next_gate": "rerun with explicit re-enable approval flags"}
        enable_capture = None
    elif state != "device":
        decision = "v438-android-wifi-reenable-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        classification = {"next_gate": "boot Android before V438"}
        enable_capture = None
    else:
        captures.extend(capture_phase(args, store, "pre"))
        enable_capture = capture_command(store, "enable-wifi", adb_shell_command(args, ENABLE_COMMAND), args.timeout)
        captures.append(enable_capture)
        if args.enable_settle_sleep > 0:
            time.sleep(args.enable_settle_sleep)
        captures.extend(capture_phase(args, store, "post"))
        pre = local_phase_state(store, captures, "pre")
        post = local_phase_state(store, captures, "post")
        classification = classify(pre, post, enable_capture.ok)
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
        "enable_settle_sleep": args.enable_settle_sleep,
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "enable_capture": asdict(enable_capture) if enable_capture else None,
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": enable_capture is not None,
        "wifi_enable_executed": enable_capture is not None,
        "wifi_bringup_executed": enable_capture is not None,
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
        phase_state = classification.get(phase) or {}
        for key in (
            "enabled_by_status",
            "disabled_by_status",
            "wifi_connected",
            "android_auto_connect_observed",
            "wlan0_has_ip",
            "default_route_wlan",
            "route_get_wlan",
            "connectivity_validated_wifi",
            "dns_surface_wlan",
            "global_listener_observed",
        ):
            state_rows.append([f"{phase}.{key}", str(phase_state.get(key, "-"))])
    for key in ("pre_contained", "post_exposure", "listener_safe"):
        state_rows.append([key, str(classification.get(key, "-"))])
    evidence_rows: list[list[str]] = []
    for phase in ("pre", "post"):
        phase_state = classification.get(phase) or {}
        for key in ("status_lines", "route_lines", "connectivity_lines", "dumpsys_wifi_lines"):
            for line in phase_state.get(key, [])[:16]:
                evidence_rows.append([f"{phase}.{key}", line])
    return "\n".join(
        [
            "# V438 Android Wi-Fi Re-enable Observation",
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
            f"- wifi_enable_executed: `{manifest['wifi_enable_executed']}`",
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
    print(f"wifi_enable_executed: {manifest['wifi_enable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
