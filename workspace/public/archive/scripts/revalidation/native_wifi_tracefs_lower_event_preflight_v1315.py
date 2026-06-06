#!/usr/bin/env python3
"""V1315 targeted tracefs lower-event preflight.

This live preflight reads tracefs event availability and format files for the
provider-internal first-power-on trace gate selected by V1314.  It does not
enable trace events, trigger PM-service/eSoC powerup, start Wi-Fi HAL, scan,
connect, use credentials, or touch PMIC/GPIO/GDSC/eSoC controls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1315-tracefs-lower-event-preflight")
LATEST_POINTER = Path("tmp/wifi/latest-v1315-tracefs-lower-event-preflight.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1315-tracefs-lower-event-preflight-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1315-tracefs-lower-event-preflight-plan.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V1314_MANIFEST = Path("tmp/wifi/v1314-dynamic-gdsc-esoc-prereq-classifier/manifest.json")
TRACEFS_TARGET = "/sys/kernel/tracing"

TARGET_TRACEPOINTS = (
    ("regulator", "regulator_enable"),
    ("regulator", "regulator_enable_complete"),
    ("regulator", "regulator_set_voltage"),
    ("regulator", "regulator_set_voltage_complete"),
    ("gpio", "gpio_direction"),
    ("gpio", "gpio_value"),
    ("irq", "irq_handler_entry"),
    ("irq", "irq_handler_exit"),
    ("clk", "clk_enable"),
    ("clk", "clk_enable_complete"),
    ("clk", "clk_prepare"),
    ("clk", "clk_prepare_complete"),
    ("power", "power_domain_target"),
    ("power", "device_pm_callback_start"),
    ("power", "device_pm_callback_end"),
    ("msm_pil_event", "pil_event"),
    ("msm_pil_event", "pil_notif"),
    ("msm_pil_event", "pil_func"),
)

REQUIRED_GROUPS = ("regulator", "gpio", "irq", "clk", "power", "msm_pil_event")

FORBIDDEN_TERMS = (
    " set_ftrace_filter",
    " set_graph_function",
    " trace_marker",
    "/enable ",
    " boot_wlan",
    " qcwlanstate",
    "/bind",
    "/unbind",
    "driver_override",
    "insmod",
    "rmmod",
    "modprobe",
    "servicemanager",
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
    "bpftool",
    "bpftrace",
    " boot ",
    " flash ",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--v1314-manifest", type=Path, default=DEFAULT_V1314_MANIFEST)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def tracepoint_label(group: str, event: str) -> str:
    return f"{group}.{event}"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def validate_device_command(command: list[str], allow_mount: bool = False) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V1315 command term {term!r}: {' '.join(command)}")
    if " mount -t " in joined and not allow_mount:
        raise RuntimeError(f"tracefs mount requires explicit V1315 allow flag: {' '.join(command)}")
    if " umount " in joined and not allow_mount:
        raise RuntimeError(f"tracefs cleanup requires explicit V1315 allow flag: {' '.join(command)}")


def run_step(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
    allow_mount: bool = False,
    allow_error: bool = False,
) -> dict[str, Any]:
    validate_device_command(command, allow_mount=allow_mount)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["payload"] = payload
    item["ok"] = bool(capture.ok or allow_error)
    item["raw_ok"] = bool(capture.ok)
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def shell_command(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def tracefs_mounted(payload: str) -> bool:
    return re.search(rf"\s{re.escape(TRACEFS_TARGET)}\s+tracefs\s", payload) is not None


def collect_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "version", ["version"], timeout=10.0)
    run_step(args, store, steps, "selftest", ["selftest"], timeout=20.0)
    run_step(args, store, steps, "status", ["status"], timeout=25.0)
    run_step(args, store, steps, "tracefs-full-before", ["tracefs", "full"], timeout=30.0, allow_error=True)
    run_step(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], timeout=15.0)


def availability_script(args: argparse.Namespace) -> str:
    grep_pattern = "|".join(f"^{group}:{event}$" for group, event in TARGET_TRACEPOINTS)
    return (
        f"BB={args.busybox}; T={TRACEFS_TARGET}; "
        "if [ -r \"$T/available_events\" ]; then "
        "printf 'v1315.available_events_readable=1\\n'; "
        "printf 'v1315.available_events_total='; $BB wc -l < \"$T/available_events\" 2>/dev/null || printf '0\\n'; "
        f"$BB grep -E '{grep_pattern}' \"$T/available_events\" 2>/dev/null || true; "
        "else printf 'v1315.available_events_readable=0\\n'; printf 'v1315.available_events_total=0\\n'; fi"
    )


def format_script(args: argparse.Namespace, group: str, event: str) -> str:
    path = f"{TRACEFS_TARGET}/events/{group}/{event}"
    return (
        f"BB={args.busybox}; P={path}; "
        f"printf 'v1315.tracepoint={group}:{event}\\n'; "
        "if [ -d \"$P\" ]; then printf 'v1315.exists=1\\n'; else printf 'v1315.exists=0\\n'; fi; "
        "if [ -r \"$P/id\" ]; then printf 'v1315.id='; $BB cat \"$P/id\" 2>&1 || true; else printf 'v1315.id=-\\n'; fi; "
        "if [ -r \"$P/format\" ]; then printf 'v1315.format_readable=1\\n'; $BB cat \"$P/format\" 2>&1 || true; "
        "else printf 'v1315.format_readable=0\\n'; fi"
    )


def collect_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    mounted_before = tracefs_mounted(step_payload(steps, "proc-mounts-before"))
    if mounted_before:
        store.write_text("native/tracefs-mount-skipped.txt", "tracefs already mounted before V1315\n")
    else:
        run_step(
            args,
            store,
            steps,
            "tracefs-mount",
            ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", TRACEFS_TARGET],
            timeout=20.0,
            allow_mount=True,
        )
    run_step(args, store, steps, "target-available-events", shell_command(args, availability_script(args)), timeout=30.0)
    for group, event in TARGET_TRACEPOINTS:
        run_step(args, store, steps, f"format-{tracepoint_label(group, event)}", shell_command(args, format_script(args, group, event)), timeout=25.0)
    if not mounted_before:
        run_step(
            args,
            store,
            steps,
            "tracefs-umount",
            ["run", args.busybox, "umount", TRACEFS_TARGET],
            timeout=20.0,
            allow_mount=True,
            allow_error=True,
        )
    run_step(args, store, steps, "tracefs-full-after", ["tracefs", "full"], timeout=30.0, allow_error=True)
    run_step(args, store, steps, "proc-mounts-after", ["cat", "/proc/mounts"], timeout=15.0)
    run_step(args, store, steps, "post-selftest", ["selftest"], timeout=20.0)


def key_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


FIELD_RE = re.compile(r"^\s*field:(?P<decl>.*?);\s*offset:(?P<offset>\d+);\s*size:(?P<size>\d+);\s*signed:(?P<signed>\d+);", re.MULTILINE)


def parse_fields(text: str) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for match in FIELD_RE.finditer(text):
        declaration = match.group("decl").strip()
        parts = declaration.split()
        raw_name = parts[-1] if parts else declaration
        name = re.sub(r"\[.*\]$", "", raw_name)
        fields.append({
            "name": name,
            "declaration": declaration,
            "offset": match.group("offset"),
            "size": match.group("size"),
            "signed": match.group("signed"),
        })
    return fields


def command_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok"))
    return False


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounts_before = step_payload(steps, "proc-mounts-before")
    mounts_after = step_payload(steps, "proc-mounts-after")
    availability = step_payload(steps, "target-available-events")
    event_rows: dict[str, dict[str, Any]] = {}
    group_available = {group: 0 for group in REQUIRED_GROUPS}
    group_format_readable = {group: 0 for group in REQUIRED_GROUPS}

    for group, event in TARGET_TRACEPOINTS:
        payload = step_payload(steps, f"format-{tracepoint_label(group, event)}")
        fields = parse_fields(payload)
        custom_fields = [field for field in fields if not field["name"].startswith("common_")]
        exists = key_value(payload, "v1315.exists") == "1"
        format_readable = key_value(payload, "v1315.format_readable") == "1"
        if exists:
            group_available[group] = group_available.get(group, 0) + 1
        if format_readable:
            group_format_readable[group] = group_format_readable.get(group, 0) + 1
        event_rows[tracepoint_label(group, event)] = {
            "tracepoint": f"{group}:{event}",
            "exists": exists,
            "id": key_value(payload, "v1315.id"),
            "format_readable": format_readable,
            "field_count": len(fields),
            "non_common_field_count": len(custom_fields),
            "non_common_fields": custom_fields,
        }

    available_events_total = key_value(availability, "v1315.available_events_total")
    try:
        available_events_count = int(available_events_total)
    except ValueError:
        available_events_count = 0
    return {
        "mounted_before": tracefs_mounted(mounts_before),
        "mounted_after": tracefs_mounted(mounts_after),
        "available_events_readable": key_value(availability, "v1315.available_events_readable") == "1",
        "available_events_total": available_events_count,
        "event_rows": event_rows,
        "group_available": group_available,
        "group_format_readable": group_format_readable,
        "pre_selftest_ok": command_ok(steps, "selftest"),
        "post_selftest_ok": command_ok(steps, "post-selftest") if any(step.get("name") == "post-selftest" for step in steps) else None,
    }


def decide(command: str, analysis: dict[str, Any], v1314: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1315-tracefs-lower-event-preflight-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1315 preflight with tracefs mount/read/cleanup only",
        )
    if command == "preflight":
        if analysis["pre_selftest_ok"] and v1314.get("decision") == "v1314-provider-internal-first-power-on-trace-gate-selected":
            return (
                "v1315-tracefs-lower-event-preflight-ready",
                True,
                "native health and V1314 prerequisite selection are present",
                "run V1315 tracefs target format preflight",
            )
        return (
            "v1315-tracefs-lower-event-preflight-blocked",
            False,
            "native health or V1314 prerequisite selection missing",
            "repair preflight before tracefs mount/read",
        )
    missing_groups = [group for group in REQUIRED_GROUPS if analysis["group_format_readable"].get(group, 0) <= 0]
    if missing_groups:
        return (
            "v1315-tracefs-lower-event-format-gap",
            False,
            f"missing readable format in groups: {', '.join(missing_groups)}",
            "adjust V1316 target event set before any lower event collector live gate",
        )
    if analysis["mounted_after"]:
        return (
            "v1315-tracefs-cleanup-gap",
            False,
            "tracefs remained mounted after V1315 cleanup",
            "cleanup tracefs before proceeding",
        )
    return (
        "v1315-tracefs-lower-event-preflight-pass",
        True,
        "target lower tracefs event groups exist with readable formats and tracefs cleanup completed",
        "V1316 can build/run a bounded tracefs event collector around the existing late per_proxy PM-service path without Wi-Fi HAL/connect or lower writes",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = []
    for label, item in analysis["event_rows"].items():
        rows.append([
            item["tracepoint"],
            item["exists"],
            item["format_readable"],
            item["id"],
            item["non_common_field_count"],
        ])
    return "\n".join([
        "# Native Init V1315 Tracefs Lower-Event Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Tracefs",
        "",
        markdown_table(["field", "value"], [
            ["mounted_before", analysis["mounted_before"]],
            ["mounted_after", analysis["mounted_after"]],
            ["available_events_readable", analysis["available_events_readable"]],
            ["available_events_total", analysis["available_events_total"]],
            ["group_available", json.dumps(analysis["group_available"], sort_keys=True)],
            ["group_format_readable", json.dumps(analysis["group_format_readable"], sort_keys=True)],
        ]),
        "",
        "## Target Events",
        "",
        markdown_table(["tracepoint", "exists", "format_readable", "id", "non_common_fields"], rows),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], [[key, manifest[key]] for key in (
            "device_commands_executed",
            "tracefs_mount_attempted",
            "tracefs_control_write_executed",
            "pm_service_trigger_executed",
            "pmic_write_executed",
            "gpio_line_request_executed",
            "direct_esoc_ioctl_executed",
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "wifi_bringup_executed",
            "flash_executed",
            "partition_write_executed",
        )]),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if args.command in {"preflight", "run"}:
        collect_preflight(args, store, steps)
    if args.command == "run":
        if not args.allow_tracefs_mount and not args.assume_yes:
            raise SystemExit("V1315 run requires --allow-tracefs-mount or --assume-yes")
        collect_live(args, store, steps)

    v1314 = load_json(args.v1314_manifest)
    analysis = build_analysis(args, steps)
    decision, passed, reason, next_step = decide(args.command, analysis, v1314)
    return {
        "cycle": "v1315",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1314_manifest": str(repo_path(args.v1314_manifest)),
        },
        "steps": steps,
        "analysis": analysis,
        "device_commands_executed": args.command in {"preflight", "run"},
        "tracefs_mount_attempted": args.command == "run",
        "tracefs_control_write_executed": False,
        "pm_service_trigger_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    latest_pointer = LATEST_POINTER
    if args.command == "plan" and args.out_dir == DEFAULT_OUT_DIR:
        args.out_dir = PLAN_OUT_DIR
        latest_pointer = PLAN_LATEST_POINTER
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(latest_pointer), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"tracefs_mounted_after: {manifest['analysis']['mounted_after']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
