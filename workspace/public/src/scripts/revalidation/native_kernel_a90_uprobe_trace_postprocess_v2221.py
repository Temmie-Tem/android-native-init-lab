#!/usr/bin/env python3
"""Run current-window a90 trace collector and V2220 postprocess integration.

This is a read-only integration wrapper. It does not create or enable tracefs
events itself; it delegates live current-window collection to the V2219
collector, then parses that collector's summary through the V2220 helper-summary
parser. The expected current-window result can be no-hit; the purpose is to
prove the handoff and artifact contract before an approved boot-window run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"

sys.path.insert(0, str(SCRIPT_DIR))
import a90_transport as transport  # noqa: E402


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


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_step(
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    command: list[str],
    *,
    timeout: float = 120.0,
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
        stdout_path=rel(stdout_path),
        stderr_path=rel(stderr_path),
    )
    steps.append(step)
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(f"{name} failed rc={completed.returncode}: {stderr_path}")
    return completed.stdout


def parse_stdout_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2221-a90-uprobe-trace-postprocess")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--wait-sec", type=int, default=0)
    parser.add_argument("--tail-lines", type=int, default=4096)
    return parser.parse_args()


def residual_state(summary: dict[str, Any]) -> dict[str, Any]:
    selftest_ok = bool(summary.get("collector_selftest_fail0"))
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
        "residual_risk": "collector-selftest-incomplete" if cleanup_required else "none",
        "wifi_scan_connect": False,
        "credentials_used": False,
        "dhcp_routes_ping": False,
        "tracefs_control_write": False,
        "bpf_attach": False,
        "probe_write_user_executed": False,
    }


def main() -> int:
    args = parse_args()
    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": rel(out_dir),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "steps": [],
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "safety": {
            "host_orchestration_only": True,
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
        with transport.phase(summary, "v2219_collector"):
            collector_stdout = run_step(
                out_dir,
                steps,
                "v2219-collector",
                [
                    sys.executable,
                    str(SCRIPT_DIR / "native_kernel_a90_uprobe_trace_buffer_collector_v2219.py"),
                    "--label",
                    "v2221-current-window-collector",
                    "--bridge-host",
                    args.bridge_host,
                    "--bridge-port",
                    str(args.bridge_port),
                    "--timeout",
                    str(args.timeout),
                    "--wait-sec",
                    str(args.wait_sec),
                    "--tail-lines",
                    str(args.tail_lines),
                ],
                timeout=max(180.0, args.timeout * 6),
            )
            collector_brief = parse_stdout_json(collector_stdout)
            collector_out_dir = REPO_ROOT / str(collector_brief["out_dir"])
            collector_summary_path = collector_out_dir / "summary.json"
            collector_summary = load_json(collector_summary_path)

        parser_out_dir = out_dir / "v2220-parser"
        with transport.phase(summary, "v2220_parser"):
            parser_stdout = run_step(
                out_dir,
                steps,
                "v2220-parser",
                [
                    sys.executable,
                    str(SCRIPT_DIR / "a90_kernel_v2220_helper_summary_trace_parser.py"),
                    "--input",
                    rel(collector_summary_path),
                    "--out-dir",
                    rel(parser_out_dir),
                    "--label",
                    "v2221-current-window-parser",
                    "--allow-nohit",
                ],
                timeout=120.0,
            )
            parser_summary = parse_stdout_json(parser_stdout)

        summary.update(
            {
                "decision": (
                    "v2221-collector-parser-integrated-current-window-hits"
                    if parser_summary.get("hit_event_total", 0) > 0
                    else "v2221-collector-parser-integrated-current-window-nohit"
                ),
                "pass": bool(collector_summary.get("pass")) and bool(parser_summary.get("pass")),
                "collector_summary_path": rel(collector_summary_path),
                "parser_summary_path": rel(parser_out_dir / "summary.json"),
                "collector_decision": collector_summary.get("decision"),
                "collector_event_exists_count": collector_summary.get("event_exists_count"),
                "collector_event_enabled_count": collector_summary.get("event_enabled_count"),
                "collector_total_hits": (collector_summary.get("hit_summary") or {}).get("total_hits"),
                "collector_selftest_fail0": collector_summary.get("selftest_fail0"),
                "parser_decision": parser_summary.get("decision"),
                "parser_event_total": parser_summary.get("event_total"),
                "parser_hit_event_total": parser_summary.get("hit_event_total"),
                "parser_key_hit_event_total": parser_summary.get("key_hit_event_total"),
                "parser_v2219_nohit_sources": parser_summary.get("v2219_nohit_sources"),
            }
        )
    except Exception as exc:  # noqa: BLE001
        summary["decision"] = "v2221-collector-parser-integration-failed"
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
                    "collector_decision": summary.get("collector_decision"),
                    "collector_total_hits": summary.get("collector_total_hits"),
                    "parser_decision": summary.get("parser_decision"),
                    "parser_hit_event_total": summary.get("parser_hit_event_total"),
                    "selftest_fail0": summary.get("collector_selftest_fail0"),
                    "error": summary.get("error"),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
