#!/usr/bin/env python3
"""Audit CNSS daemon process residue without starting Wi-Fi services."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import run_cmdv1_command  # noqa: E402
from a90_kernel_tools import collect_host_metadata, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v260-cnss-zombie-audit")
DEFAULT_TARGETS = ("cnss-daemon", "cnss_diag")
PS_HEADER_RE = re.compile(r"^\s*PID\s+")


@dataclass(frozen=True)
class ProcessEntry:
    pid: int
    state: str
    name: str
    raw_name: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def normalize_process_name(raw_name: str) -> str:
    name = raw_name.strip()
    if name.startswith("[") and name.endswith("]") and len(name) >= 2:
        name = name[1:-1]
    return name


def parse_ps_stat_comm(text: str) -> list[ProcessEntry]:
    entries: list[ProcessEntry] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or PS_HEADER_RE.match(line):
            continue
        if line.startswith(("a90:/#", "A90P1 ", "[done]", "[exit]", "run: pid=")):
            continue
        parts = line.split(None, 2)
        if len(parts) != 3 or not parts[0].isdigit():
            continue
        entries.append(
            ProcessEntry(
                pid=int(parts[0]),
                state=parts[1],
                raw_name=parts[2].strip(),
                name=normalize_process_name(parts[2]),
            )
        )
    return entries


def summarize_cnss_processes(entries: list[ProcessEntry],
                             targets: tuple[str, ...] = DEFAULT_TARGETS) -> dict[str, Any]:
    target_set = set(targets)
    target_entries = [entry for entry in entries if entry.name in target_set]
    target_zombies = [entry for entry in target_entries if entry.state.startswith("Z")]
    target_running = [entry for entry in target_entries if not entry.state.startswith("Z")]
    return {
        "targets": list(targets),
        "process_count": len(entries),
        "target_process_count": len(target_entries),
        "target_zombie_count": len(target_zombies),
        "target_running_count": len(target_running),
        "target_processes": [asdict(entry) for entry in target_entries],
        "target_zombies": [asdict(entry) for entry in target_zombies],
        "target_running": [asdict(entry) for entry in target_running],
        "clean": not target_entries,
        "zombie_free": not target_zombies,
    }


def read_proc_status(args: argparse.Namespace, pid: int) -> dict[str, Any]:
    command = ["cat", f"/proc/{pid}/status"]
    try:
        result = run_cmdv1_command(args.host, args.port, args.timeout, command)
        return {
            "pid": pid,
            "ok": result.rc == 0 and result.status == "ok",
            "rc": result.rc,
            "status": result.status,
            "text": result.text,
        }
    except Exception as exc:  # noqa: BLE001 - audit preserves failure evidence
        return {
            "pid": pid,
            "ok": False,
            "rc": None,
            "status": "exception",
            "text": f"{type(exc).__name__}: {exc}\n",
        }


def render_summary(manifest: dict[str, Any]) -> str:
    summary = manifest["process_summary"]
    lines = [
        "# CNSS Zombie Audit\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- process_count: `{summary['process_count']}`\n",
        f"- target_process_count: `{summary['target_process_count']}`\n",
        f"- target_zombie_count: `{summary['target_zombie_count']}`\n",
        f"- target_running_count: `{summary['target_running_count']}`\n\n",
        "## Target Processes\n\n",
    ]
    if summary["target_processes"]:
        for item in summary["target_processes"]:
            lines.append(
                f"- pid=`{item['pid']}` state=`{item['state']}` "
                f"name=`{item['name']}` raw=`{item['raw_name']}`\n"
            )
    else:
        lines.append("- none\n")
    lines.extend(
        [
            "\n## Guardrails\n\n",
            "- read-only process audit only\n",
            "- no CNSS daemon start\n",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing\n",
        ]
    )
    return "".join(lines)


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    command = ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm"]
    status_records: list[dict[str, Any]] = []
    try:
        result = run_cmdv1_command(args.host, args.port, args.timeout, command)
        ps_text = result.text
        ps_ok = result.rc == 0 and result.status == "ok"
        ps_record = {
            "command": command,
            "ok": ps_ok,
            "rc": result.rc,
            "status": result.status,
        }
    except Exception as exc:  # noqa: BLE001 - audit preserves failure evidence
        ps_text = f"{type(exc).__name__}: {exc}\n"
        ps_ok = False
        ps_record = {
            "command": command,
            "ok": False,
            "rc": None,
            "status": "exception",
            "error": str(exc),
        }
    store.write_text("commands/ps-A-pid-stat-comm.txt", ps_text)

    entries = parse_ps_stat_comm(ps_text)
    target_tuple = tuple(args.target)
    process_summary = summarize_cnss_processes(entries, target_tuple)
    for item in process_summary["target_processes"]:
        status = read_proc_status(args, int(item["pid"]))
        status_records.append(status)
        store.write_text(f"proc/{item['pid']}-status.txt", status["text"])

    if not ps_ok:
        decision = "cnss-process-audit-incomplete"
        reason = "ps command failed"
        pass_ok = False
    elif process_summary["target_zombie_count"] > 0:
        decision = "cnss-zombie-present"
        reason = "one or more CNSS target processes are zombies under PID1"
        pass_ok = False
    elif process_summary["target_running_count"] > 0:
        decision = "cnss-process-still-running"
        reason = "one or more CNSS target processes are still non-zombie processes"
        pass_ok = False
    else:
        decision = "cnss-process-clean"
        reason = "no CNSS target processes found"
        pass_ok = True

    manifest = {
        "created": now_iso(),
        "mode": "cnss-zombie-audit",
        "out_dir": str(out_dir),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host_metadata": collect_host_metadata(),
        "ps": ps_record,
        "process_summary": process_summary,
        "proc_status": status_records,
        "guardrails": [
            "read-only process audit only",
            "no CNSS daemon start",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--toybox", default="/cache/bin/toybox")
    parser.add_argument("--target", action="append", default=list(DEFAULT_TARGETS))
    return parser.parse_args()


def main() -> int:
    manifest = run_audit(parse_args())
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"out_dir: {manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
