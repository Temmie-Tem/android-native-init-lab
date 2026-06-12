#!/usr/bin/env python3
"""Run V2204 read-only file_operations KASLR slide anchor capture.

Flow:
1. build static AArch64 helper;
2. ensure bridge control path;
3. install helper under /cache/bin;
4. run a90_bpf_file_ops_anchor against this helper's own open files;
5. compare runtime f_op pointers with the bit-exact stock System.map;
6. run selftest and write a private JSON summary.

This is read-only observation.  It does not flash, reboot, touch Wi-Fi, execute
probe_write_user, attach cgroup BPF, or write kernel/firmware/partition state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import a90_transport as transport


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_DIR = REPO_ROOT / "workspace/public/src/native-init/helpers"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_SYSTEM_MAP = REPO_ROOT / "workspace/private/runs/kernel/v2197-stock-kallsyms/System.map"
REMOTE_ANCHOR = "/cache/bin/a90_bpf_file_ops_anchor"
REMOTE_TOYBOX = "/cache/bin/busybox"

SUMMARY_RE = re.compile(r"^summary\s+(?P<body>.+)$", re.MULTILINE)
ANCHOR_RE = re.compile(r"^anchor\s+(?P<body>.+)$", re.MULTILINE)
OFFSET_RE = re.compile(r"^offsets\s+(?P<body>.+)$", re.MULTILINE)

EXPECTED_SYMBOLS = {
    "fd0_fop": ("null_fops",),
    "fd1_fop": ("zero_fops",),
    "fd2_fop": ("version_proc_fops", "proc_reg_file_ops", "proc_reg_file_ops_no_compat"),
}


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def format_signed_hex(value: int) -> str:
    if value < 0:
        return f"-0x{-value:x}"
    return f"0x{value:x}"


def run_host(out_dir: Path,
             steps: list[StepResult],
             name: str,
             command: list[str],
             *,
             timeout: float = 120.0,
             allow_error: bool = False) -> str:
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
    result = StepResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        elapsed_sec=round(elapsed, 3),
        stdout_path=str(stdout_path.relative_to(REPO_ROOT)),
        stderr_path=str(stderr_path.relative_to(REPO_ROOT)),
    )
    steps.append(result)
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(
            f"{name} failed rc={completed.returncode}\n"
            f"stdout={stdout_path}\nstderr={stderr_path}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout


def build_helper(out_dir: Path,
                 steps: list[StepResult],
                 *,
                 source: Path,
                 output_name: str,
                 cc: str,
                 strip: str) -> Path:
    output = out_dir / output_name
    run_host(
        out_dir,
        steps,
        f"build-{output_name}",
        [cc, "-static", "-Os", "-Wall", "-Wextra", "-o", str(output), str(source)],
        timeout=120,
    )
    run_host(out_dir, steps, f"strip-{output_name}", [strip, str(output)], timeout=60)
    return output


def install_helper(args: argparse.Namespace,
                   out_dir: Path,
                   steps: list[StepResult],
                   name: str,
                   local_binary: Path,
                   remote_binary: str) -> None:
    target_dir = str(Path(remote_binary).parent).replace("\\", "/")
    target_name = Path(remote_binary).name
    tmp_target = f"{target_dir}/.{target_name}.tmp.{os.getpid()}.{int(time.time())}"
    local_hash = sha256_file(local_binary)

    a90ctl(args, out_dir, steps, f"install-{name}-mkdir", ["mkdir", target_dir], timeout=30, allow_error=True)
    a90ctl(args, out_dir, steps, f"install-{name}-cleanup", ["run", args.toybox, "rm", "-f", tmp_target], timeout=30, allow_error=True)

    port = args.transfer_port
    args.transfer_port += 1
    receive_script = (
        f"{shlex.quote(args.toybox)} nc -l -p {port} -w 3 > {shlex.quote(tmp_target)}; "
        "echo a90_install_nc_rc=$?"
    )
    receive_command = [
        sys.executable,
        str(SCRIPT_DIR / "a90ctl.py"),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(args.transfer_timeout),
        "run",
        args.toybox,
        "sh",
        "-c",
        receive_script,
    ]
    stdout_path = out_dir / f"install-{name}-receive.stdout.txt"
    stderr_path = out_dir / f"install-{name}-receive.stderr.txt"
    result_holder: dict[str, Any] = {}

    def receive_thread() -> None:
        started = time.monotonic()
        completed = subprocess.run(
            receive_command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.transfer_timeout + 10,
        )
        stdout_path.write_text(completed.stdout)
        stderr_path.write_text(completed.stderr)
        result_holder["step"] = StepResult(
            name=f"install-{name}-receive",
            command=receive_command,
            returncode=completed.returncode,
            elapsed_sec=round(time.monotonic() - started, 3),
            stdout_path=str(stdout_path.relative_to(REPO_ROOT)),
            stderr_path=str(stderr_path.relative_to(REPO_ROOT)),
        )
        result_holder["stdout"] = completed.stdout
        result_holder["stderr"] = completed.stderr

    thread = threading.Thread(target=receive_thread, daemon=True)
    thread.start()
    time.sleep(args.transfer_delay)

    with socket.create_connection((args.device_ip, port), timeout=args.connect_timeout) as sock:
        with local_binary.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sock.sendall(chunk)
        sock.shutdown(socket.SHUT_WR)

    thread.join(args.transfer_timeout + 15)
    if thread.is_alive():
        raise RuntimeError(f"install {name}: receive command did not finish")
    steps.append(result_holder["step"])
    if not result_holder["step"].ok or "a90_install_nc_rc=0" not in result_holder.get("stdout", ""):
        raise RuntimeError(f"install {name}: receive failed\n{result_holder.get('stdout', '')}\n{result_holder.get('stderr', '')}")

    a90ctl(args, out_dir, steps, f"install-{name}-chmod", ["run", args.toybox, "chmod", "755", tmp_target], timeout=30)
    sha_output = a90ctl(args, out_dir, steps, f"install-{name}-sha", ["run", args.toybox, "sha256sum", tmp_target], timeout=30)
    if local_hash not in sha_output:
        raise RuntimeError(f"install {name}: sha mismatch local={local_hash}\n{sha_output}")
    a90ctl(args, out_dir, steps, f"install-{name}-mv", ["run", args.toybox, "mv", "-f", tmp_target, remote_binary], timeout=30)


def a90ctl(args: argparse.Namespace,
           out_dir: Path,
           steps: list[StepResult],
           name: str,
           argv: list[str],
           *,
           timeout: float = 60.0,
           allow_error: bool = False) -> str:
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


def tcpctl_run(args: argparse.Namespace,
               out_dir: Path,
               steps: list[StepResult],
               name: str,
               argv: list[str],
               *,
               timeout: float,
               allow_error: bool = False) -> str:
    return a90ctl(args, out_dir, steps, name, ["run", *argv], timeout=timeout, allow_error=allow_error)


def parse_key_values(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in body.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = value
    return fields


def parse_int(value: str) -> int:
    if value.startswith(("0x", "0X")):
        return int(value, 16)
    return int(value, 10)


def parse_probe_stdout(stdout: str) -> dict[str, Any]:
    summary_match = SUMMARY_RE.search(stdout)
    if not summary_match:
        return {"summary": {}, "anchors": {}, "offsets": {}}
    summary_fields = parse_key_values(summary_match.group("body"))
    anchors_match = ANCHOR_RE.search(stdout)
    offsets_match = OFFSET_RE.search(stdout)
    summary: dict[str, Any] = {}
    for key, value in summary_fields.items():
        summary[key] = parse_int(value)
    return {
        "summary": summary,
        "anchors": parse_key_values(anchors_match.group("body")) if anchors_match else {},
        "offsets": {
            key: parse_int(value)
            for key, value in parse_key_values(offsets_match.group("body")).items()
        } if offsets_match else {},
    }


def parse_system_map(path: Path) -> dict[str, int]:
    symbols: dict[str, int] = {}
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            address = int(parts[0], 16)
        except ValueError:
            continue
        symbols.setdefault(parts[2], address)
    return symbols


def analyze_fops(probe: dict[str, Any], symbols: dict[str, int]) -> dict[str, Any]:
    summary = probe.get("summary") or {}
    observations: list[dict[str, Any]] = []
    slides: dict[int, list[str]] = {}
    for field, expected_names in EXPECTED_SYMBOLS.items():
        runtime = int(summary.get(field, 0))
        candidates: list[dict[str, Any]] = []
        for name in expected_names:
            static = symbols.get(name)
            if static is None or runtime == 0:
                continue
            slide = runtime - static
            candidates.append({
                "symbol": name,
                "static": f"0x{static:016x}",
                "runtime": f"0x{runtime:016x}",
                "slide": slide,
                "slide_hex": format_signed_hex(slide),
            })
            slides.setdefault(slide, []).append(f"{field}:{name}")
        observations.append({
            "field": field,
            "runtime": f"0x{runtime:016x}",
            "expected_symbols": list(expected_names),
            "candidates": candidates,
        })

    best_slide: int | None = None
    best_sources: list[str] = []
    for slide, sources in sorted(slides.items(), key=lambda item: (-len(item[1]), item[0])):
        if best_slide is None:
            best_slide = slide
            best_sources = sources
    unique_slides = [
        {
            "slide": slide,
            "slide_hex": format_signed_hex(slide),
            "sources": sources,
            "count": len(sources),
        }
        for slide, sources in sorted(slides.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    exact = best_slide is not None and len(best_sources) >= 2
    return {
        "observations": observations,
        "unique_slides": unique_slides,
        "best_slide": None if best_slide is None else best_slide,
        "best_slide_hex": None if best_slide is None else format_signed_hex(best_slide),
        "best_sources": best_sources,
        "exact_slide": exact,
        "reason": (
            "at least two known file_operations anchors agree"
            if exact else
            "fewer than two independent file_operations anchors agreed"
        ),
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
        "read_only_bpf": True,
        "probe_write_user_executed": False,
        "cgroup_attach": False,
    }


def render_report(summary: dict[str, Any]) -> str:
    analysis = summary.get("analysis") or {}
    probe_summary = (summary.get("probe") or {}).get("summary") or {}
    lines = [
        "# Native Init V2204 File-Operations Slide Anchor",
        "",
        "## Decision",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Pass: `{str(summary.get('pass')).lower()}`",
        f"- Exact slide: `{str(analysis.get('exact_slide')).lower()}`",
        f"- Best slide: `{analysis.get('best_slide_hex')}`",
        f"- Reason: {analysis.get('reason')}",
        f"- Phase timer contract: `{summary.get('phase_timer_contract')}`",
        f"- Residual-state contract: `{summary.get('residual_state_contract')}`",
        "",
        "## Method",
        "",
        "- Opens `/dev/null`, `/dev/zero`, and `/proc/version` read-only in the helper process.",
        "- Uses `sched:sched_switch` plus `bpf_get_current_task()` filtered to the helper pid.",
        "- Reads `task->files->fdt->fd[]->file->f_op` with `bpf_probe_read` only.",
        "- Compares runtime f_op pointers against the bit-exact stock `System.map` recovered in V2197.",
        "",
        "## Result",
        "",
        f"- Samples: `{probe_summary.get('count')}`",
        f"- Read errors: `{probe_summary.get('read_errors')}`",
        f"- task/files/fdt: `0x{int(probe_summary.get('task', 0)):016x}` / `0x{int(probe_summary.get('files', 0)):016x}` / `0x{int(probe_summary.get('fdt', 0)):016x}`",
        "",
        "| Field | Runtime f_op | Candidate slides |",
        "| --- | --- | --- |",
    ]
    for observation in analysis.get("observations") or []:
        candidates = ", ".join(
            f"`{item['symbol']}` {item['slide_hex']}"
            for item in observation.get("candidates") or []
        ) or "none"
        lines.append(f"| `{observation['field']}` | `{observation['runtime']}` | {candidates} |")
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
    parser.add_argument("--label", default="v2204-file-ops-anchor")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18084)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
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
    steps: list[StepResult] = []
    system_map = Path(args.system_map)
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "system_map": str(system_map.relative_to(REPO_ROOT)) if system_map.is_relative_to(REPO_ROOT) else str(system_map),
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
        },
    }

    try:
        with transport.phase(summary, "symbol_map_load"):
            symbols = parse_system_map(system_map)
            missing = sorted({name for names in EXPECTED_SYMBOLS.values() for name in names if name not in symbols})
            if "null_fops" in missing or "zero_fops" in missing:
                raise RuntimeError(f"required fops symbols missing from {system_map}: {missing}")

        with transport.phase(summary, "preflight_bridge_status"):
            run_host(out_dir, steps, "bridge-status", [
                sys.executable,
                str(SCRIPT_DIR / "a90_bridge.py"),
                "status",
                "--json",
            ], timeout=30, allow_error=True)
            a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=60, allow_error=True)

        with transport.phase(summary, "build_helper"):
            build_dir = out_dir / "build"
            build_dir.mkdir(parents=True, exist_ok=True)
            anchor_bin = build_dir / "a90_bpf_file_ops_anchor"
            if not args.skip_build:
                anchor_bin = build_helper(
                    build_dir,
                    steps,
                    source=HELPER_DIR / "a90_bpf_file_ops_anchor.c",
                    output_name="a90_bpf_file_ops_anchor",
                    cc=args.cc,
                    strip=args.strip,
                )
            summary["build"] = {
                "anchor_local": str(anchor_bin.relative_to(REPO_ROOT)),
                "anchor_sha256": sha256_file(anchor_bin),
            }

        if not args.skip_install:
            with transport.phase(summary, "install_helper"):
                install_helper(args, out_dir, steps, "file-ops-anchor", anchor_bin, REMOTE_ANCHOR)

        with transport.phase(summary, "anchor_check"):
            check_stdout = tcpctl_run(args, out_dir, steps, "file-ops-anchor-check-only", [
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
        with transport.phase(summary, "file_ops_anchor_live"):
            probe_stdout = tcpctl_run(
                args,
                out_dir,
                steps,
                "file-ops-anchor-live",
                helper_args,
                timeout=max(60, args.duration_ms / 1000.0 + 30),
            )
            if "result=v2204-file-ops-anchor-complete" not in probe_stdout:
                raise RuntimeError(f"live helper did not complete cleanly:\n{probe_stdout}")
            probe = parse_probe_stdout(probe_stdout)

        with transport.phase(summary, "analysis"):
            analysis = analyze_fops(probe, symbols)

        with transport.phase(summary, "post_selftest"):
            selftest = a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        summary.update({
            "decision": "v2204-file-ops-anchor-exact-slide" if analysis["exact_slide"] else "v2204-file-ops-anchor-no-exact-slide",
            "probe": probe,
            "analysis": analysis,
            "selftest_fail0": "fail=0" in selftest,
        })
        summary["pass"] = summary["decision"] == "v2204-file-ops-anchor-exact-slide" and summary["selftest_fail0"]
    except Exception as exc:
        summary["decision"] = "v2204-file-ops-anchor-failed"
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
        artifact_started = time.monotonic()
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        if "analysis" in summary:
            report_path = REPO_ROOT / "docs/reports/NATIVE_INIT_V2204_FILE_OPS_ANCHOR_2026-06-12.md"
            report_path.write_text(render_report(summary))
            summary["report_path"] = str(report_path.relative_to(REPO_ROOT))
        transport.add_total_phase(summary, "artifact_write", artifact_started, ok=True)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(json.dumps({
            "decision": summary.get("decision"),
            "pass": summary.get("pass"),
            "out_dir": summary.get("out_dir"),
            "report_path": summary.get("report_path"),
            "best_slide": (summary.get("analysis") or {}).get("best_slide_hex"),
            "exact_slide": (summary.get("analysis") or {}).get("exact_slide"),
            "samples": ((summary.get("probe") or {}).get("summary") or {}).get("count"),
            "read_errors": ((summary.get("probe") or {}).get("summary") or {}).get("read_errors"),
            "selftest_fail0": summary.get("selftest_fail0"),
            "error": summary.get("error"),
        }, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
