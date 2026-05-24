#!/usr/bin/env python3
"""V776 bounded stock-kernel tracepoint inventory.

V775 paused custom-kernel flashing and selected stock-kernel observability. This
runner performs the next minimal live gate on recovered v724: temporarily mount
tracefs if needed, read tracepoint/event surfaces, classify ICNSS/WLAN/QMI/QRTR
candidate events, and clean up any mount it created.

It does not write trace controls, attach BPF programs, trigger Wi-Fi, start HALs,
scan/connect, use credentials, change routes, ping externally, reboot, or write
boot partitions.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v776-tracepoint-inventory")
LATEST_POINTER = Path("tmp/wifi/latest-v776-tracepoint-inventory.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V775_MANIFEST = Path("tmp/wifi/v775-boot-incompat-postmortem/manifest.json")
TRACEFS_TARGET = "/sys/kernel/tracing"

CANDIDATE_PATTERNS = {
    "icnss_wlan_wifi": "icnss|wlan|wifi|wcn|qcacld|qca",
    "qmi_qrtr_servreg": "qmi|qrtr|servreg|service.loc|service_notifier|sysmon",
    "subsystem_remoteproc": "subsys|remoteproc|pil|modem|mss|mdm|esoc",
    "net_stack": "net|skb|napi|sock|tcp|udp|icmp",
    "scheduler_work": "sched|workqueue|irq|timer",
}

FORBIDDEN_TERMS = (
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
    parser.add_argument("--v775-manifest", type=Path, default=DEFAULT_V775_MANIFEST)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_device_command(command: list[str], allow_mount: bool = False) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V776 command term {term!r}: {' '.join(command)}")
    if " mount -t " in joined and not allow_mount:
        raise RuntimeError(f"tracefs mount requires explicit V776 allow flag: {' '.join(command)}")
    if " umount " in joined and not allow_mount:
        raise RuntimeError(f"tracefs cleanup requires explicit V776 allow flag: {' '.join(command)}")


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


def tracefs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(TRACEFS_TARGET)}\s+tracefs\s", text) is not None


def tracefs_state_script(args: argparse.Namespace) -> str:
    return (
        f"BB={args.busybox}; T={TRACEFS_TARGET}; "
        "$BB grep -q \" $T tracefs \" /proc/mounts && printf 'v776.mounted_during=1\\n' || printf 'v776.mounted_during=0\\n'; "
        "for f in available_events available_tracers current_tracer tracing_on trace_clock; do "
        "P=\"$T/$f\"; printf '== %s ==\\n' \"$P\"; "
        "if [ -r \"$P\" ]; then printf 'v776.readable.%s=1\\n' \"$f\"; $BB head -n 80 \"$P\" 2>&1 || true; "
        "else printf 'v776.readable.%s=0\\n' \"$f\"; fi; "
        "done; "
        "[ -d \"$T/events\" ] && printf 'v776.events_dir=1\\n' || printf 'v776.events_dir=0\\n'"
    )


def available_events_script(args: argparse.Namespace) -> str:
    return (
        f"BB={args.busybox}; T={TRACEFS_TARGET}; "
        "if [ -r \"$T/available_events\" ]; then "
        "TOTAL=$($BB wc -l < \"$T/available_events\" 2>/dev/null || printf 0); "
        "printf 'v776.available_events_total=%s\\n' \"$TOTAL\"; "
        "$BB head -n 120 \"$T/available_events\" 2>&1 || true; "
        "else printf 'v776.available_events_total=0\\n'; fi"
    )


def event_dirs_script(args: argparse.Namespace) -> str:
    return (
        f"BB={args.busybox}; T={TRACEFS_TARGET}; "
        "if [ -d \"$T/events\" ]; then $BB find \"$T/events\" -maxdepth 2 -type d 2>/dev/null | $BB head -n 220 || true; fi"
    )


def candidate_script(args: argparse.Namespace, name: str, pattern: str) -> str:
    return (
        f"BB={args.busybox}; T={TRACEFS_TARGET}; "
        "if [ -r \"$T/available_events\" ]; then "
        f"COUNT=$($BB grep -Ei '{pattern}' \"$T/available_events\" 2>/dev/null | $BB wc -l || printf 0); "
        f"printf 'v776.candidate_count.{name}=%s\\n' \"$COUNT\"; "
        f"$BB grep -Ei '{pattern}' \"$T/available_events\" 2>/dev/null | $BB head -n 120 || true; "
        f"else printf 'v776.candidate_count.{name}=0\\n'; fi"
    )


def collect_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "tracefs-full-before", ["tracefs", "full"], 30.0)
    run_step(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], 15.0)


def collect_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    mounted_before = tracefs_mounted(step_payload(steps, "proc-mounts-before"))
    if mounted_before:
        store.write_text("native/tracefs-mount-skipped.txt", "tracefs already mounted before V776\n")
    else:
        run_step(args, store, steps, "tracefs-mount", ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", TRACEFS_TARGET], 20.0, allow_mount=True)
    run_step(args, store, steps, "tracefs-state", shell_command(args, tracefs_state_script(args)), 25.0)
    run_step(args, store, steps, "available-events-head", shell_command(args, available_events_script(args)), 30.0)
    run_step(args, store, steps, "event-dirs-sample", shell_command(args, event_dirs_script(args)), 30.0)
    for name, pattern in CANDIDATE_PATTERNS.items():
        run_step(args, store, steps, f"candidate-{name}", shell_command(args, candidate_script(args, name, pattern)), 30.0)
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


def candidate_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in CANDIDATE_PATTERNS:
        raw = key_value(text, f"v776.candidate_count.{name}")
        try:
            counts[name] = int(raw)
        except ValueError:
            counts[name] = 0
    return counts


def line_hits(text: str, pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    hits: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            hits.append(line.strip())
        if len(hits) >= limit:
            break
    return hits


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v775 = load_json(args.v775_manifest)
    state = step_payload(steps, "tracefs-state")
    available = step_payload(steps, "available-events-head")
    candidate_payload = "\n".join(step_payload(steps, f"candidate-{name}") for name in CANDIDATE_PATTERNS)
    mounts_before = step_payload(steps, "proc-mounts-before")
    mounts_after = step_payload(steps, "proc-mounts-after")
    mounted_before = tracefs_mounted(mounts_before)
    mounted_after = tracefs_mounted(mounts_after)
    counts = candidate_counts(candidate_payload)
    mounted_by_us = args.command == "run" and not mounted_before and any(step.get("name") == "tracefs-mount" and step.get("ok") for step in steps)
    return {
        "v775": {
            "manifest": str(repo_path(args.v775_manifest)),
            "decision": v775.get("decision", ""),
            "pass": bool(v775.get("pass")),
            "next_step": v775.get("next_step", ""),
        },
        "approval": {
            "allow_tracefs_mount": args.allow_tracefs_mount,
            "assume_yes": args.assume_yes,
        },
        "proof": {
            "mounted_before": mounted_before,
            "mount_step_ok": any(step.get("name") == "tracefs-mount" and step.get("ok") for step in steps),
            "mounted_during": key_value(state, "v776.mounted_during") == "1",
            "mounted_by_us": mounted_by_us,
            "umount_step_ok": any(step.get("name") == "tracefs-umount" and step.get("ok") for step in steps),
            "mounted_after": mounted_after,
            "available_events_readable": key_value(state, "v776.readable.available_events") == "1",
            "available_tracers_readable": key_value(state, "v776.readable.available_tracers") == "1",
            "current_tracer_readable": key_value(state, "v776.readable.current_tracer") == "1",
            "tracing_on_readable": key_value(state, "v776.readable.tracing_on") == "1",
            "trace_clock_readable": key_value(state, "v776.readable.trace_clock") == "1",
            "events_dir": key_value(state, "v776.events_dir") == "1",
            "available_events_total": key_value(available, "v776.available_events_total"),
            "candidate_counts": counts,
            "candidate_total": sum(counts.values()),
            "candidate_lines_sample": line_hits(candidate_payload, r"icnss|wlan|wifi|wcn|qcacld|qca|qmi|qrtr|servreg|sysmon|subsys|remoteproc|pil|modem|mss|mdm|esoc"),
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
        "v775-input",
        "pass" if analysis["v775"]["decision"] == "v775-non-dtb-custom-kernel-incompat-classified" else "blocked",
        "blocker",
        f"decision={analysis['v775']['decision']} pass={analysis['v775']['pass']}",
        [analysis["v775"]["manifest"]],
        "complete V775 before selecting stock-kernel tracepoint inventory",
    )
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight then bounded live inventory")
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
        "tracefs-mount-window",
        "pass" if proof["mounted_during"] and (proof["mounted_before"] or proof["mount_step_ok"]) else "blocked",
        "blocker",
        f"mounted_before={proof['mounted_before']} mount_step_ok={proof['mount_step_ok']} mounted_during={proof['mounted_during']}",
        ["native/tracefs-state.txt"],
        "tracefs must mount/read before tracepoint inventory can classify",
    )
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
        "available-events",
        "pass" if proof["available_events_readable"] else "review",
        "warn",
        f"readable={proof['available_events_readable']} total={proof['available_events_total']}",
        ["native/available-events-head.txt"],
        "if unavailable, use event directory inventory or non-tracepoint observers",
    )
    add_check(
        checks,
        "candidate-events",
        "pass" if proof["candidate_total"] > 0 else "review",
        "warn",
        f"candidate_total={proof['candidate_total']} counts={proof['candidate_counts']}",
        ["native/candidate-*.txt"],
        "if candidates exist, classify whether later BPF tracepoint attach proof is narrowly useful",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v776-tracepoint-inventory-plan-ready",
            True,
            "plan-only; no device command, mount, BPF attach, Wi-Fi action, or network action executed",
            "run V776 preflight, then bounded tracefs mount/read/cleanup inventory",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v776-tracepoint-inventory-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blocker before using tracepoint inventory results",
        )
    proof = analysis["proof"]
    if args.command == "preflight":
        return (
            "v776-tracepoint-inventory-preflight-ready",
            True,
            "native bridge is healthy and no tracefs mount was attempted",
            "run bounded tracefs available_events inventory with explicit mount approval",
        )
    if proof["candidate_total"] > 0:
        return (
            "v776-tracepoint-candidates-found",
            True,
            "stock v724 tracefs exposes readable tracepoint inventory with candidate events",
            "V777 should classify candidate event semantics and only then consider a bounded BPF tracepoint attach proof",
        )
    return (
        "v776-tracepoint-inventory-no-focused-candidates",
        True,
        "tracefs inventory completed but found no focused ICNSS/WLAN/QMI/QRTR candidates",
        "prefer non-tracepoint stock-kernel observers; do not resume custom kernel flashing",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    proof = manifest.get("analysis", {}).get("proof", {})
    return "\n".join([
        "# V776 Tracepoint Inventory",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- tracefs_mount_attempted: `{manifest['tracefs_mount_attempted']}`",
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
        "## Tracepoint Surface",
        "",
        markdown_table(["signal", "value"], [
            ["mounted_before", proof.get("mounted_before")],
            ["mounted_by_us", proof.get("mounted_by_us")],
            ["mounted_after", proof.get("mounted_after")],
            ["available_events_readable", proof.get("available_events_readable")],
            ["available_events_total", proof.get("available_events_total")],
            ["candidate_total", proof.get("candidate_total")],
            ["candidate_counts", proof.get("candidate_counts")],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if args.command in {"preflight", "run"}:
        collect_preflight(args, store, steps)
    if args.command == "run":
        if not args.allow_tracefs_mount or not args.assume_yes:
            raise RuntimeError("V776 live run requires --allow-tracefs-mount --assume-yes")
        collect_live(args, store, steps)
    analysis = build_analysis(args, steps)
    manifest: dict[str, Any] = {
        "cycle": "v776",
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
