#!/usr/bin/env python3
"""V432 read-only Android-managed Wi-Fi control gate.

V432 checks whether Android's existing Wi-Fi runtime is ready for a later
bounded control action.  It uses read-only framework status, settings, service,
and netdev captures.  It does not enable Wi-Fi, scan, connect, change
credentials, start daemons, write sysfs/rfkill, DHCP, route traffic, reboot, or
flash.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v432-android-wifi-control-gate")
ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\bcmd\s+wifi\s+(?:set-wifi-enabled|connect-network|add-network|forget-network|start-scan|force-country-code|set-scan-always-available)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\s+(?:enable|disable)\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bwpa_cli\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\bsetprop\b", re.IGNORECASE),
)
WIFI_LINE_RE = re.compile(r"wifi|wlan|wificond|supplicant|wpa|cnss|network|internet|sta|clientmode", re.IGNORECASE)

ANDROID_SHELL_CAPTURES: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in sys.boot_completed ro.build.version.release ro.build.version.sdk ro.product.name ro.hardware "
        "init.svc.vendor.wifi_hal_ext init.svc.vendor.wifi_hal init.svc.wificond init.svc.wpa_supplicant "
        "wlan.driver.status wifi.interface; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        20,
    ),
    (
        "cmd-wifi-status",
        "cmd wifi status 2>&1 || true",
        25,
    ),
    (
        "cmd-wifi-help-head",
        "cmd wifi 2>&1 | head -80 || true",
        25,
    ),
    (
        "wifi-global-settings",
        "for s in wifi_on wifi_scan_always_enabled airplane_mode_on captive_portal_mode; do echo \"$s=$(settings get global $s 2>/dev/null)\"; done",
        20,
    ),
    (
        "wifi-secure-settings",
        "for s in location_mode; do echo \"$s=$(settings get secure $s 2>/dev/null)\"; done",
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
        "wifi-netdev-state",
        "ip link show wlan0 2>/dev/null || true; ip -o addr show wlan0 2>/dev/null || true; "
        "for f in operstate carrier mtu address; do [ -e /sys/class/net/wlan0/$f ] && echo \"$f=$(cat /sys/class/net/wlan0/$f 2>/dev/null)\"; done; "
        "echo '--- all wifi netdevs ---'; for d in /sys/class/net/wlan0 /sys/class/net/swlan0 /sys/class/net/wifi-aware0; do [ -e \"$d\" ] && echo \"$d $(cat \"$d/operstate\" 2>/dev/null)\"; done",
        25,
    ),
    (
        "wifi-rfkill-readonly",
        "for r in /sys/class/rfkill/rfkill*; do [ -e \"$r\" ] || continue; echo \"node=$r\"; for f in name type state soft hard persistent; do [ -e \"$r/$f\" ] && echo \"$f=$(cat \"$r/$f\" 2>/dev/null)\"; done; done",
        25,
    ),
    (
        "dumpsys-wifi-control-filtered",
        "dumpsys wifi 2>/dev/null | grep -Ei 'Wi-Fi is|Wifi is|mWifi|wifi enabled|ClientMode|Supplicant|wlan0|STA|connected|disconnected|NetworkInfo|score|country|interface' | head -160 || true",
        40,
    ),
)


@dataclass
class CaptureRecord:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--v431-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", value).strip("-") or "capture"


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell_command(args: argparse.Namespace, shell_command: str) -> list[str]:
    return [*adb_base(args), "shell", shell_command]


def display_command(command: list[str]) -> str:
    redacted = ["<adb-serial>" if index > 0 and command[index - 1] == "-s" else part for index, part in enumerate(command)]
    return " ".join(shlex.quote(part) for part in redacted)


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ipv4>", text)
    text = re.sub(r"(?i)(Wifi is connected to )\"[^\"]+\"", r"\1\"<redacted>\"", text)
    text = re.sub(r"(?i)(targetConfigKey=)\"[^\"]+\"([A-Z0-9_]+)?", r"\1\"<redacted>\"\2", text)
    text = re.sub(r"(?i)(nid=\d+\s+)\"[^\"]+\"([A-Z0-9_]+)?", r"\1\"<redacted>\"\2", text)
    text = re.sub(r"(?i)((?:\\)?\"<redacted>(?:\\)?\")(WPA(?:2|3)?_[A-Z0-9_]+|SAE|OWE|EAP|PSK)\b", r"\1<security>", text)
    text = re.sub(r"(?i)(Security type:\s*)\d+", r"\1<redacted>", text)
    text = re.sub(r"(?i)(networkType=)TYPE_[A-Z0-9_]+", r"\1<security>", text)
    text = re.sub(r"(?i)(\s)\"[^\"]+\"(\s+<mac>\s+rssi=)", r"\1\"<redacted>\"\2", text)
    text = re.sub(r"(?i)(\b(?:ssid|bssid|psk|password|passphrase|identity|anonymous_identity|fqdn|providerFriendlyName)\b)[:=]\s*([^\s\]]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(\[(?:SSID|BSSID)\]:\s*\[)([^\]]+)(\])", r"\1<redacted>\3", text)
    text = re.sub(r"(?im)^([A-Za-z0-9_.:-]+)(\s+(?:device|recovery|sideload|offline|unauthorized)\b)", r"<adb-serial>\2", text)
    text = re.sub(
        r"(?i)(\b(?:androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)\b)[:=]\s*([^\s\]]+)",
        r"\1=<redacted>",
        text,
    )
    return text


def truncate_text(text: str, limit: int = 14000) -> str:
    redacted = redact_text(text)
    if len(redacted) > limit:
        return redacted[:limit] + "\n[truncated in manifest]\n"
    return redacted


def validate_no_active_wifi_commands() -> None:
    joined = "\n".join(command for _, command, _ in ANDROID_SHELL_CAPTURES)
    for pattern in ACTIVE_WIFI_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"active or mutating Wi-Fi command pattern found: {pattern.pattern}")


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except FileNotFoundError as exc:
        return None, "", str(exc), time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def write_capture(store: EvidenceStore, name: str, command: list[str], text: str, error: str, rc: int | None) -> str:
    body = "\n".join(
        [
            f"$ {display_command(command)}",
            redact_text(text if text else error).rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"commands/{safe_name(name)}.txt", body)
    return str(path.relative_to(store.run_dir))


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: int) -> CaptureRecord:
    rc, text, error, duration = run_process(command, timeout)
    relative = write_capture(store, name, command, text, error, rc)
    return CaptureRecord(
        name=name,
        command=display_command(command),
        ok=rc == 0,
        rc=rc,
        duration_sec=duration,
        file=relative,
        text=truncate_text(text),
        error=error,
    )


def read_capture_text(captures: list[CaptureRecord], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return capture.text
    return ""


def read_capture_file_text(store: EvidenceStore, captures: list[CaptureRecord], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.run_dir / capture.file
        if not path.exists():
            return capture.text
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def evidence_text(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("$"))


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


def load_v431(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.v431_manifest or latest_manifest("v431-android-runtime-gap-handoff-live-su-quote-*")
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


def collect_android(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures, state = adb_state(args, store)
    if state != "device":
        return captures, state
    for name, shell_command, timeout in ANDROID_SHELL_CAPTURES:
        captures.append(capture_command(store, name, adb_shell_command(args, shell_command), max(timeout, args.timeout)))
    return captures, state


def parse_settings(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in evidence_text(text).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def wifi_status_enabled(text: str) -> bool:
    evidence = evidence_text(text).lower()
    return "wifi is enabled" in evidence or "wi-fi is enabled" in evidence or "enabled" in evidence and "disabled" not in evidence


def wifi_status_disabled(text: str) -> bool:
    evidence = evidence_text(text).lower()
    return "wifi is disabled" in evidence or "wi-fi is disabled" in evidence


def wlan0_up_lower(text: str) -> bool:
    evidence = evidence_text(text)
    return "wlan0:" in evidence and "UP" in evidence and "LOWER_UP" in evidence


def wlan0_has_ip(text: str) -> bool:
    evidence = evidence_text(text)
    return bool(re.search(r"\binet\s+(?:(?:\d{1,3}\.){3}\d{1,3}|<ipv4>)", evidence))


def wifi_connected(text: str, dumpsys_text: str) -> bool:
    evidence = (evidence_text(text) + "\n" + evidence_text(dumpsys_text)).lower()
    return (
        "wifi is connected" in evidence
        or "curstate=l3connectedstate" in evidence
        or "cmd_ipv4_provisioning_success" in evidence
        or "supplicant state: completed" in evidence
    )


def auto_connect_observed(dumpsys_text: str) -> bool:
    evidence = evidence_text(dumpsys_text).lower()
    return "cmd_start_connect" in evidence or "nominator_saved" in evidence or "networkcreator=creator_user" in evidence


def unique_matching_lines(text: str, limit: int = 220) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in evidence_text(text).splitlines():
        line = raw_line.strip()
        if not line or "grep -" in line:
            continue
        if not WIFI_LINE_RE.search(line):
            continue
        redacted = redact_text(line)
        if redacted in seen:
            continue
        seen.add(redacted)
        lines.append(redacted)
        if len(lines) >= limit:
            break
    return lines


def classify(args: argparse.Namespace, store: EvidenceStore, captures: list[CaptureRecord], state: str, v431: dict[str, Any]) -> dict[str, Any]:
    identity_text = read_capture_file_text(store, captures, "identity-props")
    status_text = read_capture_file_text(store, captures, "cmd-wifi-status")
    global_settings_text = read_capture_file_text(store, captures, "wifi-global-settings")
    secure_settings_text = read_capture_file_text(store, captures, "wifi-secure-settings")
    services_text = read_capture_file_text(store, captures, "wifi-framework-services")
    processes_text = read_capture_file_text(store, captures, "wifi-processes")
    netdev_text = read_capture_file_text(store, captures, "wifi-netdev-state")
    rfkill_text = read_capture_file_text(store, captures, "wifi-rfkill-readonly")
    dumpsys_text = read_capture_file_text(store, captures, "dumpsys-wifi-control-filtered")
    global_settings = parse_settings(global_settings_text)
    secure_settings = parse_settings(secure_settings_text)

    boot_complete = "sys.boot_completed=1" in identity_text
    cmd_status_ok = any(capture.name == "cmd-wifi-status" and capture.ok for capture in captures)
    enabled_by_status = wifi_status_enabled(status_text) or "wifi_on=1" in global_settings_text
    disabled_by_status = wifi_status_disabled(status_text) or global_settings.get("wifi_on") == "0"
    wlan_ready = wlan0_up_lower(netdev_text)
    has_ip = wlan0_has_ip(netdev_text)
    connected = wifi_connected(status_text, dumpsys_text)
    auto_connect = auto_connect_observed(dumpsys_text) or connected
    airplane_off = global_settings.get("airplane_mode_on") in {"0", "null", ""}
    framework_services = all(token in services_text for token in ("wifi", "wificond"))
    runtime_processes = all(token in processes_text for token in ("android.hardware.wifi@1.0-service", "vendor.samsung.hardware.wifi@2.0-service", "wificond", "wpa_supplicant"))
    v431_pass = bool(v431.get("pass"))

    if state == "adb-missing":
        decision = "v432-android-control-gate-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
        next_gate = "restore ADB availability"
    elif state != "device":
        decision = "v432-android-control-gate-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        next_gate = "boot Android before V432"
    elif not boot_complete:
        decision = "v432-android-control-gate-bootcomplete-missing"
        pass_ok = False
        reason = "Android ADB is online, but sys.boot_completed=1 was not observed"
        next_gate = "wait for boot-complete before Wi-Fi control planning"
    elif enabled_by_status and connected and framework_services and runtime_processes:
        decision = "v432-android-wifi-already-connected-auto-gate-pass"
        pass_ok = True
        reason = "Android boot-complete auto-connected Wi-Fi through saved framework state without V432 issuing enable/scan/connect"
        next_gate = "V433 containment/stability gate; do not run enable, scan, or connect until auto-connect risk is controlled"
    elif enabled_by_status and (wlan_ready or has_ip) and framework_services and runtime_processes:
        decision = "v432-android-wifi-already-up-control-gate-pass"
        pass_ok = True
        reason = "Android reports Wi-Fi enabled/ready and wlan0 is already UP+LOWER_UP; no enable action is needed"
        next_gate = "V433 status-stability or redacted scan-only gate; keep connect/credentials/routing blocked"
    elif disabled_by_status and airplane_off and v431_pass:
        decision = "v432-android-wifi-enable-only-ready"
        pass_ok = True
        reason = "Android Wi-Fi appears disabled but V431 runtime prerequisites and airplane-mode guard allow an enable-only plan"
        next_gate = "V433 enable-only gate with immediate status capture and disable/rollback cleanup"
    elif cmd_status_ok and v431_pass:
        decision = "v432-android-wifi-control-review-required"
        pass_ok = True
        reason = "Wi-Fi framework responded but status is ambiguous; review evidence before a mutating gate"
        next_gate = "manual review of status/dumpsys before enable-only or scan-only"
    else:
        decision = "v432-android-wifi-control-blocked"
        pass_ok = False
        reason = "Wi-Fi control preflight did not prove framework/runtime readiness"
        next_gate = "repair Android runtime evidence before mutating Wi-Fi control"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "adb_state": state,
        "boot_complete": boot_complete,
        "cmd_status_ok": cmd_status_ok,
        "enabled_by_status": enabled_by_status,
        "disabled_by_status": disabled_by_status,
        "wlan0_up_lower": wlan_ready,
        "wlan0_has_ip": has_ip,
        "wifi_connected": connected,
        "android_auto_connect_observed": auto_connect,
        "airplane_off": airplane_off,
        "global_settings": global_settings,
        "secure_settings": secure_settings,
        "framework_services_present": framework_services,
        "runtime_processes_present": runtime_processes,
        "v431": v431,
        "wifi_status_lines": unique_matching_lines(status_text),
        "wifi_settings_lines": unique_matching_lines(global_settings_text + "\n" + secure_settings_text),
        "wifi_service_lines": unique_matching_lines(services_text),
        "wifi_process_lines": unique_matching_lines(processes_text),
        "wifi_netdev_lines": unique_matching_lines(netdev_text),
        "wifi_rfkill_lines": unique_matching_lines(rfkill_text),
        "wifi_dumpsys_lines": unique_matching_lines(dumpsys_text),
    }


def guardrails() -> list[str]:
    return [
        "read-only Android Wi-Fi framework status only",
        "cmd wifi status is allowed; cmd wifi mutation subcommands are blocked",
        "no svc wifi enable/disable, no set-wifi-enabled, no start-scan, no connect-network",
        "no credentials, DHCP, routing, rfkill/sysfs write, module operation, setprop, or daemon start",
        "redacts MAC, IP, SSID/BSSID, and credential-like fields",
    ]


def run_plan(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v432-android-control-gate-plan-ready",
        "pass": True,
        "reason": "read-only Android-managed Wi-Fi control gate plan generated",
        "host": collect_host_metadata(),
        "v431": load_v431(args),
        "host_commands": [
            display_command([*adb_base(args), "devices", "-l"]),
            display_command([*adb_base(args), "get-state"]),
        ],
        "android_shell_captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in ANDROID_SHELL_CAPTURES],
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    if state == "device":
        decision = "v432-android-control-gate-adb-online"
        pass_ok = True
        reason = "Android ADB is online; run mode can collect read-only control preflight"
    elif state == "adb-missing":
        decision = "v432-android-control-gate-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    else:
        decision = "v432-android-control-gate-waiting-for-android"
        pass_ok = True
        reason = f"Android ADB is not online yet (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "v431": load_v431(args),
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v431 = load_v431(args)
    captures, state = collect_android(args, store)
    classification = classify(args, store, captures, state, v431)
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
        ["enabled_by_status", classification.get("enabled_by_status", "-")],
        ["disabled_by_status", classification.get("disabled_by_status", "-")],
        ["wlan0_up_lower", classification.get("wlan0_up_lower", "-")],
        ["wlan0_has_ip", classification.get("wlan0_has_ip", "-")],
        ["wifi_connected", classification.get("wifi_connected", "-")],
        ["android_auto_connect_observed", classification.get("android_auto_connect_observed", "-")],
        ["airplane_off", classification.get("airplane_off", "-")],
        ["framework_services_present", classification.get("framework_services_present", "-")],
        ["runtime_processes_present", classification.get("runtime_processes_present", "-")],
    ]
    evidence_rows: list[list[str]] = []
    for key in ("wifi_status_lines", "wifi_settings_lines", "wifi_service_lines", "wifi_process_lines", "wifi_netdev_lines", "wifi_dumpsys_lines"):
        for value in classification.get(key, [])[:20]:
            evidence_rows.append([key, value])
    return "\n".join(
        [
            "# V432 Android-managed Wi-Fi Control Gate",
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
    validate_no_active_wifi_commands()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = run_plan(args, store)
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
