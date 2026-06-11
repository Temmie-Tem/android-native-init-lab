#!/usr/bin/env python3
"""Run V2202 read-only timer_start timer-object histogram capture.

Flow:
1. build static AArch64 helper;
2. ensure bridge control path;
3. install helper under /cache/bin;
4. run a90_bpf_timer_object_histogram for top function/object rows;
5. run selftest and write a private JSON summary.

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


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_DIR = REPO_ROOT / "workspace/public/src/native-init/helpers"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
REMOTE_HISTOGRAM = "/cache/bin/a90_bpf_timer_object_histogram"
REMOTE_TOYBOX = "/cache/bin/busybox"

ROW_RE = re.compile(r"^row\s+(?P<body>.+)$", re.MULTILINE)
STACK_RE = re.compile(r"^stack_ip rank=(?P<rank>\d+) index=(?P<index>\d+) value=0x(?P<value>[0-9a-fA-F]+) kernelish=(?P<kernelish>[01])", re.MULTILINE)
ROWS_TOTAL_RE = re.compile(r"^rows_total=(?P<total>\d+) rows_printed=(?P<printed>\d+)", re.MULTILINE)


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


def tcpctl_run(args: argparse.Namespace,
               out_dir: Path,
               steps: list[StepResult],
               name: str,
               argv: list[str],
               *,
               timeout: float,
               allow_error: bool = False) -> str:
    return a90ctl(args, out_dir, steps, name, ["run", *argv], timeout=timeout, allow_error=allow_error)


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


def parse_histogram(stdout: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for match in ROW_RE.finditer(stdout):
        fields = parse_key_values(match.group("body"))
        row: dict[str, Any] = {}
        for key, value in fields.items():
            if key in {"function", "last_timer", "last_flags", "obj_entry_next", "obj_entry_pprev", "obj_function", "obj_data", "obj_flags"}:
                row[key] = value.lower()
            elif key == "comm":
                row[key] = value
            else:
                row[key] = parse_int(value)
        rows.append(row)
    total_match = ROWS_TOTAL_RE.search(stdout)
    stacks: dict[int, list[dict[str, Any]]] = {}
    for match in STACK_RE.finditer(stdout):
        rank = int(match.group("rank"), 10)
        stacks.setdefault(rank, []).append({
            "index": int(match.group("index"), 10),
            "value": "0x" + match.group("value").lower(),
            "kernelish": match.group("kernelish") == "1",
        })
    for rank, stack_ips in stacks.items():
        if 0 <= rank < len(rows):
            rows[rank]["stack_ips"] = stack_ips
    return {
        "rows_total": int(total_match.group("total"), 10) if total_match else len(rows),
        "rows_printed": int(total_match.group("printed"), 10) if total_match else len(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2202-timer-object-histogram")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18083)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    parser.add_argument("--duration", type=int, default=8)
    parser.add_argument("--top", type=int, default=16)
    parser.add_argument("--max-rows", type=int, default=4096)
    parser.add_argument("--dump-stacks", action="store_true")
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
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
        run_host(out_dir, steps, "bridge-status", [
            sys.executable,
            str(SCRIPT_DIR / "a90_bridge.py"),
            "status",
            "--json",
        ], timeout=30, allow_error=True)
        a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=60, allow_error=True)

        build_dir = out_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        histogram_bin = build_dir / "a90_bpf_timer_object_histogram"
        if not args.skip_build:
            histogram_bin = build_helper(
                build_dir,
                steps,
                source=HELPER_DIR / "a90_bpf_timer_object_histogram.c",
                output_name="a90_bpf_timer_object_histogram",
                cc=args.cc,
                strip=args.strip,
            )
        summary["build"] = {
            "histogram_local": str(histogram_bin.relative_to(REPO_ROOT)),
            "histogram_sha256": sha256_file(histogram_bin),
        }

        if not args.skip_install:
            install_helper(args, out_dir, steps, "timer-histogram", histogram_bin, REMOTE_HISTOGRAM)

        tcpctl_run(args, out_dir, steps, "histogram-check-only", [
            REMOTE_HISTOGRAM,
            "--top",
            str(args.top),
            "--max-rows",
            str(args.max_rows),
        ], timeout=60)

        histogram_args = [
            REMOTE_HISTOGRAM,
            "--duration",
            str(args.duration),
            "--top",
            str(args.top),
            "--max-rows",
            str(args.max_rows),
            "--busy-observe",
            "--allow-attach",
        ]
        if args.dump_stacks:
            histogram_args.append("--dump-stacks")
        histogram_stdout = tcpctl_run(
            args,
            out_dir,
            steps,
            "timer-object-histogram",
            histogram_args,
            timeout=args.duration + 90,
        )
        histogram = parse_histogram(histogram_stdout)

        selftest = a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        summary.update({
            "decision": "v2202-timer-object-histogram-captured" if histogram["rows"] else "v2202-timer-object-histogram-no-rows",
            "histogram": histogram,
            "selftest_fail0": "fail=0" in selftest,
        })
        summary["pass"] = summary["decision"] == "v2202-timer-object-histogram-captured" and summary["selftest_fail0"]
    except Exception as exc:
        summary["decision"] = "v2202-timer-object-histogram-failed"
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
        print(json.dumps({
            "decision": summary.get("decision"),
            "pass": summary.get("pass"),
            "out_dir": summary.get("out_dir"),
            "rows_total": summary.get("histogram", {}).get("rows_total"),
            "rows_printed": summary.get("histogram", {}).get("rows_printed"),
            "top_function": (summary.get("histogram", {}).get("rows") or [{}])[0].get("function"),
            "top_count": (summary.get("histogram", {}).get("rows") or [{}])[0].get("count"),
            "selftest_fail0": summary.get("selftest_fail0"),
            "error": summary.get("error"),
        }, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
