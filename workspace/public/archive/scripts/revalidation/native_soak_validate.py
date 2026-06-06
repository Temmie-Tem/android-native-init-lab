#!/usr/bin/env python3
"""Run bounded non-destructive native-init soak checks through a90ctl."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"

DEFAULT_COMMANDS = [
    "version",
    "status",
    "bootstatus",
    "selftest verbose",
    "runtime",
    "storage",
    "service list",
    "diag",
    "wififeas gate",
    "statushud",
    "autohud 2",
    "screenmenu",
    "hide",
    "netservice status",
]


@dataclass(frozen=True)
class CheckResult:
    cycle: int
    command: str
    rc: int
    output: str
    duration_sec: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--cycles", type=int, default=3, help="number of command cycles")
    parser.add_argument("--sleep", type=float, default=1.0, help="seconds between cycles")
    parser.add_argument("--timeout", type=float, default=45.0, help="per-command timeout seconds")
    parser.add_argument(
        "--expect-version",
        default="A90 Linux init 0.9.48 (v148)",
        help="expected version banner in the version command",
    )
    parser.add_argument("--out", default="tmp/soak/native-soak.txt", help="transcript path")
    parser.add_argument(
        "--command",
        action="append",
        dest="commands",
        help="override default command list; may be repeated",
    )
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
        *shlex.split(command),
    ]


def run_one(args: argparse.Namespace, cycle: int, command: str) -> CheckResult:
    started = time.monotonic()
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
    return CheckResult(cycle=cycle, command=command, rc=proc.returncode, output=proc.stdout, duration_sec=duration)


def validate_result(args: argparse.Namespace, result: CheckResult) -> list[str]:
    errors: list[str] = []
    output = result.output
    if result.rc != 0:
        errors.append(f"command returned rc={result.rc}")
    if "A90P1 END" not in output:
        errors.append("missing A90P1 END frame")
    if "status=ok" not in output:
        errors.append("missing status=ok")
    if result.command == "version" and args.expect_version not in output:
        errors.append(f"missing expected version {args.expect_version!r}")
    if result.command.startswith("selftest") and "fail=0" not in output:
        errors.append("selftest failure count is not zero")
    if result.command == "status" and "selftest: pass=" not in output:
        errors.append("status output missing selftest summary")
    return errors


def append_result(lines: list[str], result: CheckResult, errors: list[str]) -> None:
    lines.append(f"== cycle {result.cycle} :: {result.command} :: rc={result.rc} :: {result.duration_sec:.3f}s ==\n")
    lines.append(result.output.rstrip() + "\n")
    if errors:
        lines.append("ERRORS:\n")
        for error in errors:
            lines.append(f"- {error}\n")
    lines.append("\n")


def main() -> int:
    args = parse_args()
    if args.cycles < 1:
        raise SystemExit("--cycles must be >= 1")
    commands = args.commands or DEFAULT_COMMANDS
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    transcript: list[str] = []
    transcript.append("# Native Init Soak Validation\n")
    transcript.append(f"expect_version={args.expect_version}\n")
    transcript.append(f"cycles={args.cycles} sleep={args.sleep} timeout={args.timeout}\n")
    transcript.append("commands=" + ", ".join(commands) + "\n\n")

    failures = 0
    for cycle in range(1, args.cycles + 1):
        for command in commands:
            result = run_one(args, cycle, command)
            errors = validate_result(args, result)
            append_result(transcript, result, errors)
            if errors:
                failures += 1
                out_path.write_text("".join(transcript))
                print(f"FAIL cycle={cycle} command={command}: {'; '.join(errors)}")
                print(out_path)
                return 1
        if cycle != args.cycles and args.sleep > 0:
            time.sleep(args.sleep)

    out_path.write_text("".join(transcript))
    print(f"PASS cycles={args.cycles} commands={len(commands)}")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
