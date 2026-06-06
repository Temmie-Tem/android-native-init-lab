#!/usr/bin/env python3
"""V433 read-only Android Wi-Fi auto-connect containment gate.

V433 characterizes Android's already-connected Wi-Fi state before any explicit
scan/connect/server exposure work.  It samples framework status, routes, DNS
surface, listening sockets, netdev state, and filtered connectivity evidence.
It does not enable Wi-Fi, scan, connect, send network probes, change
credentials, write sysfs/rfkill, start daemons, DHCP, route traffic, reboot, or
flash.
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
from wifi_android_control_gate_v432 import (
    ACTIVE_WIFI_PATTERNS,
    CaptureRecord,
    adb_base,
    adb_shell_command,
    capture_command,
    display_command,
    evidence_text,
    read_capture_file_text,
    read_capture_text,
    redact_text,
    run_process,
    truncate_text,
    wifi_connected as v432_wifi_connected,
    wifi_status_disabled,
    wifi_status_enabled,
    wlan0_has_ip,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v433-android-wifi-autoconnect-containment")
TRAFFIC_PATTERNS = (
    re.compile(r"\b(?:ping|curl|wget|nc|netcat|telnet|iperf3?|nslookup|dig|host)\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+(?:set-wifi-enabled|connect-network|add-network|forget-network|start-scan|force-country-code|set-scan-always-available)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\s+(?:enable|disable)\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bwpa_cli\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\bsetprop\b", re.IGNORECASE),
)
ONE_SHOT_CAPTURES: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in sys.boot_completed ro.build.version.release ro.build.version.sdk ro.product.name ro.hardware "
        "init.svc.vendor.wifi_hal_ext init.svc.vendor.wifi_hal init.svc.wificond init.svc.wpa_supplicant "
        "wlan.driver.status wifi.interface; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        20,
    ),
    (
        "wifi-settings",
        "for s in wifi_on wifi_scan_always_enabled airplane_mode_on captive_portal_mode; do echo \"global.$s=$(settings get global $s 2>/dev/null)\"; done; "
        "for s in location_mode; do echo \"secure.$s=$(settings get secure $s 2>/dev/null)\"; done",
        20,
    ),
    (
        "wifi-framework-services",
        "service list 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|netd|connectivity' || true; "
        "echo '--- dumpsys names ---'; dumpsys -l 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|netd|connectivity' || true",
        30,
    ),
    (
        "wifi-processes",
        "ps -AZ 2>/dev/null | grep -Ei 'android\\.hardware\\.wifi|vendor\\.samsung\\.hardware\\.wifi|wificond|supplicant|cnss|wlan|wifi' || true",
        25,
    ),
    (
        "listening-sockets-readonly",
        "ss -lntu 2>/dev/null || netstat -lntu 2>/dev/null || true",
        25,
    ),
)
SAMPLE_CAPTURES: tuple[tuple[str, str, int], ...] = (
    (
        "cmd-wifi-status",
        "cmd wifi status 2>&1 || true",
        25,
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
        "dumpsys-wifi-filtered",
        "dumpsys wifi 2>/dev/null | grep -Ei 'Wifi is|Wi-Fi is|ClientMode|Supplicant|wlan0|STA|connected|disconnected|NetworkInfo|score|L3Connected|IPv4|NOMINATOR|CMD_START_CONNECT' | head -180 || true",
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
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--sample-interval", type=float, default=10.0)
    parser.add_argument("--v432-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


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


def latest_manifest(pattern: str) -> Path | None:
    candidates = sorted(repo_path("tmp/wifi").glob(pattern), key=lambda path: path.stat().st_mtime)
    for candidate in reversed(candidates):
        manifest = candidate / "manifest.json"
        if manifest.exists():
            return manifest
    return None


def load_v432(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.v432_manifest or latest_manifest("v432-android-control-gate-handoff-live-classifierfix-*")
    if manifest_path is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False}
    resolved = repo_path(manifest_path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "present": True,
        "path": str(resolved),
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "comparison": (payload.get("context") or {}).get("comparison"),
    }


def validate_no_mutating_or_traffic_commands() -> None:
    joined = "\n".join(command for _, command, _ in (*ONE_SHOT_CAPTURES, *SAMPLE_CAPTURES))
    for pattern in (*ACTIVE_WIFI_PATTERNS, *TRAFFIC_PATTERNS):
        if pattern.search(joined):
            raise RuntimeError(f"mutating Wi-Fi or network-traffic command pattern found: {pattern.pattern}")


def run_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def collect_android(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures, state = adb_state(args, store)
    if state != "device":
        return captures, state

    for name, shell_command, timeout in ONE_SHOT_CAPTURES:
        captures.append(capture_command(store, name, adb_shell_command(args, shell_command), max(timeout, args.timeout)))

    samples = max(1, args.samples)
    interval = max(0.0, args.sample_interval)
    for sample_index in range(1, samples + 1):
        if sample_index > 1:
            run_sleep(interval)
        for name, shell_command, timeout in SAMPLE_CAPTURES:
            sample_name = f"sample-{sample_index:02d}-{name}"
            captures.append(capture_command(store, sample_name, adb_shell_command(args, shell_command), max(timeout, args.timeout)))
    return captures, state


def capture_group_text(store: EvidenceStore, captures: list[CaptureRecord], suffix: str) -> str:
    parts: list[str] = []
    for capture in captures:
        if capture.name.endswith(suffix):
            parts.append(read_capture_file_text(store, captures, capture.name))
    return "\n".join(parts)


def parse_settings(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in evidence_text(text).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def default_route_wlan(route_text: str) -> bool:
    evidence = evidence_text(route_text)
    return bool(re.search(r"(?m)^default\b.*\bdev\s+wlan0\b", evidence))


def route_get_wlan(route_get_text: str) -> bool:
    evidence = evidence_text(route_get_text)
    return bool(re.search(r"\bdev\s+wlan0\b", evidence))


def connectivity_validated_wifi(connectivity_text: str) -> bool:
    evidence = evidence_text(connectivity_text).lower()
    return "wifi" in evidence and ("validated" in evidence or "internet" in evidence)


def dns_surface_wlan(connectivity_text: str) -> bool:
    evidence = evidence_text(connectivity_text).lower()
    return "wlan0" in evidence and ("dns" in evidence or "dnsaddresses" in evidence)


def global_listener_observed(socket_text: str) -> bool:
    evidence = evidence_text(socket_text)
    for line in evidence.splitlines():
        lowered = line.lower()
        if "listen" not in lowered:
            continue
        if "127.0.0.1" in line or "::1" in line:
            continue
        if "0.0.0.0" in line or "[::]" in line or "*:" in line or "<ipv4>" in line:
            return True
    return False


def stable_bool(values: list[bool]) -> bool:
    return bool(values) and all(value == values[0] for value in values)


def matching_lines(text: str, pattern: str, limit: int = 160) -> list[str]:
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


def classify(args: argparse.Namespace, store: EvidenceStore, captures: list[CaptureRecord], state: str, v432: dict[str, Any]) -> dict[str, Any]:
    identity_text = read_capture_file_text(store, captures, "identity-props")
    settings_text = read_capture_file_text(store, captures, "wifi-settings")
    services_text = read_capture_file_text(store, captures, "wifi-framework-services")
    processes_text = read_capture_file_text(store, captures, "wifi-processes")
    socket_text = read_capture_file_text(store, captures, "listening-sockets-readonly")
    status_text = capture_group_text(store, captures, "cmd-wifi-status")
    route_text = capture_group_text(store, captures, "route-state")
    route_get_text = capture_group_text(store, captures, "route-get-external-readonly")
    netdev_text = capture_group_text(store, captures, "netdev-state")
    connectivity_text = capture_group_text(store, captures, "connectivity-filtered")
    dumpsys_wifi_text = capture_group_text(store, captures, "dumpsys-wifi-filtered")
    settings = parse_settings(settings_text)

    boot_complete = "sys.boot_completed=1" in identity_text
    cmd_status_ok = any(capture.name.endswith("cmd-wifi-status") and capture.ok for capture in captures)
    enabled_by_status = wifi_status_enabled(status_text) or settings.get("global.wifi_on") == "1"
    disabled_by_status = wifi_status_disabled(status_text) or settings.get("global.wifi_on") == "0"
    connected_samples = [
        v432_wifi_connected(read_capture_file_text(store, captures, capture.name), dumpsys_wifi_text)
        for capture in captures
        if capture.name.endswith("cmd-wifi-status")
    ]
    has_ip_samples = [
        wlan0_has_ip(read_capture_file_text(store, captures, capture.name))
        for capture in captures
        if capture.name.endswith("netdev-state")
    ]
    route_samples = [
        default_route_wlan(read_capture_file_text(store, captures, capture.name))
        for capture in captures
        if capture.name.endswith("route-state")
    ]
    route_get_samples = [
        route_get_wlan(read_capture_file_text(store, captures, capture.name))
        for capture in captures
        if capture.name.endswith("route-get-external-readonly")
    ]
    wifi_connected = any(connected_samples)
    wlan0_ip = any(has_ip_samples)
    default_route = any(route_samples)
    route_candidate = any(route_get_samples)
    route_stable = stable_bool(route_samples) and stable_bool(route_get_samples)
    connected_stable = stable_bool(connected_samples)
    ip_stable = stable_bool(has_ip_samples)
    validated_wifi = connectivity_validated_wifi(connectivity_text)
    dns_on_wlan = dns_surface_wlan(connectivity_text)
    global_listener = global_listener_observed(socket_text)
    airplane_off = settings.get("global.airplane_mode_on") in {"0", "null", ""}
    framework_services = all(token in services_text for token in ("wifi", "connectivity"))
    runtime_processes = all(token in processes_text for token in ("android.hardware.wifi@1.0-service", "vendor.samsung.hardware.wifi@2.0-service", "wificond", "wpa_supplicant"))
    v432_auto = (v432.get("decision") == "v432-android-wifi-already-connected-auto-gate-pass")

    if state == "adb-missing":
        decision = "v433-android-autoconnect-containment-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
        next_gate = "restore ADB availability"
    elif state != "device":
        decision = "v433-android-autoconnect-containment-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        next_gate = "boot Android before V433"
    elif not boot_complete:
        decision = "v433-android-autoconnect-containment-bootcomplete-missing"
        pass_ok = False
        reason = "Android ADB is online, but sys.boot_completed=1 was not observed"
        next_gate = "wait for boot-complete before containment sampling"
    elif wifi_connected and (default_route or route_candidate or validated_wifi):
        decision = "v433-android-wifi-autoconnect-exposure-mapped"
        pass_ok = True
        reason = "Android Wi-Fi auto-connect is active and route/connectivity evidence shows possible external exposure"
        next_gate = "V434 policy decision: disable auto-connect for lab runs or continue with bounded exposure-aware stability"
    elif wifi_connected:
        decision = "v433-android-wifi-autoconnect-contained-map-pass"
        pass_ok = True
        reason = "Android Wi-Fi is connected, but sampled route evidence did not prove default external exposure"
        next_gate = "V434 bounded stability or intentional-disable cleanup gate"
    elif enabled_by_status and wlan0_ip:
        decision = "v433-android-wifi-enabled-ip-contained-map-pass"
        pass_ok = True
        reason = "Android Wi-Fi is enabled with wlan0 IP evidence, but connected state was not proven"
        next_gate = "review status before scan/connect"
    elif disabled_by_status:
        decision = "v433-android-wifi-disabled-contained-pass"
        pass_ok = True
        reason = "Android Wi-Fi appears disabled during containment sampling"
        next_gate = "enable-only gate may be reconsidered if needed"
    elif cmd_status_ok:
        decision = "v433-android-autoconnect-containment-review-required"
        pass_ok = True
        reason = "Android Wi-Fi status responded but containment state is ambiguous"
        next_gate = "manual review before any mutating Wi-Fi command"
    else:
        decision = "v433-android-autoconnect-containment-blocked"
        pass_ok = False
        reason = "V433 could not collect enough Android Wi-Fi containment evidence"
        next_gate = "repair Android control evidence before continuing"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "adb_state": state,
        "boot_complete": boot_complete,
        "samples_requested": max(1, args.samples),
        "sample_interval_sec": max(0.0, args.sample_interval),
        "cmd_status_ok": cmd_status_ok,
        "enabled_by_status": enabled_by_status,
        "disabled_by_status": disabled_by_status,
        "wifi_connected": wifi_connected,
        "wifi_connected_stable": connected_stable,
        "wlan0_has_ip": wlan0_ip,
        "wlan0_ip_stable": ip_stable,
        "default_route_wlan": default_route,
        "route_get_wlan": route_candidate,
        "route_stable": route_stable,
        "connectivity_validated_wifi": validated_wifi,
        "dns_surface_wlan": dns_on_wlan,
        "global_listener_observed": global_listener,
        "airplane_off": airplane_off,
        "framework_services_present": framework_services,
        "runtime_processes_present": runtime_processes,
        "v432_auto_connect_input": v432_auto,
        "v432": v432,
        "wifi_status_lines": matching_lines(status_text, r"wifi|ssid|bssid|supplicant|connected|disabled|enabled|rssi|score"),
        "route_lines": matching_lines(route_text + "\n" + route_get_text, r"default|wlan0|src|via|uid|table"),
        "netdev_lines": matching_lines(netdev_text, r"wlan0|inet|state|operstate|carrier|mtu"),
        "connectivity_lines": matching_lines(connectivity_text, r"wifi|validated|default|dns|route|internet|metered|score"),
        "socket_lines": matching_lines(socket_text, r"listen|tcp|udp|0\\.0\\.0\\.0|::|\\*:"),
        "dumpsys_wifi_lines": matching_lines(dumpsys_wifi_text, r"wifi|clientmode|supplicant|connected|l3connected|ipv4|nominator|cmd_start_connect"),
    }


def guardrails() -> list[str]:
    return [
        "read-only Android Wi-Fi auto-connect containment sampling only",
        "no Wi-Fi enable/disable, no scan/connect, no credentials, no DHCP/routing changes",
        "no ping/curl/wget/nc/dig/nslookup or external packet probe",
        "ip route get is allowed because it is local route lookup only",
        "no rfkill/sysfs write, module operation, setprop, or daemon start",
        "redacts MAC, IP, SSID/BSSID, serial, and credential-like fields",
    ]


def run_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v433-android-autoconnect-containment-plan-ready",
        "pass": True,
        "reason": "read-only Android Wi-Fi auto-connect containment plan generated",
        "host": collect_host_metadata(),
        "v432": load_v432(args),
        "samples": max(1, args.samples),
        "sample_interval_sec": max(0.0, args.sample_interval),
        "host_commands": [
            display_command([*adb_base(args), "devices", "-l"]),
            display_command([*adb_base(args), "get-state"]),
        ],
        "one_shot_captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in ONE_SHOT_CAPTURES],
        "sample_captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in SAMPLE_CAPTURES],
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    if state == "device":
        decision = "v433-android-autoconnect-containment-adb-online"
        pass_ok = True
        reason = "Android ADB is online; run mode can collect read-only containment samples"
    elif state == "adb-missing":
        decision = "v433-android-autoconnect-containment-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    else:
        decision = "v433-android-autoconnect-containment-waiting-for-android"
        pass_ok = True
        reason = f"Android ADB is not online yet (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "v432": load_v432(args),
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v432 = load_v432(args)
    captures, state = collect_android(args, store)
    classification = classify(args, store, captures, state, v432)
    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification", {})
    captures = manifest.get("captures", [])
    capture_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in captures
    ]
    state_rows = [
        ["boot_complete", classification.get("boot_complete", "-")],
        ["wifi_connected", classification.get("wifi_connected", "-")],
        ["wifi_connected_stable", classification.get("wifi_connected_stable", "-")],
        ["wlan0_has_ip", classification.get("wlan0_has_ip", "-")],
        ["wlan0_ip_stable", classification.get("wlan0_ip_stable", "-")],
        ["default_route_wlan", classification.get("default_route_wlan", "-")],
        ["route_get_wlan", classification.get("route_get_wlan", "-")],
        ["route_stable", classification.get("route_stable", "-")],
        ["connectivity_validated_wifi", classification.get("connectivity_validated_wifi", "-")],
        ["dns_surface_wlan", classification.get("dns_surface_wlan", "-")],
        ["global_listener_observed", classification.get("global_listener_observed", "-")],
        ["v432_auto_connect_input", classification.get("v432_auto_connect_input", "-")],
    ]
    evidence_rows: list[list[str]] = []
    for key in ("wifi_status_lines", "route_lines", "netdev_lines", "connectivity_lines", "socket_lines", "dumpsys_wifi_lines"):
        for value in classification.get(key, [])[:22]:
            evidence_rows.append([key, value])
    return "\n".join(
        [
            "# V433 Android Wi-Fi Auto-connect Containment Gate",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- adb_state: `{manifest.get('adb_state', classification.get('adb_state', '-'))}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## State Summary",
            "",
            markdown_table(["item", "value"], [[str(a), str(b)] for a, b in state_rows]),
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
    validate_no_mutating_or_traffic_commands()
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
