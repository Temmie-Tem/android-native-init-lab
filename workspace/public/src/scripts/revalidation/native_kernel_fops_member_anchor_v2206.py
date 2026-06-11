#!/usr/bin/env python3
"""Run V2206 read-only file_operations member pointer text-anchor capture.

V2204 captured the f_op object pointers for `/dev/null` and `/dev/zero`.  V2206
uses the extended helper to also read selected members inside those fops objects
(`llseek`, `read`, `write`, `read_iter`, `write_iter`, `mmap`,
`get_unmapped_area`, `splice_write`).  Those member values are text function
pointers and are used as a cleaner text-side anchor candidate.

This is read-only observation.  It does not flash, reboot, touch Wi-Fi, execute
probe_write_user, attach cgroup BPF, or write kernel/firmware/partition state.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_DIR = REPO_ROOT / "workspace/public/src/native-init/helpers"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_SYSTEM_MAP = REPO_ROOT / "workspace/private/runs/kernel/v2197-stock-kallsyms/System.map"
REMOTE_ANCHOR = "/cache/bin/a90_bpf_file_ops_anchor"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2206_FOPS_MEMBER_TEXT_ANCHOR_2026-06-12.md"

sys.path.insert(0, str(SCRIPT_DIR))
import native_kernel_file_ops_anchor_v2204 as base  # noqa: E402


EXPECTED_MEMBER_SYMBOLS = {
    "fd0_llseek": ("null_lseek",),
    "fd0_read": ("read_null",),
    "fd0_write": ("write_null",),
    "fd0_read_iter": ("read_iter_null",),
    "fd0_write_iter": ("write_iter_null",),
    "fd0_splice_write": ("splice_write_null",),
    "fd1_llseek": ("null_lseek",),
    "fd1_write": ("write_null",),
    "fd1_read_iter": ("read_iter_zero",),
    "fd1_write_iter": ("write_iter_null",),
    "fd1_mmap": ("mmap_zero",),
    "fd1_get_unmapped_area": ("get_unmapped_area_zero",),
}


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def format_signed_hex(value: int) -> str:
    if value < 0:
        return f"-0x{-value:x}"
    return f"0x{value:x}"


def analyze_members(probe: dict[str, Any], symbols: dict[str, int]) -> dict[str, Any]:
    summary = probe.get("summary") or {}
    observations: list[dict[str, Any]] = []
    slides: dict[int, list[str]] = {}
    for field, names in EXPECTED_MEMBER_SYMBOLS.items():
        runtime = int(summary.get(field, 0))
        candidates: list[dict[str, Any]] = []
        for name in names:
            static = symbols.get(name)
            if static is None or runtime == 0:
                continue
            slide = runtime - static
            candidates.append({
                "symbol": name,
                "runtime": f"0x{runtime:016x}",
                "static": f"0x{static:016x}",
                "slide": slide,
                "slide_hex": format_signed_hex(slide),
            })
            slides.setdefault(slide, []).append(f"{field}:{name}")
        observations.append({
            "field": field,
            "runtime": f"0x{runtime:016x}",
            "expected_symbols": list(names),
            "candidates": candidates,
        })
    ranked_slides = [
        {
            "slide": slide,
            "slide_hex": format_signed_hex(slide),
            "sources": sources,
            "count": len(sources),
        }
        for slide, sources in sorted(slides.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    best = ranked_slides[0] if ranked_slides else None
    exact = best is not None and int(best["count"]) >= 4
    return {
        "observations": observations,
        "ranked_slides": ranked_slides,
        "best_slide": None if best is None else best["slide"],
        "best_slide_hex": None if best is None else best["slide_hex"],
        "best_sources": [] if best is None else best["sources"],
        "exact_text_member_slide": exact,
        "reason": (
            "at least four known fops member function pointers agree"
            if exact else
            "fewer than four known fops member function pointers agreed"
        ),
    }


def render_report(summary: dict[str, Any]) -> str:
    object_analysis = summary.get("object_analysis") or {}
    member_analysis = summary.get("member_analysis") or {}
    lines = [
        "# Native Init V2206 Fops Member Text Anchor",
        "",
        "## Decision",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Pass: `{str(summary.get('pass')).lower()}`",
        f"- Object/fops slide: `{object_analysis.get('best_slide_hex')}`",
        f"- Member/text slide: `{member_analysis.get('best_slide_hex')}`",
        f"- Member exact: `{str(member_analysis.get('exact_text_member_slide')).lower()}`",
        f"- Reason: {member_analysis.get('reason')}",
        "",
        "## Interpretation",
        "",
        "- Capture succeeded when `selftest fail=0` is true; `member_exact=false` is a classifier result, not a transport/runtime failure.",
        "- The fops object pointers still agree on the V2204 object/rodata slide.",
        "- The fops member function pointers are readable, but they do not point to known real function entries under one uniform text slide.",
        "- Treat the member values as a CFP/JOPP stub layer until the stub-to-real-target decode is implemented.",
        "",
        "## Method",
        "",
        "- Opens `/dev/null` and `/dev/zero` read-only in the helper process.",
        "- Reads `current->files->fdt->fd[]->file->f_op` and selected fops members with `bpf_probe_read` only.",
        "- Compares member runtime pointers against known `drivers/char/mem.c` functions in the bit-exact stock `System.map`.",
        "",
        "## Member Function Pointers",
        "",
        "| Field | Runtime | Candidate slides |",
        "| --- | --- | --- |",
    ]
    for observation in member_analysis.get("observations") or []:
        candidates = ", ".join(
            f"`{item['symbol']}` {item['slide_hex']}"
            for item in observation.get("candidates") or []
        ) or "none"
        lines.append(f"| `{observation['field']}` | `{observation['runtime']}` | {candidates} |")
    lines.extend([
        "",
        "## Ranked Member Slides",
        "",
    ])
    for item in member_analysis.get("ranked_slides") or []:
        lines.append(f"- `{item['slide_hex']}` count={item['count']} sources=`{', '.join(item['sources'])}`")
    lines.extend([
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
        f"- System.map: `{summary.get('system_map')}`",
        f"- Helper SHA-256: `{(summary.get('build') or {}).get('anchor_sha256')}`",
        f"- Selftest fail=0: `{str(summary.get('selftest_fail0')).lower()}`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2206-fops-member-anchor")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18085)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--toybox", default=base.REMOTE_TOYBOX)
    parser.add_argument("--duration-ms", type=int, default=160)
    parser.add_argument("--system-map", default=str(DEFAULT_SYSTEM_MAP))
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--verbose-helper", action="store_true")
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[base.StepResult] = []
    system_map = Path(args.system_map)
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": rel(out_dir),
        "system_map": rel(system_map),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "steps": [],
        "safety": {
            "read_only_bpf": True,
            "probe_write_user_executed": False,
            "cgroup_attach": False,
            "wifi_action": False,
            "flash_reboot": False,
        },
    }

    try:
        symbols = base.parse_system_map(system_map)
        missing = sorted({
            name
            for names in EXPECTED_MEMBER_SYMBOLS.values()
            for name in names
            if name not in symbols
        })
        if missing:
            raise RuntimeError(f"required member symbols missing from {system_map}: {missing}")

        base.run_host(out_dir, steps, "bridge-status", [
            sys.executable,
            str(SCRIPT_DIR / "a90_bridge.py"),
            "status",
            "--json",
        ], timeout=30, allow_error=True)
        base.a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=60, allow_error=True)

        build_dir = out_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        anchor_bin = build_dir / "a90_bpf_file_ops_anchor"
        if not args.skip_build:
            anchor_bin = base.build_helper(
                build_dir,
                steps,
                source=HELPER_DIR / "a90_bpf_file_ops_anchor.c",
                output_name="a90_bpf_file_ops_anchor",
                cc=args.cc,
                strip=args.strip,
            )
        summary["build"] = {
            "anchor_local": rel(anchor_bin),
            "anchor_sha256": base.sha256_file(anchor_bin),
        }

        if not args.skip_install:
            base.install_helper(args, out_dir, steps, "fops-member-anchor", anchor_bin, REMOTE_ANCHOR)

        check_stdout = base.tcpctl_run(args, out_dir, steps, "fops-member-check-only", [
            REMOTE_ANCHOR,
            "--duration-ms",
            str(args.duration_ms),
        ], timeout=60)
        if "result=check-only" not in check_stdout:
            raise RuntimeError(f"check-only did not complete cleanly:\n{check_stdout}")

        helper_args = [
            REMOTE_ANCHOR,
            "--duration-ms",
            str(args.duration_ms),
            "--allow-attach",
        ]
        if args.verbose_helper:
            helper_args.append("--verbose")
        probe_stdout = base.tcpctl_run(
            args,
            out_dir,
            steps,
            "fops-member-live",
            helper_args,
            timeout=max(60, args.duration_ms / 1000.0 + 30),
        )
        if "result=v2204-file-ops-anchor-complete" not in probe_stdout:
            raise RuntimeError(f"live helper did not complete cleanly:\n{probe_stdout}")

        probe = base.parse_probe_stdout(probe_stdout)
        object_analysis = base.analyze_fops(probe, symbols)
        member_analysis = analyze_members(probe, symbols)
        selftest = base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)

        summary.update({
            "decision": "v2206-fops-member-text-slide-captured" if member_analysis["exact_text_member_slide"] else "v2206-fops-member-pointer-stub-layer-observed",
            "probe": probe,
            "object_analysis": object_analysis,
            "member_analysis": member_analysis,
            "selftest_fail0": "fail=0" in selftest,
        })
        summary["pass"] = bool(summary["selftest_fail0"])
    except Exception as exc:
        summary["decision"] = "v2206-fops-member-anchor-failed"
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
        if "member_analysis" in summary:
            REPORT_PATH.write_text(render_report(summary))
            summary["report_path"] = rel(REPORT_PATH)
            (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(json.dumps({
            "decision": summary.get("decision"),
            "pass": summary.get("pass"),
            "out_dir": summary.get("out_dir"),
            "report_path": summary.get("report_path"),
            "object_slide": (summary.get("object_analysis") or {}).get("best_slide_hex"),
            "member_slide": (summary.get("member_analysis") or {}).get("best_slide_hex"),
            "member_exact": (summary.get("member_analysis") or {}).get("exact_text_member_slide"),
            "selftest_fail0": summary.get("selftest_fail0"),
            "error": summary.get("error"),
        }, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
