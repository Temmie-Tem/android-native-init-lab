#!/usr/bin/env python3
"""Run a bounded release-candidate native-init soak sequence."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
INTEGRATED_VALIDATE = REPO_ROOT / "scripts" / "revalidation" / "native_integrated_validate.py"

DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.48 (v148)"

UI_COMMANDS = [
    "screenmenu",
    "status",
    "policycheck run",
    "hide",
    "statushud",
    "autohud 2",
    "hide",
]

STORAGE_COMMANDS = [
    "runtime",
    "helpers status",
    "userland status",
    "storage",
    "mountsd status",
]

EXPOSURE_COMMANDS = [
    "exposure guard",
    "netservice status",
    "rshell audit",
    "service list",
    "service status autohud",
    "service status tcpctl",
    "service status rshell",
]

FINAL_COMMANDS = [
    "bootstatus",
    "diag summary",
    "status",
]


@dataclass
class SoakResult:
    phase: str
    cycle: int
    command: str
    rc: int
    protocol_rc: int | None
    protocol_status: str
    duration_sec: float
    errors: list[str]
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=45.0, help="per-command timeout seconds")
    parser.add_argument("--cycles", type=int, default=10, help="focused soak cycles")
    parser.add_argument("--sleep", type=float, default=0.5, help="seconds between focused cycles")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", default="tmp/soak/native-rc-v148.txt", help="text transcript path")
    parser.add_argument("--json-out", default=None, help="optional JSON summary path")
    parser.add_argument("--keep-going", action="store_true", help="continue after failures")
    parser.add_argument("--skip-integrated", action="store_true", help="skip native_integrated_validate.py phase")
    parser.add_argument("--with-ncm-ping", action="store_true", help="also ping 192.168.7.2 if host NCM is already configured")
    parser.add_argument("--device-ip", default="192.168.7.2", help="device NCM IPv4 address for opt-in ping")
    return parser.parse_args()


def a90ctl_command(args: argparse.Namespace, command: str) -> list[str]:
    return [
        sys.executable,
        str(A90CTL),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(int(args.timeout)),
        "--json",
        *shlex.split(command),
    ]


def integrated_command(args: argparse.Namespace, out_path: Path) -> list[str]:
    json_path = out_path.with_suffix(".integrated.json")
    text_path = out_path.with_suffix(".integrated.txt")
    return [
        sys.executable,
        str(INTEGRATED_VALIDATE),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(int(args.timeout)),
        "--expect-version",
        args.expect_version,
        "--out",
        str(text_path),
        "--json-out",
        str(json_path),
    ]


def run_cmdv1(args: argparse.Namespace, phase: str, cycle: int, command: str) -> SoakResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            a90ctl_command(args, command),
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout + 5,
            check=False,
        )
        duration = time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = (exc.stdout or "") + (exc.stderr or "")
        return SoakResult(phase, cycle, command, 124, None, "timeout", args.timeout + 5, ["host timeout"], text)

    errors: list[str] = []
    protocol_rc: int | None = None
    protocol_status = "missing"
    text = proc.stdout
    try:
        payload = json.loads(proc.stdout)
        end = payload.get("end", {})
        if isinstance(end, dict):
            protocol_status = str(end.get("status", "missing"))
            protocol_rc = int(str(end.get("rc", "1")), 0)
        text = str(payload.get("text", proc.stdout))
    except (TypeError, ValueError) as exc:
        errors.append(f"invalid a90ctl json: {exc}")

    if proc.returncode != 0:
        errors.append(f"a90ctl rc={proc.returncode}")
    if "A90P1 END" not in text:
        errors.append("missing A90P1 END frame")
    if protocol_status != "ok":
        errors.append(f"protocol status={protocol_status}")
    if protocol_rc != 0:
        errors.append(f"protocol rc={protocol_rc}")

    validate_semantics(args, command, text, errors)
    return SoakResult(phase, cycle, command, proc.returncode, protocol_rc, protocol_status, duration, errors, text)


def require(text: str, needle: str, errors: list[str], message: str) -> None:
    if needle not in text:
        errors.append(message)


def validate_semantics(args: argparse.Namespace, command: str, text: str, errors: list[str]) -> None:
    if command == "version":
        require(text, args.expect_version, errors, "version missing expected banner")
    elif command == "status":
        for needle in ("selftest: pass=", "pid1guard:", "exposure: guard=", "runtime:"):
            require(text, needle, errors, f"status missing {needle}")
    elif command == "bootstatus":
        for needle in ("selftest:", "pid1guard:", "exposure:", "runtime:"):
            require(text, needle, errors, f"bootstatus missing {needle}")
    elif command.startswith("selftest"):
        require(text, "fail=0", errors, "selftest failure count is not zero")
    elif command.startswith("pid1guard"):
        require(text, "fail=0", errors, "pid1guard failure count is not zero")
    elif command == "exposure guard":
        require(text, "guard=ok", errors, "exposure guard is not ok")
        require(text, "fail=0", errors, "exposure failure count is not zero")
    elif command.startswith("policycheck"):
        require(text, "fail=0", errors, "policycheck failure count is not zero")
    elif command == "screenmenu":
        require(text, "show requested", errors, "screenmenu did not report show request")
    elif command == "hide":
        require(text, "hide requested", errors, "hide did not report hide request")
    elif command == "mountsd status":
        require(text, "mountsd:", errors, "mountsd status output missing prefix")
    elif command == "netservice status":
        require(text, "netservice:", errors, "netservice status output missing prefix")
    elif command == "rshell audit":
        require(text, "rshell-audit:", errors, "rshell audit output missing prefix")
        if "token_value=" in text:
            errors.append("rshell audit may expose token value")


def append_result(lines: list[str], result: SoakResult) -> None:
    verdict = "PASS" if not result.errors else "FAIL"
    lines.append(
        f"== {verdict} phase={result.phase} cycle={result.cycle} "
        f"cmd={result.command!r} host_rc={result.rc} proto_rc={result.protocol_rc} "
        f"status={result.protocol_status} duration={result.duration_sec:.3f}s ==\n"
    )
    lines.append(result.text.rstrip() + "\n")
    if result.errors:
        lines.append("ERRORS:\n")
        for error in result.errors:
            lines.append(f"- {error}\n")
    lines.append("\n")


def run_integrated(args: argparse.Namespace, out_path: Path, lines: list[str]) -> tuple[int, float, str]:
    started = time.monotonic()
    proc = subprocess.run(
        integrated_command(args, out_path),
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=(args.timeout + 5) * 30,
        check=False,
    )
    duration = time.monotonic() - started
    lines.append(f"== {'PASS' if proc.returncode == 0 else 'FAIL'} phase=integrated rc={proc.returncode} duration={duration:.3f}s ==\n")
    lines.append(proc.stdout.rstrip() + "\n\n")
    return proc.returncode, duration, proc.stdout


def run_ping(args: argparse.Namespace, lines: list[str]) -> tuple[int, float, str]:
    started = time.monotonic()
    proc = subprocess.run(
        ["ping", "-c", "3", "-W", "2", args.device_ip],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )
    duration = time.monotonic() - started
    lines.append(f"== {'PASS' if proc.returncode == 0 else 'FAIL'} phase=ncm-ping rc={proc.returncode} duration={duration:.3f}s ==\n")
    lines.append(proc.stdout.rstrip() + "\n\n")
    return proc.returncode, duration, proc.stdout


def run_phase(
    args: argparse.Namespace,
    phase: str,
    cycle: int,
    commands: list[str],
    transcript: list[str],
    results: list[SoakResult],
    out_path: Path,
) -> bool:
    ok = True
    for command in commands:
        result = run_cmdv1(args, phase, cycle, command)
        results.append(result)
        append_result(transcript, result)
        out_path.write_text("".join(transcript))
        if result.errors:
            ok = False
            if not args.keep_going:
                return False
    return ok


def main() -> int:
    args = parse_args()
    if args.cycles < 1:
        raise SystemExit("--cycles must be >= 1")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    transcript: list[str] = []
    results: list[SoakResult] = []
    transcript.append("# Native Init RC Soak\n")
    transcript.append(f"expect_version={args.expect_version}\n")
    transcript.append(f"cycles={args.cycles} timeout={args.timeout} sleep={args.sleep}\n")
    transcript.append(f"keep_going={args.keep_going} skip_integrated={args.skip_integrated} with_ncm_ping={args.with_ncm_ping}\n\n")

    overall_ok = True
    command_count = 0

    preflight = ["version", "status"]
    if not run_phase(args, "preflight", 0, preflight, transcript, results, out_path):
        overall_ok = False
    command_count += len(preflight)
    if not overall_ok and not args.keep_going:
        return finish(args, out_path, transcript, results, command_count, overall_ok)

    if not args.skip_integrated:
        rc, _duration, _text = run_integrated(args, out_path, transcript)
        out_path.write_text("".join(transcript))
        if rc != 0:
            overall_ok = False
            if not args.keep_going:
                return finish(args, out_path, transcript, results, command_count, overall_ok)

    for cycle in range(1, args.cycles + 1):
        for phase, commands in (
            ("ui", UI_COMMANDS),
            ("storage", STORAGE_COMMANDS),
            ("exposure", EXPOSURE_COMMANDS),
        ):
            if not run_phase(args, phase, cycle, commands, transcript, results, out_path):
                overall_ok = False
                if not args.keep_going:
                    return finish(args, out_path, transcript, results, command_count, overall_ok)
            command_count += len(commands)
        if cycle != args.cycles and args.sleep > 0:
            time.sleep(args.sleep)

    if args.with_ncm_ping:
        rc, _duration, _text = run_ping(args, transcript)
        out_path.write_text("".join(transcript))
        if rc != 0:
            overall_ok = False
            if not args.keep_going:
                return finish(args, out_path, transcript, results, command_count, overall_ok)

    if not run_phase(args, "final", 0, FINAL_COMMANDS, transcript, results, out_path):
        overall_ok = False
    command_count += len(FINAL_COMMANDS)

    return finish(args, out_path, transcript, results, command_count, overall_ok)


def finish(
    args: argparse.Namespace,
    out_path: Path,
    transcript: list[str],
    results: list[SoakResult],
    command_count: int,
    overall_ok: bool,
) -> int:
    failures = [item for item in results if item.errors]
    transcript.append(
        f"# Summary: status={'PASS' if overall_ok else 'FAIL'} "
        f"commands={len(results)} failures={len(failures)}\n"
    )
    out_path.write_text("".join(transcript))
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
    print(f"{'PASS' if overall_ok else 'FAIL'} commands={len(results)} failures={len(failures)}")
    print(out_path)
    if args.json_out:
        print(args.json_out)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
