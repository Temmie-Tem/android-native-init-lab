#!/usr/bin/env python3
"""V521 Android companion-service recapture runner.

This collector is Android-ADB read-only. It captures QRTR/QMI companion
services, init rc entries, candidate binaries, and dmesg/logcat evidence before
any native qcwlanstate retry, daemon start, Wi-Fi HAL start, scan/connect,
link-up, DHCP, route change, or external ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v521-android-companion-recapture")
DEFAULT_V520_MANIFEST = Path("tmp/wifi/v520-companion-service-availability-plan/manifest.json")
COMPANION_TERMS = (
    "qrtr",
    "qmi",
    "qmiproxy",
    "sysmon",
    "service-notifier",
    "wlan_pd",
    "rmtfs",
    "rmt_storage",
    "pd-mapper",
    "tqftp",
    "tftp",
    "tftp_server",
    "cnss",
    "icnss",
    "wlan",
    "wifi",
    "servicemanager",
    "perfd",
)
COMPANION_RE = re.compile("|".join(re.escape(term) for term in COMPANION_TERMS), re.IGNORECASE)
BIN_RE = re.compile(r"/(?:system|system_ext|vendor|odm|product)/.*(?:qrtr-ns|qmiproxy|sysmon-qmi|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftpserv|tftp_server|cnss-daemon|cnss_diag)$", re.IGNORECASE)
QMI_READY_RE = re.compile(r"QMI Server Connected|BDF file|WLAN FW is ready|wlan_pd|sysmon-qmi|service-notifier|Modem QMI Readiness", re.IGNORECASE)

ADB_COMMANDS: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in sys.boot_completed ro.build.version.release ro.build.version.sdk ro.product.name ro.hardware ro.boot.hardware ro.boot.verifiedbootstate ro.boot.vbmeta.device_state; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        15,
    ),
    (
        "companion-processes",
        "ps -AZ 2>/dev/null | grep -Ei 'qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|cnss|wlan|wifi|servicemanager|perfd' || true",
        25,
    ),
    (
        "companion-processes-wide",
        "ps -A -o USER,PID,PPID,STAT,COMM,ARGS 2>/dev/null | grep -Ei 'qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|cnss|wlan|wifi|servicemanager|perfd' || true",
        25,
    ),
    (
        "companion-props",
        "getprop | grep -Ei 'init\\.svc\\..*(qrtr|qmi|qmiproxy|sysmon|service|rmtfs|rmt|pd|tqftp|tftp|cnss|wifi|wlan)|ro\\.boottime\\..*(qrtr|qmi|qmiproxy|sysmon|service|rmtfs|rmt|pd|tqftp|tftp|cnss|wifi|wlan)|qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|wlan_pd|firmware' || true",
        25,
    ),
    (
        "companion-initrc",
        "grep -RHiE 'service .*(qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|cnss|wifi|wlan)|on property:.*(qrtr|qmi|qmiproxy|sysmon|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|cnss|wifi|wlan)|wlan_pd|pdr' /system/etc/init /system_ext/etc/init /vendor/etc/init /odm/etc/init /product/etc/init 2>/dev/null || true",
        45,
    ),
    (
        "companion-binaries",
        "find /system /system_ext /vendor /odm /product -type f \\( -name qrtr-ns -o -name qmiproxy -o -name sysmon-qmi -o -name service-notifier -o -name rmtfs -o -name rmt_storage -o -name pd-mapper -o -name tqftpserv -o -name tftp_server -o -name cnss-daemon -o -name cnss_diag \\) 2>/dev/null | sort || true",
        45,
    ),
    (
        "companion-devnodes",
        "ls -l /dev/qrtr* /dev/qmi* /dev/cnss* /dev/diag /dev/socket 2>/dev/null | grep -Ei 'qrtr|qmi|cnss|diag|wifi|wlan|perfd|property|vendor' || true",
        25,
    ),
    (
        "proc-net-qrtr",
        "cat /proc/net/qrtr 2>/dev/null || true",
        15,
    ),
    (
        "companion-dmesg",
        "dmesg 2>/dev/null | grep -Ei 'qrtr|qmi|qmiproxy|sysmon|service-notifier|wlan_pd|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|cnss|icnss|bdf|bdwlan|regdb|firmware' | tail -n 1000 || true",
        60,
    ),
    (
        "companion-logcat",
        "logcat -d -v threadtime 2>/dev/null | grep -Ei 'qrtr|qmi|qmiproxy|sysmon|service-notifier|wlan_pd|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|cnss|icnss|bdf|bdwlan|regdb|firmware' | tail -n 1000 || true",
        75,
    ),
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
    parser.add_argument("--v520-manifest", type=Path, default=DEFAULT_V520_MANIFEST)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--timeout", type=float, default=30.0)
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
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(ssid|bssid|psk|password|passphrase)=([^\s]+)", r"\1=<redacted>", text)
    return text


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


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": True}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def adb_devices(args: argparse.Namespace) -> dict[str, Any]:
    rc, text, error, duration = run_command([*adb_base(args), "devices", "-l"], timeout=10)
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


def boot_completed(captures: list[Capture]) -> bool:
    text = "\n".join(capture.text for capture in captures if capture.name == "identity-props")
    return "sys.boot_completed=1" in text


def focus_lines(text: str, pattern: re.Pattern[str], limit: int = 160) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$"):
            continue
        if "grep -E" in line or "find /" in line:
            continue
        if not pattern.search(line):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def summarize(captures: list[Capture]) -> dict[str, Any]:
    text = "\n".join(capture.text for capture in captures)
    binary_lines = focus_lines(text, BIN_RE, 80)
    companion_lines = focus_lines(text, COMPANION_RE, 160)
    qmi_lines = focus_lines(text, QMI_READY_RE, 120)
    return {
        "boot_completed": boot_completed(captures),
        "all_commands_ok": all(capture.ok for capture in captures),
        "binary_lines": binary_lines,
        "companion_lines": companion_lines,
        "qmi_ready_lines": qmi_lines,
        "has_qrtr_ns_process": bool(re.search(r"\bqrtr-ns\b", text)),
        "has_qmiproxy": bool(re.search(r"\bqmiproxy\b", text)),
        "has_sysmon_qmi": bool(re.search(r"\bsysmon-qmi\b", text, re.IGNORECASE)),
        "has_service_notifier": bool(re.search(r"\bservice-notifier\b", text, re.IGNORECASE)),
        "has_mainline_set": bool(re.search(r"\brmtfs\b", text) and re.search(r"\bpd-mapper\b", text) and re.search(r"\btqftpserv\b", text)),
        "has_qmi_server_connected": bool(re.search(r"QMI Server Connected", text, re.IGNORECASE)),
        "has_bdf": bool(re.search(r"BDF file|regdb\.bin|bdwlan\.bin", text, re.IGNORECASE)),
        "has_fw_ready": bool(re.search(r"WLAN FW is ready", text, re.IGNORECASE)),
    }


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    rc, text, error, duration = run_command([*adb_base(args), "wait-for-device"], timeout=args.timeout)
    captures.append(write_capture(store, "adb-wait-for-device", [*adb_base(args), "wait-for-device"], rc, text, error, duration))
    for name, shell_command, timeout in ADB_COMMANDS:
        command = adb_shell(args, shell_command)
        rc, text, error, duration = run_command(command, timeout=max(args.timeout, timeout))
        captures.append(write_capture(store, name, command, rc, text, error, duration))
    return captures


def decide(command: str, serial: str | None, v520: dict[str, Any], devices: dict[str, Any], captures: list[Capture], summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v521-android-companion-recapture-plan-ready", True, "plan-only; no adb command executed", "boot Android and run V521 recapture"
    if v520.get("decision") != "v520-companion-android-recapture-needed" or v520.get("pass") is not True:
        return "v521-prerequisite-blocked", False, f"v520 decision={v520.get('decision')} pass={v520.get('pass')}", "run V520 planner first"
    if devices["device_count"] == 0:
        return "v521-android-adb-unavailable", True, "no Android ADB device is currently visible", "boot Android or run approved Android handoff before recapture"
    if command == "preflight":
        if not selected_device_available(argparse.Namespace(serial=serial), devices):
            return "v521-android-adb-selection-needed", True, f"device_count={devices['device_count']}", "rerun with --serial"
        return "v521-android-recapture-preflight-ready", True, "one Android ADB device is visible", "run V521 recapture"
    if not captures or not summary.get("boot_completed"):
        return "v521-android-not-boot-complete", False, "Android ADB is visible but sys.boot_completed=1 was not captured", "wait for Android boot-complete and rerun"
    if summary["binary_lines"]:
        return "v521-companion-startables-captured", True, "Android companion binary candidates were captured", "export candidates and design bounded native companion start-only proof"
    if summary["has_qrtr_ns_process"] and summary["has_qmiproxy"] and summary["has_qmi_server_connected"]:
        return "v521-vendor-companion-equivalent-captured", True, "Android vendor companion service evidence was captured without direct binary lines", "expand export path or inspect process executable links"
    return "v521-companion-recapture-review", True, "Android recapture completed but startable companion set is still unresolved", "inspect companion lines before native start-only design"


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    capture_rows = [[item["name"], item["status"], item["rc"], item["duration_sec"], item["file"]] for item in captures]
    summary_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, list) else str(value)] for key, value in manifest.get("android_summary", {}).items() if key not in {"companion_lines", "qmi_ready_lines", "binary_lines"}]
    command_rows = [[name, command] for name, command, _ in ADB_COMMANDS]
    return "\n".join([
        "# V521 Android Companion Recapture",
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
        manifest.get("adb_devices", {}).get("text", "").rstrip(),
        "```",
        "",
        "## Android Summary",
        "",
        markdown_table(["field", "value"], summary_rows),
        "",
        "## Captures",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], capture_rows) if capture_rows else "- none",
        "",
        "## Companion Lines",
        "",
        "\n".join(f"- {line[:260]}" for line in (manifest.get("android_summary", {}).get("companion_lines") or [])[:60]) or "- none",
        "",
        "## QMI Ready Lines",
        "",
        "\n".join(f"- {line[:260]}" for line in (manifest.get("android_summary", {}).get("qmi_ready_lines") or [])[:60]) or "- none",
        "",
        "## Binary Lines",
        "",
        "\n".join(f"- {line[:260]}" for line in (manifest.get("android_summary", {}).get("binary_lines") or [])[:60]) or "- none",
        "",
        "## Command Contract",
        "",
        markdown_table(["name", "shell"], command_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v520 = load_json(args.v520_manifest)
    devices = adb_devices(args) if args.command != "plan" else {"rc": None, "text": "", "error": "", "duration_sec": 0.0, "devices": [], "device_count": 0}
    captures: list[Capture] = []
    android_summary: dict[str, Any] = {
        "boot_completed": False,
        "all_commands_ok": False,
        "binary_lines": [],
        "companion_lines": [],
        "qmi_ready_lines": [],
        "has_qrtr_ns_process": False,
        "has_qmiproxy": False,
        "has_sysmon_qmi": False,
        "has_service_notifier": False,
        "has_mainline_set": False,
        "has_qmi_server_connected": False,
        "has_bdf": False,
        "has_fw_ready": False,
    }
    if args.command == "run" and selected_device_available(args, devices):
        captures = collect(args, store)
        android_summary = summarize(captures)
    decision, pass_ok, reason, next_step = decide(args.command, args.serial, v520, devices, captures, android_summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v520": {
            "exists": v520.get("exists"),
            "path": v520.get("path"),
            "decision": v520.get("decision"),
            "pass": v520.get("pass"),
        },
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
