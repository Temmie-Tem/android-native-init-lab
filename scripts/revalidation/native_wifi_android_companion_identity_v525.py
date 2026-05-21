#!/usr/bin/env python3
"""V525 Android companion-service identity recapture.

This Android-ADB collector is read-only. It captures init service blocks,
process identity, SELinux context, uid/gid/group/capability state, and binary
labels for the companion services identified by V523/V524. It does not start
daemons, change properties, enable Wi-Fi, scan, connect, request DHCP, route
traffic, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v525-android-companion-identity")
DEFAULT_V523_MANIFEST = Path("tmp/wifi/v524-companion-contract/manifest.json")
TARGET_SERVICES = (
    "vendor.qrtr-ns",
    "vendor.rmt_storage",
    "vendor.tftp_server",
    "vendor.pd_mapper",
    "cnss_diag",
    "cnss-daemon",
)
TARGET_PROCESSES = (
    "qrtr-ns",
    "rmt_storage",
    "tftp_server",
    "pd-mapper",
    "cnss_diag",
    "cnss-daemon",
)
TARGET_USERS = (
    "vendor_qrtr",
    "vendor_rfs",
    "nobody",
    "system",
    "wifi",
)


ADB_COMMANDS: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in sys.boot_completed ro.product.name ro.hardware ro.boot.hardware ro.boot.verifiedbootstate ro.boot.vbmeta.device_state; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        15,
    ),
    (
        "service-blocks",
        r"""for f in /system/etc/init/*.rc /system_ext/etc/init/*.rc /vendor/etc/init/*.rc /vendor/etc/init/hw/*.rc /odm/etc/init/*.rc /product/etc/init/*.rc; do
  [ -f "$f" ] || continue
  awk '
    /^service[ \t]+(vendor\.qrtr-ns|vendor\.rmt_storage|vendor\.tftp_server|vendor\.pd_mapper|cnss_diag|cnss-daemon|qmiproxy)[ \t]/ {print "### " FILENAME; print; active=1; next}
    /^[^ \t]/ {active=0}
    active {print}
  ' "$f"
done""",
        45,
    ),
    (
        "service-props",
        "getprop | grep -Ei 'init\\.svc\\.(vendor\\.qrtr-ns|vendor\\.rmt_storage|vendor\\.tftp_server|vendor\\.pd_mapper|cnss_diag|cnss-daemon|qmiproxy)|init\\.svc_debug_pid\\.(vendor\\.qrtr-ns|vendor\\.rmt_storage|vendor\\.tftp_server|vendor\\.pd_mapper|cnss_diag|cnss-daemon|qmiproxy)|ro\\.boottime\\.(vendor\\.qrtr-ns|vendor\\.rmt_storage|vendor\\.tftp_server|vendor\\.pd_mapper|cnss_diag|cnss-daemon|qmiproxy)' || true",
        20,
    ),
    (
        "target-processes",
        "ps -AZ 2>/dev/null | grep -Ei 'qrtr-ns|rmt_storage|tftp_server|pd-mapper|cnss_diag|cnss-daemon|qmiproxy' || true; ps -A -o USER,PID,PPID,STAT,COMM,ARGS 2>/dev/null | grep -Ei 'qrtr-ns|rmt_storage|tftp_server|pd-mapper|cnss_diag|cnss-daemon|qmiproxy' || true",
        25,
    ),
    (
        "target-proc-identity",
        r"""for name in qrtr-ns rmt_storage tftp_server pd-mapper cnss_diag cnss-daemon qmiproxy; do
  for pid in $(pidof "$name" 2>/dev/null); do
    echo "### process=$name pid=$pid"
    echo -n "cmdline="; tr '\000' ' ' < "/proc/$pid/cmdline" 2>/dev/null; echo
    echo -n "exe="; readlink -f "/proc/$pid/exe" 2>/dev/null || true
    echo -n "attr_current="; cat "/proc/$pid/attr/current" 2>/dev/null || true
    grep -E '^(Name|Uid|Gid|Groups|CapInh|CapPrm|CapEff|CapBnd|CapAmb):' "/proc/$pid/status" 2>/dev/null || true
  done
done""",
        35,
    ),
    (
        "android-ids",
        "for u in vendor_qrtr vendor_rfs nobody system wifi shell; do id \"$u\" 2>/dev/null || true; done",
        20,
    ),
    (
        "passwd-group-filtered",
        "(cat /system/etc/passwd /vendor/etc/passwd /odm/etc/passwd /product/etc/passwd 2>/dev/null || true) | grep -Ei 'vendor_qrtr|vendor_rfs|nobody|system|wifi|shell' || true; echo '--- groups ---'; (cat /system/etc/group /vendor/etc/group /odm/etc/group /product/etc/group 2>/dev/null || true) | grep -Ei 'vendor_qrtr|vendor_rfs|nobody|system|wifi|shell|net_admin|net_raw|inet|diag' || true",
        25,
    ),
    (
        "binary-labels",
        "ls -lZ /vendor/bin/qrtr-ns /vendor/bin/rmt_storage /vendor/bin/tftp_server /vendor/bin/pd-mapper /vendor/bin/cnss_diag /vendor/bin/cnss-daemon /system/bin/qmiproxy 2>/dev/null || true",
        20,
    ),
    (
        "companion-dmesg-identity",
        "dmesg 2>/dev/null | grep -Ei 'starting service .*(qrtr|rmt_storage|tftp|pd_mapper|cnss)|rmt_storage|tftp_server|pd-mapper|qrtr-ns|cnss-daemon|cnss_diag|permission|avc|denied' | tail -n 600 || true",
        60,
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
    parser.add_argument("--v523-manifest", type=Path, default=DEFAULT_V523_MANIFEST)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--no-su", action="store_true")
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
    except Exception as exc:  # noqa: BLE001 - evidence runner preserves failures
        return None, "", str(exc), time.monotonic() - started


def redact(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
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


def summarize(captures: list[Capture]) -> dict[str, Any]:
    text = "\n".join(capture.text for capture in captures)
    service_blocks = {
        service: bool(re.search(rf"service\s+{re.escape(service)}\s+", text))
        for service in TARGET_SERVICES
    }
    process_identities = {
        process: bool(re.search(rf"^### process={re.escape(process)}\s+pid=\d+", text, re.MULTILINE))
        for process in TARGET_PROCESSES
    }
    user_ids = {
        user: bool(re.search(rf"\buid=\d+\({re.escape(user)}\)|\b{re.escape(user)}\b", text))
        for user in TARGET_USERS
    }
    return {
        "boot_completed": boot_completed(captures),
        "all_commands_ok": all(capture.ok for capture in captures),
        "service_blocks": service_blocks,
        "process_identities": process_identities,
        "user_ids": user_ids,
        "all_required_service_blocks": all(service_blocks.values()),
        "all_required_process_identities": all(process_identities.values()),
    }


def decide(args: argparse.Namespace, v523: dict[str, Any], devices: dict[str, Any], captures: list[Capture], summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    command = args.command
    if command == "plan":
        return "v525-companion-identity-plan-ready", True, "plan-only; no adb command executed", "boot Android and run identity recapture"
    if v523.get("decision") != "v523-companion-contract-ready" or v523.get("pass") is not True:
        return "v525-prerequisite-blocked", False, f"v523 decision={v523.get('decision')} pass={v523.get('pass')}", "run V523 after exact recapture first"
    if devices["device_count"] == 0:
        return "v525-android-adb-unavailable", True, "no Android ADB device is currently visible", "boot Android or run approved Android handoff before identity recapture"
    if command == "preflight":
        if not selected_device_available(args, devices):
            return "v525-android-adb-selection-needed", True, f"device_count={devices['device_count']}", "rerun with --serial"
        return "v525-android-identity-preflight-ready", True, "one Android ADB device is visible", "run V525 identity recapture"
    if not captures or not summary.get("boot_completed"):
        return "v525-android-not-boot-complete", False, "Android ADB is visible but sys.boot_completed=1 was not captured", "wait for Android boot-complete and rerun"
    if summary.get("all_required_service_blocks") and summary.get("all_required_process_identities"):
        return "v525-companion-identity-captured", True, "service blocks and process identities captured for required companion set", "implement bounded native companion start-only proof"
    return "v525-companion-identity-incomplete", False, "required identity evidence is incomplete", "inspect captures and widen identity filters"


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    capture_rows = [[item["name"], item["status"], item["rc"], item["duration_sec"], item["file"]] for item in captures]
    summary = manifest.get("android_summary", {})
    service_rows = [[key, str(value)] for key, value in (summary.get("service_blocks") or {}).items()]
    process_rows = [[key, str(value)] for key, value in (summary.get("process_identities") or {}).items()]
    user_rows = [[key, str(value)] for key, value in (summary.get("user_ids") or {}).items()]
    command_rows = [[name, command] for name, command, _ in ADB_COMMANDS]
    return "\n".join(
        [
            "# V525 Android Companion Identity",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## ADB Devices",
            "",
            "```text",
            manifest.get("adb_devices", {}).get("text", "").rstrip(),
            "```",
            "",
            "## Service Blocks",
            "",
            markdown_table(["service", "captured"], service_rows) if service_rows else "- none",
            "",
            "## Process Identities",
            "",
            markdown_table(["process", "captured"], process_rows) if process_rows else "- none",
            "",
            "## User IDs",
            "",
            markdown_table(["user", "captured"], user_rows) if user_rows else "- none",
            "",
            "## Captures",
            "",
            markdown_table(["name", "status", "rc", "duration_sec", "file"], capture_rows) if capture_rows else "- none",
            "",
            "## Command Contract",
            "",
            markdown_table(["name", "shell"], command_rows),
            "",
        ]
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v523 = load_json(args.v523_manifest)
    devices = adb_devices(args) if args.command != "plan" else {"rc": None, "text": "", "error": "", "duration_sec": 0.0, "devices": [], "device_count": 0}
    captures: list[Capture] = []
    android_summary: dict[str, Any] = {
        "boot_completed": False,
        "all_commands_ok": False,
        "service_blocks": {},
        "process_identities": {},
        "user_ids": {},
        "all_required_service_blocks": False,
        "all_required_process_identities": False,
    }
    if args.command == "run" and selected_device_available(args, devices):
        captures = collect(args, store)
        android_summary = summarize(captures)
    decision, pass_ok, reason, next_step = decide(args, v523, devices, captures, android_summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v523": {
            "exists": v523.get("exists"),
            "path": v523.get("path"),
            "decision": v523.get("decision"),
            "pass": v523.get("pass"),
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
