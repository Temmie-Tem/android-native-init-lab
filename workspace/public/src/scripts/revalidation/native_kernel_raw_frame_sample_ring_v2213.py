#!/usr/bin/env python3
"""Run V2213 bounded-large raw frame sample-ring capture.

V2213 prepares the "try longer, but with convergence metrics" path after V2212.
It keeps the run read-only and bounded while allowing helper-pid or all-task
sched_switch sampling.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_DIR = REPO_ROOT / "workspace/public/src/native-init/helpers"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
REMOTE_HELPER = "/cache/bin/a90_bpf_raw_frame_sample_ring"
REMOTE_TOYBOX = "/cache/bin/busybox"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2213_RAW_FRAME_SAMPLE_RING_LIVE_2026-06-12.md"

sys.path.insert(0, str(SCRIPT_DIR))
import native_kernel_file_ops_anchor_v2204 as base  # noqa: E402


STATS_RE = re.compile(r"^stats\s+(?P<body>.+)$", re.MULTILINE)
SAMPLE_RE = re.compile(r"^sample\s+(?P<body>.+)$", re.MULTILINE)
OFFSETS_RE = re.compile(r"^offsets\s+(?P<body>.+)$", re.MULTILINE)
SAMPLES_RE = re.compile(r"^samples\s+(?P<body>.+)$", re.MULTILINE)

KERNEL_TEXT_MIN = 0xFFFFFF8008000000
KERNEL_TEXT_MAX = 0xFFFFFF800C000000
KERNEL_VA_MIN = 0xFFFFFF8000000000
KERNEL_VA_MAX = 0xFFFFFFFFFFFFFFFF


def parse_int(value: str) -> int:
    if value.startswith(("0x", "0X")):
        return int(value, 16)
    return int(value, 10)


def parse_helper_stdout(stdout: str) -> dict[str, Any]:
    stats_match = STATS_RE.search(stdout)
    offsets_match = OFFSETS_RE.search(stdout)
    samples_match = SAMPLES_RE.search(stdout)
    parsed: dict[str, Any] = {
        "stats": {},
        "offsets": {},
        "sample_meta": {},
        "samples": [],
        "raw_stdout": stdout,
    }
    if offsets_match:
        parsed["offsets"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(offsets_match.group("body")).items()
        }
    if stats_match:
        parsed["stats"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(stats_match.group("body")).items()
        }
    if samples_match:
        parsed["sample_meta"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(samples_match.group("body")).items()
        }
    for match in SAMPLE_RE.finditer(stdout):
        fields = base.parse_key_values(match.group("body"))
        row: dict[str, Any] = {}
        for key, value in fields.items():
            if key == "comm":
                row[key] = value
            else:
                row[key] = parse_int(value)
        parsed["samples"].append(row)
    return parsed


def classify_addr(value: int) -> dict[str, Any]:
    return {
        "hex": f"0x{value:016x}",
        "nonzero": value != 0,
        "kernel_va": KERNEL_VA_MIN <= value <= KERNEL_VA_MAX,
        "kernel_text": KERNEL_TEXT_MIN <= value < KERNEL_TEXT_MAX,
        "aligned_4": value % 4 == 0,
        "aligned_16": value % 16 == 0,
    }


def analyze_probe(probe: dict[str, Any]) -> dict[str, Any]:
    samples = probe.get("samples") or []
    fields = [
        "thread_pc",
        "fp_slot_next",
        "fp_slot_raw_lr",
        "fp2_slot_next",
        "fp2_slot_raw_lr",
        "sp_slot8",
    ]
    unique: dict[str, set[int]] = {field: set() for field in fields}
    counts = {
        "printed_samples": len(samples),
        "walkable_fp_next": 0,
        "walkable_fp2_next": 0,
        "raw_lr_kernel_text": 0,
        "raw_lr_kernel_va_nontext": 0,
        "raw_lr_nonzero": 0,
        "thread_pc_kernel_text": 0,
    }
    comms: set[str] = set()
    pids: set[int] = set()
    for sample in samples:
        comm = str(sample.get("comm", ""))
        if comm:
            comms.add(comm)
        pids.add(int(sample.get("pid", 0)))
        for field in fields:
            value = int(sample.get(field, 0))
            if value:
                unique[field].add(value)
        if int(sample.get("fp_slot_next", 0)) != 0:
            counts["walkable_fp_next"] += 1
        if int(sample.get("fp2_slot_next", 0)) != 0:
            counts["walkable_fp2_next"] += 1
        raw_lr = int(sample.get("fp_slot_raw_lr", 0))
        raw_meta = classify_addr(raw_lr)
        if raw_lr:
            counts["raw_lr_nonzero"] += 1
        if raw_meta["kernel_text"]:
            counts["raw_lr_kernel_text"] += 1
        elif raw_meta["kernel_va"] and raw_lr:
            counts["raw_lr_kernel_va_nontext"] += 1
        if classify_addr(int(sample.get("thread_pc", 0)))["kernel_text"]:
            counts["thread_pc_kernel_text"] += 1

    stats = probe.get("stats") or {}
    sample_meta = probe.get("sample_meta") or {}
    occupied = int(sample_meta.get("occupied", 0))
    capacity = int(sample_meta.get("capacity", 0) or stats.get("sample_capacity", 0))
    saturation = occupied >= capacity if capacity else False
    return {
        "counts": counts,
        "unique_counts": {field: len(values) for field, values in unique.items()},
        "unique_preview": {
            field: [f"0x{value:016x}" for value in sorted(values)[:12]]
            for field, values in unique.items()
        },
        "unique_comms": sorted(comms)[:32],
        "unique_comm_count": len(comms),
        "unique_pid_count": len({pid for pid in pids if pid}),
        "sample_ring_saturated": saturation,
        "occupied_samples": occupied,
        "capacity": capacity,
        "convergence_hint": (
            "ring saturated; rerun with shorter staged durations or lower print limit for convergence comparison"
            if saturation else
            "ring not saturated; longer duration can still add information"
        ),
    }


def render_report(summary: dict[str, Any]) -> str:
    probe = summary.get("probe") or {}
    stats = probe.get("stats") or {}
    analysis = summary.get("analysis") or {}
    counts = analysis.get("counts") or {}
    unique_counts = analysis.get("unique_counts") or {}
    lines = [
        "# Native Init V2213 Raw Frame Sample Ring",
        "",
        "## Decision",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Pass: `{str(summary.get('pass')).lower()}`",
        f"- Total samples observed: `{stats.get('count')}`",
        f"- Printed samples parsed: `{counts.get('printed_samples')}`",
        f"- Occupied ring slots: `{analysis.get('occupied_samples')}` / `{analysis.get('capacity')}`",
        f"- Selftest fail=0: `{str(summary.get('selftest_fail0')).lower()}`",
        "",
        "## Method",
        "",
        "- Uses bounded BPF array maps: one stats row plus a 1024-slot sample ring.",
        "- Supports helper-pid mode and `--all-tasks` mode; no unbounded kernel storage is used.",
        "- Samples `thread.cpu_context.{fp,sp,pc}` plus raw `fp/sp` slots with `bpf_probe_read` only.",
        "- Does not use `probe_write_user`, cgroup attach, Wi-Fi, flash, reboot, or partition/firmware writes.",
        "",
        "## Metrics",
        "",
        f"- Unique comms: `{analysis.get('unique_comm_count')}`",
        f"- Unique pids: `{analysis.get('unique_pid_count')}`",
        f"- Walkable `fp_slot_next`: `{counts.get('walkable_fp_next')}`",
        f"- Walkable `fp2_slot_next`: `{counts.get('walkable_fp2_next')}`",
        f"- Raw LR nonzero: `{counts.get('raw_lr_nonzero')}`",
        f"- Raw LR in kernel text: `{counts.get('raw_lr_kernel_text')}`",
        f"- Raw LR kernel VA outside text: `{counts.get('raw_lr_kernel_va_nontext')}`",
        f"- Thread PC in kernel text: `{counts.get('thread_pc_kernel_text')}`",
        "",
        "| Field | Unique Count | Preview |",
        "| --- | ---: | --- |",
    ]
    for field in ["thread_pc", "fp_slot_raw_lr", "fp_slot_next", "fp2_slot_raw_lr", "sp_slot8"]:
        preview = ", ".join((analysis.get("unique_preview") or {}).get(field) or []) or "none"
        lines.append(f"| `{field}` | {unique_counts.get(field, 0)} | {preview} |")
    lines.extend([
        "",
        "## Convergence",
        "",
        f"- Ring saturated: `{str(analysis.get('sample_ring_saturated')).lower()}`",
        f"- Hint: {analysis.get('convergence_hint')}",
        "",
        "## Safety",
        "",
    ])
    for key, value in (summary.get("safety") or {}).items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend([
        "",
        "## Evidence",
        "",
        f"- Private run: `{summary.get('out_dir')}`",
        f"- Helper SHA-256: `{(summary.get('build') or {}).get('helper_sha256')}`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2213-raw-frame-sample-ring")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18113)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    parser.add_argument("--duration-ms", type=int, default=1000)
    parser.add_argument("--print-limit", type=int, default=256)
    parser.add_argument("--all-tasks", action="store_true")
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--verbose-helper", action="store_true")
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{base.now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[base.StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "args": {
            "duration_ms": args.duration_ms,
            "print_limit": args.print_limit,
            "all_tasks": args.all_tasks,
        },
        "steps": [],
        "safety": {
            "read_only_bpf": True,
            "probe_write_user_executed": False,
            "cgroup_attach": False,
            "wifi_action": False,
            "flash_reboot": False,
            "partition_or_firmware_write": False,
        },
    }

    try:
        base.run_host(out_dir, steps, "bridge-status", [
            sys.executable,
            str(SCRIPT_DIR / "a90_bridge.py"),
            "status",
            "--json",
        ], timeout=30, allow_error=True)
        base.a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=60, allow_error=True)

        build_dir = out_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        helper_bin = build_dir / "a90_bpf_raw_frame_sample_ring"
        if not args.skip_build:
            helper_bin = base.build_helper(
                build_dir,
                steps,
                source=HELPER_DIR / "a90_bpf_raw_frame_sample_ring.c",
                output_name="a90_bpf_raw_frame_sample_ring",
                cc=args.cc,
                strip=args.strip,
            )
        summary["build"] = {
            "helper_local": str(helper_bin.relative_to(REPO_ROOT)),
            "helper_sha256": base.sha256_file(helper_bin),
        }

        if not args.skip_install:
            base.install_helper(args, out_dir, steps, "raw-frame-sample-ring", helper_bin, REMOTE_HELPER)

        check_args = [REMOTE_HELPER, "--duration-ms", str(args.duration_ms), "--print-limit", str(args.print_limit)]
        if args.all_tasks:
            check_args.append("--all-tasks")
        check_stdout = base.tcpctl_run(args, out_dir, steps, "raw-frame-sample-ring-check-only", check_args, timeout=60)
        if "result=check-only" not in check_stdout:
            raise RuntimeError(f"check-only did not complete cleanly:\n{check_stdout}")

        helper_args = [
            REMOTE_HELPER,
            "--duration-ms",
            str(args.duration_ms),
            "--print-limit",
            str(args.print_limit),
            "--allow-attach",
        ]
        if args.all_tasks:
            helper_args.append("--all-tasks")
        if args.verbose_helper:
            helper_args.append("--verbose")
        probe_stdout = base.tcpctl_run(
            args,
            out_dir,
            steps,
            "raw-frame-sample-ring-live",
            helper_args,
            timeout=max(60, args.duration_ms / 1000.0 + 30),
        )
        if "result=v2213-raw-frame-sample-ring-complete" not in probe_stdout:
            raise RuntimeError(f"live helper did not complete cleanly:\n{probe_stdout}")

        probe = parse_helper_stdout(probe_stdout)
        analysis = analyze_probe(probe)
        selftest = base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        total = int((probe.get("stats") or {}).get("count", 0))
        printed = len(probe.get("samples") or [])
        if total > 0 and printed > 0:
            decision = "v2213-raw-frame-sample-ring-captured"
        elif total > 0:
            decision = "v2213-samples-observed-not-printed"
        else:
            decision = "v2213-no-sched-switch-samples"
        summary.update({
            "decision": decision,
            "probe": probe,
            "analysis": analysis,
            "selftest_fail0": "fail=0" in selftest,
        })
        summary["pass"] = decision == "v2213-raw-frame-sample-ring-captured" and summary["selftest_fail0"]
    except Exception as exc:
        summary["decision"] = "v2213-raw-frame-sample-ring-failed"
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
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        if "probe" in summary:
            REPORT_PATH.write_text(render_report(summary))
            summary["report_path"] = str(REPORT_PATH.relative_to(REPO_ROOT))
            (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "decision": summary.get("decision"),
        "pass": summary.get("pass"),
        "out_dir": summary.get("out_dir"),
        "report_path": summary.get("report_path"),
        "selftest_fail0": summary.get("selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
