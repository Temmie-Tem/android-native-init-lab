#!/usr/bin/env python3
"""V670 Android/native Wi-Fi service-order delta classifier.

This host-only classifier compares Android init/service ordering against the
V668 native companion order. It does not contact the device, start services,
start Wi-Fi HAL, scan, connect, run DHCP, change routes, use credentials, or
ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v670-android-service-order-delta")
DEFAULT_V668_MANIFEST = Path("tmp/wifi/v668-cnss2-focused-capture-live/manifest.json")
DEFAULT_V669_MANIFEST = Path("tmp/wifi/v669-android-cnss2-runtime-delta/manifest.json")
DEFAULT_ANDROID_PROPS = Path("tmp/wifi/v520-companion-service-availability-plan/inputs/v206_props.txt")
DEFAULT_ANDROID_INITRC = Path("tmp/wifi/v520-companion-service-availability-plan/inputs/v206_initrc.txt")
DEFAULT_ANDROID_PROCESSES = Path("tmp/wifi/v520-companion-service-availability-plan/inputs/v206_processes.txt")
DEFAULT_ANDROID_DMESG = Path(
    "tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/"
    "v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt"
)

SERVICE_NAMES = (
    "vendor.wifi_hal_legacy",
    "vendor.wifi_hal_ext",
    "cnss_diag",
    "wificond",
    "cnss-daemon",
    "wpa_supplicant",
)
LATE_ONLY_SERVICES = ("wpa_supplicant",)
REQUIRED_PRE_CNSS_SERVICES = ("vendor.wifi_hal_legacy", "vendor.wifi_hal_ext", "cnss_diag", "wificond")
FORBIDDEN_ACTIONS = (
    "device command",
    "service start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
)

PROP_RE = re.compile(r"^\[(?P<key>[^\]]+)\]: \[(?P<value>[^\]]*)\]")
DMESG_TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
DMESG_START_RE = re.compile(r"starting service '(?P<service>cnss_diag|cnss-daemon|vendor\.wifi_hal_ext|vendor\.wifi_hal_legacy|wificond|wpa_supplicant)'", re.I)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v668-manifest", type=Path, default=DEFAULT_V668_MANIFEST)
    parser.add_argument("--v669-manifest", type=Path, default=DEFAULT_V669_MANIFEST)
    parser.add_argument("--android-props", type=Path, default=DEFAULT_ANDROID_PROPS)
    parser.add_argument("--android-initrc", type=Path, default=DEFAULT_ANDROID_INITRC)
    parser.add_argument("--android-processes", type=Path, default=DEFAULT_ANDROID_PROCESSES)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def parse_props(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        match = PROP_RE.match(line.strip())
        if match:
            props[match.group("key")] = match.group("value")
    return props


def parse_boottime_ns(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    return int(value)


def boottime_summary(props: dict[str, str]) -> dict[str, Any]:
    services: dict[str, dict[str, Any]] = {}
    for name in SERVICE_NAMES:
        state = props.get(f"init.svc.{name}", "")
        pid = props.get(f"init.svc_debug_pid.{name}", "")
        boottime_ns = parse_boottime_ns(props.get(f"ro.boottime.{name}"))
        services[name] = {
            "state": state,
            "pid": pid,
            "boottime_ns": boottime_ns,
            "boottime_ms": None if boottime_ns is None else round(boottime_ns / 1_000_000.0, 3),
        }
    ordered = sorted(
        ((name, data["boottime_ns"]) for name, data in services.items() if data["boottime_ns"] is not None),
        key=lambda item: item[1],
    )
    cnss_time = services["cnss-daemon"]["boottime_ns"]
    deltas_to_cnss_ms: dict[str, float | None] = {}
    for name, data in services.items():
        if data["boottime_ns"] is None or cnss_time is None:
            deltas_to_cnss_ms[name] = None
        else:
            deltas_to_cnss_ms[name] = round((data["boottime_ns"] - cnss_time) / 1_000_000.0, 3)
    return {
        "services": services,
        "ordered": [name for name, _ in ordered],
        "deltas_to_cnss_daemon_ms": deltas_to_cnss_ms,
        "wifi_interface": props.get("wifi.interface", ""),
        "wifi_active_interface": props.get("wifi.active.interface", ""),
        "wlan_driver_status": props.get("wlan.driver.status", ""),
        "firmware_version": props.get("vendor.wlan.firmware.version", ""),
        "driver_version": props.get("vendor.wlan.driver.version", ""),
    }


def parse_dmesg_starts(text: str) -> dict[str, Any]:
    starts: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        match = DMESG_START_RE.search(line)
        if not match:
            continue
        ts_match = DMESG_TS_RE.match(line.strip())
        timestamp = float(ts_match.group("ts")) if ts_match else None
        service = match.group("service")
        starts.setdefault(service, {"timestamp": timestamp, "line": line.strip()})
    ordered = sorted(
        ((name, item["timestamp"]) for name, item in starts.items() if item["timestamp"] is not None),
        key=lambda item: item[1],
    )
    return {"starts": starts, "ordered": [name for name, _ in ordered]}


def parse_initrc(text: str) -> dict[str, Any]:
    service_defs: dict[str, list[str]] = {name: [] for name in SERVICE_NAMES}
    triggers: dict[str, list[str]] = {
        "wlan_driver_status": [],
        "wifi_interface": [],
        "wifi_hal": [],
        "supplicant": [],
        "firmware": [],
    }
    capability_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for name in SERVICE_NAMES:
            if f"service {name} " in line or (name == "cnss-daemon" and "service cnss-daemon " in line):
                service_defs[name].append(line)
        if "on property:wlan.driver.status=ok" in line:
            triggers["wlan_driver_status"].append(line)
        if "property:wifi.interface" in line:
            triggers["wifi_interface"].append(line)
        if "vendor.wifi" in line or "android.hardware.wifi" in line:
            triggers["wifi_hal"].append(line)
        if "supplicant" in line:
            triggers["supplicant"].append(line)
        if "firmware" in line:
            triggers["firmware"].append(line)
        if "capabilities " in line or "group " in line:
            if any(term in line for term in ("wifi", "net_raw", "net_admin", "NET_RAW", "NET_ADMIN", "SYS_MODULE")):
                capability_lines.append(line)
    return {
        "service_defs": service_defs,
        "triggers": triggers,
        "capability_lines": capability_lines[:80],
    }


def parse_processes(text: str) -> dict[str, Any]:
    hits: dict[str, list[str]] = {name: [] for name in SERVICE_NAMES}
    context_by_name: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("$ ") or stripped.startswith("rc="):
            continue
        for name in SERVICE_NAMES:
            process_name = {
                "vendor.wifi_hal_legacy": "android.hardware.wifi@1.0-service",
                "vendor.wifi_hal_ext": "vendor.samsung.hardware.wifi@2.0-service",
                "cnss_diag": "cnss_diag",
                "wificond": "wificond",
                "cnss-daemon": "cnss-daemon",
                "wpa_supplicant": "wpa_supplicant",
            }[name]
            if process_name in stripped:
                hits[name].append(stripped)
                context_by_name.setdefault(name, stripped.split()[0] if stripped.split() else "")
    return {"hits": hits, "context_by_name": context_by_name}


def native_order(v668: dict[str, Any]) -> list[str]:
    value = v668.get("expected_order") or ""
    if not value:
        live = v668.get("live") or {}
        value = live.get("expected_order") or ""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def build_checks(v668: dict[str, Any],
                 v669: dict[str, Any],
                 boot: dict[str, Any],
                 initrc: dict[str, Any],
                 processes: dict[str, Any],
                 native: list[str]) -> list[dict[str, Any]]:
    services = boot["services"]
    pre_cnss_ready = all(services[name]["state"] == "running" for name in REQUIRED_PRE_CNSS_SERVICES)
    pre_cnss_before = all(
        boot["deltas_to_cnss_daemon_ms"].get(name) is not None
        and boot["deltas_to_cnss_daemon_ms"][name] < 0
        for name in REQUIRED_PRE_CNSS_SERVICES
    )
    service_defs_ready = all(initrc["service_defs"].get(name) for name in SERVICE_NAMES)
    process_contexts_ready = all(processes["hits"].get(name) for name in REQUIRED_PRE_CNSS_SERVICES + ("cnss-daemon",))
    native_has_hal_wificond = any("wifi" in item or "wificond" in item for item in native)
    return [
        {
            "name": "v669-runtime-delta-classified",
            "status": "pass" if v669.get("decision") == "v669-android-native-cnss2-runtime-delta-classified" else "blocked",
            "detail": v669.get("decision"),
            "next_step": "run V669 first if runtime delta is missing",
        },
        {
            "name": "android-pre-cnss-services-running",
            "status": "pass" if pre_cnss_ready else "blocked",
            "detail": {name: services[name]["state"] for name in REQUIRED_PRE_CNSS_SERVICES},
            "next_step": "refresh Android props if service states are missing",
        },
        {
            "name": "android-pre-cnss-services-before-cnss-daemon",
            "status": "pass" if pre_cnss_before else "blocked",
            "detail": {name: boot["deltas_to_cnss_daemon_ms"].get(name) for name in REQUIRED_PRE_CNSS_SERVICES},
            "next_step": "refresh Android boottime props if ordering is missing",
        },
        {
            "name": "android-initrc-service-definitions-present",
            "status": "pass" if service_defs_ready else "blocked",
            "detail": {name: bool(initrc["service_defs"].get(name)) for name in SERVICE_NAMES},
            "next_step": "recapture Android init rc service definitions",
        },
        {
            "name": "android-process-contexts-present",
            "status": "pass" if process_contexts_ready else "blocked",
            "detail": processes["context_by_name"],
            "next_step": "recapture Android process contexts",
        },
        {
            "name": "native-v668-order-missing-hal-wificond",
            "status": "pass" if not native_has_hal_wificond else "review",
            "detail": native,
            "next_step": "if native order already contains Wi-Fi HAL/wificond, inspect live evidence instead",
        },
        {
            "name": "supplicant-is-late-only",
            "status": "pass" if services["wpa_supplicant"]["boottime_ns"] and services["cnss-daemon"]["boottime_ns"]
            and services["wpa_supplicant"]["boottime_ns"] > services["cnss-daemon"]["boottime_ns"] else "blocked",
            "detail": {name: boot["deltas_to_cnss_daemon_ms"].get(name) for name in LATE_ONLY_SERVICES},
            "next_step": "keep supplicant blocked until wlan0 exists",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v670-android-service-order-delta-plan-ready",
            True,
            "plan-only; no evidence classification or device command executed",
            "run V670 host-only classifier",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v670-android-service-order-delta-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh missing Android/native input evidence",
        )
    return (
        "v670-android-service-order-delta-classified",
        True,
        "Android has Wi-Fi HAL legacy/ext, cnss_diag, and wificond running before cnss-daemon, while V668 native order lacks Wi-Fi HAL and wificond before CNSS retry",
        "plan a service74-gated Android userspace-order start-only proof: managers plus Wi-Fi HAL/wificond before fresh CNSS retry; keep supplicant, scan/connect, DHCP, routes, and external ping blocked",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v668 = load_json(args.v668_manifest)
    v669 = load_json(args.v669_manifest)
    props = parse_props(read_text(args.android_props))
    boot = boottime_summary(props)
    initrc = parse_initrc(read_text(args.android_initrc))
    processes = parse_processes(read_text(args.android_processes))
    dmesg = parse_dmesg_starts(read_text(args.android_dmesg))
    native = native_order(v668)
    checks = build_checks(v668, v669, boot, initrc, processes, native)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v668_manifest": str(repo_path(args.v668_manifest)),
            "v669_manifest": str(repo_path(args.v669_manifest)),
            "android_props": str(repo_path(args.android_props)),
            "android_initrc": str(repo_path(args.android_initrc)),
            "android_processes": str(repo_path(args.android_processes)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
        },
        "checks": checks,
        "android_boot": boot,
        "android_initrc": initrc,
        "android_processes": processes,
        "android_dmesg_starts": dmesg,
        "native_v668_order": native,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def check_rows(checks: list[dict[str, Any]]) -> list[list[str]]:
    return [[check["name"], check["status"], str(check["detail"]), check["next_step"]] for check in checks]


def service_rows(boot: dict[str, Any], processes: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in SERVICE_NAMES:
        service = boot["services"][name]
        rows.append([
            name,
            str(service["state"]),
            str(service["boottime_ms"]),
            str(boot["deltas_to_cnss_daemon_ms"].get(name)),
            processes["context_by_name"].get(name, ""),
        ])
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V670 Android/native Wi-Fi Service-order Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows(manifest["checks"])),
        "",
        "## Android Service Order",
        "",
        markdown_table(["service", "state", "boottime_ms", "delta_to_cnss_daemon_ms", "SELinux context"], service_rows(manifest["android_boot"], manifest["android_processes"])),
        "",
        "## Native V668 Order",
        "",
        "`" + ",".join(manifest["native_v668_order"]) + "`",
        "",
        "## Interpretation",
        "",
        "- Android has Wi-Fi HAL legacy/ext and `wificond` running before `cnss-daemon`.",
        "- V668 native starts lower companions and CNSS retry without Wi-Fi HAL or `wificond` in the order.",
        "- `wpa_supplicant` is late relative to `cnss-daemon`, so it remains blocked until `wlan0` exists.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
