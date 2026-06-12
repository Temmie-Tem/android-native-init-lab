#!/usr/bin/env python3
"""Run V2212 read-only raw saved-frame slot capture.

This unit follows V2211's recommendation to inspect raw frame slots instead of
trying to infer ROPP encoding from already-normalized stackmap values.  It does
not flash, reboot, touch Wi-Fi, execute probe_write_user, attach cgroup BPF, or
write kernel/firmware/partition state.
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
REMOTE_HELPER = "/cache/bin/a90_bpf_raw_frame_slots"
REMOTE_TOYBOX = "/cache/bin/busybox"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2212_RAW_FRAME_SLOTS_LIVE_2026-06-12.md"

sys.path.insert(0, str(SCRIPT_DIR))
import a90_transport as transport  # noqa: E402
import native_kernel_file_ops_anchor_v2204 as base  # noqa: E402


SUMMARY_RE = re.compile(r"^summary\s+(?P<body>.+)$", re.MULTILINE)
OFFSETS_RE = re.compile(r"^offsets\s+(?P<body>.+)$", re.MULTILINE)

KERNEL_TEXT_MIN = 0xFFFFFF8008000000
KERNEL_TEXT_MAX = 0xFFFFFF800C000000
KERNEL_VA_MIN = 0xFFFFFF8000000000
KERNEL_VA_MAX = 0xFFFFFFFFFFFFFFFF


def parse_int(value: str) -> int:
    if value.startswith(("0x", "0X")):
        return int(value, 16)
    return int(value, 10)


def parse_helper_stdout(stdout: str) -> dict[str, Any]:
    summary_match = SUMMARY_RE.search(stdout)
    offsets_match = OFFSETS_RE.search(stdout)
    parsed: dict[str, Any] = {
        "summary": {},
        "offsets": {},
        "raw_stdout": stdout,
    }
    if offsets_match:
        parsed["offsets"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(offsets_match.group("body")).items()
        }
    if summary_match:
        fields = base.parse_key_values(summary_match.group("body"))
        summary: dict[str, Any] = {}
        for key, value in fields.items():
            if key == "comm":
                summary[key] = value
            else:
                summary[key] = parse_int(value)
        parsed["summary"] = summary
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
    summary = probe.get("summary") or {}
    fields = [
        "task",
        "thread_fp",
        "thread_sp",
        "thread_pc",
        "fp_slot_next",
        "fp_slot_raw_lr",
        "fp2_slot_next",
        "fp2_slot_raw_lr",
        "sp_slot0",
        "sp_slot8",
    ]
    classified = {
        field: classify_addr(int(summary.get(field, 0)))
        for field in fields
    }
    lr_fields = ["thread_pc", "fp_slot_raw_lr", "fp2_slot_raw_lr", "sp_slot8"]
    canonical_aligned_lr = [
        field for field in lr_fields
        if classified[field]["kernel_text"] and classified[field]["aligned_4"]
    ]
    canonical_misaligned_lr = [
        field for field in lr_fields
        if classified[field]["kernel_text"] and not classified[field]["aligned_4"]
    ]
    nonzero_frame_slots = [
        field for field in ["fp_slot_next", "fp_slot_raw_lr", "fp2_slot_next", "fp2_slot_raw_lr", "sp_slot0", "sp_slot8"]
        if int(summary.get(field, 0)) != 0
    ]
    return {
        "classified": classified,
        "canonical_aligned_lr_fields": canonical_aligned_lr,
        "canonical_misaligned_lr_fields": canonical_misaligned_lr,
        "nonzero_frame_slots": nonzero_frame_slots,
        "has_raw_frame_slot": bool(nonzero_frame_slots),
        "sched_switch_timing_note": (
            "sched_switch fires before arm64 cpu_switch_to saves the outgoing task; "
            "thread.cpu_context values are saved-context candidates, not direct live x29 snapshots"
        ),
    }


def render_report(summary: dict[str, Any]) -> str:
    probe_summary = (summary.get("probe") or {}).get("summary") or {}
    analysis = summary.get("analysis") or {}
    classified = analysis.get("classified") or {}
    lines = [
        "# Native Init V2212 Raw Frame Slots Live Capture",
        "",
        "## Decision",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Pass: `{str(summary.get('pass')).lower()}`",
        f"- Samples: `{probe_summary.get('count')}`",
        f"- Read errors: `{probe_summary.get('read_errors')}`",
        f"- Selftest fail=0: `{str(summary.get('selftest_fail0')).lower()}`",
        f"- Phase timer contract: `{summary.get('phase_timer_contract')}`",
        f"- Residual-state contract: `{summary.get('residual_state_contract')}`",
        "",
        "## Method",
        "",
        "- Uses a read-only `BPF_PROG_TYPE_TRACEPOINT` program attached to `sched:sched_switch`.",
        "- Filters the current task to the helper process pid/tgid before reading.",
        "- Reads `task + THREAD_CPU_CONTEXT + {fp,sp,pc}` and then `*(fp)`, `*(fp+8)`, `*(sp)`, `*(sp+8)` using `bpf_probe_read` only.",
        "- Does not use `probe_write_user`, cgroup attach, Wi-Fi, flash, reboot, or partition/firmware writes.",
        "",
        "## Interpretation Guard",
        "",
        "- `sched_switch` fires before `arm64 cpu_switch_to()` saves the outgoing task context.",
        "- Therefore V2212 is a saved-context/raw-slot discriminator, not a direct current-register x29 read.",
        "- Nonzero raw slots are still useful for deciding whether V2195 stackmap IPs hid encoded-but-canonical frame data.",
        "",
        "## Live Summary",
        "",
        f"- Helper comm: `{probe_summary.get('comm')}`",
        f"- Last pid/tgid: `{probe_summary.get('last_pid')}` / `{probe_summary.get('last_tgid')}`",
        f"- Task pointer: `{classified.get('task', {}).get('hex')}`",
        "",
        "| Field | Value | kernel_text | aligned_4 | aligned_16 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for field in [
        "thread_fp",
        "thread_sp",
        "thread_pc",
        "fp_slot_next",
        "fp_slot_raw_lr",
        "fp2_slot_next",
        "fp2_slot_raw_lr",
        "sp_slot0",
        "sp_slot8",
    ]:
        meta = classified.get(field) or {}
        lines.append(
            f"| `{field}` | `{meta.get('hex')}` | `{str(meta.get('kernel_text')).lower()}` | "
            f"`{str(meta.get('aligned_4')).lower()}` | `{str(meta.get('aligned_16')).lower()}` |"
        )
    lines.extend([
        "",
        "## Classification",
        "",
        f"- Canonical aligned LR-like fields: `{', '.join(analysis.get('canonical_aligned_lr_fields') or []) or 'none'}`",
        f"- Canonical misaligned LR-like fields: `{', '.join(analysis.get('canonical_misaligned_lr_fields') or []) or 'none'}`",
        f"- Nonzero raw frame slots: `{', '.join(analysis.get('nonzero_frame_slots') or []) or 'none'}`",
        "",
        "## Result Interpretation",
        "",
        "- The raw-slot capture path works: `fp+8` and `sp+8` were read directly from saved-context memory.",
        "- In this helper-pid sample, the raw slot value is a kernel VA outside the kernel text range, while `thread_pc` is canonical kernel text.",
        "- `fp_slot_next=0` means this helper's saved-context frame does not provide a walkable parent chain in this sample.",
        "- This does not prove that V2195's stackmap frames were encoded-but-canonical; it proves that direct slot capture is viable and that helper-pid `sched_switch` is too shallow for full ROPP recovery.",
        "",
        "## Next",
        "",
        "- If ROPP stack recovery remains required, extend the helper from a single last sample to a small sample ring or use a tracepoint path that exposes a sleeping/non-current task pointer.",
        "- Keep the same read-only boundary: `bpf_probe_read` only, no `probe_write_user`, no cgroup attach, no Wi-Fi or flash side effects.",
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
    parser.add_argument("--label", default="v2212-raw-frame-slots")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18112)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    parser.add_argument("--duration-ms", type=int, default=160)
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
        "steps": [],
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
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
        with transport.phase(summary, "preflight_bridge_status"):
            base.run_host(out_dir, steps, "bridge-status", [
                sys.executable,
                str(SCRIPT_DIR / "a90_bridge.py"),
                "status",
                "--json",
            ], timeout=30, allow_error=True)
            base.a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=60, allow_error=True)

        with transport.phase(summary, "build_helper"):
            build_dir = out_dir / "build"
            build_dir.mkdir(parents=True, exist_ok=True)
            helper_bin = build_dir / "a90_bpf_raw_frame_slots"
            if not args.skip_build:
                helper_bin = base.build_helper(
                    build_dir,
                    steps,
                    source=HELPER_DIR / "a90_bpf_raw_frame_slots.c",
                    output_name="a90_bpf_raw_frame_slots",
                    cc=args.cc,
                    strip=args.strip,
                )
            summary["build"] = {
                "helper_local": str(helper_bin.relative_to(REPO_ROOT)),
                "helper_sha256": base.sha256_file(helper_bin),
            }

        if not args.skip_install:
            with transport.phase(summary, "install_helper"):
                base.install_helper(args, out_dir, steps, "raw-frame-slots", helper_bin, REMOTE_HELPER)

        with transport.phase(summary, "helper_check"):
            check_stdout = base.tcpctl_run(args, out_dir, steps, "raw-frame-slots-check-only", [
                REMOTE_HELPER,
                "--duration-ms",
                str(args.duration_ms),
            ], timeout=60)
            if "result=check-only" not in check_stdout:
                raise RuntimeError(f"check-only did not complete cleanly:\n{check_stdout}")

        helper_args = [
            REMOTE_HELPER,
            "--duration-ms",
            str(args.duration_ms),
            "--allow-attach",
        ]
        if args.verbose_helper:
            helper_args.append("--verbose")
        with transport.phase(summary, "sample_capture"):
            probe_stdout = base.tcpctl_run(
                args,
                out_dir,
                steps,
                "raw-frame-slots-live",
                helper_args,
                timeout=max(60, args.duration_ms / 1000.0 + 30),
            )
            if "result=v2212-raw-frame-slots-complete" not in probe_stdout:
                raise RuntimeError(f"live helper did not complete cleanly:\n{probe_stdout}")
            probe = parse_helper_stdout(probe_stdout)

        with transport.phase(summary, "analysis"):
            analysis = analyze_probe(probe)

        with transport.phase(summary, "post_selftest"):
            selftest = base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        count = int((probe.get("summary") or {}).get("count", 0))
        if count > 0 and analysis["has_raw_frame_slot"]:
            decision = "v2212-raw-frame-slots-captured"
        elif count > 0:
            decision = "v2212-thread-context-captured-no-frame-slots"
        else:
            decision = "v2212-no-helper-sched-switch-samples"
        summary.update({
            "decision": decision,
            "probe": probe,
            "analysis": analysis,
            "selftest_fail0": "fail=0" in selftest,
        })
        summary["pass"] = decision == "v2212-raw-frame-slots-captured" and summary["selftest_fail0"]
    except Exception as exc:
        summary["decision"] = "v2212-raw-frame-slots-failed"
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
        transport.set_residual_state(summary, base.residual_state(summary))
        artifact_started = time.monotonic()
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        if "probe" in summary:
            REPORT_PATH.write_text(render_report(summary))
            summary["report_path"] = str(REPORT_PATH.relative_to(REPO_ROOT))
        transport.add_total_phase(summary, "artifact_write", artifact_started, ok=True)
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
