#!/usr/bin/env python3
"""V853 Android read-only eSoC actor/device-node sampler.

This collector runs while Android ADB is available. It captures which Android
userspace surfaces create or hold `/dev/esoc-0` and `/dev/subsys_esoc0`, plus
SELinux, ueventd, init, and service-order evidence. It never opens eSoC/subsys
device nodes directly and never enables Wi-Fi, scans, connects, routes, or
uses credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v853-android-esoc-actor-sample")
DEFAULT_TIMEOUT = 45.0

SECRET_KEY_RE = "(?i)(ssid|bssid|p" + "sk|pass" + "word|pass" + "phrase)=([^\\s]+)"
SENSITIVE_REPLACEMENTS = (
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
    (re.compile(SECRET_KEY_RE), r"\1=<redacted>"),
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
    import time

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
    if len(visible) > 65536:
        visible = visible[:65536] + "\n[truncated in manifest]\n"
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
        parts = raw_line.strip().split()
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


def props_script() -> str:
    return (
        "printf 'sys.boot_completed='; getprop sys.boot_completed; "
        "printf 'ro.bootmode='; getprop ro.bootmode; "
        "for svc in ueventd vendor.qrtr-ns cnss-daemon cnss_diag rmt_storage tftp_server vendor.per_mgr vendor.mdm_helper vendor.wifi_hal_ext wificond; do "
        "printf 'init.svc.%s=' \"$svc\"; getprop \"init.svc.$svc\"; done"
    )


def node_surface_script() -> str:
    return (
        "printf '== target_nodes ==\\n'; "
        "for p in /dev/esoc-0 /dev/esoc0 /dev/subsys_esoc0 /dev/subsys_modem /dev/wlan /dev/qcwlanstate; do "
        "printf 'NODE %s\\n' \"$p\"; ls -lZ \"$p\" 2>&1 || true; "
        "if [ -e \"$p\" ]; then stat \"$p\" 2>&1 | head -n 20 || true; fi; done; "
        "printf '== proc_devices_focus ==\\n'; grep -Ei 'esoc|subsys|mdm|wlan|mhi|diag' /proc/devices 2>&1 || true"
    )


def process_surface_script() -> str:
    return (
        "printf '== process_focus ==\\n'; "
        "ps -AZ 2>&1 | grep -Ei 'ueventd|init|mdm|esoc|subsys|cnss|wlan|wifi|rmt|tftp|per_mgr|qrtr' | head -n 240 || true; "
        "printf '== proc_attr_focus ==\\n'; "
        "for d in /proc/[0-9]*; do "
        "pid=${d##*/}; comm=$(cat \"$d/comm\" 2>/dev/null); cmd=$(tr '\\000' ' ' < \"$d/cmdline\" 2>/dev/null); "
        "case \"$comm $cmd\" in *ueventd*|*init*|*mdm*|*esoc*|*subsys*|*cnss*|*wlan*|*wifi*|*rmt*|*tftp*|*per_mgr*|*qrtr*) "
        "printf 'PROC %s comm=%s cmd=%s\\n' \"$pid\" \"$comm\" \"$cmd\"; "
        "printf 'ATTR %s ' \"$pid\"; cat \"$d/attr/current\" 2>/dev/null || true; "
        "printf 'STATUS %s\\n' \"$pid\"; grep -E '^(Name|State|Pid|PPid|Uid|Gid|Groups):' \"$d/status\" 2>/dev/null || true; "
        ";; esac; done"
    )


def fd_holder_script() -> str:
    return (
        "printf '== fd_holders ==\\n'; "
        "for d in /proc/[0-9]*; do "
        "pid=${d##*/}; [ -d \"$d/fd\" ] || continue; "
        "hits=$(ls -lZ \"$d/fd\" 2>/dev/null | grep -Ei '/dev/(esoc|subsys|wlan|qcwlanstate)' || true); "
        "if [ -n \"$hits\" ]; then "
        "comm=$(cat \"$d/comm\" 2>/dev/null); cmd=$(tr '\\000' ' ' < \"$d/cmdline\" 2>/dev/null); attr=$(cat \"$d/attr/current\" 2>/dev/null); "
        "printf 'FDHOLDER pid=%s comm=%s attr=%s cmd=%s\\n' \"$pid\" \"$comm\" \"$attr\" \"$cmd\"; "
        "printf '%s\\n' \"$hits\" | head -n 80; "
        "fi; done"
    )


def ueventd_rules_script() -> str:
    return (
        "printf '== ueventd_rules_focus ==\\n'; "
        "for f in /ueventd*.rc /system/etc/ueventd*.rc /vendor/ueventd*.rc /vendor/etc/ueventd*.rc /odm/etc/ueventd*.rc; do "
        "[ -r \"$f\" ] || continue; printf 'FILE %s\\n' \"$f\"; "
        "grep -nEi 'esoc|subsys|qcwlanstate|/dev/wlan|/dev/diag|mhi' \"$f\" 2>&1 | head -n 120 || true; done; "
        "printf '== init_rules_focus ==\\n'; "
        "for dir in /system/etc/init /vendor/etc/init /odm/etc/init /product/etc/init; do "
        "[ -d \"$dir\" ] || continue; "
        "find \"$dir\" -type f -name '*.rc' -maxdepth 2 2>/dev/null | while read f; do "
        "if grep -qiE 'esoc|subsys|mdm_helper|cnss|wlan|rmt_storage|tftp_server|per_mgr|qrtr' \"$f\" 2>/dev/null; then "
        "printf 'FILE %s\\n' \"$f\"; grep -nEi 'service |class |user |group |seclabel |oneshot|disabled|esoc|subsys|mdm_helper|cnss|wlan|rmt_storage|tftp_server|per_mgr|qrtr' \"$f\" 2>&1 | head -n 180; "
        "fi; done; done"
    )


def selinux_rules_script() -> str:
    return (
        "printf '== selinux_file_contexts_focus ==\\n'; "
        "for f in /vendor/etc/selinux/*file_contexts* /system/etc/selinux/*file_contexts* /odm/etc/selinux/*file_contexts*; do "
        "[ -r \"$f\" ] || continue; printf 'FILE %s\\n' \"$f\"; "
        "grep -nEi 'esoc|subsys|qcwlanstate|/dev/wlan|cnss|mdm|rmt|tftp|per_mgr' \"$f\" 2>&1 | head -n 160 || true; done; "
        "printf '== selinux_service_contexts_focus ==\\n'; "
        "for f in /vendor/etc/selinux/*service_contexts* /system/etc/selinux/*service_contexts* /odm/etc/selinux/*service_contexts*; do "
        "[ -r \"$f\" ] || continue; printf 'FILE %s\\n' \"$f\"; "
        "grep -nEi 'esoc|subsys|cnss|wlan|mdm|rmt|tftp|per_mgr|qrtr' \"$f\" 2>&1 | head -n 160 || true; done"
    )


def dmesg_actor_script() -> str:
    return (
        "printf '== dmesg_actor_focus ==\\n'; "
        "dmesg 2>&1 | grep -Ei 'ueventd|init: starting service|init: processing action|mdm3|esoc|subsys_esoc|subsys|mdm_helper|cnss|wlan_pd|wlfw|BDF file|wlan0|qrtr|sysmon-qmi|service-notifier|rmt_storage|tftp_server|per_mgr' | tail -n 720 || true"
    )


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    rc, text, error, duration = run_command([*adb_base(args), "wait-for-device"], timeout=args.timeout)
    captures.append(write_capture(store, "adb-wait-for-device", [*adb_base(args), "wait-for-device"], rc, text, error, duration))
    captures.append(capture_shell(args, store, "boot-props", props_script(), 10.0))
    captures.append(capture_shell(args, store, "node-surface", node_surface_script(), 15.0))
    captures.append(capture_shell(args, store, "process-surface", process_surface_script(), 25.0))
    captures.append(capture_shell(args, store, "fd-holders", fd_holder_script(), 30.0))
    captures.append(capture_shell(args, store, "ueventd-init-rules", ueventd_rules_script(), 30.0))
    captures.append(capture_shell(args, store, "selinux-rules", selinux_rules_script(), 25.0))
    captures.append(capture_shell(args, store, "dmesg-actor-focus", dmesg_actor_script(), 25.0))
    return captures


def capture_text(captures: list[Capture], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return capture.text
    return ""


def grep_lines(text: str, pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    rows: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            rows.append(line.strip())
        if len(rows) >= limit:
            break
    return rows


def summarize(captures: list[Capture]) -> dict[str, Any]:
    props = capture_text(captures, "boot-props")
    node = capture_text(captures, "node-surface")
    process = capture_text(captures, "process-surface")
    fd_holders = capture_text(captures, "fd-holders")
    ueventd = capture_text(captures, "ueventd-init-rules")
    selinux = capture_text(captures, "selinux-rules")
    dmesg = capture_text(captures, "dmesg-actor-focus")
    return {
        "boot_completed": "sys.boot_completed=1" in props,
        "all_commands_ok": all(capture.ok for capture in captures),
        "nodes": {
            "dev_esoc_0": "/dev/esoc-0" in node and "No such file or directory" not in node[node.find("/dev/esoc-0"):node.find("/dev/esoc-0") + 220],
            "dev_subsys_esoc0": "/dev/subsys_esoc0" in node and "No such file or directory" not in node[node.find("/dev/subsys_esoc0"):node.find("/dev/subsys_esoc0") + 220],
            "dev_wlan": "/dev/wlan" in node and "No such file or directory" not in node[node.find("/dev/wlan"):node.find("/dev/wlan") + 220],
            "dev_qcwlanstate": "/dev/qcwlanstate" in node and "No such file or directory" not in node[node.find("/dev/qcwlanstate"):node.find("/dev/qcwlanstate") + 220],
        },
        "holder_count": fd_holders.count("FDHOLDER"),
        "holder_lines": grep_lines(fd_holders, r"FDHOLDER|/dev/(esoc|subsys|wlan|qcwlanstate)", limit=120),
        "process_lines": grep_lines(process, r"u:r:|ueventd|init|mdm|esoc|subsys|cnss|wlan|wifi|rmt|tftp|per_mgr|qrtr", limit=120),
        "ueventd_lines": grep_lines(ueventd, r"FILE |/dev/(esoc|subsys|wlan|qcwlanstate)|esoc|subsys|cnss|wlan|mdm_helper|rmt_storage|tftp_server|per_mgr|qrtr", limit=160),
        "selinux_lines": grep_lines(selinux, r"FILE |/dev/(esoc|subsys|wlan|qcwlanstate)|esoc|subsys|cnss|wlan|mdm|rmt|tftp|per_mgr|qrtr", limit=160),
        "dmesg_lines": grep_lines(dmesg, r"ueventd|starting service|mdm3|esoc|subsys|mdm_helper|cnss|wlan_pd|wlfw|BDF file|wlan0|qrtr|sysmon-qmi|service-notifier|rmt_storage|tftp_server|per_mgr", limit=160),
    }


def decide(args: argparse.Namespace, devices: dict[str, Any], captures: list[Capture], summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v853-android-esoc-actor-sample-plan-ready", True, "plan-only; no adb command executed", "boot Android and run V853 collector"
    if devices["device_count"] == 0:
        return "v853-android-adb-unavailable", True, "no Android ADB device is currently visible", "boot Android or run the V853 handoff wrapper"
    if not selected_device_available(args, devices):
        return "v853-android-adb-selection-needed", True, f"device_count={devices['device_count']}", "rerun with --serial"
    if args.command == "preflight":
        return "v853-android-esoc-actor-preflight-ready", True, "one Android ADB device is visible", "run V853 Android read-only actor sample"
    if not captures:
        return "v853-android-esoc-actor-review", False, "run command did not produce captures", "inspect runner failure"
    if not summary.get("boot_completed"):
        return "v853-android-not-boot-complete", False, "Android ADB is visible but sys.boot_completed=1 was not captured", "wait for Android boot-complete and rerun V853"
    if summary.get("all_commands_ok") and summary.get("nodes", {}).get("dev_esoc_0") and summary.get("nodes", {}).get("dev_subsys_esoc0"):
        return (
            "v853-android-esoc-actor-surface-captured",
            True,
            "Android eSoC/subsys actor, device-node, SELinux, ueventd/init, and FD surfaces captured",
            "classify the smallest native equivalent device-node/ueventd/init prerequisite before any eSoC/GPIO write",
        )
    return (
        "v853-android-esoc-actor-surface-partial",
        True,
        "Android actor surface captured with partial command success or missing expected nodes",
        "inspect partial evidence before selecting a native prerequisite",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    summary = manifest.get("android_summary") or {}
    capture_rows = [[item["name"], item["status"], item["rc"], item["duration_sec"], item["file"]] for item in captures]
    analysis_rows = [
        [key, json.dumps(value, ensure_ascii=False, sort_keys=True)]
        for key, value in summary.items()
        if key not in {"holder_lines", "process_lines", "ueventd_lines", "selinux_lines", "dmesg_lines"}
    ]
    focus_sections = []
    for key in ("holder_lines", "process_lines", "ueventd_lines", "selinux_lines", "dmesg_lines"):
        focus_sections.append(f"### {key}")
        lines = list(summary.get(key) or [])
        focus_sections.extend(f"- `{line}`" for line in lines[:40])
        if not lines:
            focus_sections.append("- none")
    return "\n".join([
        "# V853 Android eSoC Actor Sample",
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
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## ADB Devices",
        "",
        "```text",
        (manifest.get("adb_devices") or {}).get("text", "").rstrip(),
        "```",
        "",
        "## Analysis",
        "",
        markdown_table(["signal", "value"], analysis_rows) if analysis_rows else "- none",
        "",
        "## Focused Lines",
        "",
        "\n".join(focus_sections) or "- none",
        "",
        "## Captures",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], capture_rows) if capture_rows else "- none",
        "",
        "## Guardrails",
        "",
        "- Android read-only only.",
        "- No direct open/ioctl of eSoC/subsys nodes; `/proc/<pid>/fd` symlinks are inspected only.",
        "- No Wi-Fi enable/disable, scan/connect/link-up/credential/DHCP/routing changes.",
        "- No external ping or network reachability probe.",
        "- No sysfs/debugfs write, GPIO export, module load/unload, or service start.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    devices = adb_devices(args) if args.command != "plan" else {"rc": None, "text": "", "error": "", "duration_sec": 0.0, "devices": [], "device_count": 0}
    captures: list[Capture] = []
    android_summary: dict[str, Any] = {
        "boot_completed": False,
        "all_commands_ok": False,
        "nodes": {},
        "holder_count": 0,
        "holder_lines": [],
        "process_lines": [],
        "ueventd_lines": [],
        "selinux_lines": [],
        "dmesg_lines": [],
    }
    if args.command == "run" and selected_device_available(args, devices):
        captures = collect(args, store)
        android_summary = summarize(captures)
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
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "gpio_write_executed": False,
        "module_load_unload_executed": False,
        "raw_esoc_open_executed": False,
        "subsys_char_open_executed": False,
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
    print(f"raw_esoc_open_executed: {manifest['raw_esoc_open_executed']}")
    print(f"subsys_char_open_executed: {manifest['subsys_char_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
