#!/usr/bin/env python3
"""V611 Android read-only lower-surface recapture collector.

This collector is intended to run only while Android ADB is available. It
captures lower modem/QRTR/service-notifier surfaces that V610 could not prove
from filtered Android evidence. It must not enable Wi-Fi, start native daemons,
write sysfs, scan, connect, route, use credentials, or ping externally.
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
from native_wifi_qmi_publication_precondition_v610 import (
    TIMELINE_MARKERS,
    count_by_marker,
    deltas,
    first_by_marker,
    load_json,
    native_surface,
    parse_events,
    parse_key_values,
    read_binary_text,
    readback_summary,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v611-android-lower-surface-recapture")
DEFAULT_TIMEOUT = 45.0
DEFAULT_V609_DIR = Path("tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live")

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

LOWER_DMESG_PATTERN = (
    "qrtr: Modem QMI Readiness|sysmon-qmi|service-notifier|wlan_pd|"
    "icnss_qmi: QMI Server Connected|BDF file|regdb\\.bin|bdwlan\\.bin|"
    "WLAN FW is ready|wlan0|memshare|cma_alloc|servloc|service_locator|"
    "QIPCRTR|rpmsg|rmt_storage|tftp|pd-mapper|subsys-pil|Power/Clock"
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
    parser.add_argument("--v609-dir", type=Path, default=DEFAULT_V609_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sample-delay", type=float, default=5.0)
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
    visible = redact(text if text else error)
    if len(visible) > 12000:
        visible = visible[:12000] + "\n[truncated in manifest]\n"
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
    command = [*adb_base(args), "devices", "-l"]
    rc, text, error, duration = run_command(command, timeout=10.0)
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


def state_command(prefix: str, delay: float = 0.0) -> str:
    lines: list[str] = []
    if delay > 0:
        lines.append(f"sleep {delay:.3f}")
    lines.append(f"echo 'A90_ANDROID_LOWER_SURFACE {prefix} BEGIN'")
    for key, path in STATE_PATHS.items():
        lines.append(f"echo '### {key} {path}'")
        lines.append(f"cat {shlex.quote(path)} 2>&1 || true")
    lines.append(f"echo 'A90_ANDROID_LOWER_SURFACE {prefix} END'")
    return "; ".join(lines)


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    wait_command = [*adb_base(args), "wait-for-device"]
    rc, text, error, duration = run_command(wait_command, timeout=args.timeout)
    captures.append(write_capture(store, "adb-wait-for-device", wait_command, rc, text, error, duration))
    captures.append(capture_shell(args, store, "boot-props", "echo sys.boot_completed=$(getprop sys.boot_completed); echo init.svc.vendor.qrtr-ns=$(getprop init.svc.vendor.qrtr-ns); echo init.svc.cnss-daemon=$(getprop init.svc.cnss-daemon); echo init.svc.cnss_diag=$(getprop init.svc.cnss_diag)", 10.0))
    captures.append(capture_shell(args, store, "subsys-state-initial", state_command("initial"), 15.0))
    captures.append(capture_shell(args, store, "proc-net-protocols", "cat /proc/net/protocols 2>&1 || true", 10.0))
    captures.append(capture_shell(args, store, "proc-net-qrtr", "cat /proc/net/qrtr 2>&1 || true", 10.0))
    captures.append(capture_shell(args, store, "rpmsg-devices", "find /sys/bus/rpmsg/devices -maxdepth 2 -print 2>&1 || true", 15.0))
    captures.append(capture_shell(args, store, "debug-lower-surface-list", "find /sys/kernel/debug -maxdepth 3 \\( -iname '*esoc*' -o -iname '*memshare*' -o -iname '*service*' -o -iname '*qrtr*' -o -iname '*rpmsg*' \\) -print 2>&1 | head -n 240 || true", 20.0))
    captures.append(capture_shell(args, store, "debug-esoc-readonly", "if [ -d /sys/kernel/debug/esoc ]; then find /sys/kernel/debug/esoc -maxdepth 2 -type f -print 2>/dev/null | while read f; do echo ### $f; cat $f 2>&1 | head -n 40; done; else echo missing:/sys/kernel/debug/esoc; fi", 20.0))
    captures.append(capture_shell(args, store, "dmesg-lower-surface-tail", f"dmesg 2>&1 | grep -Ei {shlex.quote(LOWER_DMESG_PATTERN)} | tail -n 500 || true", 25.0))
    captures.append(capture_shell(args, store, "dmesg-unfiltered-tail", "dmesg 2>&1 | tail -n 900 || true", 25.0))
    captures.append(capture_shell(args, store, "subsys-state-delayed", state_command("delayed", args.sample_delay), args.sample_delay + 20.0))
    return captures


def parse_state_capture(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_key = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            parts = line.split(maxsplit=2)
            current_key = parts[1] if len(parts) >= 2 else ""
            continue
        if not current_key or line.startswith("$") or line.startswith("A90_ANDROID_LOWER_SURFACE"):
            continue
        if line.startswith("cat:") or line.startswith("/system/bin/sh:"):
            values[current_key] = line
        elif current_key not in values:
            values[current_key] = line
    return values


def boot_completed(captures: list[Capture]) -> bool:
    text = "\n".join(capture.text for capture in captures if capture.name == "boot-props")
    return "sys.boot_completed=1" in text


def capture_text(captures: list[Capture], *names: str) -> str:
    wanted = set(names)
    return "\n".join(capture.text for capture in captures if capture.name in wanted)


def v609_summary(args: argparse.Namespace) -> dict[str, Any]:
    v609_dir = repo_path(args.v609_dir)
    manifest = load_json(v609_dir / "manifest.json")
    companion = read_binary_text(v609_dir / "native" / "companion-start-only-with-holder.txt")
    companion_keys = parse_key_values(companion)
    return {
        "manifest_path": str(v609_dir / "manifest.json"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "surface": native_surface(manifest, companion_keys),
        "qrtr_readback": readback_summary(manifest),
    }


def summarize(args: argparse.Namespace, captures: list[Capture], store: EvidenceStore) -> dict[str, Any]:
    initial = parse_state_capture(capture_text(captures, "subsys-state-initial"))
    delayed = parse_state_capture(capture_text(captures, "subsys-state-delayed"))
    selected = delayed or initial
    normalized = "\n".join(f"{key}={selected.get(key, '')}" for key in sorted(STATE_PATHS)).rstrip() + "\n"
    store.write_text("android-lower-surface-state.txt", normalized)
    dmesg_text = capture_text(captures, "dmesg-lower-surface-tail", "dmesg-unfiltered-tail")
    events = parse_events(dmesg_text, "android-v611")
    found = first_by_marker(events)
    counts = count_by_marker(events)
    protocols = capture_text(captures, "proc-net-protocols")
    qrtr = capture_text(captures, "proc-net-qrtr")
    rpmsg = capture_text(captures, "rpmsg-devices")
    return {
        "boot_completed": boot_completed(captures),
        "all_commands_ok": all(capture.ok for capture in captures),
        "initial_values": initial,
        "delayed_values": delayed,
        "selected_values": selected,
        "mss_state": selected.get("mss_state", ""),
        "mdm3_state": selected.get("mdm3_state", ""),
        "state_values_ready": bool(selected.get("mss_state")) and bool(selected.get("mdm3_state")),
        "event_count": len(events),
        "counts": {marker: counts.get(marker, 0) for marker in TIMELINE_MARKERS},
        "first": {marker: asdict(event) for marker, event in found.items() if marker in TIMELINE_MARKERS},
        "deltas_ms": deltas(found),
        "has_qipcrtr_protocol": "QIPCRTR" in protocols,
        "has_proc_net_qrtr": "No such file" not in qrtr and bool(qrtr.strip()),
        "has_rpmsg_ipcrtr": "IPCRTR" in rpmsg,
        "has_memshare_evidence": counts.get("memshare_request", 0) > 0 or counts.get("memshare_fail", 0) > 0,
        "has_service_locator": counts.get("service_locator", 0) > 0,
        "has_service_notifier_pair": counts.get("service_notifier_180", 0) > 0 and counts.get("service_notifier_74", 0) > 0,
        "has_sibling_sysmon": any(counts.get(marker, 0) > 0 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp", "sysmon_esoc0")),
        "v609": v609_summary(args),
    }


def decide(args: argparse.Namespace,
           devices: dict[str, Any],
           captures: list[Capture],
           summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v611-android-lower-surface-plan-ready",
            True,
            "plan-only; no adb command executed",
            "boot Android or run handoff, then execute V611 read-only collector",
        )
    if devices["device_count"] == 0:
        return (
            "v611-android-adb-unavailable",
            False,
            "no Android ADB device is currently visible",
            "run Android handoff before V611 live collection",
        )
    if not selected_device_available(args, devices):
        return (
            "v611-android-adb-selection-needed",
            False,
            f"device_count={devices['device_count']}",
            "rerun with --serial",
        )
    if args.command == "preflight":
        return (
            "v611-android-lower-surface-preflight-ready",
            True,
            "one Android ADB device is visible",
            "run V611 Android read-only lower-surface recapture",
        )
    if not captures:
        return "v611-capture-too-filtered", False, "run command produced no captures", "inspect collector failure"
    if not summary.get("boot_completed"):
        return (
            "v611-android-not-boot-complete",
            False,
            "Android ADB is visible but sys.boot_completed=1 was not captured",
            "wait for Android boot-complete and rerun V611",
        )
    if not summary.get("state_values_ready") or summary.get("event_count", 0) == 0:
        return (
            "v611-capture-too-filtered",
            False,
            "subsystem values or lower dmesg events were not captured",
            "recapture with root ADB and broader read-only dmesg/sysfs access",
        )
    if summary.get("has_service_notifier_pair") and summary.get("has_sibling_sysmon"):
        return (
            "v611-ready-for-native-targeted-trigger",
            True,
            "Android lower-surface recapture contains sibling sysmon and service-notifier publication evidence",
            "compare captured lower surfaces against V609, then design the narrowest native targeted observer",
        )
    return (
        "v611-android-lower-surface-captured",
        True,
        "Android lower-surface bundle captured but does not yet prove the full service-notifier publication path",
        "compare available surfaces against V609 before native runtime changes",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    summary = manifest.get("android_summary") or {}
    capture_rows = [[item["name"], item["status"], item["rc"], f"{item['duration_sec']:.3f}s", item["file"]] for item in captures]
    state_rows = [[key, value] for key, value in sorted((summary.get("selected_values") or {}).items())]
    marker_rows = [[marker, str((summary.get("counts") or {}).get(marker, 0))] for marker in TIMELINE_MARKERS]
    deltas_rows = [[key, value] for key, value in (summary.get("deltas_ms") or {}).items()]
    return "\n".join([
        "# V611 Android Lower-Surface Recapture",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Android State",
        "",
        markdown_table(["key", "value"], state_rows if state_rows else [["-", "-"]]),
        "",
        "## Surface Booleans",
        "",
        markdown_table(
            ["surface", "value"],
            [
                ["boot_completed", str(summary.get("boot_completed"))],
                ["has_qipcrtr_protocol", str(summary.get("has_qipcrtr_protocol"))],
                ["has_proc_net_qrtr", str(summary.get("has_proc_net_qrtr"))],
                ["has_rpmsg_ipcrtr", str(summary.get("has_rpmsg_ipcrtr"))],
                ["has_memshare_evidence", str(summary.get("has_memshare_evidence"))],
                ["has_service_locator", str(summary.get("has_service_locator"))],
                ["has_service_notifier_pair", str(summary.get("has_service_notifier_pair"))],
                ["has_sibling_sysmon", str(summary.get("has_sibling_sysmon"))],
            ],
        ),
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Timing Deltas",
        "",
        markdown_table(["delta", "ms"], deltas_rows),
        "",
        "## Captures",
        "",
        markdown_table(["capture", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["none", "-", "-", "-", "-"]]),
        "",
        "## Guardrails",
        "",
        "- No Wi-Fi enable, scan/connect/link-up, credentials, DHCP, routing, or external ping.",
        "- No native daemon, service-manager, Wi-Fi HAL, subsystem sysfs write, or QMI payload.",
        "- `plan` does not contact ADB; `preflight` only checks ADB device selection.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    devices = adb_devices(args) if args.command != "plan" else {
        "rc": None,
        "text": "",
        "error": "",
        "duration_sec": 0.0,
        "devices": [],
        "device_count": 0,
    }
    captures = collect(args, store) if args.command == "run" and selected_device_available(args, devices) else []
    summary = summarize(args, captures, store) if captures else {"v609": v609_summary(args)}
    decision, pass_ok, reason, next_step = decide(args, devices, captures, summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "android_summary": summary,
        "captures": [asdict(capture) for capture in captures],
        "forbidden_actions": [
            "Wi-Fi enable/scan/connect/link-up",
            "credential/DHCP/routing/external ping",
            "native daemon/service-manager/Wi-Fi HAL start",
            "subsystem sysfs write or QMI payload",
        ],
        "device_commands_executed": args.command in {"preflight", "run"},
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
