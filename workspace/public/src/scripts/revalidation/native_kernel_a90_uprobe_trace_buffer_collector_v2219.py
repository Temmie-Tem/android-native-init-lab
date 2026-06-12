#!/usr/bin/env python3
"""Run V2219 a90 trace_uprobe trace-buffer collector.

This collector intentionally does not attach BPF and does not write tracefs.
It reads the already-registered a90cnss/a90libqmi/a90pmsrv trace_uprobe event
state and snapshots the trace buffer for matching lines.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
REMOTE_TOYBOX = "/cache/bin/busybox"

sys.path.insert(0, str(SCRIPT_DIR))
import a90_transport as transport  # noqa: E402

EVENTS = [
    "a90cnss:wlfw_start",
    "a90cnss:wlfw_service_request",
    "a90cnss:wlfw_ind_register_qmi",
    "a90cnss:wlfw_cap_qmi",
    "a90cnss:wlfw_bdf_entry",
    "a90cnss:wlfw_bdf_send_ret",
    "a90cnss:wlfw_qmi_ind_cb_entry",
    "a90cnss:wlfw_handle_ind_type",
    "a90cnss:wlfw_handle_ind_type_0x28",
    "a90cnss:wlfw_handle_ind_type_0x2a",
    "a90cnss:wlfw_handle_ind_type_0x41",
    "a90cnss:dms_service_request",
    "a90cnss:dms_get_wlan_address_entry",
    "a90cnss:wlan_send_status_entry",
    "a90cnss:wlan_send_version_entry",
    "a90cnss:pm_init_pm_client_register_call",
    "a90cnss:pm_init_pm_client_connect_call",
    "a90libqmi:libqmi_client_init_instance_entry",
    "a90libqmi:libqmi_get_service_list_lookup_call",
    "a90libqmi:libqmi_get_service_list_lookup_ret",
    "a90pmsrv:pm_service_post_ack_qmi_restart_ind_call",
]

CONTROL_LINE_RE = re.compile(
    r"^(a90:/#|A90P1 BEGIN|A90P1 END|\[done\]|\[exit |run: pid=|cmdv1x )"
)
LINKER_WARNING_RE = re.compile(r"^(WARNING: )?linker: Warning: failed to find generated linker configuration")
TRACE_LINE_RE = re.compile(
    r"^\s*(?P<task>.+?)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+"
    r"(?P<flags>\S+)\s+(?P<ts>\d+\.\d+):\s+"
    r"(?:(?P<group>a90cnss|a90libqmi|a90pmsrv):)?"
    r"(?P<event>[A-Za-z0-9_]+):\s+"
    r"\((?P<probe_ip>0x[0-9a-fA-F]+)\)(?P<args>.*)$"
)
KV_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\"[^\"]*\"|\S+)")


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    elapsed_sec: float
    stdout_path: str
    stderr_path: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def run_host(
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    command: list[str],
    *,
    timeout: float = 60.0,
    allow_error: bool = False,
) -> str:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    elapsed = time.monotonic() - started
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    step = StepResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        elapsed_sec=round(elapsed, 3),
        stdout_path=str(stdout_path.relative_to(REPO_ROOT)),
        stderr_path=str(stderr_path.relative_to(REPO_ROOT)),
    )
    steps.append(step)
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(
            f"{name} failed rc={completed.returncode}\n"
            f"stdout={stdout_path}\nstderr={stderr_path}\n{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout


def a90ctl(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    argv: list[str],
    *,
    timeout: float = 60.0,
    allow_error: bool = False,
) -> str:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "a90ctl.py"),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(timeout),
    ]
    if allow_error:
        command.append("--allow-error")
    command.extend(argv)
    return run_host(out_dir, steps, name, command, timeout=timeout + 10, allow_error=allow_error)


def run_device_shell(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    script: str,
    *,
    timeout: float = 60.0,
    allow_error: bool = False,
) -> str:
    return a90ctl(
        args,
        out_dir,
        steps,
        name,
        ["run", args.toybox, "sh", "-c", script],
        timeout=timeout,
        allow_error=allow_error,
    )


def clean_cmdv1_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip("\r")
        if CONTROL_LINE_RE.match(line):
            continue
        if LINKER_WARNING_RE.match(line):
            continue
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def parse_event_state(text: str) -> dict[str, dict[str, Any]]:
    clean = clean_cmdv1_text(text)
    states: dict[str, dict[str, Any]] = {}
    current: str | None = None
    pending_key: str | None = None
    for line in clean.splitlines():
        if line.startswith("EVENT "):
            current = line.split(" ", 1)[1].strip()
            states[current] = {"exists": False, "id": None, "enable": None}
            pending_key = None
            continue
        if current is None:
            continue
        if pending_key and re.fullmatch(r"\d+", line.strip()):
            value = line.strip()
            if pending_key == "id":
                states[current]["id"] = int(value, 10)
            else:
                states[current]["enable"] = value
            pending_key = None
            continue
        if line == "exists=1":
            states[current]["exists"] = True
            continue
        if line.startswith("id="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                states[current]["id"] = int(value)
                pending_key = None
            else:
                pending_key = "id"
            continue
        if line.startswith("enable="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                states[current]["enable"] = value
                pending_key = None
            else:
                pending_key = "enable"
            continue
    return states


def event_name_map(states: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for full_name in states:
        group, name = full_name.split(":", 1)
        mapping.setdefault(name, []).append(group)
    return mapping


def parse_args_text(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for match in KV_RE.finditer(text):
        value = match.group("value")
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        parsed[match.group("key")] = value
    return parsed


def is_kernel_va(value: int) -> bool:
    return value >= 0xFFFFFF8000000000


def parse_trace_lines(text: str, states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    clean = clean_cmdv1_text(text)
    name_to_groups = event_name_map(states)
    rows: list[dict[str, Any]] = []
    for line in clean.splitlines():
        match = TRACE_LINE_RE.match(line)
        if not match:
            continue
        event = match.group("event")
        group = match.group("group")
        if group is None:
            groups = name_to_groups.get(event, [])
            group = groups[0] if len(groups) == 1 else "unknown"
        full_name = f"{group}:{event}" if group != "unknown" else event
        probe_ip = int(match.group("probe_ip"), 16)
        rows.append(
            {
                "line": line,
                "group": group,
                "event": event,
                "full_name": full_name,
                "task": match.group("task").strip(),
                "pid": int(match.group("pid"), 10),
                "cpu": int(match.group("cpu"), 10),
                "flags": match.group("flags"),
                "timestamp": float(match.group("ts")),
                "probe_ip": f"0x{probe_ip:016x}",
                "probe_ip_kernel_va": is_kernel_va(probe_ip),
                "args": parse_args_text(match.group("args")),
            }
        )
    return rows


def summarize_hits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    first: dict[str, dict[str, Any]] = {}
    last: dict[str, dict[str, Any]] = {}
    kernel_ip_count = 0
    for row in rows:
        name = row["full_name"]
        counts[name] = counts.get(name, 0) + 1
        first.setdefault(name, row)
        last[name] = row
        if row["probe_ip_kernel_va"]:
            kernel_ip_count += 1
    return {
        "total_hits": len(rows),
        "event_counts": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
        "first_hits": {key: value["line"] for key, value in sorted(first.items())},
        "last_hits": {key: value["line"] for key, value in sorted(last.items())},
        "kernel_probe_ip_count": kernel_ip_count,
        "user_probe_ip_count": len(rows) - kernel_ip_count,
    }


def residual_state(summary: dict[str, Any]) -> dict[str, Any]:
    selftest_ok = bool(summary.get("selftest_fail0"))
    device_touched = bool(summary.get("steps"))
    cleanup_required = bool(device_touched and not selftest_ok)
    return {
        "device_touched": device_touched,
        "flash_reboot": False,
        "test_flash_ok": False,
        "rollback_ok": True,
        "rollback_attempt": "not-needed-no-flash",
        "selftest_ok": selftest_ok,
        "cleanup_required": cleanup_required,
        "residual_risk": "post-selftest-incomplete" if cleanup_required else "none",
        "wifi_scan_connect": False,
        "credentials_used": False,
        "dhcp_routes_ping": False,
        "tracefs_control_write": False,
        "bpf_attach": False,
        "probe_write_user_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2219-a90-uprobe-trace-buffer")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    parser.add_argument("--tail-lines", type=int, default=4096)
    parser.add_argument("--wait-sec", type=int, default=2)
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "steps": [],
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "safety": {
            "tracefs_control_write": False,
            "bpf_attach": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
        },
    }

    try:
        with transport.phase(summary, "preflight_bridge_status"):
            run_host(
                out_dir,
                steps,
                "bridge-status",
                [sys.executable, str(SCRIPT_DIR / "a90_bridge.py"), "status", "--json"],
                timeout=30,
                allow_error=True,
            )
            a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=args.timeout, allow_error=True)

        events_shell = " ".join(EVENTS)
        state_script = (
            "for e in " + events_shell + "; do "
            "g=${e%:*}; n=${e#*:}; d=/sys/kernel/tracing/events/$g/$n; "
            "echo EVENT $e; "
            "test -d $d && echo exists=1 || echo exists=0; "
            "test -r $d/id && { echo -n id=; cat $d/id; }; "
            "test -r $d/enable && { echo -n enable=; cat $d/enable; }; "
            "done; "
            "echo tracing_on=$(cat /sys/kernel/tracing/tracing_on 2>/dev/null); "
            "echo trace_clock=$(cat /sys/kernel/tracing/trace_clock 2>/dev/null | tr '\\n' ' ')"
        )
        with transport.phase(summary, "event_state_snapshot"):
            event_state_raw = run_device_shell(args, out_dir, steps, "event-state", state_script, timeout=args.timeout)
            event_state_clean = clean_cmdv1_text(event_state_raw)
            (out_dir / "event_state.txt").write_text(event_state_clean)
            states = parse_event_state(event_state_raw)

        if args.wait_sec > 0:
            with transport.phase(summary, "bounded_idle_wait"):
                run_device_shell(args, out_dir, steps, "bounded-idle-wait", f"sleep {args.wait_sec}", timeout=args.wait_sec + 20)

        trace_script = (
            "grep -E 'a90cnss|a90libqmi|a90pmsrv' /sys/kernel/tracing/trace 2>/dev/null "
            f"| tail -n {args.tail_lines}"
        )
        with transport.phase(summary, "trace_buffer_snapshot"):
            trace_raw = run_device_shell(args, out_dir, steps, "trace-buffer-snapshot", trace_script, timeout=args.timeout, allow_error=True)
            trace_clean = clean_cmdv1_text(trace_raw)
            (out_dir / "a90_trace_tail.txt").write_text(trace_clean)
        with transport.phase(summary, "trace_parse"):
            rows = parse_trace_lines(trace_raw, states)
            (out_dir / "parsed_hits.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
            hit_summary = summarize_hits(rows)

        with transport.phase(summary, "post_selftest"):
            selftest = a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        existing = [name for name, state in states.items() if state.get("exists")]
        enabled = [name for name, state in states.items() if state.get("enable") == "1"]
        summary.update(
            {
                "decision": (
                    "v2219-a90-uprobe-trace-buffer-hits-captured"
                    if rows
                    else "v2219-a90-uprobe-trace-buffer-ready-current-window-nohit"
                ),
                "pass": bool(existing) and bool(enabled) and "fail=0" in selftest,
                "event_state": states,
                "event_total": len(EVENTS),
                "event_exists_count": len(existing),
                "event_enabled_count": len(enabled),
                "events_existing": existing,
                "events_enabled": enabled,
                "trace_tail_path": str((out_dir / "a90_trace_tail.txt").relative_to(REPO_ROOT)),
                "parsed_hits_path": str((out_dir / "parsed_hits.json").relative_to(REPO_ROOT)),
                "hit_summary": hit_summary,
                "trace_buffer_line_count": len(trace_clean.splitlines()) if trace_clean else 0,
                "collector_mode": "trace-buffer-read-only",
                "selftest_fail0": "fail=0" in selftest,
            }
        )
    except Exception as exc:  # noqa: BLE001
        summary["decision"] = "v2219-a90-uprobe-trace-buffer-failed"
        summary["pass"] = False
        summary["error"] = str(exc)
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [
            {
                "name": step.name,
                "command": step.command,
                "returncode": step.returncode,
                "ok": step.ok,
                "elapsed_sec": step.elapsed_sec,
                "stdout_path": step.stdout_path,
                "stderr_path": step.stderr_path,
            }
            for step in steps
        ]
        transport.set_residual_state(summary, residual_state(summary))
        transport.add_total_phase(summary, "artifact_write", time.monotonic(), ok=True)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "decision": summary.get("decision"),
                    "pass": summary.get("pass"),
                    "out_dir": summary.get("out_dir"),
                    "event_exists_count": summary.get("event_exists_count"),
                    "event_enabled_count": summary.get("event_enabled_count"),
                    "trace_buffer_line_count": summary.get("trace_buffer_line_count"),
                    "total_hits": (summary.get("hit_summary") or {}).get("total_hits"),
                    "selftest_fail0": summary.get("selftest_fail0"),
                    "error": summary.get("error"),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
