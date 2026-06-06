#!/usr/bin/env python3
"""V590 Android read-only modem/esoc subsystem state sampler.

This collector is intended to run only while Android ADB is available. It
captures read-only modem/esoc subsystem state, rpmsg, QRTR, and readiness
timeline evidence. It must not enable Wi-Fi, start HALs, scan, connect, route,
or ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v590-android-subsys-state-sample")
DEFAULT_TIMEOUT = 45.0

STATE_PATHS = {
    "mss_uevent": "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/uevent",
    "mss_name": "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/name",
    "mss_state": "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state",
    "mss_restart_level": "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/restart_level",
    "mss_firmware_name": "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/firmware_name",
    "mss_crash_count": "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/crash_count",
    "mdm3_uevent": "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/uevent",
    "mdm3_name": "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/name",
    "mdm3_state": "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state",
    "mdm3_restart_level": "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/restart_level",
    "mdm3_firmware_name": "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/firmware_name",
    "mdm3_crash_count": "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/crash_count",
    "rpmsg_drivers_autoprobe": "/sys/bus/rpmsg/drivers_autoprobe",
}

READINESS_RE = re.compile(
    r"qrtr: Modem QMI Readiness|sysmon-qmi|service-notifier|wlan_pd|"
    r"icnss_qmi: QMI Server Connected|BDF file|regdb\.bin|bdwlan\.bin|"
    r"WLAN FW is ready|wlan0",
    re.I,
)
SENSITIVE_REPLACEMENTS = (
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
    (re.compile(r"(?i)(ssid|bssid|psk|password|passphrase)=([^\s]+)"), r"\1=<redacted>"),
    (re.compile(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)"), r"\1=<redacted>"),
)


@dataclass(frozen=True)
class Capture:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
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
    parser.add_argument("--serial")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sample-delay", type=float, default=5.0)
    parser.add_argument("--no-su", action="store_true", help="do not run adb shell commands through su -c")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.no_su:
        return [*adb_base(args), "shell", shell_command]
    return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell_command)]


def shell_state_command(prefix: str, delay: float = 0.0) -> str:
    lines = []
    if delay > 0:
        lines.append(f"sleep {delay:.3f}")
    lines.append(f"echo 'A90_ANDROID_SUBSYS_SAMPLE {prefix} BEGIN'")
    for key, path in STATE_PATHS.items():
        lines.append(f"echo '### {key} {path}'")
        lines.append(f"cat {shlex.quote(path)} 2>&1 || true")
    lines.append(f"echo 'A90_ANDROID_SUBSYS_SAMPLE {prefix} END'")
    return "; ".join(lines)


def run_command(command: list[str], timeout: float) -> tuple[int | None, str, str, float]:
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
    except Exception as exc:  # noqa: BLE001 - evidence runner preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def redact(text: str) -> str:
    redacted = text
    for pattern, replacement in SENSITIVE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, command: list[str], rc: int | None, text: str, error: str, duration: float) -> Capture:
    body = f"$ {' '.join(command)}\n{redact(text if text else error).rstrip()}\nrc={rc}\n"
    path = store.write_text(f"android/commands/{safe_name(name)}.txt", body)
    visible = redact(text)
    if len(visible) > 8192:
        visible = visible[:8192] + "\n[truncated in manifest]\n"
    return Capture(
        name=name,
        command=" ".join(command),
        ok=rc == 0,
        rc=rc,
        status="ok" if rc == 0 else "missing",
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        text=visible,
        error=error,
    )


def adb_devices(args: argparse.Namespace) -> dict[str, Any]:
    rc, text, error, duration = run_command([*adb_base(args), "devices", "-l"], timeout=10.0)
    devices: list[str] = []
    for raw_line in text.splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return {
        "rc": rc,
        "text": redact(text),
        "error": error,
        "duration_sec": duration,
        "devices": devices,
        "device_count": len(devices),
    }


def selected_device_available(args: argparse.Namespace, devices: dict[str, Any]) -> bool:
    if args.serial:
        return args.serial in devices["devices"]
    return devices["device_count"] == 1


def capture_shell(args: argparse.Namespace, store: EvidenceStore, name: str, shell_command: str, timeout: float) -> Capture:
    command = adb_shell(args, shell_command)
    rc, text, error, duration = run_command(command, timeout=max(args.timeout, timeout))
    return write_capture(store, name, command, rc, text, error, duration)


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    rc, text, error, duration = run_command([*adb_base(args), "wait-for-device"], timeout=args.timeout)
    captures.append(write_capture(store, "adb-wait-for-device", [*adb_base(args), "wait-for-device"], rc, text, error, duration))
    captures.append(capture_shell(args, store, "boot-props", "echo sys.boot_completed=$(getprop sys.boot_completed); echo init.svc.vendor.qrtr-ns=$(getprop init.svc.vendor.qrtr-ns); echo init.svc.cnss-daemon=$(getprop init.svc.cnss-daemon); echo init.svc.cnss_diag=$(getprop init.svc.cnss_diag)", 10.0))
    captures.append(capture_shell(args, store, "subsys-state-initial", shell_state_command("initial"), 15.0))
    captures.append(capture_shell(args, store, "rpmsg-devices", "find /sys/bus/rpmsg/devices -maxdepth 2 -print 2>&1 || true", 15.0))
    captures.append(capture_shell(args, store, "proc-net-qrtr", "cat /proc/net/qrtr 2>&1 || true", 10.0))
    captures.append(capture_shell(args, store, "readiness-dmesg-tail", "dmesg 2>&1 | grep -Ei 'qrtr: Modem QMI Readiness|sysmon-qmi|service-notifier|wlan_pd|icnss_qmi: QMI Server Connected|BDF file|regdb\\.bin|bdwlan\\.bin|WLAN FW is ready|wlan0' | tail -n 240 || true", 20.0))
    captures.append(capture_shell(args, store, "subsys-state-delayed", shell_state_command("delayed", args.sample_delay), args.sample_delay + 20.0))
    return captures


def boot_completed(captures: list[Capture]) -> bool:
    text = "\n".join(capture.text for capture in captures if capture.name == "boot-props")
    return "sys.boot_completed=1" in text


def parse_state_capture(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_key = ""
    for raw_line in redact(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            parts = line.split(maxsplit=2)
            current_key = parts[1] if len(parts) >= 2 else ""
            continue
        if not current_key or line.startswith("$") or line.startswith("A90_ANDROID_SUBSYS_SAMPLE"):
            continue
        if line.startswith("cat:") or line.startswith("/system/bin/sh:"):
            values[current_key] = line
        elif current_key not in values:
            values[current_key] = line
    return values


def readiness_lines(captures: list[Capture]) -> list[str]:
    lines: list[str] = []
    for capture in captures:
        if capture.name != "readiness-dmesg-tail":
            continue
        for raw_line in capture.text.splitlines():
            line = raw_line.strip()
            if line and not line.startswith("$") and READINESS_RE.search(line):
                lines.append(line)
    return lines[-120:]


def summarize(captures: list[Capture], store: EvidenceStore) -> dict[str, Any]:
    initial = parse_state_capture("\n".join(capture.text for capture in captures if capture.name == "subsys-state-initial"))
    delayed = parse_state_capture("\n".join(capture.text for capture in captures if capture.name == "subsys-state-delayed"))
    selected = delayed or initial
    normalized_lines = [f"{key}={selected.get(key, '')}" for key in sorted(STATE_PATHS)]
    normalized = "\n".join(normalized_lines).rstrip() + "\n"
    store.write_text("android-subsys-state.txt", normalized)
    lower_lines = readiness_lines(captures)
    return {
        "boot_completed": boot_completed(captures),
        "all_commands_ok": all(capture.ok for capture in captures),
        "initial_values": initial,
        "delayed_values": delayed,
        "selected_values": selected,
        "mss_state": selected.get("mss_state", ""),
        "mdm3_state": selected.get("mdm3_state", ""),
        "state_values_ready": bool(selected.get("mss_state")) and bool(selected.get("mdm3_state")),
        "non_offline_state": any(
            str(selected.get(key, "")).upper() not in {"", "OFFLINE", "OFFLINING"}
            for key in ("mss_state", "mdm3_state")
        ),
        "readiness_lines": lower_lines,
        "has_qrtr_readiness": any("Modem QMI Readiness" in line for line in lower_lines),
        "has_sysmon_qmi": any("sysmon-qmi" in line for line in lower_lines),
        "has_service_notifier": any("service-notifier" in line for line in lower_lines),
        "has_wlan_pd": any("wlan_pd" in line for line in lower_lines),
    }


def decide(args: argparse.Namespace,
           devices: dict[str, Any],
           captures: list[Capture],
           summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v590-android-subsys-state-sample-plan-ready", True, "plan-only; no adb command executed", "boot Android and run V590 collector"
    if devices["device_count"] == 0:
        return "v590-android-adb-unavailable", True, "no Android ADB device is currently visible", "boot Android or run approved Android handoff before V590 run"
    if not selected_device_available(args, devices):
        return "v590-android-adb-selection-needed", True, f"device_count={devices['device_count']}", "rerun with --serial"
    if args.command == "preflight":
        return "v590-android-subsys-state-preflight-ready", True, "one Android ADB device is visible", "run V590 Android read-only state sample"
    if not captures:
        return "v590-android-subsys-state-review", False, "run command did not produce captures", "inspect runner failure"
    if not summary.get("boot_completed"):
        return "v590-android-not-boot-complete", False, "Android ADB is visible but sys.boot_completed=1 was not captured", "wait for Android boot-complete and rerun V590"
    if not summary.get("state_values_ready"):
        return "v590-android-subsys-state-missing", False, "Android booted but modem/esoc state values were not captured", "inspect sysfs paths and root availability"
    if summary.get("non_offline_state"):
        return (
            "v590-android-subsys-nonoffline-captured",
            True,
            f"Android read-only sample captured non-offline modem/esoc state: mss={summary.get('mss_state')} mdm3={summary.get('mdm3_state')}",
            "rerun V589 with the V590 android-subsys-state.txt sample, then plan native readiness trigger if delta is confirmed",
        )
    return (
        "v590-android-subsys-still-offline-captured",
        True,
        f"Android read-only sample captured modem/esoc state but both remain offline-class: mss={summary.get('mss_state')} mdm3={summary.get('mdm3_state')}",
        "capture a tighter Android timing window or compare rpmsg/QRTR readiness before native trigger design",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    summary = manifest.get("android_summary") or {}
    capture_rows = [[item["name"], item["status"], item["rc"], item["duration_sec"], item["file"]] for item in captures]
    selected_rows = [[key, value] for key, value in sorted((summary.get("selected_values") or {}).items())]
    readiness = summary.get("readiness_lines") or []
    return "\n".join([
        "# V590 Android Subsystem State Sample",
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
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## ADB Devices",
        "",
        "```text",
        (manifest.get("adb_devices") or {}).get("text", "").rstrip(),
        "```",
        "",
        "## Selected Values",
        "",
        markdown_table(["name", "value"], selected_rows) if selected_rows else "- none",
        "",
        "## Readiness Lines",
        "",
        "\n".join(f"- {line[:260]}" for line in readiness[:80]) if readiness else "- none",
        "",
        "## Captures",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], capture_rows) if capture_rows else "- none",
        "",
        "## Normalized State Sample",
        "",
        "- `android-subsys-state.txt`" if summary.get("selected_values") else "- not generated with state values",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    devices = adb_devices(args) if args.command != "plan" else {"rc": None, "text": "", "error": "", "duration_sec": 0.0, "devices": [], "device_count": 0}
    captures: list[Capture] = []
    android_summary: dict[str, Any] = {
        "boot_completed": False,
        "all_commands_ok": False,
        "initial_values": {},
        "delayed_values": {},
        "selected_values": {},
        "mss_state": "",
        "mdm3_state": "",
        "state_values_ready": False,
        "non_offline_state": False,
        "readiness_lines": [],
        "has_qrtr_readiness": False,
        "has_sysmon_qmi": False,
        "has_service_notifier": False,
        "has_wlan_pd": False,
    }
    if args.command == "run" and selected_device_available(args, devices):
        captures = collect(args, store)
        android_summary = summarize(captures, store)
    decision, pass_ok, reason, next_step = decide(args, devices, captures, android_summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "captures": [asdict(capture) for capture in captures],
        "android_summary": android_summary,
        "device_commands_executed": args.command == "run" and bool(captures),
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
