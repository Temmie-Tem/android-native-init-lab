#!/usr/bin/env python3
"""V777 bounded tracepoint format/field classifier.

V776 proved stock v724 exposes candidate tracepoints. V777 reads only selected
tracepoint format/id files to decide whether a later BPF tracepoint attach proof
would expose useful modem/PIL/QMI/Wi-Fi fields.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v777-tracepoint-format-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v777-tracepoint-format-classifier.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V776_MANIFEST = Path("tmp/wifi/v776-tracepoint-inventory/manifest.json")
TRACEFS_TARGET = "/sys/kernel/tracing"

TRACEPOINTS = (
    ("msm_pil_event", "pil_event"),
    ("msm_pil_event", "pil_notif"),
    ("msm_pil_event", "pil_func"),
    ("dfc", "dfc_qmi_tc"),
    ("cfg80211", "cfg80211_report_wowlan_wakeup"),
)

FORBIDDEN_TERMS = (
    " enable",
    " set_ftrace_filter",
    " set_graph_function",
    " trace_marker",
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
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--v776-manifest", type=Path, default=DEFAULT_V776_MANIFEST)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def tracepoint_label(group: str, event: str) -> str:
    return f"{group}.{event}"


def tracepoint_path(group: str, event: str) -> str:
    return f"{TRACEFS_TARGET}/events/{group}/{event}"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def tracefs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(TRACEFS_TARGET)}\s+tracefs\s", text) is not None


def validate_device_command(command: list[str], allow_mount: bool = False) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V777 command term {term!r}: {' '.join(command)}")
    if " mount -t " in joined and not allow_mount:
        raise RuntimeError(f"tracefs mount requires explicit V777 allow flag: {' '.join(command)}")
    if " umount " in joined and not allow_mount:
        raise RuntimeError(f"tracefs cleanup requires explicit V777 allow flag: {' '.join(command)}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             allow_mount: bool = False) -> dict[str, Any]:
    validate_device_command(command, allow_mount=allow_mount)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def shell_command(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def format_read_script(args: argparse.Namespace, group: str, event: str) -> str:
    base = tracepoint_path(group, event)
    return (
        f"BB={args.busybox}; P={base}; "
        f"printf 'v777.tracepoint={group}:{event}\\n'; "
        "if [ -d \"$P\" ]; then printf 'v777.exists=1\\n'; else printf 'v777.exists=0\\n'; fi; "
        "if [ -r \"$P/id\" ]; then printf 'v777.id='; $BB cat \"$P/id\" 2>&1 || true; else printf 'v777.id=-\\n'; fi; "
        "if [ -r \"$P/format\" ]; then printf 'v777.format_readable=1\\n'; $BB cat \"$P/format\" 2>&1 || true; "
        "else printf 'v777.format_readable=0\\n'; fi"
    )


def collect_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "tracefs-full-before", ["tracefs", "full"], 30.0)
    run_step(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], 15.0)


def collect_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    mounted_before = tracefs_mounted(step_payload(steps, "proc-mounts-before"))
    if mounted_before:
        store.write_text("native/tracefs-mount-skipped.txt", "tracefs already mounted before V777\n")
    else:
        run_step(args, store, steps, "tracefs-mount", ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", TRACEFS_TARGET], 20.0, allow_mount=True)
    for group, event in TRACEPOINTS:
        label = tracepoint_label(group, event)
        run_step(args, store, steps, f"format-{label}", shell_command(args, format_read_script(args, group, event)), 25.0)
    if not mounted_before:
        run_step(args, store, steps, "tracefs-umount", ["run", args.busybox, "umount", TRACEFS_TARGET], 20.0, allow_mount=True)
    run_step(args, store, steps, "tracefs-full-after", ["tracefs", "full"], 30.0)
    run_step(args, store, steps, "proc-mounts-after", ["cat", "/proc/mounts"], 15.0)


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def key_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


FIELD_RE = re.compile(r"^\s*field:(?P<decl>.*?);\s*offset:(?P<offset>\d+);\s*size:(?P<size>\d+);\s*signed:(?P<signed>\d+);", re.MULTILINE)


def parse_fields(text: str) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for match in FIELD_RE.finditer(text):
        declaration = match.group("decl").strip()
        raw_name = declaration.split()[-1] if declaration.split() else declaration
        name = re.sub(r"\[.*\]$", "", raw_name)
        fields.append({
            "name": name,
            "declaration": declaration,
            "offset": match.group("offset"),
            "size": match.group("size"),
            "signed": match.group("signed"),
        })
    return fields


def non_common_fields(fields: list[dict[str, str]]) -> list[dict[str, str]]:
    return [field for field in fields if not field["name"].startswith("common_")]


def format_payloads(steps: list[dict[str, Any]]) -> dict[str, str]:
    payloads: dict[str, str] = {}
    for group, event in TRACEPOINTS:
        label = tracepoint_label(group, event)
        payloads[label] = step_payload(steps, f"format-{label}")
    return payloads


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v776 = load_json(args.v776_manifest)
    mounts_before = step_payload(steps, "proc-mounts-before")
    mounts_after = step_payload(steps, "proc-mounts-after")
    mounted_before = tracefs_mounted(mounts_before)
    mounted_after = tracefs_mounted(mounts_after)
    payloads = format_payloads(steps)
    events: dict[str, Any] = {}
    useful_event_count = 0
    for label, payload in payloads.items():
        fields = parse_fields(payload)
        custom_fields = non_common_fields(fields)
        format_readable = key_value(payload, "v777.format_readable") == "1"
        if format_readable and custom_fields:
            useful_event_count += 1
        events[label] = {
            "tracepoint": key_value(payload, "v777.tracepoint"),
            "exists": key_value(payload, "v777.exists") == "1",
            "id": key_value(payload, "v777.id"),
            "format_readable": format_readable,
            "field_count": len(fields),
            "non_common_field_count": len(custom_fields),
            "non_common_fields": custom_fields,
        }
    return {
        "v776": {
            "manifest": str(repo_path(args.v776_manifest)),
            "decision": v776.get("decision", ""),
            "pass": bool(v776.get("pass")),
            "next_step": v776.get("next_step", ""),
        },
        "approval": {
            "allow_tracefs_mount": args.allow_tracefs_mount,
            "assume_yes": args.assume_yes,
        },
        "proof": {
            "mounted_before": mounted_before,
            "mount_step_ok": any(step.get("name") == "tracefs-mount" and step.get("ok") for step in steps),
            "mounted_by_us": args.command == "run" and not mounted_before and any(step.get("name") == "tracefs-mount" and step.get("ok") for step in steps),
            "umount_step_ok": any(step.get("name") == "tracefs-umount" and step.get("ok") for step in steps),
            "mounted_after": mounted_after,
            "format_event_count": len(events),
            "format_readable_count": sum(1 for event in events.values() if event["format_readable"]),
            "useful_event_count": useful_event_count,
            "events": events,
        },
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str],
              next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    command = manifest["command"]
    analysis = manifest["analysis"]
    proof = analysis["proof"]
    checks: list[Check] = []
    add_check(
        checks,
        "v776-input",
        "pass" if analysis["v776"]["decision"] == "v776-tracepoint-candidates-found" else "blocked",
        "blocker",
        f"decision={analysis['v776']['decision']} pass={analysis['v776']['pass']}",
        [analysis["v776"]["manifest"]],
        "complete V776 tracepoint inventory before format classification",
    )
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight then bounded format reads")
        return checks
    add_check(
        checks,
        "bridge-native-health",
        "pass" if any(step.get("name") == "version" and step.get("ok") for step in manifest["steps"]) else "blocked",
        "blocker",
        "version command ok" if any(step.get("name") == "version" and step.get("ok") for step in manifest["steps"]) else "version command missing/failed",
        ["native/version.txt"],
        "restore v724 bridge command path",
    )
    if command == "preflight":
        add_check(checks, "preflight-only", "pass", "info", "no tracefs mount attempted", ["native/tracefs-full-before.txt"], "run with explicit tracefs mount approval")
        return checks
    add_check(
        checks,
        "tracefs-cleanup",
        "pass" if (proof["mounted_before"] or not proof["mounted_after"]) else "blocked",
        "blocker",
        f"mounted_before={proof['mounted_before']} mounted_by_us={proof['mounted_by_us']} umount_step_ok={proof['umount_step_ok']} mounted_after={proof['mounted_after']}",
        ["native/proc-mounts-after.txt"],
        "cleanup tracefs mount before continuing",
    )
    add_check(
        checks,
        "format-readability",
        "pass" if proof["format_readable_count"] == proof["format_event_count"] else "review",
        "warn",
        f"format_readable={proof['format_readable_count']}/{proof['format_event_count']}",
        ["native/format-*.txt"],
        "if formats are unreadable, avoid BPF attach and use non-tracepoint observers",
    )
    add_check(
        checks,
        "useful-fields",
        "pass" if proof["useful_event_count"] > 0 else "review",
        "warn",
        f"useful_event_count={proof['useful_event_count']}",
        ["native/format-*.txt"],
        "if event-specific fields exist, select a bounded BPF attach proof target",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v777-tracepoint-format-classifier-plan-ready",
            True,
            "plan-only; no device command, BPF attach, Wi-Fi action, or network action executed",
            "run V777 preflight, then bounded tracepoint format reads",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v777-tracepoint-format-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blocker before using tracepoint format results",
        )
    proof = analysis["proof"]
    if args.command == "preflight":
        return (
            "v777-tracepoint-format-preflight-ready",
            True,
            "native bridge is healthy and no tracefs mount was attempted",
            "run bounded tracepoint format reads with explicit mount approval",
        )
    if proof["useful_event_count"] > 0:
        return (
            "v777-tracepoint-format-fields-classified",
            True,
            "selected stock-kernel tracepoints expose readable event-specific fields",
            "V778 can plan one bounded BPF tracepoint attach proof against the most useful low-risk event",
        )
    return (
        "v777-tracepoint-format-no-useful-fields",
        True,
        "selected candidate tracepoints have no useful event-specific fields",
        "prefer non-BPF stock observers and keep custom kernel flashing paused",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    proof = manifest.get("analysis", {}).get("proof", {})
    rows: list[list[Any]] = []
    for label, event in (proof.get("events") or {}).items():
        rows.append([
            label,
            event.get("id"),
            event.get("format_readable"),
            event.get("field_count"),
            event.get("non_common_field_count"),
            ", ".join(field.get("name", "") for field in event.get("non_common_fields", [])[:8]),
        ])
    return "\n".join([
        "# V777 Tracepoint Format Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        f"- wifi_action_executed: `{manifest['wifi_action_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]),
        "",
        "## Formats",
        "",
        markdown_table(["event", "id", "readable", "fields", "event_fields", "sample_fields"], rows),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if args.command in {"preflight", "run"}:
        collect_preflight(args, store, steps)
    if args.command == "run":
        if not args.allow_tracefs_mount or not args.assume_yes:
            raise RuntimeError("V777 live run requires --allow-tracefs-mount --assume-yes")
        collect_live(args, store, steps)
    analysis = build_analysis(args, steps)
    manifest: dict[str, Any] = {
        "cycle": "v777",
        "generated_at": now_iso(),
        "command": args.command,
        "steps": steps,
        "analysis": analysis,
        "device_commands_executed": args.command in {"preflight", "run"},
        "tracefs_mount_attempted": args.command == "run",
        "bpf_attach_executed": False,
        "ftrace_control_write_executed": False,
        "wifi_action_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args, checks, analysis)
    manifest.update({
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
    })
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(LATEST_POINTER, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"tracefs_mount_attempted: {manifest['tracefs_mount_attempted']}")
    print(f"bpf_attach_executed: {manifest['bpf_attach_executed']}")
    print(f"wifi_action_executed: {manifest['wifi_action_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
